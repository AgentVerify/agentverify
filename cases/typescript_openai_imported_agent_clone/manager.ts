import { Agent, RunResult } from "@openai/agents";
import { fakeAgent } from "./fake-agents";
import { writerAgent as namedWriterAgent } from "./agent-barrel";
import { writerAgent as starWriterAgent } from "./agent-star-barrel";
import { writerAgent } from "./agents";
import { ambiguousWriterAgent } from "./ambiguous-star-barrel";

const importedClone = writerAgent.clone({
  name: "Imported clone",
  tools: [],
});

const namedReexportClone = namedWriterAgent.clone({
  name: "Named reexport clone",
});

const starReexportClone = starWriterAgent.clone({
  name: "Star reexport clone",
});

const ambiguousClone = ambiguousWriterAgent.clone({
  name: "Ambiguous clone",
});
void ambiguousClone;

const fakeClone = fakeAgent.clone({
  name: "Fake clone",
});
void fakeClone;

function consumeAgentRun(result: RunResult<unknown, Agent<unknown, any>>) {
  return result.finalOutput;
}
void consumeAgentRun;
