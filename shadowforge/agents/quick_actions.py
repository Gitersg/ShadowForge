"""Predefined quick automation actions — reliable, no OCR required."""

from __future__ import annotations

import time
from typing import Any

QUICK_ACTIONS: dict[str, dict[str, Any]] = {
    "show_desktop": {
        "label": "Show Desktop (Win+D)",
        "keys": "win+d",
        "description": "Minimize all windows and show desktop",
    },
    "open_run": {
        "label": "Open Run Dialog (Win+R)",
        "keys": "win+r",
        "description": "Open the Windows Run dialog",
    },
    "open_explorer": {
        "label": "Open File Explorer (Win+E)",
        "keys": "win+e",
        "description": "Open File Explorer",
    },
    "screenshot_now": {
        "label": "Screenshot Now",
        "action": "capture_screen",
        "agent": "vision",
        "description": "Take an instant screenshot",
    },
    "save_file": {
        "label": "Save File (Ctrl+S)",
        "keys": "ctrl+s",
        "description": "Press Ctrl+S in the active window",
    },
    "copy_paste": {
        "label": "Copy then Paste",
        "keys": "ctrl+c",
        "then_keys": "ctrl+v",
        "delay": 0.5,
        "description": "Copy selection then paste",
    },
    "switch_window": {
        "label": "Switch Window (Alt+Tab)",
        "keys": "alt+tab",
        "description": "Switch to the next window",
    },
    "refresh": {
        "label": "Refresh (F5)",
        "keys": "f5",
        "description": "Refresh the active window",
    },
    "select_all": {
        "label": "Select All (Ctrl+A)",
        "keys": "ctrl+a",
        "description": "Select all in active window",
    },
    "type_custom": {
        "label": "Type Custom Text",
        "description": "Type your text at the cursor after countdown",
    },
    "custom_hotkey": {
        "label": "Custom Hotkey",
        "description": "Press a custom key combo e.g. ctrl+shift+s",
    },
}


def list_quick_actions() -> list[dict[str, str]]:
    return [
        {"id": k, "label": v["label"], "description": v.get("description", "")}
        for k, v in QUICK_ACTIONS.items()
    ]