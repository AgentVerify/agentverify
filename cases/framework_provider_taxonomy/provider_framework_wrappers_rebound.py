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

from pydantic_ai.embeddings.bedrock import BedrockEmbeddingModel
from pydantic_ai.embeddings.google import GoogleEmbeddingModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.xai import XaiModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.google_cloud import GoogleCloudProvider
from pydantic_ai.providers.xai import XaiProvider

AnthropicProvider = factory
AnthropicModel = factory
GoogleProvider = factory
GoogleCloudProvider = factory
GoogleModel = factory
GoogleEmbeddingModel = factory
BedrockProvider = factory
BedrockConverseModel = factory
BedrockEmbeddingModel = factory
XaiProvider = factory
XaiModel = factory
DeepSeekProvider = factory

not_anthropic_provider = AnthropicProvider(api_key="test")
not_anthropic_model = AnthropicModel("claude-sonnet-4-5")
not_google_provider = GoogleProvider(api_key="test")
not_google_cloud_provider = GoogleCloudProvider(project="project", location="us-central1")
not_google_model = GoogleModel("gemini-2.5-flash")
not_google_embedding = GoogleEmbeddingModel("gemini-embedding-001")
not_bedrock_provider = BedrockProvider(region_name="us-east-1")
not_bedrock_model = BedrockConverseModel("amazon.nova-lite-v1:0")
not_bedrock_embedding = BedrockEmbeddingModel("amazon.titan-embed-text-v2:0")
not_xai_provider = XaiProvider(api_key="test")
not_xai_model = XaiModel("grok-4.3")
not_deepseek_provider = DeepSeekProvider(api_key="test")
