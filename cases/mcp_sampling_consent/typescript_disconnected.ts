import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'real-client', version: '1.0.0' },
  { capabilities: { sampling: {} } },
);
const other = makeLocalClient();

other.setRequestHandler('sampling/createMessage', async request => ({
  role: 'assistant',
  content: { type: 'text', text: String(request.params) },
  model: 'host-model',
}));

void client;
