from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.anthropic import AnthropicChatCompletionClient
from autogen_ext.models.openai import (
    AzureOpenAIChatCompletionClient,
    OpenAIChatCompletionClient,
)

openai_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
azure_client = AzureOpenAIChatCompletionClient(
    model="gpt-4o",
    azure_endpoint="https://example.openai.azure.com",
)
anthropic_client = AnthropicChatCompletionClient(model="claude-3-5-sonnet-latest")
agent = AssistantAgent("assistant", model_client=openai_client)
