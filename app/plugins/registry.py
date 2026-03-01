from app.core.plugin_base import PluginBase


class PluginRegistry:
    """
    Central registry for synthesizer plugins.
    Plugins register themselves here on app startup via discover().
    New plugins only need to: implement PluginBase and call PluginRegistry.register()
    from their module — then be imported in discover().
    """
    _plugins: dict[str, PluginBase] = {}

    @classmethod
    def register(cls, plugin: PluginBase) -> None:
        cls._plugins[plugin.id] = plugin

    @classmethod
    def discover(cls) -> None:
        """Import all plugin modules to trigger self-registration."""
        from app.plugins.chiptune.plugin import ChiptunePlugin
        cls.register(ChiptunePlugin())

    @classmethod
    def get(cls, plugin_id: str) -> PluginBase | None:
        return cls._plugins.get(plugin_id)

    @classmethod
    def list_all(cls) -> list[PluginBase]:
        return list(cls._plugins.values())
