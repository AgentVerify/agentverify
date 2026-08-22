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

import NativeAnthropic from '@anthropic-ai/sdk';
import { GoogleGenAI } from '@google/genai';
import NativeOpenAI from 'openai';

NativeOpenAI = fakeProvider;
NativeAnthropic = fakeProvider;
GoogleGenAI = fakeProvider;

const notNativeOpenAI = new NativeOpenAI();
const notNativeAnthropic = new NativeAnthropic();
const notNativeGoogle = new GoogleGenAI({});

const CommonJSOpenAI = require('openai');
const CommonJSAnthropic = require('@anthropic-ai/sdk');
CommonJSOpenAI = fakeProvider;
CommonJSAnthropic = fakeProvider;
const notCommonJSOpenAI = new CommonJSOpenAI();
const notCommonJSAnthropic = new CommonJSAnthropic();
