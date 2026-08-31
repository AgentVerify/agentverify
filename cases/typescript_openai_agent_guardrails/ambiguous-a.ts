import {
  InputGuardrail,
} from "@openai/agents";

export const ambiguousInputGuardrails: InputGuardrail[] = [
  {
    name: "Ambiguous A",
    async execute() {
      return { tripwireTriggered: false };
    },
  },
];
