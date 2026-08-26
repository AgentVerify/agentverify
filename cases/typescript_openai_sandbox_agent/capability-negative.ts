import {
  SandboxAgent,
  filesystem as reboundFilesystem,
  memory as reboundMemory,
  skills as reboundSkills,
} from '@openai/agents/sandbox';

reboundFilesystem = replacementFilesystem;
reboundMemory = replacementMemory;
reboundSkills = replacementSkills;

const agent = new SandboxAgent({
  name: 'Capability Shadow Sandbox',
  capabilities: [reboundFilesystem(), reboundMemory(), reboundSkills()],
});

void agent;
