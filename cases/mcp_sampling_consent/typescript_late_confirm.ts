import { Client } from '@modelcontextprotocol/client';

const client = new Client(
  { name: 'late-confirm-client', version: '1.0.0' },
  { capabilities: { sampling: {} } },
);

client.setRequestHandler('sampling/createMessage', async request => {
  const result = await provider.generate({ messages: request.params.messages });
  const approved = await ui.confirm('Allow?');
  if (!approved) {
    throw new Error('User rejected sampling request');
  }
  return {
    role: 'assistant',
    content: { type: 'text', text: result.text },
    model: result.model,
  };
});
