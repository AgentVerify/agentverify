import Anthropic from '@anthropic-ai/sdk';
import { GoogleGenAI as GeminiClient } from '@google/genai';
import OpenAI, { OpenAI as NamedOpenAI } from 'openai';

const openAIClient = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const namedOpenAIClient = new NamedOpenAI();
const anthropicClient = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const googleClient = new GeminiClient({ apiKey: process.env.GEMINI_API_KEY });
