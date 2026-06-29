"""Planner agent — rule-based task decomposition and decision routing."""

from __future__ import annotations

from typing import Any, Optional

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.message_bus import Message, MessageBus
from shadowforge.core.task_planner import WORKFLOW_TEMPLATES, TaskPlanner
from shadowforge.ml.decision_engine import DecisionEngine


class PlannerAgent(BaseAgent):
    """Analyzes goals, selects workflows, and routes tasks to agents."""

    def __init__(
        self,
        message_bus: MessageBus,
        task_planner: Optional[TaskPlanner] = None,
        name: str = "planner",
    ) -> None:
        super().__init__(
            name=name,
            message_bus=message_bus,
            capabilities=["plan_workflow", "analyze_goal", "suggest_action", "route_task"],
        )
        self.task_planner = task_planner or TaskPlanner()
        self.decision_engine = DecisionEngine()

    def process(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "")
        params = task.get("params", {})

        handlers = {
            "plan_workflow": self._plan_workflow,
            "analyze_goal": self._analyze_goal,
            "suggest_action": self._suggest_action,
            "route_task": self._route_task,
            "list_workflows": self._list_workflows,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")

        return handler(params)

    def _on_message(self, message: Message) -> None:
        if message.message_type == "request_plan":
            goal = message.payload.get("goal", "")
            plan = self._analyze_goal({"goal": goal})
            self.send_message(message.sender, plan, message_type="plan_response")

    def _plan_workflow(self, params: dict[str, Any]) -> dict[str, Any]:
        workflow_name = params.get("workflow")
        if not workflow_name:
            goal = params.get("goal", "")
            suggestion = self.decision_engine.suggest_workflow(goal)
            workflow_name = suggestion.get("workflow", "screen_audit")

        overrides = params.get("overrides", {})
        tasks = self.task_planner.create_workflow(workflow_name, overrides)
        return {
            "success": True,
            "workflow": workflow_name,
            "task_count": len(tasks),
            "tasks": [t.to_dict() for t in tasks],
        }

    def _analyze_goal(self, params: dict[str, Any]) -> dict[str, Any]:
        goal = params.get("goal", "")
        suggestion = self.decision_engine.suggest_workflow(goal)
        confidence = suggestion.get("confidence", 0.0)

        return {
            "success": True,
            "goal": goal,
            "recommended_workflow": suggestion.get("workflow"),
            "confidence": confidence,
            "reasoning": suggestion.get("reasoning", ""),
            "alternative_workflows": suggestion.get("alternatives", []),
        }

    def _suggest_action(self, params: dict[str, Any]) -> dict[str, Any]:
        context = params.get("context", {})
        decision = self.decision_engine.decide(context)
        return {
            "success": True,
            "decision": decision,
        }

    def _route_task(self, params: dict[str, Any]) -> dict[str, Any]:
        action_type = params.get("type", "")
        routing = self.decision_engine.route_action(action_type)
        return {
            "success": True,
            "agent": routing.get("agent"),
            "action": routing.get("action"),
            "params": routing.get("params", {}),
        }

    def _list_workflows(self, params: dict[str, Any]) -> dict[str, Any]:
        workflows = {
            name: [{"name": s["name"], "agent": s["agent"]} for s in steps]
            for name, steps in WORKFLOW_TEMPLATES.items()
        }
        return {"success": True, "workflows": workflows}