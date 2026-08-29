class FakeAgent {
  clone(config: { name: string }) {
    return config;
  }
}

export const fakeAgent = new FakeAgent();
