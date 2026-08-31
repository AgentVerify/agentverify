import { RealtimeOutputGuardrail } from "@openai/agents/realtime";

export const ambiguousRealtimeOutputGuardrails: RealtimeOutputGuardrail[] = [
  {
    name: "Ambiguous realtime A",
    async execute() {
      return {
        tripwireTriggered: false,
      };
    },
  },
];
