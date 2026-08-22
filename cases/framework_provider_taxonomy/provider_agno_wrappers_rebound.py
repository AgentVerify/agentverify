from agno.models.anthropic import Claude
from agno.models.azure import AzureOpenAI
from agno.models.google import Gemini
from agno.models.google.gemini import Gemini as DirectGemini
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat, OpenAIResponses
from agno.models.openai.chat import OpenAIChat as DirectOpenAIChat


OpenAIChat = factory
OpenAIResponses = factory
DirectOpenAIChat = factory
Gemini = factory
DirectGemini = factory
Claude = factory
AzureOpenAI = factory
Groq = factory

not_openai_chat = OpenAIChat(id="gpt-5-mini")
not_openai_responses = OpenAIResponses(id="gpt-5-mini")
not_direct_openai_chat = DirectOpenAIChat(id="gpt-5-mini")
not_gemini = Gemini(id="gemini-2.5-flash")
not_direct_gemini = DirectGemini(id="gemini-2.5-flash")
not_claude = Claude(id="claude-sonnet-4-5")
not_azure = AzureOpenAI(id="gpt-5-mini")
not_groq = Groq(id="openai/gpt-oss-120b")
