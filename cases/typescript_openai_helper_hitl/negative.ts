import { Agent, run } from "@openai/agents";

async function unresolvedParameter(unknownAgent: Agent<unknown, any>) {
  await runWithHitl(unknownAgent, "do not resolve caller parameters");
}

async function typedButUnproven(agent: Agent<unknown, any>, input: string) {
  let result = await run(agent, input);
  const state = result.state;
  state.reject(result.interruptions[0], { message: "looks close" });
}

async function untypedHelper(agent: Agent<unknown, any>) {
  const localAgent = new Agent({ name: "Local negative helper agent" });
  await looseRunWithHitl(localAgent, "do not resolve untyped helpers");
}

async function runWithHitl(agent: Agent<unknown, any>, input: string) {
  let result = await run(agent, input);
  const state = result.state;
  state.reject(result.interruptions[0], { message: "helper called with unknown agent" });
  await run(agent, state);
}

async function looseRunWithHitl(agent, input: string) {
  let result = await run(agent, input);
  const state = result.state;
  state.reject(result.interruptions[0], { message: "missing Agent parameter type" });
  await run(agent, state);
}
