from agentscope.model import OpenAIChatModel as ProjectOpenAIChatModel
from pydantic_ai.models.anthropic import AnthropicModel as ProjectAnthropicModel
from pydantic_ai.models.groq import GroqModel as ReboundGroqModel
from pydantic_ai.providers.anthropic import AnthropicProvider as ProjectAnthropicProvider


ReboundGroqModel = factory
