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

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator and executor."""
        self._agents[agent.name] = agent
        self.executor.register_agent(agent)
        agent.start()
        self.logger.info("Orchestrator registered agent: %s", agent.name)

    def load_plugins(self) -> list[BaseAgent]:
        """Load and register all plugins from the plugin directory."""
        agents = self.plugin_manager.load_all(self.message_bus)
        for agent in agents:
            self.register_agent(agent)
        return agents

    def run_workflow(
        self,
        workflow_name: str,
        overrides: Optional[dict[str, Any]] = None,
    ) -> list[Task]:
        """Queue and optionally execute a named workflow."""
        tasks = self.planner.enqueue_workflow(workflow_name, overrides)
        self.logger.info("Queued workflow '%s' with %d tasks", workflow_name, len(tasks))
        self._notify_status()
        return tasks

    def run_task(
        self,
        name: str,
        agent: str,
        action: str,
        params: Optional[dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        execute_now: bool = False,
    ) -> Task:
        """Create and optionally immediately execute a single task."""
        task = self.planner.create_custom_task(name, agent, action, params, priority)
        self.planner.enqueue(task)
        if execute_now:
            self.executor.execute_task(task)
        self._notify_status()
        return task

    def start_executor(self) -> None:
        """Start background task execution."""
        self.executor.start()

    def stop_executor(self) -> None:
        """Stop background task execution."""
        self.executor.stop()

    def stop_all(self) -> None:
        """Stop executor and all agents."""
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
            "plugins": self.plugin_manager.list_plugins(),
            "message_count": len(self.message_bus.get_history()),
        }

    def on_status_change(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._status_callbacks.append(callback)

    def _on_task_complete(self, task: Task) -> None:
        self.history.record(
            agent=task.agent,
            action=task.action,
            status="completed",
            details=task.result or {},
        )
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