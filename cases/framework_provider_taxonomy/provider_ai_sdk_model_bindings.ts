import { createOpenAI, openai } from '@ai-sdk/openai';

const LANGUAGE_MODEL = 'gpt-5-mini';
const EMBEDDING_MODEL: string = 'text-embedding-3-small';
const languageModel = openai(LANGUAGE_MODEL);
const embeddingModel = createOpenAI().embeddingModel(EMBEDDING_MODEL);
const MODEL_IDS = {
  language: 'gpt-5-mini-object',
  embedding: 'text-embedding-3-large',
  bracketLanguage: 'gpt-5-mini-bracket',
  bracketEmbedding: 'text-embedding-3-bracket',
  'language-model': 'gpt-5-mini-quoted-key',
  'embedding-model': 'text-embedding-3-quoted-key',
} as const;
const objectLanguageModel = openai(MODEL_IDS.language);
const objectEmbeddingModel = createOpenAI().embeddingModel(MODEL_IDS.embedding);
const bracketLanguageModel = openai(MODEL_IDS["bracketLanguage"]);
const bracketEmbeddingModel = createOpenAI().embeddingModel(MODEL_IDS['bracketEmbedding']);
const quotedLanguageModel = openai(MODEL_IDS["language-model"]);
const quotedEmbeddingModel = createOpenAI().embeddingModel(MODEL_IDS["embedding-model"]);
void languageModel;
void embeddingModel;
void objectLanguageModel;
void objectEmbeddingModel;
void bracketLanguageModel;
void bracketEmbeddingModel;
void quotedLanguageModel;
void quotedEmbeddingModel;
