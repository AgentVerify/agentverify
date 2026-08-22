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
