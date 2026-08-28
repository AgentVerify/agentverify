import { Agent } from "@openai/agents";

const dynamicParallelToolCalls = Boolean(process.env.PARALLEL_TOOL_CALLS);

export const sequentialAgent = new Agent({
  name: "Sequential tool agent",
  modelSettings: {
    parallelToolCalls: false,
  },
});

export const parallelAgent = new Agent({
  name: "Parallel tool agent",
  modelSettings: {
    parallelToolCalls: true,
  },
});

export const dynamicAgent = new Agent({
  name: "Dynamic tool concurrency agent",
  modelSettings: {
    parallelToolCalls: dynamicParallelToolCalls,
  },
});
