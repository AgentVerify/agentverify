import { Agent, tool } from "@openai/agents";
import { z } from "zod";

const lookupTool = tool({
  name: "lookup",
  description: "Lookup a record.",
  parameters: z.object({ query: z.string() }),
  execute: ({ query }) => query,
});

const baseAgent = new Agent({
  name: "Base reviewer",
  instructions: "Review user requests.",
  tools: [lookupTool],
});

const copiedAgent = baseAgent.clone({
  name: "Copied reviewer",
  instructions: "Review user requests in a stricter tone.",
});

const isolatedAgent = baseAgent.clone({
  name: "Isolated reviewer",
  tools: [...baseAgent.tools],
});

const dynamicClone = baseAgent.clone(getCloneConfig());
void dynamicClone;

let reboundAgent = new Agent({
  name: "Initial",
  instructions: "Initial instructions.",
});
const replacementAgent = new Agent({
  name: "Replacement",
  instructions: "Replacement instructions.",
});
reboundAgent = replacementAgent;

const reboundClone = reboundAgent.clone({
  name: "Should stay unresolved",
});
void reboundClone;

function getCloneConfig() {
  return { name: "Dynamic" };
}
