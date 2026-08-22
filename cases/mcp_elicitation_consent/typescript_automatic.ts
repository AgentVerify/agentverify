import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'automatic-client', version: '1.0.0' },
  { capabilities: { elicitation: { form: {}, url: {} } } },
);

client.setRequestHandler('elicitation/create', async request => {
  if (request.params.mode === 'url') {
    return { action: 'accept' };
  }
  return { action: 'accept', content: { city: 'Lisbon' } };
});
