import { Runner, run } from '@openai/agents';
import { SandboxAgent, shell } from '@openai/agents/sandbox';
import { BlaxelSandboxClient } from '@openai/agents-extensions/sandbox/blaxel';
import {
  DockerSandboxClient,
  UnixLocalSandboxClient,
} from '@openai/agents/sandbox/local';

declare const manifest: unknown;
declare const useDocker: boolean;

const directClient = new UnixLocalSandboxClient();
const directAgent = new SandboxAgent({
  name: 'Direct Client Sandbox',
  capabilities: [shell()],
});
await run(directAgent, 'inspect the workspace', {
  sandbox: { client: directClient },
});

const dockerClient = new DockerSandboxClient({ image: 'python:3.14-slim' });
const dockerSession = await dockerClient.create(manifest);
const dockerAgent = new SandboxAgent({
  name: 'Docker Session Sandbox',
  capabilities: [shell()],
});
await run(dockerAgent, 'inspect the workspace', {
  sandbox: { session: dockerSession },
});

const inlineAgent = new SandboxAgent({
  name: 'Inline Client Sandbox',
  capabilities: [shell()],
});
await run(inlineAgent, 'inspect the workspace', {
  sandbox: { client: new UnixLocalSandboxClient() },
});

const client = new UnixLocalSandboxClient();
const session = await client.create(manifest);
const shorthandAgent = new SandboxAgent({
  name: 'Session Shorthand Sandbox',
  capabilities: [shell()],
});
await run(shorthandAgent, 'inspect the workspace', {
  sandbox: { session },
});

const conditionalClient = useDocker
  ? (() => {
      return new DockerSandboxClient({ image: 'python:3.14-slim' });
    })()
  : new UnixLocalSandboxClient();
const conditionalSession = await conditionalClient.create(manifest);
const conditionalAgent = new SandboxAgent({
  name: 'Conditional Runtime Sandbox',
  capabilities: [shell()],
});
await run(conditionalAgent, 'inspect the workspace', {
  sandbox: { session: conditionalSession },
});

const resumableClient = client as {
  resume(value: unknown): Promise<unknown>;
};
let resumedSession: unknown;
resumedSession = await resumableClient.resume(session);
const resumedAgent = new SandboxAgent({
  name: 'Resumed Session Sandbox',
  capabilities: [shell()],
});
await run(resumedAgent, 'inspect the workspace', {
  sandbox: { session: resumedSession },
});

const extensionClient = new BlaxelSandboxClient({ image: 'node:22-bookworm-slim' });
const runnerAgent = new SandboxAgent({
  name: 'Runner Extension Sandbox',
  capabilities: [shell()],
});
const runner = new Runner({
  workflowName: 'extension sandbox example',
  sandbox: { client: extensionClient },
});
await runner.run(runnerAgent, 'inspect the cloud sandbox');
