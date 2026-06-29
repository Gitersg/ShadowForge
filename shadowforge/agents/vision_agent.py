"""Vision agent — screen capture, OCR, and UI element detection."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.message_bus import MessageBus

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

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
        ocr_engine: str = "pytesseract",
        name: str = "vision",
    ) -> None:
        super().__init__(
            name=name,
            message_bus=message_bus,
            capabilities=["capture_screen", "ocr_screen", "detect_elements", "find_text"],
        )
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_engine = ocr_engine
        self._last_screenshot: Optional[Path] = None
        self._last_ocr_text: str = ""

    def process(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "")
        params = task.get("params", {})

        handlers = {
            "capture_screen": self._capture_screen,
            "ocr_screen": self._ocr_screen,
            "detect_elements": self._detect_elements,
            "find_text": self._find_text,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")

        return handler(params)

    def _capture_screen(self, params: dict[str, Any]) -> dict[str, Any]:
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow is required for screen capture")

        region = params.get("region")
        img = ImageGrab.grab(bbox=region) if region else ImageGrab.grab()

        timestamp = int(time.time())
        filepath = self.screenshot_dir / f"screen_{timestamp}.png"
        img.save(filepath)
        self._last_screenshot = filepath

        self.logger.info("Screenshot saved: %s", filepath)
        return {
            "success": True,
            "path": str(filepath),
            "size": img.size,
            "timestamp": timestamp,
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

        if not TESSERACT_AVAILABLE:
            return self._fallback_ocr(img_path)

        try:
            import pytesseract as tess
            from PIL import Image

            img = Image.open(img_path)
            text = tess.image_to_string(img)
            data = tess.image_to_data(img, output_type=tess.Output.DICT)

            words: list[dict[str, Any]] = []
            for i, word in enumerate(data["text"]):
                if word.strip():
                    words.append({
                        "text": word,
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "w": data["width"][i],
                        "h": data["height"][i],
                        "confidence": data["conf"][i],
                    })

            self._last_ocr_text = text
            self.logger.info("OCR extracted %d words", len(words))
            return {
                "success": True,
                "text": text,
                "words": words,
                "word_count": len(words),
                "source": str(img_path),
            }
        except Exception as exc:
            self.logger.warning("Tesseract OCR failed: %s", exc)
            return self._fallback_ocr(img_path)

    def _fallback_ocr(self, img_path: Path) -> dict[str, Any]:
        """Basic contour-based text region detection when OCR unavailable."""
        img = cv2.imread(str(img_path))
        if img is None:
            raise RuntimeError(f"Cannot read image: {img_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions: list[dict[str, int]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 20 and h > 10:
                regions.append({"x": x, "y": y, "w": w, "h": h})

        return {
            "success": True,
            "text": "",
            "words": [],
            "text_regions": regions,
            "word_count": 0,
            "source": str(img_path),
            "note": "OCR unavailable — returned text region bounding boxes only",
        }

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
        self.logger.info("Detected %d UI elements", len(elements))
        return {
            "success": True,
            "elements": elements[:50],
            "total_detected": len(elements),
            "source": str(image_path),
        }

    def _find_text(self, params: dict[str, Any]) -> dict[str, Any]:
        target = params.get("text", "")
        ocr_result = self._ocr_screen(params)

        matches: list[dict[str, Any]] = []
        for word_info in ocr_result.get("words", []):
            if target.lower() in word_info["text"].lower():
                matches.append(word_info)

        if matches:
            best = matches[0]
            center_x = best["x"] + best["w"] // 2
            center_y = best["y"] + best["h"] // 2
        else:
            center_x, center_y = 0, 0

        return {
            "success": bool(matches),
            "matches": matches,
            "match_count": len(matches),
            "click_position": {"x": center_x, "y": center_y},
            "searched_text": target,
        }