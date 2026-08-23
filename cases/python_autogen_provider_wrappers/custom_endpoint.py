from autogen_ext.models.openai import OpenAIChatCompletionClient

client = OpenAIChatCompletionClient(
    model="custom-model",
    base_url="https://compatible.example/v1",
)
