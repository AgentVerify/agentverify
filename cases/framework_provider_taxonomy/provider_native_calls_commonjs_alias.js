const { GoogleGenAI: GeminiAliasClient } = require('@google/genai');

const aliasedGoogleClient = new GeminiAliasClient();

const aliasedGoogleResponse = await aliasedGoogleClient.models.generateContent({ model: 'gemini-2.5-pro' });

const { OpenAI: NamedOpenAICommonJS } = require('openai');
const { Anthropic: NamedAnthropicCommonJS } = require('@anthropic-ai/sdk');

const aliasedOpenAIClient = new NamedOpenAICommonJS();
const aliasedAnthropicClient = new NamedAnthropicCommonJS();

const aliasedOpenAIResponse = await aliasedOpenAIClient.responses.create({ model: 'gpt-5.6-mini' });
const aliasedAnthropicMessage = await aliasedAnthropicClient.messages.create({ model: 'claude-sonnet-4-6' });
