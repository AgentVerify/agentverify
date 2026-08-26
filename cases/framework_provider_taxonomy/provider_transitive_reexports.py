from provider_aliases import (
    TransitiveOpenAIChatModel,
    TransitiveReboundAnthropicModel,
)

transitive_openai = TransitiveOpenAIChatModel(model="gpt-4.1-mini")
transitive_rebound = TransitiveReboundAnthropicModel("claude-sonnet-4-5")
