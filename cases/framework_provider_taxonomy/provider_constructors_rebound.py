from mistralai import Mistral as MistralClient
from groq import AsyncGroq
import cohere as co
import ollama as local_models


MistralClient = factory
AsyncGroq = factory
co = transport
local_models = transport

not_mistral = MistralClient(model="mistral-large-latest")
not_groq = AsyncGroq(model="llama-3.3-70b-versatile")
not_cohere = co.Client(model="command-r-plus")
not_ollama = local_models.Client(model="llama3.3")

not_a_mistral_model = Agent(model="mixtral-8x7b")
