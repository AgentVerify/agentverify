import { RealtimeOutputGuardrail } from "@openai/agents/realtime";

export const ambiguousRealtimeOutputGuardrails: RealtimeOutputGuardrail[] = [
  {
    name: "Ambiguous realtime B",
    async execute() {
      return {
        tripwireTriggered: true,
      };
    },
  },
];
