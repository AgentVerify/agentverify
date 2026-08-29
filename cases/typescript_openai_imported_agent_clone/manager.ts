import { Agent, RunResult } from "@openai/agents";
import { fakeAgent } from "./fake-agents";
import { writerAgent } from "./agents";

const importedClone = writerAgent.clone({
  name: "Imported clone",
  tools: [],
});

const fakeClone = fakeAgent.clone({
  name: "Fake clone",
});
void fakeClone;

function consumeAgentRun(result: RunResult<unknown, Agent<unknown, any>>) {
  return result.finalOutput;
}
void consumeAgentRun;
