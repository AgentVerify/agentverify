import { createAzure, openai } from './provider_ai_sdk_star_reexports';

const starOpenAIModel = openai('gpt-5-star-reexport');
const starAzureEmbedding = createAzure({
  resourceName: 'agentverify-resource',
  apiKey: process.env.AZURE_API_KEY,
}).embeddingModel('text-embedding-3-small-azure-star-reexport');

void starOpenAIModel;
void starAzureEmbedding;
