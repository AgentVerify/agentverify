const OpenAIClient = require('openai');
const AnthropicClient = require('@anthropic-ai/sdk');

const openaiClient = new OpenAIClient({ apiKey: process.env.OPENAI_API_KEY });
const anthropicClient = new AnthropicClient();
