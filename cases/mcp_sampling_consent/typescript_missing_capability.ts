import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'disabled-client', version: '1.0.0' },
  { capabilities: { roots: {} } },
);

client.setRequestHandler('sampling/createMessage', async request => ({
  role: 'assistant',
  content: { type: 'text', text: String(request.params) },
  model: 'host-model',
}));
