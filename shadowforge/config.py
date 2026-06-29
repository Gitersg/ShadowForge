"""Configuration loader for ShadowForge."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "name": "ShadowForge",
        "version": "1.0.0",
        "theme": "dark",
    },
    "logging": {
        "level": "INFO",
        "log_to_file": True,
        "log_dir": "logs",
    },
    "agents": {
        "vision": {
            "ocr_engine": "pytesseract",
            "screenshot_dir": "data/screenshots",
            "confidence_threshold": 0.6,
        },
        "file": {
            "default_scan_depth": 3,
            "duplicate_hash_algorithm": "md5",
            "organize_categories": {
                "images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
                "documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".xlsx"],
                "videos": [".mp4", ".avi", ".mkv", ".mov"],
                "audio": [".mp3", ".wav", ".flac", ".ogg"],
                "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "code": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp"],
            },
        },
        "automation": {
            "pause_between_actions": 0.3,
            "failsafe": True,
            "screenshot_on_action": True,
        },
        "planner": {
            "max_concurrent_tasks": 1,
            "retry_failed": False,
        },
    },
    "gui": {
        "window_width": 1100,
        "window_height": 750,
        "refresh_interval_ms": 1000,
        "accent_color": "#6C63FF",
    },
    "plugins": {
        "directory": "plugins",
        "auto_load": True,
    },
}


class Config:
    """Loads and provides access to ShadowForge configuration."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or Path("config.json")
        self._config = self._load()

    def _load(self) -> dict[str, Any]:
        config = DEFAULT_CONFIG.copy()
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    user_config = json.load(f)
                config = self._deep_merge(config, user_config)
            except (json.JSONDecodeError, OSError):
                pass
        self._apply_env_overrides(config)
        return config

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_overrides(self, config: dict[str, Any]) -> None:
        if level := os.getenv("SF_LOG_LEVEL"):
            config["logging"]["level"] = level
        if theme := os.getenv("SF_THEME"):
            config["app"]["theme"] = theme

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot notation (e.g. 'agents.vision.ocr_engine')."""
        keys = key.split(".")
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def save(self) -> None:
        """Persist current config to disk."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    @property
    def data(self) -> dict[str, Any]:
        return self._config