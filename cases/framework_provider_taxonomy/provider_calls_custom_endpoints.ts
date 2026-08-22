import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { createOpenAI } from '@ai-sdk/openai';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import NativeAnthropic from '@anthropic-ai/sdk';
import { GoogleGenAI } from '@google/genai';
import NativeOpenAI from 'openai';

const baseURL = 'https://gateway.example/v1';
const providerConfig = { apiKey: process.env.PROVIDER_API_KEY };

const customOpenAI = createOpenAI({ baseURL, apiKey: process.env.PROVIDER_API_KEY });
const customOpenAIModel = customOpenAI('custom-model');
const customAnthropic = createAnthropic({
  baseURL: 'https://azure.example/anthropic/v1',
  apiKey: process.env.PROVIDER_API_KEY,
});
const customAnthropicModel = customAnthropic('claude-custom');
const unknownGoogle = createGoogleGenerativeAI(providerConfig);
const unknownGoogleModel = unknownGoogle('gemini-custom');
const spreadOpenAI = createOpenAI({ ...providerConfig });
const spreadOpenAIModel = spreadOpenAI('spread-custom');
const compatible = createOpenAICompatible({
  name: 'custom',
  baseURL,
  apiKey: process.env.PROVIDER_API_KEY,
});
const compatibleModel = compatible('compatible-custom');
const getterOpenAI = createOpenAI({
  get baseURL() {
    return 'https://getter.example/v1';
  },
  apiKey: process.env.PROVIDER_API_KEY,
});
const getterOpenAIModel = getterOpenAI('getter-custom');
const nativeCustomOpenAI = new NativeOpenAI({ baseURL });
const nativeUnknownAnthropic = new NativeAnthropic(providerConfig);
const nativeSpreadGoogle = new GoogleGenAI({ ...providerConfig });
const nativeNestedGoogle = new GoogleGenAI({
  apiKey: process.env.PROVIDER_API_KEY,
  httpOptions: { baseUrl: 'https://google-proxy.example/v1' },
});
const CommonJSOpenAI = require('openai');
const CommonJSAnthropic = require('@anthropic-ai/sdk');
const commonJSCustomOpenAI = new CommonJSOpenAI({ baseURL });
const commonJSUnknownAnthropic = new CommonJSAnthropic(providerConfig);
