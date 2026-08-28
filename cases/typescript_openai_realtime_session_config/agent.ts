import { RealtimeAgent, RealtimeSession } from "@openai/agents/realtime";

const dynamicParallelToolCalls = Boolean(process.env.REALTIME_PARALLEL_TOOL_CALLS);

const greeter = new RealtimeAgent({
  name: "Realtime greeter",
});

export const sequentialSession = new RealtimeSession(greeter, {
  config: {
    parallelToolCalls: false,
  },
});

export const parallelSession = new RealtimeSession(greeter, {
  config: {
    parallelToolCalls: true,
  },
});

export const reasoningSession = new RealtimeSession(greeter, {
  config: {
    reasoning: {
      effort: "low",
    },
  },
});

export const dynamicSession = new RealtimeSession(greeter, {
  config: {
    parallelToolCalls: dynamicParallelToolCalls,
  },
});
