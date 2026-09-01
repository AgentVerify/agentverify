import { Agent, hostedMcpTool } from "@openai/agents";
import { importedPolicy as starPolicy } from "./star";
import { importedPolicy as ambiguousStarPolicy } from "./ambiguous-star";

const starAgent = new Agent({
  name: "Hosted MCP star policy agent",
  tools: [
    hostedMcpTool({
      serverLabel: "star",
      serverUrl: "https://mcp.example.com/mcp",
      requireApproval: starPolicy,
    }),
    hostedMcpTool({
      serverLabel: "ambiguous-star",
      serverUrl: "https://mcp.example.com/mcp",
      requireApproval: ambiguousStarPolicy,
    }),
  ],
});
void starAgent;
