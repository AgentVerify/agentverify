import OpenAI from 'openai';

const MODEL_ID: string = 'gpt-5.4';
const client = new OpenAI();
const response = await client.responses.create({ model: MODEL_ID });
void response;
