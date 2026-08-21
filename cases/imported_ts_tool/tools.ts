import { tool } from "@openai/agents";
import { exec } from "node:child_process";

export const runCommand = tool({
  name: "run_command",
  needsApproval: true,
  execute: async ({ command }) => exec(command),
});
