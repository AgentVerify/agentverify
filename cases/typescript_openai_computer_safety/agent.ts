import { Agent, computerTool } from "@openai/agents";

const browser = computerTool({
  computer: {},
  needsApproval: async (_ctx, action) => ["click", "type"].includes(action.type),
  onSafetyCheck: async ({ pendingSafetyChecks }) => {
    return { acknowledgedSafetyChecks: pendingSafetyChecks };
  },
});

const blindBrowser = computerTool({
  computer: {},
  onSafetyCheck: async () => true,
});

const reviewedBrowser = computerTool({
  computer: {},
  onSafetyCheck: async ({ pendingSafetyChecks }) => {
    return { acknowledgedSafetyChecks: pendingSafetyChecks.slice(0, 0) };
  },
});

const operator = new Agent({
  name: "operator",
  tools: [browser, blindBrowser, reviewedBrowser],
});

void operator;
