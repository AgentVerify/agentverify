import { run } from '@openai/agents';
import { SandboxAgent } from '@openai/agents/sandbox';
import {
  UnixLocalSandboxClient as ReboundUnixLocalSandboxClient,
} from '@openai/agents/sandbox/local';

ReboundUnixLocalSandboxClient = ReplacementSandboxClient;

declare const manifest: unknown;
declare const unknownClient: { create(value: unknown): Promise<unknown> };

const reboundClient = new ReboundUnixLocalSandboxClient();
const reboundAgent = new SandboxAgent({
  name: 'Rebound Client Sandbox',
});
await run(reboundAgent, 'inspect the workspace', {
  sandbox: { client: reboundClient },
});

const unknownSession = await unknownClient.create(manifest);
const sessionAgent = new SandboxAgent({
  name: 'Unknown Session Sandbox',
});
await run(sessionAgent, 'inspect the workspace', {
  sandbox: { session: unknownSession },
});
