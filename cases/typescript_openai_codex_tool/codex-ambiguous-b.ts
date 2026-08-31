import { codexTool } from "@openai/agents-extensions/experimental/codex";

export const ambiguousCodex = codexTool({
  sandboxMode: "workspace-write",
  defaultThreadOptions: {
    approvalPolicy: "never",
  },
});

