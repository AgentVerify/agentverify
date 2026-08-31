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

const snakeCaseBrowser = computerTool({
  computer: {},
  onSafetyCheck: async ({ pendingSafetyChecks }) => {
    return { acknowledged_safety_checks: pendingSafetyChecks };
  },
});

const expressionBrowser = computerTool({
  computer: {},
  onSafetyCheck: async ({ pendingSafetyChecks }) => ({
    acknowledgedSafetyChecks: pendingSafetyChecks,
  }),
});

const perRequestBrowser = computerTool({
  computer: {
    create: async ({ runContext }) => {
      return await createBrowser(runContext);
    },
    dispose: async ({ runContext, computer }) => {
      await closeBrowser(runContext, computer);
    },
  },
});

const leakyFactoryBrowser = computerTool({
  computer: {
    create: async ({ runContext }) => {
      return await createBrowser(runContext);
    },
  },
});

const emptyAckBrowser = computerTool({
  computer: {},
  onSafetyCheck: async () => {
    return { acknowledgedSafetyChecks: [] };
  },
});

const operator = new Agent({
  name: "operator",
  tools: [
    browser,
    blindBrowser,
    reviewedBrowser,
    snakeCaseBrowser,
    expressionBrowser,
    perRequestBrowser,
    leakyFactoryBrowser,
    emptyAckBrowser,
  ],
});

void operator;
