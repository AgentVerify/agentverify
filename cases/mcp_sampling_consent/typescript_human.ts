import { Client } from '@modelcontextprotocol/client';

class Host {
  constructor(private ui: UI, private provider: Provider) {}

  register(client: Client): void {
    client.setRequestHandler('sampling/createMessage', async request => {
      const requestText = [
        `system: ${request.params.systemPrompt ?? ''}`,
        ...request.params.messages.map(message => `${message.role}: ${message.content}`),
      ].join('\n');
      this.ui.attention(requestText);
      const grantedMaxTokens = Math.min(request.params.maxTokens, 512);
      const approved = await this.ui.confirm('Allow?');
      if (!approved) {
        throw new Error('User rejected sampling request');
      }
      const result = await this.provider.generate({
        messages: request.params.messages,
        maxTokens: grantedMaxTokens,
      });
      return {
        role: 'assistant',
        content: { type: 'text', text: result.text },
        model: result.model,
      };
    });
  }
}

const client = new Client(
  { name: 'reviewed-client', version: '1.0.0' },
  { capabilities: { sampling: {} } },
);
const host = new Host(ui, provider);
host.register(client);
