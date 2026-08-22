import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'nested-result-client', version: '1.0.0' },
  { capabilities: { elicitation: { form: {} } } },
);

client.setRequestHandler('elicitation/create', async () => {
  return { result: { action: 'accept', content: {} } };
});
