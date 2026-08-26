import { run } from '@openai/agents';
import {
  SandboxAgent,
  SandboxAgent as AliasedSandboxAgent, filesystem, memory,
  shell,
  shell as sandboxShell,
} from '@openai/agents/sandbox';

const localSandbox = new SandboxAgent({
  name: 'Local Sandbox Assistant',
  model: 'gpt-5-mini',
  capabilities: [filesystem(), shell()],
});

const aliasedSandbox = new AliasedSandboxAgent({
  name: 'Aliased Sandbox Assistant',
  capabilities: [
    sandboxShell(),
  ],
});

function buildReturnedSandboxAgent(name: string) {
  return new SandboxAgent({
    name,
    capabilities: [memory({ generate: false }), shell()],
  });
}

const buildNamedReturnedSandboxAgent = () => {
  return new AliasedSandboxAgent({
    name: 'Returned Named Sandbox Assistant',
    capabilities: [sandboxShell()],
  });
};

function buildConditionalReturnedSandboxAgent(enabled: boolean) {
  if (enabled) {
    return new SandboxAgent({
      name: 'Conditional Returned Sandbox Assistant',
      capabilities: [shell()],
    });
  }
  return localSandbox;
}

await run(localSandbox, 'Inspect the project.');
await run(aliasedSandbox, 'Inspect the project.');
await run(buildReturnedSandboxAgent('Returned Dynamic Sandbox Assistant'), 'Inspect the project.');
await run(buildNamedReturnedSandboxAgent(), 'Inspect the project.');
void buildConditionalReturnedSandboxAgent;
