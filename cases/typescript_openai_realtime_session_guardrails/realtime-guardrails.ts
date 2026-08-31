import { RealtimeOutputGuardrail } from "@openai/agents/realtime";

export const importedRealtimeOutputGuardrails: RealtimeOutputGuardrail[] = [
  {
    name: "Imported no password guardrail",
    async execute({ agentOutput }) {
      return {
        tripwireTriggered: agentOutput.includes("password"),
      };
    },
  },
];

export const importedRealtimeLiteralGuardrails: RealtimeOutputGuardrail[] = [
  {
    name: "Imported literal realtime guardrail",
    async execute() {
      return {
        tripwireTriggered: false,
      };
    },
  },
];
