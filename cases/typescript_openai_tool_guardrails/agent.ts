import {
  Agent,
  ToolGuardrailFunctionOutputFactory,
  defineToolInputGuardrail,
  defineToolOutputGuardrail,
  tool,
} from "@openai/agents";
import { z } from "zod";

const blockSecrets = defineToolInputGuardrail({
  name: "block_secrets",
  run: async ({ toolCall }) => {
    const args = JSON.parse(toolCall.arguments) as { text?: string };
    if (args.text?.includes("sk-")) {
      return ToolGuardrailFunctionOutputFactory.rejectContent(
        "Remove secrets before calling this tool.",
      );
    }
    return ToolGuardrailFunctionOutputFactory.allow();
  },
});

const redactOutput = defineToolOutputGuardrail({
  name: "redact_output",
  run: async ({ output }) => {
    if (String(output ?? "").includes("sk-")) {
      return {
        behavior: {
          type: "rejectContent",
          message: "Output contained sensitive data.",
        },
      };
    }
    return { behavior: { type: "allow" } };
  },
});

const classifyTool = tool({
  name: "classify_text",
  description: "Classify text for internal routing.",
  parameters: z.object({
    text: z.string(),
  }),
  inputGuardrails: [blockSecrets],
  outputGuardrails: [
    redactOutput,
    {
      name: "inline_output_allow",
      run: async () => {
        return { behavior: { type: "allow" } };
      },
    },
  ],
  execute: ({ text }) => `length:${text.length}`,
});

const dynamicGuardrails = process.env.ENABLE_TOOL_GUARDRAILS ? [blockSecrets] : [];
const dynamicTool = tool({
  name: "dynamic_tool",
  description: "Has dynamic guardrail configuration.",
  parameters: z.object({ text: z.string() }),
  inputGuardrails: dynamicGuardrails,
  execute: ({ text }) => text,
});

const mutableGuardrail = defineToolInputGuardrail({
  name: "mutable_input_guardrail",
  run: async () => ToolGuardrailFunctionOutputFactory.allow(),
});
mutableGuardrail.name = "changed_guardrail";

const mutableTool = tool({
  name: "mutable_tool",
  description: "Has a mutated guardrail binding.",
  parameters: z.object({ text: z.string() }),
  inputGuardrails: [mutableGuardrail],
  execute: ({ text }) => text,
});

const lookalikeTool = {
  name: "lookalike",
  inputGuardrails: [blockSecrets],
};
void lookalikeTool;

const agent = new Agent({
  name: "Classifier",
  instructions: "Classify incoming text.",
  tools: [classifyTool, dynamicTool, mutableTool],
});
