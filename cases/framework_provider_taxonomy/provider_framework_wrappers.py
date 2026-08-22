import agentscope.model as agent_models
from pydantic_ai.embeddings.cohere import CohereEmbeddingModel
from pydantic_ai.models.cohere import CohereModel
from pydantic_ai.models.groq import GroqModel as PydanticGroqModel
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.cohere import CohereProvider
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.ollama import OllamaProvider


ollama_public = agent_models.OllamaChatModel(model="qwen3:14b")
groq_provider = GroqProvider(api_key="test")
mistral_provider = MistralProvider(api_key="test")
cohere_provider = CohereProvider(api_key="test")
ollama_provider = OllamaProvider(base_url="http://localhost:11434/v1")
groq_model = PydanticGroqModel("llama-3.3-70b-versatile", provider=groq_provider)
mistral_model = MistralModel("mistral-large-latest", provider=mistral_provider)
cohere_model = CohereModel("command-r-plus", provider=cohere_provider)
ollama_model = OllamaModel("qwen3:14b", provider=ollama_provider)
cohere_embedding = CohereEmbeddingModel("embed-v4.0", provider=cohere_provider)
anthropic_public = agent_models.AnthropicChatModel(model="claude-opus-4-5")
gemini_public = agent_models.GeminiChatModel(model="gemini-2.5-flash")
openai_chat_public = agent_models.OpenAIChatModel(model="gpt-4.1")
openai_response_public = agent_models.OpenAIResponseModel(model="gpt-4.1")
dashscope_public = agent_models.DashScopeChatModel(model="qwen-plus")
deepseek_public = agent_models.DeepSeekChatModel(model="deepseek-chat")
moonshot_public = agent_models.MoonshotChatModel(model="kimi-k2.5")
xai_public = agent_models.XAIChatModel(model="grok-3")

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


anthropic_provider = AnthropicProvider(api_key="test")
anthropic_model = AnthropicModel("claude-sonnet-4-5", provider=anthropic_provider)
google_provider = GoogleProvider(api_key="test")
google_cloud_provider = GoogleCloudProvider(project="project", location="us-central1")
google_model = GoogleModel("gemini-2.5-flash", provider=google_provider)
google_embedding = GoogleEmbeddingModel("gemini-embedding-001", provider=google_provider)
bedrock_provider = BedrockProvider(region_name="us-east-1")
bedrock_model = BedrockConverseModel("amazon.nova-lite-v1:0", provider=bedrock_provider)
bedrock_embedding = BedrockEmbeddingModel("amazon.titan-embed-text-v2:0", provider=bedrock_provider)
xai_provider = XaiProvider(api_key="test")
xai_model = XaiModel("grok-4.3", provider=xai_provider)
deepseek_provider = DeepSeekProvider(api_key="test")
