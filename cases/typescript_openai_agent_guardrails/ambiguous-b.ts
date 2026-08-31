import {
  InputGuardrail,
} from "@openai/agents";

export const ambiguousInputGuardrails: InputGuardrail[] = [
  {
    name: "Ambiguous B",
    async execute() {
      return { tripwireTriggered: true };
    },
  },
];
