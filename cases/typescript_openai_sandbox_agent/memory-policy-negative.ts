import { memory } from '@openai/agents/sandbox';

declare const dynamicMemoriesDir: string;
declare const dynamicSessionsDir: string;
declare const dynamicReadPolicy: boolean;
declare const dynamicGenerationPolicy: boolean;

const dynamicMemory = memory({
  layout: {
    memoriesDir: dynamicMemoriesDir,
    sessionsDir: dynamicSessionsDir,
  },
  read: dynamicReadPolicy,
  generate: dynamicGenerationPolicy,
});

void dynamicMemory;
