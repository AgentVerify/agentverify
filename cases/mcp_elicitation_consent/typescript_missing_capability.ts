import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'disabled-client', version: '1.0.0' },
  { capabilities: { sampling: {} } },
);

client.setRequestHandler('elicitation/create', async () => ({ action: 'accept', content: {} }));
