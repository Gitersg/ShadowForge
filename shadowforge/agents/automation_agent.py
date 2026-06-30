"""Automation agent — mouse, keyboard, and UI control via PyAutoGUI."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.message_bus import MessageBus

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class AutomationAgent(BaseAgent):
    """Performs mouse, keyboard, and UI automation actions."""

    def __init__(
        self,
        message_bus: MessageBus,
        pause: float = 0.3,
        failsafe: bool = True,
        screenshot_on_action: bool = True,
        screenshot_dir: str = "data/screenshots",
        name: str = "automation",
    ) -> None:
        super().__init__(
            name=name,
            message_bus=message_bus,
            capabilities=[
                "click", "double_click", "type_text", "hotkey",
                "execute_keys", "move_mouse", "screenshot",
            ],
        )
        self.pause = pause
        self.screenshot_on_action = screenshot_on_action
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        if PYAUTOGUI_AVAILABLE:
            pyautogui.PAUSE = pause
            pyautogui.FAILSAFE = failsafe

    def process(self, task: dict[str, Any]) -> dict[str, Any]:
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("PyAutoGUI is not installed")

        action = task.get("action", "")
        params = task.get("params", {})

        handlers = {
            "click": self._click,
            "double_click": self._double_click,
            "type_text": self._type_text,
            "hotkey": self._hotkey,
            "execute_keys": self._execute_keys,
            "move_mouse": self._move_mouse,
            "screenshot": self._screenshot,
            "scroll": self._scroll,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")

        result = handler(params)
        if self.screenshot_on_action and action not in ("screenshot", "execute_keys"):
            snap = self._screenshot({"label": action})
            result["action_screenshot"] = snap.get("path")
        return result

    def _click(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))

        button = params.get("button", "left")
        clicks = params.get("clicks", 1)
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.1)
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        self.logger.info("Clicked at (%d, %d)", x, y)
        return {"success": True, "action": "click", "x": x, "y": y, "button": button}

    def _double_click(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        pyautogui.doubleClick(x=x, y=y)
        return {"success": True, "action": "double_click", "x": x, "y": y}

    def _type_text(self, params: dict[str, Any]) -> dict[str, Any]:
        text = params.get("text", "")
        interval = params.get("interval", 0.05)
        if text.isascii():
            pyautogui.typewrite(text, interval=interval)
        else:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        self.logger.info("Typed %d characters", len(text))
        return {"success": True, "action": "type_text", "length": len(text)}

    def _hotkey(self, params: dict[str, Any]) -> dict[str, Any]:
        keys = params.get("keys", [])
        if isinstance(keys, str):
            keys = [k.strip() for k in keys.replace(" ", "").split("+") if k.strip()]
        pyautogui.hotkey(*keys)
        return {"success": True, "action": "hotkey", "keys": keys}

    def _execute_keys(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute keyboard instruction: hotkey (ctrl+s) or type text (type:hello)."""
        keys = params.get("keys", "").strip()
        if not keys:
            return {"success": True, "action": "execute_keys", "skipped": True}

        if keys.lower().startswith("type:"):
            text = keys[5:]
            pyautogui.write(text) if not text.isascii() else pyautogui.typewrite(text, interval=0.04)
            self.logger.info("Typed via execute_keys: %s", text[:30])
            return {"success": True, "action": "execute_keys", "typed": text}

        key_list = [k.strip().lower() for k in keys.replace(" ", "").split("+") if k.strip()]
        key_map = {"control": "ctrl", "cmd": "win", "command": "win"}
        key_list = [key_map.get(k, k) for k in key_list]
        pyautogui.hotkey(*key_list)
        self.logger.info("Key combo: %s", "+".join(key_list))
        return {"success": True, "action": "execute_keys", "keys": key_list}

    def _move_mouse(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        duration = params.get("duration", 0.5)
        pyautogui.moveTo(x, y, duration=duration)
        return {"success": True, "action": "move_mouse", "x": x, "y": y}

    def _scroll(self, params: dict[str, Any]) -> dict[str, Any]:
        amount = params.get("amount", 3)
        x, y = params.get("x"), params.get("y")
        if x is not None and y is not None:
            pyautogui.scroll(amount, x=x, y=y)
        else:
            pyautogui.scroll(amount)
        return {"success": True, "action": "scroll", "amount": amount}

    def _screenshot(self, params: dict[str, Any]) -> dict[str, Any]:
        label = params.get("label", "auto")
        timestamp_ms = int(time.time() * 1000)
        filepath = self.screenshot_dir / f"auto_{label}_{timestamp_ms}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        return {"success": True, "path": str(filepath)}