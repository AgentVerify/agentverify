from agno.models.anthropic import Claude
from agno.models.azure import AzureOpenAI
from agno.models.google import Gemini
from agno.models.google.gemini import Gemini as DirectGemini
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat, OpenAIResponses
from agno.models.openai.chat import OpenAIChat as DirectOpenAIChat


openai_chat = OpenAIChat(id="gpt-5-mini")
openai_responses = OpenAIResponses(id="gpt-5-mini")
direct_openai_chat = DirectOpenAIChat(id="gpt-5-mini")
gemini = Gemini(id="gemini-2.5-flash")
direct_gemini = DirectGemini(id="gemini-2.5-flash")
claude = Claude(id="claude-sonnet-4-5")
azure = AzureOpenAI(id="gpt-5-mini")
groq = Groq(id="openai/gpt-oss-120b")
custom_openai = OpenAIChat(id="custom-model", base_url="https://gateway.example/v1")
custom_groq = Groq(id="custom-model", base_url="https://gateway.example/v1")
