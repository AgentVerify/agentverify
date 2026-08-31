import { Agent } from "@openai/agents";

export const ambiguousWriterAgent = new Agent({
  name: "Ambiguous writer",
  instructions: "Write a conflicting report.",
});
