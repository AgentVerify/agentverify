import { ToolInputGuardrailDefinition } from "@openai/agents";

export const ambiguousToolInputGuardrails: ToolInputGuardrailDefinition[] = [
  {
    name: "Ambiguous imported tool B",
    run: async () => {
      return {
        behavior: {
          type: "rejectContent",
          message: "Ambiguous source must not be attributed.",
        },
      };
    },
  },
];
