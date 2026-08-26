const OpenAIClient = require('openai');
const AnthropicClient = require('@anthropic-ai/sdk');
const { GoogleGenAI } = require('@google/genai');

const openaiClient = new OpenAIClient({ apiKey: process.env.OPENAI_API_KEY });
const anthropicClient = new AnthropicClient();
const googleClient = new GoogleGenAI();

const openaiResponse = await openaiClient.responses.create({ model: 'gpt-5-mini' });
const anthropicMessage = await anthropicClient.messages.create({ model: 'claude-sonnet-4-6' });
const googleResponse = await googleClient.models.generateContent({ model: 'gemini-2.5-flash' });
