import OpenAI from 'openai';

const client = new OpenAI();

let MUTABLE_MODEL = 'gpt-mutable';
MUTABLE_MODEL = process.env.MODEL_ID ?? MUTABLE_MODEL;
await client.responses.create({ model: MUTABLE_MODEL });

await client.responses.create({ model: LATE_MODEL });
const LATE_MODEL = 'gpt-late';

const MODEL_PREFIX = 'gpt';
const COMPOSED_MODEL = `${MODEL_PREFIX}-composed`;
await client.responses.create({ model: COMPOSED_MODEL });

const SHADOWED_MODEL = 'gpt-global';
async function shadowed(SHADOWED_MODEL: string) {
  return client.responses.create({ model: SHADOWED_MODEL });
}

const REBOUND_MODEL = 'gpt-original';
REBOUND_MODEL = 'gpt-rebound';
await client.responses.create({ model: REBOUND_MODEL });

void shadowed;

const runtimeSuffix = process.env.MODEL_SUFFIX ?? 'runtime';
const UNKNOWN_TEMPLATE_MODEL = `${MODEL_PREFIX}-${runtimeSuffix}`;
await client.responses.create({ model: UNKNOWN_TEMPLATE_MODEL });

const MUTABLE_MODEL_IDS = {
  chat: 'gpt-object-original',
};
MUTABLE_MODEL_IDS.chat = process.env.MODEL_ID ?? MUTABLE_MODEL_IDS.chat;
await client.responses.create({ model: MUTABLE_MODEL_IDS.chat });

const UNKNOWN_MODEL_IDS = {
  chat: `${MODEL_PREFIX}-${runtimeSuffix}`,
};
await client.responses.create({ model: UNKNOWN_MODEL_IDS.chat });
