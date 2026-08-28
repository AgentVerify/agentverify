import { Agent, run } from "@openai/agents";

const AUTO_APPROVE_HITL = process.env.AUTO_APPROVE_HITL === "1";

async function confirm(question: string): Promise<boolean> {
  if (AUTO_APPROVE_HITL) {
    console.log(`[auto-approve] ${question}`);
    return true;
  }
  return question.length > 0;
}

const agent = new Agent({
  name: "Approval decision agent",
});

let result = await run(agent, "start approval flow");
const approvalState = result.state;
for (const interruption of result.interruptions ?? []) {
  const ok = await confirm("approve?");
  if (ok) {
    approvalState.approve(interruption);
  } else {
    approvalState.reject(interruption);
  }
}

let inlineResult = await run(agent, "start direct approval flow");
for (const interruption of inlineResult.interruptions ?? []) {
  if (await confirm("approve inline?")) {
    inlineResult.state.approve(interruption);
  }
}

let reassignedResult = await run(agent, "start reassigned approval flow");
for (const interruption of reassignedResult.interruptions ?? []) {
  let maybe = await confirm("approve after reassignment?");
  maybe = false;
  if (maybe) {
    reassignedResult.state.approve(interruption);
  }
}
