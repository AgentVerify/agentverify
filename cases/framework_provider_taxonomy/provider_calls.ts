import { mistral as hostedMistral } from '@ai-sdk/mistral';
import { createGroq as buildGroq } from '@ai-sdk/groq';
import { cohere } from '@ai-sdk/cohere';

const mistralModel = hostedMistral('mistral-small-latest');
const configuredGroq = buildGroq({ apiKey: process.env.GROQ_API_KEY });
const groqModel = configuredGroq('llama-3.3-70b-versatile');
const cohereEmbedding = cohere.embedding('embed-english-v3.0');

async function dynamicallyLoadedGroq(modelId: string) {
  const { groq: dynamicGroq } = await import('@ai-sdk/groq');
  return dynamicGroq(modelId);
}

import { openai } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { xai } from '@ai-sdk/xai';
import { createAzure } from '@ai-sdk/azure';

const openAIModel = openai('gpt-5-mini');
const openAIImage = openai.image('gpt-image-2');
const configuredAnthropic = createAnthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const anthropicModel = configuredAnthropic('claude-sonnet-4-5');
const googleEmbedding = createGoogleGenerativeAI({
  apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY,
}).textEmbeddingModel('gemini-embedding-001');
const xaiModel = xai('grok-4');
const configuredAzure = createAzure({
  resourceName: 'agentverify-resource',
  apiKey: process.env.AZURE_API_KEY,
  ...spreadIfDefined('apiVersion', process.env.AZURE_API_VERSION),
});
const azureEmbedding = configuredAzure.embeddingModel('text-embedding-3-small-azure');

const { openai: commonJSOpenAI } = require('@ai-sdk/openai');
const { createAzure: commonJSCreateAzure } = require('@ai-sdk/azure');
const commonJSOpenAIModel = commonJSOpenAI('gpt-5-commonjs');
const commonJSAzureEmbedding = commonJSCreateAzure({
  resourceName: 'agentverify-resource',
  apiKey: process.env.AZURE_API_KEY,
}).embeddingModel('text-embedding-3-small-azure-commonjs');
