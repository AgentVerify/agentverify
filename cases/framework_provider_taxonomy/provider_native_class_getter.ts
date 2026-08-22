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
