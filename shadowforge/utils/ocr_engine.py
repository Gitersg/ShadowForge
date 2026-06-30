"""Unified OCR engine — Tesseract with Windows auto-detect and EasyOCR fallback."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger("shadowforge.ocr")

TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

_easyocr_reader: Any = None


def configure_tesseract() -> bool:
    """Auto-configure Tesseract path on Windows."""
    try:
        import pytesseract
    except ImportError:
        return False

    if shutil.which("tesseract"):
        return True

    for path in TESSERACT_PATHS:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info("Tesseract found at %s", path)
            return True
    return False


def extract_text(image_path: Path) -> dict[str, Any]:
    """Extract text and word positions from an image."""
    if configure_tesseract():
        try:
            import pytesseract as tess
            from PIL import Image

            img = Image.open(image_path)
            text = tess.image_to_string(img)
            data = tess.image_to_data(img, output_type=tess.Output.DICT)
            words: list[dict[str, Any]] = []
            for i, word in enumerate(data["text"]):
                if word.strip():
                    conf = data["conf"][i]
                    if isinstance(conf, str):
                        continue
                    words.append({
                        "text": word,
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "w": data["width"][i],
                        "h": data["height"][i],
                        "confidence": conf,
                    })
            if words:
                return {
                    "success": True,
                    "engine": "tesseract",
                    "text": text,
                    "words": words,
                    "word_count": len(words),
                }
        except Exception as exc:
            logger.warning("Tesseract failed: %s", exc)

    return _easyocr_extract(image_path)


def _easyocr_extract(image_path: Path) -> dict[str, Any]:
    """Fallback OCR using EasyOCR."""
    global _easyocr_reader
    try:
        import easyocr
        import numpy as np
        from PIL import Image

        if _easyocr_reader is None:
            logger.info("Loading EasyOCR model (first run may take a moment)...")
            _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)

        img = np.array(Image.open(image_path))
        results = _easyocr_reader.readtext(img)
        words: list[dict[str, Any]] = []
        lines: list[str] = []
        for bbox, text, conf in results:
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            x, y = int(min(xs)), int(min(ys))
            w, h = int(max(xs) - x), int(max(ys) - y)
            words.append({
                "text": text,
                "x": x, "y": y, "w": w, "h": h,
                "confidence": round(float(conf) * 100, 1),
            })
            lines.append(text)

        return {
            "success": bool(words),
            "engine": "easyocr",
            "text": "\n".join(lines),
            "words": words,
            "word_count": len(words),
        }
    except ImportError:
        return {"success": False, "engine": "none", "text": "", "words": [], "word_count": 0}
    except Exception as exc:
        logger.warning("EasyOCR failed: %s", exc)
        return {"success": False, "engine": "easyocr", "text": "", "words": [], "word_count": 0}


def find_text_on_screen(words: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    """Find all OCR word matches for target text (partial match supported)."""
    if not target.strip():
        return []
    target_lower = target.lower().strip()
    matches: list[dict[str, Any]] = []
    for word in words:
        if target_lower in word["text"].lower():
            matches.append(word)
    if matches:
        return matches

    # Try multi-word: combine adjacent words in same line
    for i, word in enumerate(words):
        combined = word["text"]
        for j in range(i + 1, min(i + 5, len(words))):
            combined += " " + words[j]["text"]
            if target_lower in combined.lower():
                matches.append(word)
                break
    return matches