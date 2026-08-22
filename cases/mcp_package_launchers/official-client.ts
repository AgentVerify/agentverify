import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';

const official = new StdioClientTransport({
  command: 'npx',
  args: ['-y', 'official-mcp-server'],
});
