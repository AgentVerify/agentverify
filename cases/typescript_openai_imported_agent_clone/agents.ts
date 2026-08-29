import { Agent } from "@openai/agents";

export const writerAgent = new Agent({
  name: "Imported writer",
  instructions: "Write a report.",
});
