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
