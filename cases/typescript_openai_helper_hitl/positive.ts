import { Agent, run } from "@openai/agents";

async function firstFlow() {
  const agent = new Agent({ name: "First helper agent" });
  await runWithHitl(agent, "open the browser");
}

async function secondFlow() {
  const agent = new Agent({ name: "Second helper agent" });
  await runWithHitl(agent, "open the browser");
}

async function runWithHitl(agent: Agent<unknown, any>, input: string) {
  let result = await run(agent, input);
  const state = result.state;
  for (const interruption of result.interruptions ?? []) {
    state.reject(interruption, {
      message: `Tool execution for "${interruption.name}" was dismissed.`,
    });
  }
  result = await run(agent, state);
  return result;
}
