"""Task execution engine — runs queued tasks with workflow context chaining."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.task_planner import Task, TaskPlanner, TaskStatus


class TaskExecutor:
    """Executes tasks from the planner queue using registered agents."""

    def __init__(
        self,
        planner: TaskPlanner,
        on_task_complete: Optional[Callable[[Task], None]] = None,
        on_task_error: Optional[Callable[[Task, str], None]] = None,
    ) -> None:
        self.planner = planner
        self.agents: dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("shadowforge.executor")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_task_complete = on_task_complete
        self._on_task_error = on_task_error
        self._workflow_context: dict[str, dict[str, Any]] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents[agent.name] = agent
        self.logger.info("Registered agent: %s", agent.name)

    def unregister_agent(self, agent_name: str) -> None:
        self.agents.pop(agent_name, None)

    def set_workflow_context(self, parent_id: str, overrides: dict[str, Any]) -> None:
        """Seed workflow context with user-provided parameters."""
        self._workflow_context[parent_id] = dict(overrides)

    def _merge_params(self, task: Task) -> dict[str, Any]:
        """Merge workflow context into task params for chained execution."""
        merged = dict(task.params)
        if not task.parent_id:
            return merged

        ctx = self._workflow_context.get(task.parent_id, {})
        for key in ("target_text", "scan_path", "keys", "depth"):
            if key in ctx and key not in merged:
                merged[key] = ctx[key]

        if "target_text" in merged and "text" not in merged:
            merged["text"] = merged["target_text"]
        if "scan_path" in merged and "path" not in merged:
            merged["path"] = merged["scan_path"]

        if merged.get("use_context") or task.action in ("click", "click_at_target", "execute_keys"):
            if "click_position" in ctx:
                merged["x"] = ctx["click_position"]["x"]
                merged["y"] = ctx["click_position"]["y"]
            if "keys" in ctx and "keys" not in merged:
                merged["keys"] = ctx["keys"]

        return merged

    def _update_context(self, task: Task, result: dict[str, Any]) -> None:
        if not task.parent_id:
            return
        bucket = self._workflow_context.setdefault(task.parent_id, {})
        bucket.update(result)

    def execute_task(self, task: Task) -> dict[str, Any]:
        agent = self.agents.get(task.agent)
        if not agent:
            raise RuntimeError(f"No agent registered for: {task.agent}")

        self.planner.mark_running(task)
        self.logger.info("Executing task: %s [%s]", task.name, task.task_id)

        try:
            params = self._merge_params(task)
            if params.get("require_target") and task.parent_id:
                ctx = self._workflow_context.get(task.parent_id, {})
                if ctx.get("success") is False:
                    raise RuntimeError(
                        f"Target '{ctx.get('searched_text', '')}' not found on screen. "
                        "Ensure the text is visible before running Smart Automate."
                    )
            payload = {"action": task.action, "params": params, "task_id": task.task_id}
            result = agent.process(payload)
            self._update_context(task, result)
            self.planner.mark_completed(task, result)
            if self._on_task_complete:
                self._on_task_complete(task)
            return result
        except Exception as exc:
            error_msg = str(exc)
            self.planner.mark_failed(task, error_msg)
            self.logger.error("Task failed: %s — %s", task.name, error_msg)
            if self._on_task_error:
                self._on_task_error(task, error_msg)
            raise

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info("Task executor started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.info("Task executor stopped")

    def _run_loop(self) -> None:
        while self._running:
            task = self.planner.dequeue()
            if task:
                try:
                    self.execute_task(task)
                except Exception:
                    pass
            else:
                threading.Event().wait(0.5)

    @property
    def is_running(self) -> bool:
        return self._running