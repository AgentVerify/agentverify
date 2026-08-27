import { Agent, Runner, run } from '@openai/agents';
import { file, gitRepo, localDir, Manifest, SandboxAgent, shell } from '@openai/agents/sandbox';
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

const inlineCreatedSession = await new DockerSandboxClient({
  image: 'python:3.14-slim',
}).create(manifest);
const inlineCreatedAgent = new SandboxAgent({
  name: 'Inline Created Session Sandbox',
  capabilities: [shell()],
});
await run(inlineCreatedAgent, 'inspect the workspace', {
  sandbox: { session: inlineCreatedSession },
});

function buildHelperRuntimeAgent() {
  return new SandboxAgent({
    name: 'Helper Runtime Sandbox',
    capabilities: [shell()],
  });
}

const helperRuntimeAgent = buildHelperRuntimeAgent();
await run(helperRuntimeAgent, 'inspect the helper workspace', {
  sandbox: { session },
});

const optionRunnerAgent = new SandboxAgent({
  name: 'Runner Option Session Sandbox',
  capabilities: [shell()],
});
const optionRunner = new Runner({
  workflowName: 'option session example',
});
await optionRunner.run(optionRunnerAgent, 'inspect the option workspace', {
  sandbox: { session },
});

type SandboxSessionState = unknown;
const typedSession: SandboxSessionState = await client.create(manifest);
const typedOptionRunnerAgent = new SandboxAgent({
  name: 'Typed Runner Option Session Sandbox',
  capabilities: [shell()],
});
const typedOptionRunner = new Runner({
  workflowName: 'typed option session example',
});
await typedOptionRunner.run(typedOptionRunnerAgent, 'inspect the typed option workspace', {
  sandbox: { session: typedSession },
});

const asToolRuntimeAgent = new SandboxAgent({
  name: 'asTool Runtime Sandbox',
  capabilities: [shell()],
});
const asToolOrchestrator = new Agent({
  name: 'asTool Runtime Orchestrator',
  tools: [
    asToolRuntimeAgent.asTool({
      toolName: 'review_sandbox_workspace',
      runConfig: {
        sandbox: { session },
      },
    }),
  ],
});

const exposedPortClient = new DockerSandboxClient({
  image: 'node:22-bookworm-slim',
  exposedPorts: [3000, 8080],
});

const sharedSkillsDir = '/opt/company/agent-skills';
const sandboxNodeEnv = 'integration';
const localRepoDir = '/opt/company/repo-template';
const grantManifest = new Manifest({
  entries: {
    'task.md': file({ content: 'Fix the failing test.' }),
    repo: gitRepo({ repo: 'openai/openai-agents-js', ref: 'main' }),
    localRepo: localDir({ src: localRepoDir }),
  },
  extraPathGrants: [
    {
      path: sharedSkillsDir,
      readOnly: true,
      description: 'Shared skill bundle.',
    },
  ],
  environment: {
    NODE_ENV: sandboxNodeEnv,
    SANDBOX_TOKEN: 'do-not-copy',
  },
});

const limitedConcurrencyAgent = new SandboxAgent({
  name: 'Limited Concurrency Sandbox',
  capabilities: [shell()],
});
await run(limitedConcurrencyAgent, 'inspect with bounded manifest work', {
  sandbox: {
    client: directClient,
    concurrencyLimits: {
      manifestEntries: 4,
      localDirFiles: 16,
    },
  },
});
