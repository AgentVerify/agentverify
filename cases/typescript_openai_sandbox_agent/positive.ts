import { run } from '@openai/agents';
import {
  SandboxAgent,
  SandboxAgent as AliasedSandboxAgent,
  shell,
  shell as sandboxShell,
} from '@openai/agents/sandbox';

const localSandbox = new SandboxAgent({
  name: 'Local Sandbox Assistant',
  model: 'gpt-5-mini',
  capabilities: [shell()],
});

const aliasedSandbox = new AliasedSandboxAgent({
  name: 'Aliased Sandbox Assistant',
  capabilities: [
    sandboxShell(),
  ],
});

await run(localSandbox, 'Inspect the project.');
await run(aliasedSandbox, 'Inspect the project.');
