#!/usr/bin/env python3
"""ShadowForge — Local Multi-Agent Desktop Automation System.

Entry point for the application. Launches the GUI dashboard.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from shadowforge.agents.automation_agent import AutomationAgent
from shadowforge.agents.file_agent import FileAgent
from shadowforge.agents.planner_agent import PlannerAgent
from shadowforge.agents.vision_agent import VisionAgent
from shadowforge.config import Config
from shadowforge.core.orchestrator import Orchestrator
from shadowforge.gui.dashboard import Dashboard
from shadowforge.utils.logger import setup_logging


def create_orchestrator(config: Config) -> Orchestrator:
    """Initialize orchestrator with all core agents."""
    orchestrator = Orchestrator(config.data)
    bus = orchestrator.message_bus

    vision_cfg = config.get("agents.vision", {})
    file_cfg = config.get("agents.file", {})
    auto_cfg = config.get("agents.automation", {})

    agents = [
        VisionAgent(
            message_bus=bus,
            screenshot_dir=vision_cfg.get("screenshot_dir", "data/screenshots"),
            ocr_engine=vision_cfg.get("ocr_engine", "pytesseract"),
        ),
        FileAgent(
            message_bus=bus,
            organize_categories=file_cfg.get("organize_categories"),
        ),
        AutomationAgent(
            message_bus=bus,
            pause=auto_cfg.get("pause_between_actions", 0.3),
            failsafe=auto_cfg.get("failsafe", True),
            screenshot_on_action=auto_cfg.get("screenshot_on_action", True),
        ),
        PlannerAgent(
            message_bus=bus,
            task_planner=orchestrator.planner,
        ),
    ]

    for agent in agents:
        orchestrator.register_agent(agent)

    if config.get("plugins.auto_load", True):
        plugin_dir = Path(config.get("plugins.directory", "plugins"))
        orchestrator.plugin_manager.plugin_dir = plugin_dir
        orchestrator.load_plugins()

    return orchestrator


def run_cli_workflow(orchestrator: Orchestrator, workflow: str) -> None:
    """Run a workflow from the command line without GUI."""
    print(f"Running workflow: {workflow}")
    orchestrator.run_workflow(workflow)
    orchestrator.start_executor()

    import time
    while orchestrator.planner.get_stats()["pending"] > 0 or orchestrator.planner.get_stats()["running"] > 0:
        time.sleep(0.5)

    stats = orchestrator.planner.get_stats()
    print(f"Done — completed: {stats['completed']}, failed: {stats['failed']}")
    orchestrator.stop_all()


def main() -> None:
    parser = argparse.ArgumentParser(description="ShadowForge — Local Multi-Agent Desktop Automation")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (no GUI)")
    parser.add_argument("--workflow", type=str, help="Workflow to run in CLI mode")
    parser.add_argument("--log-level", type=str, default=None, help="Override log level")
    args = parser.parse_args()

    config = Config(Path(args.config))
    log_level = args.log_level or config.get("logging.level", "INFO")
    log_dir = Path(config.get("logging.log_dir", "logs"))
    setup_logging(log_dir=log_dir, level=log_level, log_to_file=config.get("logging.log_to_file", True))

    orchestrator = create_orchestrator(config)

    if args.cli:
        workflow = args.workflow or "screen_audit"
        run_cli_workflow(orchestrator, workflow)
    else:
        app = Dashboard(orchestrator, config.data)
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()


if __name__ == "__main__":
    main()