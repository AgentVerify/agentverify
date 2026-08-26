import OpenAI from 'openai';

export const exportedArrow = async (client: OpenAI) => {
  await client.responses.create({ model: 'gpt-exported-arrow' });
};

exportedArrow(new OpenAI());

const mixedArrow = async (client: OpenAI) => {
  await client.responses.create({ model: 'gpt-mixed-arrow' });
};

mixedArrow(new OpenAI());
mixedArrow(fakeProvider);

const escapedArrow = async (client: OpenAI) => {
  await client.responses.create({ model: 'gpt-escaped-arrow' });
};

registerCallback(escapedArrow);
escapedArrow(new OpenAI());

const expressionArrow = (client: OpenAI) =>
  client.responses.create({ model: 'gpt-expression-arrow' });

expressionArrow(new OpenAI());
