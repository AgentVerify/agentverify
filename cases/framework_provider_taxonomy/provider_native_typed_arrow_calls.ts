import OpenAI from 'openai';

const startArrow = async () => {
  await middleArrow(new OpenAI({ apiKey: process.env.OPENAI_API_KEY }));
};

const middleArrow = async (client: OpenAI) => {
  await leafArrow(client);
};

const leafArrow = async (client: OpenAI) => {
  await client.responses.create({ model: 'gpt-arrow' });
};
