import { anthropic } from "@ai-sdk/anthropic";
import { WorkflowAgent } from "@ai-sdk/workflow";

const localWorkflowModel = anthropic("claude-local");
const localCastModel = anthropic("claude-local-cast") as any;
let localMutableModel = anthropic("claude-local-mutable");
localMutableModel = anthropic("claude-local-changed");

const localModelAgent = new WorkflowAgent({ model: localWorkflowModel });
const localCastAgent = new WorkflowAgent({ model: localCastModel });
const localMutableAgent = new WorkflowAgent({ model: localMutableModel });

void localModelAgent;
void localCastAgent;
void localMutableAgent;
