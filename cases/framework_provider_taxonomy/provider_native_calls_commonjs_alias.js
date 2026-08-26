const { GoogleGenAI: GeminiAliasClient } = require('@google/genai');

const aliasedGoogleClient = new GeminiAliasClient();

const aliasedGoogleResponse = await aliasedGoogleClient.models.generateContent({ model: 'gemini-2.5-pro' });
