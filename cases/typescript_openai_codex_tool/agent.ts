import { Agent } from "@openai/agents";
import { codexTool as makeCodex } from "@openai/agents-extensions/experimental/codex";

const workspace = "/tmp/agentverify-codex-workspace";

const codex = makeCodex({
  sandboxMode: "workspace-write",
  defaultThreadOptions: {
    model: "gpt-5.4",
    modelReasoningEffort: "low",
    networkAccessEnabled: true,
    webSearchEnabled: false,
    approvalPolicy: "never",
    workingDirectory: workspace,
  },
  onStream: onCodexStream,
});

const agent = new Agent({
  name: "Codex reviewer",
  instructions: "Always inspect the workspace through Codex.",
  tools: [codex],
});

const inlineAgent = new Agent<{ codexThreadId_engineer?: string }>({
  name: "Inline Codex reviewer",
  instructions: "Reuse the same Codex task for follow-up questions.",
  tools: [
    makeCodex({
      name: "codex_engineer",
      sandboxMode: "workspace-write",
      defaultThreadOptions: {
        model: "gpt-5.4",
        modelReasoningEffort: "low",
        networkAccessEnabled: true,
        webSearchEnabled: false,
        approvalPolicy: "never",
        workingDirectory: workspace,
      },
      useRunContextThreadId: true,
      onStream: onCodexStream,
    }),
  ],
});

const threadOptionsAgent = new Agent({
  name: "Thread Options Codex reviewer",
  instructions: "Use Codex without an explicit approval policy.",
  tools: [
    makeCodex({
      sandboxMode: "workspace-write",
      defaultThreadOptions: {
        model: "gpt-5.4",
        networkAccessEnabled: true,
        webSearchEnabled: false,
      },
    }),
  ],
});

const mutableCodex = makeCodex({
  sandboxMode: "workspace-write",
  defaultThreadOptions: {
    approvalPolicy: "never",
  },
});
mutableCodex.extra = true;

const mutableAgent = new Agent({
  name: "Mutable Codex reviewer",
  tools: [mutableCodex],
});

function onCodexStream() {}

void agent;
void inlineAgent;
void threadOptionsAgent;
void mutableAgent;
