import { SandboxAgent as LocalSandboxAgent, shell } from './local-sandbox';
import {
  SandboxAgent as ReboundSandboxAgent,
  shell as reboundShell,
} from '@openai/agents/sandbox';

const nearSandbox = new LocalSandboxAgent({
  name: 'Near Sandbox',
  capabilities: [shell()],
});

ReboundSandboxAgent = replacement;
const reboundSandbox = new ReboundSandboxAgent({
  name: 'Rebound Sandbox',
  capabilities: [reboundShell()],
});

function buildNearSandbox() {
  return new LocalSandboxAgent({
    name: 'Near Returned Sandbox',
    capabilities: [shell()],
  });
}

function buildReboundSandbox() {
  return new ReboundSandboxAgent({
    name: 'Rebound Returned Sandbox',
    capabilities: [reboundShell()],
  });
}

void nearSandbox;
void reboundSandbox;
void buildNearSandbox;
void buildReboundSandbox;
