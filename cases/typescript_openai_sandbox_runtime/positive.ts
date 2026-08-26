import { run } from '@openai/agents';
import { SandboxAgent, shell } from '@openai/agents/sandbox';
import {
  DockerSandboxClient,
  UnixLocalSandboxClient,
} from '@openai/agents/sandbox/local';

declare const manifest: unknown;

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
