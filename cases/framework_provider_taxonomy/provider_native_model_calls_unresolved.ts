import OpenAI from 'openai';

const reboundClient = new OpenAI();
reboundClient = fakeProvider;
const reboundResponse = await reboundClient.responses.create({ model: 'gpt-rebound' });

const unknownClient = new OpenAI();
const unknownResponse = await unknownClient.responses.create(requestConfig);
const unrelatedResponse = await unknownClient.files.create({ model: 'not-a-model-call' });
