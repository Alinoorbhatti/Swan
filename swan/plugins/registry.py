from __future__ import annotations

from swan.plugins.base import AgentPlugin


class UnknownPluginError(KeyError):
    def __init__(self, plugin_type: str) -> None:
        super().__init__(f"Unknown plugin type: {plugin_type!r}. Run `swan plugin list` to see available types.")


class PluginRegistry:
    _plugins: dict[str, type[AgentPlugin]] = {}

    @classmethod
    def register(cls, plugin_cls: type[AgentPlugin]) -> None:
        cls._plugins[plugin_cls.plugin_type] = plugin_cls

    @classmethod
    def resolve(cls, plugin_type: str) -> type[AgentPlugin]:
        if plugin_type not in cls._plugins:
            raise UnknownPluginError(plugin_type)
        return cls._plugins[plugin_type]

    @classmethod
    def list_types(cls) -> list[str]:
        return sorted(cls._plugins.keys())

    @classmethod
    def clear(cls) -> None:
        """For testing only."""
        cls._plugins.clear()
