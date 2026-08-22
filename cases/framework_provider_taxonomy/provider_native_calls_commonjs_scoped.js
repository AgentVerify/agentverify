function buildClient() {
  const ScopedOpenAI = require('openai');
  return new ScopedOpenAI();
}
