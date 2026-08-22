import { Client } from '@modelcontextprotocol/client';

let client = new Client(
  { name: 'reassigned-client', version: '1.0.0' },
  { capabilities: { elicitation: { form: {} } } },
);
client = makeLocalClient();

client.setRequestHandler('elicitation/create', async () => ({
  action: 'accept',
  content: {},
}));
