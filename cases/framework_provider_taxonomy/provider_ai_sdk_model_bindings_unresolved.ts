import { openai } from '@ai-sdk/openai';

let MUTABLE_MODEL = 'gpt-mutable';
MUTABLE_MODEL = process.env.MODEL_ID ?? MUTABLE_MODEL;
const mutableModel = openai(MUTABLE_MODEL);

const composedPrefix = 'gpt';
const composedModelId = `${composedPrefix}-composed`;
const composedModel = openai(composedModelId);

const SHADOWED_MODEL = 'gpt-global';
function shadowed(SHADOWED_MODEL: string) {
  return openai(SHADOWED_MODEL);
}

const REBOUND_MODEL = 'gpt-original';
REBOUND_MODEL = 'gpt-rebound';
const reboundModel = openai(REBOUND_MODEL);

const forwardModel = openai(FORWARD_MODEL);
const FORWARD_MODEL = 'gpt-forward';

void mutableModel;
void composedModel;
void shadowed;
void reboundModel;
void forwardModel;

const runtimeSuffix = process.env.MODEL_SUFFIX ?? 'runtime';
const unknownTemplateModelId = `${composedPrefix}-${runtimeSuffix}`;
const unknownTemplateModel = openai(unknownTemplateModelId);

void unknownTemplateModel;
