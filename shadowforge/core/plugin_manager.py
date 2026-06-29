"""Plugin system for dynamically loading custom agents."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Optional, Type

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.message_bus import MessageBus


class PluginManager:
    """Discovers and loads agent plugins from a directory."""

    def __init__(self, plugin_dir: Optional[Path] = None) -> None:
        self.plugin_dir = plugin_dir or Path("plugins")
        self.logger = logging.getLogger("shadowforge.plugins")
        self._loaded: dict[str, Type[BaseAgent]] = {}

    def discover(self) -> list[str]:
        """Scan plugin directory for Python modules."""
        if not self.plugin_dir.exists():
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            return []

        modules: list[str] = []
        for file in self.plugin_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue
            modules.append(file.stem)
        return modules

    def load_plugin(
        self,
        module_name: str,
        message_bus: MessageBus,
        **kwargs: Any,
    ) -> Optional[BaseAgent]:
        """Load a plugin module and instantiate its agent class."""
        if module_name in self._loaded:
            agent_cls = self._loaded[module_name]
            return agent_cls(name=module_name, message_bus=message_bus, **kwargs)

        plugin_path = self.plugin_dir / f"{module_name}.py"
        if not plugin_path.exists():
            self.logger.error("Plugin not found: %s", module_name)
            return None

        try:
            spec_name = f"shadowforge_plugins.{module_name}"
            spec = importlib.util.spec_from_file_location(spec_name, plugin_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load spec for {module_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            agent_cls = self._find_agent_class(module)
            if agent_cls is None:
                self.logger.error("No BaseAgent subclass in %s", module_name)
                return None

            self._loaded[module_name] = agent_cls
            agent = agent_cls(name=module_name, message_bus=message_bus, **kwargs)
            self.logger.info("Loaded plugin: %s", module_name)
            return agent

        except Exception as exc:
            self.logger.error("Failed to load plugin %s: %s", module_name, exc)
            return None

    def load_all(self, message_bus: MessageBus, **kwargs: Any) -> list[BaseAgent]:
        """Discover and load all available plugins."""
        agents: list[BaseAgent] = []
        for module_name in self.discover():
            agent = self.load_plugin(module_name, message_bus, **kwargs)
            if agent:
                agents.append(agent)
        return agents

    def _find_agent_class(self, module: Any) -> Optional[Type[BaseAgent]]:
        """Find the first BaseAgent subclass in a module."""
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseAgent)
                and obj is not BaseAgent
                and not inspect.isabstract(obj)
            ):
                return obj
        return None

    def register_class(self, name: str, agent_cls: Type[BaseAgent]) -> None:
        """Manually register an agent class as a plugin."""
        self._loaded[name] = agent_cls
        self.logger.info("Registered plugin class: %s", name)

    def list_plugins(self) -> list[str]:
        return list(self._loaded.keys())