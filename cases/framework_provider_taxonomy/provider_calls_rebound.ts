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

import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { openai } from '@ai-sdk/openai';
import { xai } from '@ai-sdk/xai';

openai = fakeProvider;
createAnthropic = fakeFactory;
createGoogleGenerativeAI = fakeFactory;
xai = fakeProvider;

const notOpenAI = openai('gpt-5-mini');
const notAnthropic = createAnthropic({});
const notGoogle = createGoogleGenerativeAI({});
const notXai = xai('grok-4');
