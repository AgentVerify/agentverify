from anthropic import Anthropic
from openai import AzureOpenAI


anthropic = Anthropic()
azure = AzureOpenAI(azure_deployment="gpt-4o-enterprise")

