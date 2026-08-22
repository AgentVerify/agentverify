import { Client } from '@local/mcp-client';

const client = new Client(
  { name: 'wrong-client', version: '1.0.0' },
  { capabilities: { sampling: {} } },
);

client.setRequestHandler('sampling/createMessage', async request => ({
  role: 'assistant',
  content: { type: 'text', text: String(request.params) },
  model: 'host-model',
}));
