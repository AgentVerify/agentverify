import OpenAI from 'openai';

function replaceConstructor(OpenAI: unknown) {
  return new OpenAI();
}
