function buildClient() {
  const ScopedOpenAI = require('openai');
  const { GoogleGenAI } = require('@google/genai');
  return new ScopedOpenAI();
}

function buildNamedClients() {
  const { OpenAI: ScopedNamedOpenAI } = require('openai');
  const { Anthropic: ScopedNamedAnthropic } = require('@anthropic-ai/sdk');
  return [new ScopedNamedOpenAI(), new ScopedNamedAnthropic()];
}
