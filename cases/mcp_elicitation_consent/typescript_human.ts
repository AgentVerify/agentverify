import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'reviewed-client', version: '1.0.0' },
  { capabilities: { elicitation: { form: {}, url: {} } } },
);

client.setRequestHandler('elicitation/create', async request => {
  ui.attention(`${request.params.message}\n${request.params.url ?? ''}`);
  const approved = await ui.confirm('Accept this elicitation?');
  return approved
    ? { action: 'accept', content: { confirmed: true } }
    : { action: 'decline' };
});
