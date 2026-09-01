import { Agent, hostedMcpTool } from "@openai/agents";
import readline from "node:readline/promises";

async function promptApproval(item: { name: string }) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const answer = await rl.question(`Approve hosted MCP tool ${item.name}? `);
  rl.close();
  return answer.trim().toLowerCase() === "yes";
}

async function approveSomehow() {
  return Math.random() > 0.5;
}

const agent = new Agent({
  name: "Hosted MCP callback policy agent",
  tools: [
    hostedMcpTool({
      serverLabel: "prompted",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => {
        const approved = await promptApproval(item);
        return { approve: approved };
      },
    }),

    hostedMcpTool({
      serverLabel: "opaque",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async () => ({ approve: await approveSomehow() }),
    }),

    // Keep this fallback case on a unique occurrence-qualified line anchor.
    // The wider fixture already has hostedMcpTool@36 in agent.ts.
    hostedMcpTool({
      serverLabel: "fallback",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => {
        const approved = item ? await promptApproval(item) : false;
        return { approve: approved };
      },
    }),
    hostedMcpTool({
      serverLabel: "predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => ({
        approve: item.name !== "delete_page",
      }),
    }),
    hostedMcpTool({
      serverLabel: "local-predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async () => {
        const item = { name: "delete_page" };
        return { approve: item.name !== "delete_page" };
      },
    }),
    hostedMcpTool({
      serverLabel: "prefix-predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => ({
        approve: item.name.startsWith("read_"),
      }),
    }),
    hostedMcpTool({
      serverLabel: "contains-predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => ({
        approve: item.name.includes("_read_"),
      }),
    }),
    hostedMcpTool({
      serverLabel: "set-predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => ({
        approve: ["read_page", "list_pages"].includes(item.name),
      }),
    }),
    hostedMcpTool({
      serverLabel: "local-set-predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => {
        const allowed = ["read_page", "list_pages"];
        return { approve: allowed.includes(item.name) };
      },
    }),
    hostedMcpTool({
      serverLabel: "destructured-predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, { name }) => ({
        approve: name === "read_page",
      }),
    }),
    hostedMcpTool({
      serverLabel: "nested-number-predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => ({
        approve: item.data.riskScore !== 10,
      }),
    }),
    hostedMcpTool({
      serverLabel: "nested-boolean-predicate",
      serverUrl: "https://mcp.example.test/mcp",
      requireApproval: "always",
      onApproval: async (_context, item) => ({
        approve: item.data.readOnly === true,
      }),
    }),
  ],
});
void agent;
