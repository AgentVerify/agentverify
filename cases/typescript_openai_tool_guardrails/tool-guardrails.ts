import {
  ToolInputGuardrailDefinition,
  ToolOutputGuardrailDefinition,
} from "@openai/agents";

export const importedToolInputGuardrails: ToolInputGuardrailDefinition[] = [
  {
    name: "imported_private_input_guardrail",
    run: async ({ toolCall }) => {
      if (String(toolCall.arguments ?? "").includes("private")) {
        return {
          behavior: {
            type: "rejectContent",
            message: "Do not pass private data to this tool.",
          },
        };
      }
      return { behavior: { type: "allow" } };
    },
  },
];

export const importedToolOutputGuardrails: ToolOutputGuardrailDefinition[] = [
  {
    name: "imported_output_allow_guardrail",
    run: async () => {
      return { behavior: { type: "allow" } };
    },
  },
];
