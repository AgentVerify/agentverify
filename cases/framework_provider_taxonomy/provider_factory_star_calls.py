from provider_factories import *

star_factory_openai = make_openai_model("gpt-4.1-star")
star_factory_static = make_static_openai_model()
not_star_filtered = make_anthropic_model("claude-sonnet-4-5")
not_star_ambiguous = ambiguous_model("gpt-4.1")
not_star_rebound = rebound_model("gpt-4.1")
