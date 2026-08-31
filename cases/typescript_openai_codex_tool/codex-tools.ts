import { codexTool } from "@openai/agents-extensions/experimental/codex";

export const importedCodex = codexTool({
  name: "imported_codex_reviewer",
  sandboxMode: "workspace-write",
  defaultThreadOptions: {
    model: "gpt-5.4",
    networkAccessEnabled: false,
    webSearchEnabled: false,
    approvalPolicy: "never",
  },
});

