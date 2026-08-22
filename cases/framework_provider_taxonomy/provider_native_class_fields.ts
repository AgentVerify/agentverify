import Anthropic from '@anthropic-ai/sdk';
import { GoogleGenAI } from '@google/genai';
import OpenAI from 'openai';

class OpenAIService {
  private readonly client: OpenAI;
  constructor() {
    this.client = new OpenAI();
  }
  async generate(requestConfig: object) {
    return this.client.responses.create(requestConfig);
  }
}

class AnthropicService {
  private readonly client: Anthropic;
  constructor() {
    this.client = new Anthropic();
  }
  async generate(modelName: string) {
    return this.client.messages.create({ model: modelName });
  }
}

class GoogleService {
  private readonly client: GoogleGenAI;
  constructor() {
    this.client = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
  }
  async generate() {
    return this.client.models.generateContent({ model: 'gemini-2.5-flash' });
  }
}

class FieldInitializerService {
  private readonly client = new OpenAI();
  async generate(requestConfig: object) {
    return this.client.chat.completions.create(requestConfig);
  }
}
