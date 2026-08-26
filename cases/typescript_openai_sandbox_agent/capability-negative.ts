import {
  SandboxAgent,
  filesystem as reboundFilesystem,
  memory as reboundMemory,
} from '@openai/agents/sandbox';

reboundFilesystem = replacementFilesystem;
reboundMemory = replacementMemory;

const agent = new SandboxAgent({
  name: 'Capability Shadow Sandbox',
  capabilities: [reboundFilesystem(), reboundMemory()],
});

void agent;
