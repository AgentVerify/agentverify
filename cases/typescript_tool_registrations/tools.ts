import { createTool as mastraTool } from "@mastra/core/tools";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

export const lookup = mastraTool({
  id: "lookup",
  inputSchema: {},
  execute: async ({ query }) => fetch(`https://search.example?q=${query}`),
});

export const toolSet = {
  requester: mastraTool({
    id: "requester",
    inputSchema: {},
    execute: async ({ url }) => fetch(url),
  }),
};

const registeredName = "download";
const server = new McpServer({ name: "fixture", version: "1.0.0" });

server.registerTool(registeredName, {}, async ({ url }) => {
  return fetch(url);
});

server.registerTool("status", {}, async () => {
  return fetch("https://status.example/health");
});
