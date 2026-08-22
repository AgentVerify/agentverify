import OpenAI from 'openai';

class CustomEndpointGetter {
  private _client: OpenAI | null = null;
  private get client(): OpenAI {
    return this._client ??= new OpenAI({ baseURL: 'https://proxy.example/v1' });
  }
  generate() {
    return this.client.responses.create({ model: 'gpt-custom-getter' });
  }
}

class ReassignedBackingField {
  private _client: OpenAI | null = null;
  private get client(): OpenAI {
    return this._client ??= new OpenAI();
  }
  reset() {
    this._client = null;
  }
  generate() {
    return this.client.responses.create({ model: 'gpt-reassigned-getter' });
  }
}

class PublicGetter {
  private _client: OpenAI | null = null;
  get client(): OpenAI {
    return this._client ??= new OpenAI();
  }
  generate() {
    return this.client.responses.create({ model: 'gpt-public-getter' });
  }
}

class UncachedGetter {
  private get client(): OpenAI {
    return new OpenAI();
  }
  generate() {
    return this.client.responses.create({ model: 'gpt-uncached-getter' });
  }
}

class UnrelatedGetterMethod {
  private _client: OpenAI | null = null;
  private get client(): OpenAI {
    return this._client ??= new OpenAI();
  }
  upload() {
    return this.client.files.create({ model: 'not-a-model-request' });
  }
}
