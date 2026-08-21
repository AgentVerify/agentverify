import { Agent, tool } from "@openai/agents";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { exec } from "node:child_process";

const client = new Client({ name: "example", version: "1.0.0" });

const runCommand = tool({
  name: "run_command",
  execute: async ({ command }) => exec(command),
});

const agent = new Agent({
  name: "operator",
  model: "gpt-5",
  tools: [runCommand],
});

const autoApprove = true; // Intentionally unsafe regression case.
const result = await client.callTool({ name: toolName, arguments: params });
