import { Agent, hostedMcpTool } from "@openai/agents";

function fakeHostedMcpTool(options: unknown) {
  return options;
}

const agent = new Agent({
  name: "Hosted MCP policy agent",
  tools: [
    hostedMcpTool({
      serverLabel: "deepwiki",
      serverUrl: "https://mcp.deepwiki.com/mcp",
    }),
    hostedMcpTool({
      serverLabel: "calendar",
      connectorId: "connector_googlecalendar",
      requireApproval: "never",
    }),
    hostedMcpTool({
      serverLabel: "wiki",
      serverUrl: "https://mcp.deepwiki.com/mcp",
      requireApproval: {
        never: { toolNames: ["read_wiki_structure"], readOnly: true },
        always: { toolNames: ["ask_question"] },
      },
      onApproval: async () => ({ approve: false }),
    }),
    fakeHostedMcpTool({
      serverLabel: "fake",
      requireApproval: "always",
    }),
  ],
});
void agent;
