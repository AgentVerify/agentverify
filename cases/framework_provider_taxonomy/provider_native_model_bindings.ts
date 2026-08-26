import OpenAI from 'openai';

const MODEL_ID: string = 'gpt-5.4';
const client = new OpenAI();
const response = await client.responses.create({ model: MODEL_ID });
const MODEL_IDS = {
  chat: 'gpt-5.4-object',
} as const;
const objectResponse = await client.responses.create({ model: MODEL_IDS.chat });
void response;
void objectResponse;
