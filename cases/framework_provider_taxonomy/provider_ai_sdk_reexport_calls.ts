import { projectGoogleFactory, projectOpenAI } from './provider_ai_sdk_reexports';
import { transitiveOpenAI } from './provider_ai_sdk_transitive_reexports';

const localOpenAIModel = projectOpenAI('gpt-5-reexport');
const localGoogleEmbedding = projectGoogleFactory().textEmbeddingModel('gemini-embedding-reexport');
const transitiveOpenAIModel = transitiveOpenAI('gpt-5-transitive-reexport');

void localOpenAIModel;
void localGoogleEmbedding;
void transitiveOpenAIModel;
