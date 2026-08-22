import OpenAI from 'openai';

class MutableField {
  private client: OpenAI;
  constructor() {
    this.client = new OpenAI();
  }
  async generate() {
    return this.client.responses.create({ model: 'gpt-mutable' });
  }
}

class ReassignedField {
  private readonly client: OpenAI;
  constructor() {
    this.client = new OpenAI();
    this.client = new OpenAI();
  }
  async generate() {
    return this.client.responses.create({ model: 'gpt-reassigned' });
  }
}

class CustomEndpointField {
  private readonly client: OpenAI;
  constructor() {
    this.client = new OpenAI({ baseURL: 'https://proxy.example/v1' });
  }
  async generate() {
    return this.client.responses.create({ model: 'gpt-custom' });
  }
}

class UnrelatedMethodField {
  private readonly client: OpenAI;
  constructor() {
    this.client = new OpenAI();
  }
  async upload() {
    return this.client.files.create({ model: 'not-a-model-request' });
  }
}

class CrossScopeField {
  private readonly client: FakeOpenAI;
  async generate() {
    return this.client.responses.create({ model: 'gpt-cross-scope' });
  }
  buildLocalClient() {
    class LocalClient {
      private readonly client: OpenAI;
      constructor() {
        this.client = new OpenAI();
      }
    }
    return LocalClient;
  }
}
