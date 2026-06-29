"""ShadowForge example usage — programmatic API without GUI."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadowforge.agents.file_agent import FileAgent
from shadowforge.agents.planner_agent import PlannerAgent
from shadowforge.agents.vision_agent import VisionAgent
from shadowforge.config import Config
from shadowforge.core.message_bus import MessageBus
from shadowforge.core.orchestrator import Orchestrator
from shadowforge.utils.logger import setup_logging


def main() -> None:
    setup_logging(level="INFO")

    config = Config(Path(__file__).parent.parent / "config.json")
    orchestrator = Orchestrator(config.data)
    bus = orchestrator.message_bus

    # Register agents
    orchestrator.register_agent(VisionAgent(message_bus=bus))
    orchestrator.register_agent(FileAgent(message_bus=bus))
    orchestrator.register_agent(PlannerAgent(message_bus=bus, task_planner=orchestrator.planner))

    # Example 1: Plan from a natural-language goal
    print("\n=== Example 1: Goal Planning ===")
    plan_task = orchestrator.run_task(
        name="Analyze goal",
        agent="planner",
        action="analyze_goal",
        params={"goal": "organize my desktop and remove duplicates"},
        execute_now=True,
    )
    if plan_task.result:
        print(f"Recommended workflow: {plan_task.result['recommended_workflow']}")
        print(f"Confidence: {plan_task.result['confidence']}")

    # Example 2: Screen capture
    print("\n=== Example 2: Screen Capture ===")
    screen_task = orchestrator.run_task(
        name="Capture screen",
        agent="vision",
        action="capture_screen",
        execute_now=True,
    )
    if screen_task.result:
        print(f"Screenshot saved: {screen_task.result['path']}")

    # Example 3: File scan
    print("\n=== Example 3: File Scan ===")
    scan_task = orchestrator.run_task(
        name="Scan desktop",
        agent="file",
        action="scan_directory",
        params={"path": "~/Desktop", "depth": 2},
        execute_now=True,
    )
    if scan_task.result:
        print(f"Files found: {scan_task.result['file_count']}")
        print(f"Total size: {scan_task.result['total_size_mb']} MB")

    # Example 4: Run full workflow
    print("\n=== Example 4: Full Workflow ===")
    orchestrator.run_workflow("screen_audit")
    orchestrator.start_executor()

    while True:
        stats = orchestrator.planner.get_stats()
        if stats["pending"] == 0 and stats["running"] == 0:
            break
        time.sleep(0.3)

    print(f"Workflow complete — {stats['completed']} tasks done")
    orchestrator.stop_all()
    print("\nAll examples finished successfully!")


if __name__ == "__main__":
    main()