import { mistral as hostedMistral } from '@ai-sdk/mistral';
import { createGroq as buildGroq } from '@ai-sdk/groq';
import { cohere } from '@ai-sdk/cohere';

hostedMistral = fakeProvider;
buildGroq = fakeFactory;
cohere = fakeProvider;

const notMistral = hostedMistral('mistral-small-latest');
const notGroq = buildGroq({});
const notCohere = cohere('command-r-plus');

async function nearNamePackage() {
  const { groq } = await import('@ai-sdk/groq-adapter');
  return groq('llama-3.3-70b-versatile');
}
