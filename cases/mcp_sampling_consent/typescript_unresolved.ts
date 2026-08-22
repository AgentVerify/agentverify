import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'unresolved-client', version: '1.0.0' },
  { capabilities: { sampling: {} } },
);

client.setRequestHandler('sampling/createMessage', handleSampling);
