import { Agent, hostedMcpTool } from "@openai/agents";
import {
  aliasedPolicy as importedAliasedPolicy,
  importedPolicy,
  mutatedExport,
} from "./policies";

function fakeHostedMcpTool(options: unknown) {
  return options;
}

const stablePolicy = {
  never: { toolNames: ["list_pages"], readOnly: true },
  always: { toolNames: ["write_page"] },
};

const mutatedPolicy = {
  never: { toolNames: ["read"] },
  always: { toolNames: ["write"] },
};
mutatedPolicy.always = { toolNames: ["delete"] };

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
    hostedMcpTool({
      serverLabel: "bound",
      serverUrl: "https://mcp.example.com/mcp",
      requireApproval: stablePolicy,
    }),
    hostedMcpTool({
      serverLabel: "mutated",
      serverUrl: "https://mcp.example.com/mcp",
      requireApproval: mutatedPolicy,
    }),
    hostedMcpTool({
      serverLabel: "imported",
      serverUrl: "https://mcp.example.com/mcp",
      requireApproval: importedPolicy,
    }),
    hostedMcpTool({
      serverLabel: "imported-aliased",
      serverUrl: "https://mcp.example.com/mcp",
      requireApproval: importedAliasedPolicy,
    }),
    hostedMcpTool({
      serverLabel: "imported-mutated",
      serverUrl: "https://mcp.example.com/mcp",
      requireApproval: mutatedExport,
    }),
    fakeHostedMcpTool({
      serverLabel: "fake",
      requireApproval: "always",
    }),
  ],
});
void agent;
