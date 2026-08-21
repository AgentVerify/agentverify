import requests
from agents import function_tool
from google.adk.agents import LlmAgent
from google.adk.plugins.bigquery_agent_analytics_plugin import (
    BigQueryAgentAnalyticsPlugin,
    BigQueryLoggerConfig,
)
from google.adk.runners import InMemoryRunner


@function_tool
def send_audited(payload: dict) -> None:
    requests.post("https://example.invalid/send", json=payload)


@function_tool
def send_unaudited(payload: dict) -> None:
    requests.post("https://example.invalid/send", json=payload)


audited_agent = LlmAgent(name="audited_agent", tools=[send_audited])
audit_plugin = BigQueryAgentAnalyticsPlugin(project_id="project", dataset_id="audit")
audited_runner = InMemoryRunner(root_agent=audited_agent, plugins=[audit_plugin])

disabled_agent = LlmAgent(name="disabled_agent", tools=[send_unaudited])
disabled_config = BigQueryLoggerConfig(enabled=False)
disabled_plugin = BigQueryAgentAnalyticsPlugin(
    project_id="project", dataset_id="audit", config=disabled_config
)
disabled_runner = InMemoryRunner(root_agent=disabled_agent, plugins=[disabled_plugin])
