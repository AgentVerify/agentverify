import agno.agent
import google.adk
import llama_index.core
import semantic_kernel
import smolagents
from google import genai
from google.genai import types
from langchain_aws import ChatBedrock

import boto3


bedrock = boto3.client("bedrock-runtime")
agent = google.adk.Agent(model="gemini-2.5-pro")

