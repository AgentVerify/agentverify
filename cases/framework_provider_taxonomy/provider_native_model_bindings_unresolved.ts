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
