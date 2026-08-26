from provider_factories import (
    ambiguous_model,
    make_anthropic_model,
    make_openai_model,
    make_static_openai_model,
    rebound_model,
)


factory_openai = make_openai_model("gpt-4.1")
factory_anthropic = make_anthropic_model(model_name="claude-sonnet-4-5")
factory_static = make_static_openai_model()
not_ambiguous = ambiguous_model("gpt-4.1")
not_rebound = rebound_model("gpt-4.1")
