import { mcpTransport } from "./mcp-transport";

export const mcpToolValidator = {
  async validateAgentMcpTool(tool: any) {
    const transport = mcpTransport.createTransport({
      protocol: tool.protocol,
      serverUrl: tool.serverUrl,
      auth: tool.auth,
    });
    const client = new Client({ name: "validator", version: "1" });
    await client.connect(transport);
    return client.listTools();
  },
};
