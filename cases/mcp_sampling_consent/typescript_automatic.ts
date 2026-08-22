import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'automatic-client', version: '1.0.0' },
  { capabilities: { sampling: {} } },
);

client.setRequestHandler('sampling/createMessage', async request => ({
  role: 'assistant',
  content: { type: 'text', text: request.params.messages.at(-1)?.content ?? 'response' },
  model: 'host-model',
}));
