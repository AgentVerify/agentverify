from local_providers import ProjectAnthropicModel, ProjectOpenAIChatModel
from provider_star_aliases import *

__all__ = [
    "make_openai_model",
    "make_static_openai_model",
    "ambiguous_model",
    "rebound_model",
]


def make_openai_model(model_name):
    return ProjectOpenAIChatModel(model=model_name)


def make_anthropic_model(model_name):
    return ProjectAnthropicModel(model_name)


def make_static_openai_model():
    return TransitiveOpenAIChatModel(model="gpt-4.1-mini")


def ambiguous_model(model_name):
    if model_name:
        return ProjectOpenAIChatModel(model=model_name)
    return ProjectAnthropicModel(model_name)


def rebound_model(model_name):
    ProjectOpenAIChatModel = factory
    return ProjectOpenAIChatModel(model=model_name)
