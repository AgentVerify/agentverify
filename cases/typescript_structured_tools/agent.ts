import {
  Agent,
  applyPatchTool,
  computerTool as localComputerTool,
  shellTool as localShellTool,
  tool,
  toolNamespace,
} from "@openai/agents";
import { shellTool as unrelatedShellTool } from "./fake";

const safeTool = tool({
  name: "safe",
  execute: async () => "words such as async and return are not tool names",
});

const namespaceTools = toolNamespace({
  name: "lookup",
  tools: [safeTool],
});

const assignedShell = localShellTool({
  shell: { run: async () => ({ output: [] }) },
  needsApproval: false,
});

const worker = new Agent({ name: "worker" });

const operator = new Agent({
  name: "operator",
  tools: [
    safeTool,
    assignedShell,
    ...namespaceTools,
    applyPatchTool({
      editor: {},
      needsApproval: true,
    }),
    localComputerTool({
      computer: {},
      needsApproval: async (_ctx, action) => ["click", "type"].includes(action.type),
    }),
    worker.asTool({
      toolName: "worker_tool",
      runConfig: { model: "gpt-5.4", modelSettings: { reasoning: { effort: "low" }, text: { verbosity: "low" } } }, runOptions: { maxTurns: 3 },
    }),
    worker.asTool({
      toolName: "approved_worker_tool",
      needsApproval: true,
    }),
    worker.asTool({
      toolName: "conditional_worker_tool",
      needsApproval: async (_ctx, { input }) => input.includes("deploy"),
    }),
    // A leading comment belongs to the next entry, not to an extra tool token.
    unknownFactory({ description: "do not parse these words as tools" }),
    unrelatedShellTool({ shell: {} }),
    ...[conditionalTool],
  ],
});
