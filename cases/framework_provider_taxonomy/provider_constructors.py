from mistralai import Mistral as MistralClient
from groq import AsyncGroq
import cohere as co
import ollama as local_models
from langchain_cohere import ChatCohere
from langchain_groq import ChatGroq as GroqChat


mistral = MistralClient()
groq = AsyncGroq()
cohere = co.Client()
ollama = local_models.Client()
cohere_chat = ChatCohere(model="command-r-plus")
groq_chat = GroqChat(model="llama-3.3-70b-versatile")

agent = Agent(model="mistral-large-latest")
