from typing import List, Optional

from google.adk.plugins.bigquery_agent_analytics_plugin import BasePlugin
from google.adk.plugins.plugin_manager import PluginManager


class Runner:
    def __init__(self, plugins: Optional[List[BasePlugin]] = None):
        app = type("App", (), {"plugins": plugins or []})()
        self.plugin_manager = PluginManager(
            plugins=app.plugins,
        )


class InMemoryRunner(Runner):
    pass
