const OpenAIClient = require('openai');
const AnthropicClient = require('@anthropic-ai/sdk');

const openaiClient = new OpenAIClient({ apiKey: process.env.OPENAI_API_KEY });
const anthropicClient = new AnthropicClient();

const openaiResponse = await openaiClient.responses.create({ model: 'gpt-5-mini' });
const anthropicMessage = await anthropicClient.messages.create({ model: 'claude-sonnet-4-6' });
