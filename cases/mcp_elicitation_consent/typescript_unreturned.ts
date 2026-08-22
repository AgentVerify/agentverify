import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'unreturned-client', version: '1.0.0' },
  { capabilities: { elicitation: { form: {} } } },
);

client.setRequestHandler('elicitation/create', async () => {
  const preview = { action: 'accept', content: { ignored: true } };
  void preview;
  return { action: 'decline' };
});
