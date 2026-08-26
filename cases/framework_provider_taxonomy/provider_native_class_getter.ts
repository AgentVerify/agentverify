import Anthropic from '@anthropic-ai/sdk';

class LazyAnthropicService {
  private _client: Anthropic | null = null;
  private get client(): Anthropic {
    return this._client ??= new Anthropic();
  }
  async generate(requestConfig: object) {
    return this.client.messages.create(requestConfig);
  }
}

const ANTHROPIC_MODEL = 'claude-sonnet-4-6-local';

class MCPStyleLazyAnthropicService {
  private _anthropic: Anthropic | null = null;
  private tools: Anthropic.Tool[] = [];

  private get anthropic(): Anthropic {
    return this._anthropic ??= new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  }

  async processQuery(messages: Anthropic.MessageParam[]) {
    return this.anthropic.messages.create({
      model: ANTHROPIC_MODEL,
      max_tokens: 1000,
      messages,
      tools: this.tools,
    });
  }
}
