"""Rule-based + lightweight ML decision engine (no LLM)."""

from __future__ import annotations

import re
from typing import Any


# Keyword → workflow mapping rules
GOAL_RULES: list[dict[str, Any]] = [
    {
        "patterns": [r"organize", r"sort", r"clean\s*up", r"tidy", r"desktop"],
        "workflow": "organize_desktop",
        "weight": 1.0,
    },
    {
        "patterns": [r"screen", r"ocr", r"read", r"capture", r"see", r"look", r"audit"],
        "workflow": "screen_audit",
        "weight": 1.0,
    },
    {
        "patterns": [r"download", r"duplicat", r"remove", r"delete"],
        "workflow": "cleanup_downloads",
        "weight": 0.9,
    },
    {
        "patterns": [r"click", r"automate", r"press", r"type", r"mouse"],
        "workflow": "automate_click",
        "weight": 0.8,
    },
]

ACTION_ROUTING: dict[str, dict[str, Any]] = {
    "file_scan": {"agent": "file", "action": "scan_directory"},
    "file_organize": {"agent": "file", "action": "organize_by_type"},
    "file_dedup": {"agent": "file", "action": "find_duplicates"},
    "screen_capture": {"agent": "vision", "action": "capture_screen"},
    "ocr": {"agent": "vision", "action": "ocr_screen"},
    "ui_detect": {"agent": "vision", "action": "detect_elements"},
    "click": {"agent": "automation", "action": "click"},
    "type": {"agent": "automation", "action": "type_text"},
    "hotkey": {"agent": "automation", "action": "hotkey"},
}


class DecisionEngine:
    """Rule-based decision maker with keyword scoring. No external APIs."""

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def suggest_workflow(self, goal: str) -> dict[str, Any]:
        """Match a natural-language goal to the best workflow."""
        goal_lower = goal.lower()
        scores: dict[str, float] = {}

        for rule in GOAL_RULES:
            rule_score = 0.0
            matched_patterns: list[str] = []
            for pattern in rule["patterns"]:
                if re.search(pattern, goal_lower):
                    rule_score += rule["weight"]
                    matched_patterns.append(pattern)

            if rule_score > 0:
                workflow = rule["workflow"]
                scores[workflow] = scores.get(workflow, 0) + rule_score

        if not scores:
            return {
                "workflow": "screen_audit",
                "confidence": 0.3,
                "reasoning": "No keyword match — defaulting to screen audit",
                "alternatives": list({r["workflow"] for r in GOAL_RULES}),
            }

        best_workflow = max(scores, key=scores.get)
        max_score = scores[best_workflow]
        confidence = min(max_score / 2.0, 1.0)

        alternatives = sorted(
            [(w, s) for w, s in scores.items() if w != best_workflow],
            key=lambda x: x[1],
            reverse=True,
        )

        result = {
            "workflow": best_workflow,
            "confidence": round(confidence, 2),
            "reasoning": f"Matched workflow '{best_workflow}' with score {max_score:.1f}",
            "alternatives": [w for w, _ in alternatives[:3]],
        }
        self._history.append({"goal": goal, "result": result})
        return result

    def decide(self, context: dict[str, Any]) -> dict[str, Any]:
        """Make a decision based on structured context."""
        file_count = context.get("file_count", 0)
        has_duplicates = context.get("has_duplicates", False)
        screen_text = context.get("screen_text", "")

        decisions: list[dict[str, Any]] = []

        if file_count > 50:
            decisions.append({
                "action": "organize_by_type",
                "agent": "file",
                "priority": "high",
                "reason": f"Large directory with {file_count} files",
            })

        if has_duplicates:
            decisions.append({
                "action": "find_duplicates",
                "agent": "file",
                "priority": "medium",
                "reason": "Duplicate files detected",
            })

        if "error" in screen_text.lower() or "warning" in screen_text.lower():
            decisions.append({
                "action": "capture_screen",
                "agent": "vision",
                "priority": "high",
                "reason": "Error/warning detected on screen",
            })

        if not decisions:
            decisions.append({
                "action": "capture_screen",
                "agent": "vision",
                "priority": "low",
                "reason": "No specific triggers — default observation",
            })

        return {
            "decisions": decisions,
            "top_decision": decisions[0],
            "context_analyzed": list(context.keys()),
        }

    def route_action(self, action_type: str) -> dict[str, Any]:
        """Route an action type to the appropriate agent."""
        routing = ACTION_ROUTING.get(action_type, {
            "agent": "planner",
            "action": "analyze_goal",
            "params": {"goal": action_type},
        })
        return routing

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)