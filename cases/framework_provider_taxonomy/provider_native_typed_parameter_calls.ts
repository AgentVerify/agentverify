import OpenAI from 'openai';

async function start() {
  await middle(new OpenAI({ apiKey: process.env.OPENAI_API_KEY }));
}

async function middle(client: OpenAI) {
  await leaf(client);
}

async function leaf(client: OpenAI) {
  await client.responses.create({ model: 'gpt-5.4' });
}
