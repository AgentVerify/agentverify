import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { createOpenAI } from '@ai-sdk/openai';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';

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
