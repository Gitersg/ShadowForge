"""Vision agent — screen capture, OCR, interval monitoring, UI detection."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.continuous_capture import ContinuousCapture
from shadowforge.core.message_bus import MessageBus
from shadowforge.utils.ocr_engine import extract_text, find_text_on_screen

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class VisionAgent(BaseAgent):
    """Captures screens, performs OCR, and detects UI elements."""

    def __init__(
        self,
        message_bus: MessageBus,
        screenshot_dir: str = "data/screenshots",
        ocr_engine: str = "auto",
        name: str = "vision",
    ) -> None:
        super().__init__(
            name=name,
            message_bus=message_bus,
            capabilities=[
                "capture_screen", "ocr_screen", "detect_elements",
                "find_text", "start_interval_capture", "stop_interval_capture",
            ],
        )
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_engine = ocr_engine
        self._last_screenshot: Optional[Path] = None
        self._last_ocr_text: str = ""
        self._capture_counter = 0
        self._continuous = ContinuousCapture(self._interval_capture_shot)

    def process(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "")
        params = task.get("params", {})

        handlers = {
            "capture_screen": self._capture_screen,
            "ocr_screen": self._ocr_screen,
            "detect_elements": self._detect_elements,
            "find_text": self._find_text,
            "start_interval_capture": self._start_interval_capture,
            "stop_interval_capture": self._stop_interval_capture,
        }
        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
        return handler(params)

    def start_interval_capture(self, interval_sec: float) -> dict[str, Any]:
        return self._start_interval_capture({"interval": interval_sec})

    def stop_interval_capture(self) -> dict[str, Any]:
        return self._stop_interval_capture({})

    def get_capture_status(self) -> dict[str, Any]:
        return self._continuous.get_status()

    def _interval_capture_shot(self) -> dict[str, Any]:
        return self._capture_screen({"tag": "interval"})

    def _start_interval_capture(self, params: dict[str, Any]) -> dict[str, Any]:
        interval = float(params.get("interval", 5))
        self._continuous.start(interval)
        return {"success": True, "interval": interval, **self._continuous.get_status()}

    def _stop_interval_capture(self, params: dict[str, Any]) -> dict[str, Any]:
        self._continuous.stop()
        return {"success": True, **self._continuous.get_status()}

    def _capture_screen(self, params: dict[str, Any]) -> dict[str, Any]:
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow is required for screen capture")

        region = params.get("region")
        img = ImageGrab.grab(bbox=region) if region else ImageGrab.grab()

        self._capture_counter += 1
        tag = params.get("tag", "screen")
        timestamp_ms = int(time.time() * 1000)
        filepath = self.screenshot_dir / f"{tag}_{timestamp_ms}_{self._capture_counter}.png"
        img.save(filepath)
        self._last_screenshot = filepath

        self.logger.info("Screenshot saved: %s", filepath.name)
        return {
            "success": True,
            "path": str(filepath),
            "size": img.size,
            "timestamp": timestamp_ms,
            "capture_number": self._capture_counter,
        }

    def _ocr_screen(self, params: dict[str, Any]) -> dict[str, Any]:
        image_path = params.get("path")
        if image_path:
            img_path = Path(image_path)
        elif self._last_screenshot:
            img_path = self._last_screenshot
        else:
            capture_result = self._capture_screen({})
            img_path = Path(capture_result["path"])

        ocr_result = extract_text(img_path)
        self._last_ocr_text = ocr_result.get("text", "")
        ocr_result["source"] = str(img_path)
        return ocr_result

    def _detect_elements(self, params: dict[str, Any]) -> dict[str, Any]:
        image_path = params.get("path", str(self._last_screenshot) if self._last_screenshot else None)
        if not image_path:
            capture = self._capture_screen({})
            image_path = capture["path"]

        img = cv2.imread(str(image_path))
        if img is None:
            raise RuntimeError(f"Cannot read image: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        elements: list[dict[str, Any]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < 500:
                continue
            aspect = w / h if h > 0 else 0
            element_type = "button" if 1.5 < aspect < 6 and h < 60 else "panel" if area > 10000 else "element"
            elements.append({
                "type": element_type,
                "x": x, "y": y, "w": w, "h": h,
                "area": area,
                "center": (x + w // 2, y + h // 2),
            })

        elements.sort(key=lambda e: e["area"], reverse=True)
        return {
            "success": True,
            "elements": elements[:50],
            "total_detected": len(elements),
            "source": str(image_path),
        }

    def _find_text(self, params: dict[str, Any]) -> dict[str, Any]:
        target = params.get("text", "").strip()
        if not target:
            raise ValueError("No target text specified. Enter the word or phrase to find.")

        ocr_result = self._ocr_screen(params)
        words = ocr_result.get("words", [])
        matches = find_text_on_screen(words, target)

        if not matches and ocr_result.get("text"):
            # Full-text line search with approximate position from first word
            for word in words:
                if target.lower()[:3] in word["text"].lower():
                    matches.append(word)
                    break

        if matches:
            best = matches[0]
            center_x = best["x"] + best["w"] // 2
            center_y = best["y"] + best["h"] // 2
            success = True
        else:
            center_x, center_y = 0, 0
            success = False
            self.logger.warning("Text '%s' not found on screen", target)

        return {
            "success": success,
            "matches": matches,
            "match_count": len(matches),
            "click_position": {"x": center_x, "y": center_y},
            "searched_text": target,
            "ocr_engine": ocr_result.get("engine", "unknown"),
        }

    def stop(self) -> None:
        self._continuous.stop()
        super().stop()