"""Base plugin class and plugin manager."""

import asyncio
from typing import Any


class Plugin:
    """Base class for all NEXUS plugins/integrations."""

    name: str = "unknown"
    description: str = ""
    icon: str = "●"

    async def is_available(self) -> bool:
        """Check if this plugin's dependencies are available."""
        return True

    async def get_status(self) -> dict:
        """Return current status for the dashboard panel."""
        return {"connected": False}

    async def get_data(self) -> dict:
        """Return data for the dashboard widget."""
        return {}

    async def handle_command(self, command: str, args: str) -> str | None:
        """Handle a slash command. Return response text or None if not handled."""
        return None


class PluginManager:
    """Manages all loaded plugins."""

    def __init__(self):
        self.plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin):
        self.plugins[plugin.name] = plugin

    async def get_all_status(self) -> dict:
        statuses = {}
        for name, plugin in self.plugins.items():
            try:
                available = await plugin.is_available()
                if available:
                    statuses[name] = await plugin.get_status()
                else:
                    statuses[name] = {"connected": False, "reason": "unavailable"}
            except Exception as e:
                statuses[name] = {"connected": False, "error": str(e)}
        return statuses

    async def get_all_data(self) -> dict:
        data = {}
        for name, plugin in self.plugins.items():
            try:
                data[name] = await plugin.get_data()
            except Exception:
                data[name] = {}
        return data

    async def handle_command(self, command: str, args: str) -> str | None:
        """Route a command to the appropriate plugin."""
        for plugin in self.plugins.values():
            result = await plugin.handle_command(command, args)
            if result is not None:
                return result
        return None

    def get_commands(self) -> list[dict]:
        """Get all available commands from all plugins."""
        commands = []
        for plugin in self.plugins.values():
            if hasattr(plugin, 'commands'):
                commands.extend(plugin.commands)
        return commands
