import { Agent, tool } from "@openai/agents";

const evaluate = tool({
  name: "evaluate",
  execute: async ({ source }) => eval(source),
});

const agent = new Agent({ name: "evaluator", tools: [evaluate] });

