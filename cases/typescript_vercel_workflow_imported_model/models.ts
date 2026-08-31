import { anthropic } from "@ai-sdk/anthropic";

export const workflowModel = anthropic("claude-imported");
export const castModel = anthropic("claude-cast") as any;
export const mutableModel = anthropic("claude-mutable");
mutableModel = anthropic("claude-changed");
