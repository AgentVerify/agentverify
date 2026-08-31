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

import { ambiguousToolInputGuardrails } from "./tool-ambiguous-barrel";
import { importedToolInputGuardrails } from "./tool-guardrails";
import { reexportedToolOutputGuardrails } from "./tool-reexports";

const importedGuardrailTool = tool({
  name: "imported_guardrail_tool",
  description: "Uses imported typed tool guardrail arrays.",
  parameters: z.object({ text: z.string() }),
  inputGuardrails: importedToolInputGuardrails,
  outputGuardrails: reexportedToolOutputGuardrails,
  execute: ({ text }) => text,
});

const ambiguousImportedGuardrailTool = tool({
  name: "ambiguous_imported_guardrail_tool",
  description: "Uses an ambiguous imported tool guardrail array.",
  parameters: z.object({ text: z.string() }),
  inputGuardrails: ambiguousToolInputGuardrails,
  execute: ({ text }) => text,
});

const importedGuardrailAgent = new Agent({
  name: "Imported tool guardrail classifier",
  instructions: "Classify with imported guardrail tools.",
  tools: [importedGuardrailTool, ambiguousImportedGuardrailTool],
});

void importedGuardrailTool;
void ambiguousImportedGuardrailTool;
void importedGuardrailAgent;

import { exportedGuardrailTool } from "./exported-tools";

const importedToolAgent = new Agent({
  name: "Imported exported tool guardrail classifier",
  instructions: "Classify with an imported guarded tool.",
  tools: [exportedGuardrailTool],
});

void importedToolAgent;

function containsClassifiedTerm(value: string | undefined): boolean {
  return String(value ?? "").includes("classified");
}

const helperPredicateGuardrail = defineToolInputGuardrail({
  name: "helper_predicate_guardrail",
  run: async ({ toolCall }) => {
    const args = JSON.parse(toolCall.arguments) as { text?: string };
    if (containsClassifiedTerm(args.text)) {
      return ToolGuardrailFunctionOutputFactory.rejectContent(
        "Remove classified terms before calling this tool.",
      );
    }
    return ToolGuardrailFunctionOutputFactory.allow();
  },
});

const helperPredicateTool = tool({
  name: "helper_predicate_tool",
  description: "Uses a same-file helper predicate guardrail.",
  parameters: z.object({ text: z.string() }),
  inputGuardrails: [helperPredicateGuardrail],
  execute: ({ text }) => text,
});

const helperPredicateAgent = new Agent({
  name: "Helper predicate tool guardrail classifier",
  instructions: "Classify with a helper predicate guardrail.",
  tools: [helperPredicateTool],
});

void helperPredicateAgent;

import { containsExportControlledTerm } from "./tool-predicates";

const importedHelperPredicateGuardrail = defineToolInputGuardrail({
  name: "imported_helper_predicate_guardrail",
  run: async ({ toolCall }) => {
    const args = JSON.parse(toolCall.arguments) as { text?: string };
    if (containsExportControlledTerm(args.text)) {
      return ToolGuardrailFunctionOutputFactory.rejectContent(
        "Remove export-controlled terms before calling this tool.",
      );
    }
    return ToolGuardrailFunctionOutputFactory.allow();
  },
});

const importedHelperPredicateTool = tool({
  name: "imported_helper_predicate_tool",
  description: "Uses an imported helper predicate guardrail.",
  parameters: z.object({ text: z.string() }),
  inputGuardrails: [importedHelperPredicateGuardrail],
  execute: ({ text }) => text,
});

const importedHelperPredicateAgent = new Agent({
  name: "Imported helper predicate tool guardrail classifier",
  instructions: "Classify with an imported helper predicate guardrail.",
  tools: [importedHelperPredicateTool],
});

void importedHelperPredicateAgent;
