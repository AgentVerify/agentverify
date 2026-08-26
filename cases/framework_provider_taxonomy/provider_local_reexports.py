from local_providers import (
    ProjectAnthropicModel,
    ProjectAnthropicProvider,
    ProjectOpenAIChatModel,
    ReboundGroqModel,
)


anthropic_provider = ProjectAnthropicProvider(api_key="test")
anthropic_model = ProjectAnthropicModel("claude-sonnet-4-5", provider=anthropic_provider)
openai_model = ProjectOpenAIChatModel(model="gpt-4.1")
not_groq = ReboundGroqModel("llama-3.3-70b-versatile")
