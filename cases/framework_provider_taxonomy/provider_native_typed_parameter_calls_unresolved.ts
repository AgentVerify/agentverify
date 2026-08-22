import OpenAI from 'openai';

export async function externallyCallable(client: OpenAI) {
  await client.responses.create({ model: 'gpt-exported' });
}

async function mixedCallSites(client: OpenAI) {
  await client.responses.create({ model: 'gpt-mixed' });
}

mixedCallSites(new OpenAI());
mixedCallSites(fakeProvider);

async function cycleA(client: OpenAI) {
  await cycleB(client);
}

async function cycleB(client: OpenAI) {
  await cycleA(client);
  await client.responses.create({ model: 'gpt-cycle' });
}

async function escapedCallback(client: OpenAI) {
  await client.responses.create({ model: 'gpt-escaped' });
}

registerCallback(escapedCallback);
escapedCallback(new OpenAI());
