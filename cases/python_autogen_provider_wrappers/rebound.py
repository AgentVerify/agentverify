from autogen_ext.models.openai import OpenAIChatCompletionClient


def wrapper(**kwargs):
    return kwargs


OpenAIChatCompletionClient = wrapper  # noqa: F811
client = OpenAIChatCompletionClient(model="gpt-4o-mini")
