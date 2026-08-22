import { Client } from '@local/mcp-client';

const client = new Client(
  { name: 'wrong-client', version: '1.0.0' },
  { capabilities: { elicitation: { form: {} } } },
);

client.setRequestHandler('elicitation/create', async () => ({ action: 'accept', content: {} }));
