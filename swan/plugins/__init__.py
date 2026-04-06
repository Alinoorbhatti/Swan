from __future__ import annotations

import importlib.metadata
import logging

from swan.plugins.registry import PluginRegistry

log = logging.getLogger("swan.plugins")

_loaded = False


def load_plugins() -> None:
    """Discover and register all agent plugins.

    Built-ins are registered first, then any third-party plugins
    declared under the ``swan.plugins`` entry-point group.
    """
    global _loaded
    if _loaded:
        return

    from swan.plugins.builtin import shell, http
    for mod in (shell, http):
        PluginRegistry.register(mod.Plugin)
        log.debug("plugin_loaded", extra={"plugin_type": mod.Plugin.plugin_type})

    for ep in importlib.metadata.entry_points(group="swan.plugins"):
        # Skip builtins already registered above
        if ep.name in ("shell", "http"):
            continue
        try:
            plugin_cls = ep.load()
            PluginRegistry.register(plugin_cls)
            log.debug("plugin_loaded", extra={"plugin_type": plugin_cls.plugin_type, "source": ep.name})
        except Exception as exc:
            log.warning("Failed to load plugin %s: %s", ep.name, exc)

    _loaded = True
