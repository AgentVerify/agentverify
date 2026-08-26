function buildClient() {
  const ScopedOpenAI = require('openai');
  const { GoogleGenAI } = require('@google/genai');
  return new ScopedOpenAI();
}
