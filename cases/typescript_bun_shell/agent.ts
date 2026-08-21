import { Agent, createTool } from "@cline/sdk";

const agent = new Agent({
  name: "operator",
  tools: [
    createTool({
      name: "dynamic_shell",
      execute: async (input) => Bun.spawn(["sh", "-c", input.command]),
    }),
    createTool({
      name: "fixed_shell",
      execute: async () => Bun.spawn(["sh", "-c", "pwd"]),
    }),
    createTool({
      name: "argv",
      execute: async () => Bun.spawn(["git", "status"]),
    }),
  ],
});

const documentation = 'Bun.spawn(["sh", "-c", input.command])';
