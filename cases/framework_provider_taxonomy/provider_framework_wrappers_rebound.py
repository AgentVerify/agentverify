from agentscope.model import OllamaChatModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider


OllamaChatModel = factory
GroqModel = factory
GroqProvider = factory

not_ollama = OllamaChatModel(model="qwen3:14b")
not_groq_model = GroqModel("llama-3.3-70b-versatile")
not_groq_provider = GroqProvider(api_key="test")

from agentscope.model import OpenAIChatModel

OpenAIChatModel = factory
not_openai = OpenAIChatModel(model="gpt-4.1")

from agentscope.model import (
    DashScopeChatModel,
    DeepSeekChatModel,
    MoonshotChatModel,
    XAIChatModel,
)

DashScopeChatModel = factory
DeepSeekChatModel = factory
MoonshotChatModel = factory
XAIChatModel = factory

not_dashscope = DashScopeChatModel(model="qwen-plus")
not_deepseek = DeepSeekChatModel(model="deepseek-chat")
not_moonshot = MoonshotChatModel(model="kimi-k2.5")
not_xai = XAIChatModel(model="grok-3")
