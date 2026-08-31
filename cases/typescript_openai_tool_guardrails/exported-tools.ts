import { tool } from "@openai/agents";
import { z } from "zod";

import {
  importedToolInputGuardrails,
  importedToolOutputGuardrails,
} from "./tool-guardrails";

export const exportedGuardrailTool = tool({
  name: "exported_guardrail_tool",
  description: "Uses guardrails from an exported sibling tool.",
  parameters: z.object({ text: z.string() }),
  inputGuardrails: importedToolInputGuardrails,
  outputGuardrails: importedToolOutputGuardrails,
  execute: ({ text }) => text,
});
