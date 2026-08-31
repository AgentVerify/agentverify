import { ToolInputGuardrailDefinition } from "@openai/agents";

export const ambiguousToolInputGuardrails: ToolInputGuardrailDefinition[] = [
  {
    name: "Ambiguous imported tool A",
    run: async () => {
      return { behavior: { type: "allow" } };
    },
  },
];
