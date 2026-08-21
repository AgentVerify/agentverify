import { Agent, tool } from "@openai/agents";
import { exec } from "node:child_process";

const approvedCommand = tool({
  name: "approved_command",
  needsApproval: true,
  execute: async ({ command }) => exec(command),
});

const conditionalCommand = tool({
  name: "conditional_command",
  // needsApproval: true would make every invocation require approval.
  needsApproval: async (_context, { command }) => command.startsWith("git status"),
  execute: async ({ command }) => exec(command),
});

const disabledApproval = tool({
  name: "disabled_approval",
  description: "The literal text needsApproval: true is not a policy.",
  needsApproval: false,
  execute: async ({ command }) => exec(command),
});

const agent = new Agent({
  name: "operator",
  tools: [approvedCommand, conditionalCommand, disabledApproval],
});

void agent;
