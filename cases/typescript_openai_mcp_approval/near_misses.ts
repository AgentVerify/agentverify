import { Agent as OtherAgent, MCPServerStdio as OtherServer } from 'unrelated-agents';

const unrelated = new OtherServer({
  fullCommand: 'pnpm exec mcp-server-filesystem ./workspace',
});
const unrelatedAgent = new OtherAgent({ mcpServers: [unrelated] });

import { Agent, MCPServerStdio } from '@openai/agents';
MCPServerStdio = class FakeServer {};
const rebound = new MCPServerStdio({
  fullCommand: 'pnpm exec mcp-server-filesystem ./workspace',
});
const reboundAgent = new Agent({ mcpServers: [rebound] });
