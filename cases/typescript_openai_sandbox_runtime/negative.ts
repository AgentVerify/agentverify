import { Agent, Runner, run } from '@openai/agents';
import { SandboxAgent } from '@openai/agents/sandbox';
import {
  UnixLocalSandboxClient,
  UnixLocalSandboxClient as ReboundUnixLocalSandboxClient,
} from '@openai/agents/sandbox/local';

ReboundUnixLocalSandboxClient = ReplacementSandboxClient;

declare const manifest: unknown;
declare const useDocker: boolean;
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

const halfKnownClient = useDocker
  ? unknownClient
  : new UnixLocalSandboxClient();
const halfKnownSession = await halfKnownClient.create(manifest);
const halfKnownAgent = new SandboxAgent({
  name: 'Half Known Conditional Sandbox',
});
await run(halfKnownAgent, 'inspect the workspace', {
  sandbox: { session: halfKnownSession },
});

const unknownResumableClient = unknownClient as {
  resume(value: unknown): Promise<unknown>;
};
let unknownResumedSession: unknown;
unknownResumedSession = await unknownResumableClient.resume(manifest);
const unknownResumedAgent = new SandboxAgent({
  name: 'Unknown Resumed Session Sandbox',
});
await run(unknownResumedAgent, 'inspect the workspace', {
  sandbox: { session: unknownResumedSession },
});

const unknownRunnerAgent = new SandboxAgent({
  name: 'Unknown Runner Sandbox',
});
const unknownRunner = new Runner({
  sandbox: { client: unknownClient },
});
await unknownRunner.run(unknownRunnerAgent, 'inspect the workspace');

const inlineUnknownSession = await new UnknownSandboxClient().create(manifest);
const inlineUnknownAgent = new SandboxAgent({
  name: 'Unknown Inline Created Session Sandbox',
});
await run(inlineUnknownAgent, 'inspect the workspace', {
  sandbox: { session: inlineUnknownSession },
});

function buildUnknownHelperAgent() {
  return new UnknownSandboxAgent({
    name: 'Unknown Helper Runtime Sandbox',
  });
}

const unknownHelperRuntimeAgent = buildUnknownHelperAgent();
await run(unknownHelperRuntimeAgent, 'inspect the helper workspace', {
  sandbox: { session: inlineUnknownSession },
});

const unknownOptionRunnerAgent = new SandboxAgent({
  name: 'Unknown Option Runner Sandbox',
});
const unknownOptionRunner = new Runner({
  workflowName: 'unknown option session example',
});
await unknownOptionRunner.run(unknownOptionRunnerAgent, 'inspect the option workspace', {
  sandbox: { session: inlineUnknownSession },
});

const unknownAsToolRuntimeAgent = new SandboxAgent({
  name: 'Unknown asTool Runtime Sandbox',
});
const unknownAsToolOrchestrator = new Agent({
  name: 'Unknown asTool Runtime Orchestrator',
  tools: [
    unknownAsToolRuntimeAgent.asTool({
      toolName: 'review_unknown_sandbox_workspace',
      runConfig: {
        sandbox: { session: inlineUnknownSession },
      },
    }),
  ],
});

const unknownExposedPortClient = new UnknownSandboxClient({
  exposedPorts: [3000],
});

declare const dynamicSnapshotBaseDir: string;
const unknownSnapshotClient = new UnknownSandboxClient({
  snapshot: {
    type: 'local',
    baseDir: '/tmp/agentverify-sandbox-snapshots',
  },
});
const unknownGrantManifest = new UnknownManifest({
  entries: {
    'task.md': file({ content: 'untrusted' }),
  },
  extraPathGrants: [
    {
      path: '/tmp/agentverify-skills',
      readOnly: true,
    },
  ],
  environment: {
    NODE_ENV: 'unknown',
  },
});

declare const runtimeLimit: number;
const unknownLimitedConcurrencyAgent = new SandboxAgent({
  name: 'Unknown Limited Concurrency Sandbox',
});
await run(unknownLimitedConcurrencyAgent, 'inspect with unknown limits', {
  sandbox: {
    client: unknownClient,
    concurrencyLimits: {
      manifestEntries: 4,
      localDirFiles: runtimeLimit,
    },
  },
});

declare const dynamicRoot: string;
const unknownRootManifest = new UnknownManifest({
  root: '/workspace',
});
const dynamicRootManifest = new Manifest({
  root: dynamicRoot,
});
