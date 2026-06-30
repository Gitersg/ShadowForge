"""Central orchestrator — coordinates agents, planning, and execution."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.message_bus import MessageBus
from shadowforge.core.plugin_manager import PluginManager
from shadowforge.core.task_executor import TaskExecutor
from shadowforge.core.task_planner import Task, TaskPlanner, TaskPriority
from shadowforge.utils.history import ActionHistory


class Orchestrator:
    """Top-level coordinator for the ShadowForge multi-agent system."""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.logger = logging.getLogger("shadowforge.orchestrator")
        self.message_bus = MessageBus()
        self.planner = TaskPlanner()
        self.history = ActionHistory()
        self.plugin_manager = PluginManager()
        self.executor = TaskExecutor(
            self.planner,
            on_task_complete=self._on_task_complete,
            on_task_error=self._on_task_error,
        )
        self._agents: dict[str, BaseAgent] = {}
        self._status_callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._last_folder_report: dict[str, Any] = {}
        self._last_quick_action_result: dict[str, Any] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent
        self.executor.register_agent(agent)
        agent.start()
        self.logger.info("Orchestrator registered agent: %s", agent.name)

    def load_plugins(self) -> list[BaseAgent]:
        agents = self.plugin_manager.load_all(self.message_bus)
        for agent in agents:
            self.register_agent(agent)
        return agents

    def run_workflow(
        self,
        workflow_name: str,
        overrides: Optional[dict[str, Any]] = None,
    ) -> list[Task]:
        tasks = self.planner.enqueue_workflow(workflow_name, overrides)
        if tasks and overrides and tasks[0].parent_id:
            self.executor.set_workflow_context(tasks[0].parent_id, overrides)
        self.logger.info("Queued workflow '%s' with %d tasks", workflow_name, len(tasks))
        self._notify_status()
        return tasks

    def run_folder_scan(self, folder_path: str, depth: int = 5) -> list[Task]:
        """Fresh folder scan — clears cache and queue, scans the exact path given."""
        self.planner.reset_for_new_run()
        file_agent = self._agents.get("file")
        if file_agent and hasattr(file_agent, "clear_scan_cache"):
            file_agent.clear_scan_cache()

        overrides = {
            "path": folder_path,
            "scan_path": folder_path,
            "depth": depth,
            "force_rescan": True,
        }
        workflow = "folder_scanner"
        tasks = self.planner.enqueue_workflow(workflow, overrides)
        if tasks and tasks[0].parent_id:
            self.executor.set_workflow_context(tasks[0].parent_id, overrides)
        self.logger.info("Folder scan queued for: %s", folder_path)
        self._notify_status()
        return tasks

    def run_quick_action(
        self,
        action_id: str,
        custom_text: str = "",
        custom_keys: str = "",
        countdown: int = 3,
    ) -> dict[str, Any]:
        """Run a reliable preset automation action."""
        automation = self._agents.get("automation")
        vision = self._agents.get("vision")
        if not automation:
            raise RuntimeError("Automation agent not available")

        if action_id == "screenshot_now" and vision:
            if countdown > 0:
                import time
                time.sleep(countdown)
            task = self.run_task("Screenshot", "vision", "capture_screen", execute_now=True)
            result = task.result or {}
            self._last_quick_action_result = result
            self._notify_status()
            return result

        task = self.run_task(
            name=f"Quick: {action_id}",
            agent="automation",
            action="run_quick_action",
            params={
                "action_id": action_id,
                "custom_text": custom_text,
                "custom_keys": custom_keys,
                "countdown": countdown,
            },
            execute_now=True,
        )
        result = task.result or {}
        self._last_quick_action_result = result
        self._notify_status()
        return result

    def run_task(
        self,
        name: str,
        agent: str,
        action: str,
        params: Optional[dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        execute_now: bool = False,
    ) -> Task:
        task = self.planner.create_custom_task(name, agent, action, params, priority)
        self.planner.enqueue(task)
        if execute_now:
            self.executor.execute_task(task)
        self._notify_status()
        return task

    def start_screen_monitor(self, interval_sec: float = 5.0) -> dict[str, Any]:
        """Start continuous screenshot capture at the given interval."""
        if not self.executor.is_running:
            self.start_executor()
        vision = self._agents.get("vision")
        if not vision or not hasattr(vision, "start_interval_capture"):
            raise RuntimeError("Vision agent not available")
        result = vision.start_interval_capture(interval_sec)
        self.history.record("vision", "interval_capture", "started", {"interval": interval_sec})
        self._notify_status()
        return result

    def stop_screen_monitor(self) -> dict[str, Any]:
        vision = self._agents.get("vision")
        if vision and hasattr(vision, "stop_interval_capture"):
            result = vision.stop_interval_capture()
            self.history.record("vision", "interval_capture", "stopped", result)
            self._notify_status()
            return result
        return {"success": True}

    def get_screen_monitor_status(self) -> dict[str, Any]:
        vision = self._agents.get("vision")
        if vision and hasattr(vision, "get_capture_status"):
            return vision.get_capture_status()
        return {"running": False, "capture_count": 0, "interval_sec": 0}

    def start_executor(self) -> None:
        self.executor.start()

    def stop_executor(self) -> None:
        self.stop_screen_monitor()
        self.executor.stop()

    def stop_all(self) -> None:
        self.stop_screen_monitor()
        self.stop_executor()
        for agent in self._agents.values():
            agent.stop()

    def get_agent_status(self) -> list[dict[str, Any]]:
        return [agent.get_status() for agent in self._agents.values()]

    def get_system_status(self) -> dict[str, Any]:
        return {
            "agents": self.get_agent_status(),
            "task_stats": self.planner.get_stats(),
            "executor_running": self.executor.is_running,
            "screen_monitor": self.get_screen_monitor_status(),
            "plugins": self.plugin_manager.list_plugins(),
            "message_count": len(self.message_bus.get_history()),
        }

    def on_status_change(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._status_callbacks.append(callback)

    def _on_task_complete(self, task: Task) -> None:
        details = task.result or {}
        self.history.record(
            agent=task.agent,
            action=task.action,
            status="completed",
            details=details,
        )
        if task.action in ("analyze_summary", "find_duplicates", "scan_directory"):
            self._last_folder_report = {**self._last_folder_report, **details}
        self._notify_status()

    def _on_task_error(self, task: Task, error: str) -> None:
        self.history.record(
            agent=task.agent,
            action=task.action,
            status="failed",
            details={"error": error},
        )
        self._notify_status()

    def _notify_status(self) -> None:
        status = self.get_system_status()
        for callback in self._status_callbacks:
            try:
                callback(status)
            except Exception:
                pass