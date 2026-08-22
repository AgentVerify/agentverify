import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'real-client', version: '1.0.0' },
  { capabilities: { elicitation: { form: {} } } },
);
const other = makeLocalClient();

other.setRequestHandler('elicitation/create', async () => ({ action: 'accept', content: {} }));

void client;
