import { Agent, MCPServerStdio, createMCPToolStaticFilter } from '@openai/agents';
import { createRequire } from 'node:module';
const writable = new MCPServerStdio({
  name: 'Writable Files',
  fullCommand: 'pnpm exec mcp-server-filesystem ./workspace',
});
const writableAgent = new Agent({ name: 'Writer', mcpServers: [writable] });

const require = createRequire(import.meta.url);
const packageServer = new MCPServerStdio({
  name: 'Resolved Package Files',
  command: process.execPath,
  args: [
    require.resolve('@modelcontextprotocol/server-filesystem/dist/index.js'),
    './workspace',
  ],
});
const packageAgent = new Agent({ name: 'Package Writer', mcpServers: [packageServer] });

const readOnly = new MCPServerStdio({
  name: 'Read Only Files',
  fullCommand: 'pnpm exec mcp-server-filesystem ./workspace',
  toolFilter: createMCPToolStaticFilter({
    allowed: ['read_file', 'list_directory'],
    blocked: ['write_file'],
  }),
});
const reader = new Agent({ name: 'Reader', mcpServers: [readOnly] });

const unresolvedFilter = new MCPServerStdio({
  name: 'Unresolved Filter',
  fullCommand: 'pnpm exec mcp-server-filesystem ./workspace',
  toolFilter: createMCPToolStaticFilter({ allowed: ['read_file', 'write_file'] }),
});
const unresolvedAgent = new Agent({
  name: 'Unresolved Filter Agent',
  mcpServers: [unresolvedFilter],
});

const unbound = new MCPServerStdio({
  name: 'Unbound Files',
  fullCommand: 'pnpm exec mcp-server-filesystem ./workspace',
});
