import { createOpenAI, openai } from '@ai-sdk/openai';

const LANGUAGE_MODEL = 'gpt-5-mini';
const EMBEDDING_MODEL: string = 'text-embedding-3-small';
const languageModel = openai(LANGUAGE_MODEL);
const embeddingModel = createOpenAI().embeddingModel(EMBEDDING_MODEL);
void languageModel;
void embeddingModel;
