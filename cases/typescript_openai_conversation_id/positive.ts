import { Agent, Runner, RunState, generateTraceId, run, withTrace } from '@openai/agents';
import { OpenAI } from 'openai';

const agent = new Agent({
  name: 'Server Conversation Agent',
});

const client = new OpenAI();
const { id: conversationId } = await client.conversations.create({});

await run(agent, 'remember this server-managed thread', {
  conversationId, maxTurns: 6,
});

const runner = new Runner({
  workflowName: 'server-managed conversation example', modelSettings: { toolChoice: 'required' },
});
await runner.run(agent, 'continue this server-managed thread', {
  conversationId, maxTurns: 7,
});

const first = await run(agent, 'start with previous response continuity');
const previousResponseId = first.lastResponseId;
await run(agent, 'continue with the previous response id', {
  previousResponseId,
});

const historyFirst = await run(agent, 'start with history continuity');
const messages = historyFirst.history;
messages.push({ role: 'user', content: 'continue from history' });
await run(agent, messages);

let carriedItems = [{ role: 'user', content: 'start carried history' }];
const carriedFirst = await run(agent, carriedItems);
carriedItems = carriedFirst.history;
await runner.run(agent, carriedItems);

const directStateFirst = await run(agent, 'start direct state resume');
await run(agent, directStateFirst.state);

let interrupted = await run(agent, 'start interrupted state');
interrupted = await run(agent, interrupted.state);

let streamed = await run(agent, 'start named state resume', { stream: true });
const resumeState = streamed.state;
await runner.run(agent, resumeState, { stream: true });

let interruptedApproval = await run(agent, 'start approval-state handling');
const approvalState = interruptedApproval.state;
for (const interruption of interruptedApproval.interruptions ?? []) {
  approvalState.approve(interruption);
  approvalState.reject(interruption);
}
await run(agent, approvalState);

let inlineApproval = await run(agent, 'start inline approval-state handling');
for (const interruption of inlineApproval.interruptions ?? []) {
  inlineApproval.state.approve(interruption);
  inlineApproval.state.reject(interruption);
}

let persistedApproval = await run(agent, 'start serialized approval-state handling');
await fs.writeFile(
  'agentverify-result-state.json',
  JSON.stringify(persistedApproval.state, null, 2),
  'utf-8',
);
const persistedStateText = await fs.readFile('agentverify-result-state.json', 'utf-8');
const persistedState = await RunState.fromString(agent, persistedStateText);
for (const interruption of persistedApproval.interruptions ?? []) {
  persistedState.approve(interruption);
  persistedState.reject(interruption);
}
await run(agent, persistedState);

const rejectionText = 'Reviewer denied the requested tool call.';
const runtimeRejectionText = process.env.REJECTION_REASON ?? 'fallback denial';
let messageApproval = await run(agent, 'start custom rejection-message handling');
const messageState = messageApproval.state;
for (const interruption of messageApproval.interruptions ?? []) {
  messageState.reject(interruption, { message: 'Rejected by reviewer.' });
  messageState.reject(interruption, { message: rejectionText });
  messageState.reject(interruption, { message: `Rejected ${interruption.name}` });
  messageState.reject(interruption, { message: runtimeRejectionText });
}
await run(agent, messageState);

let loopItems = [{ role: 'user', content: 'start loop history feedback' }];
while (shouldContinue) {
  const loopResult = await run(agent, loopItems);
  loopItems = loopResult.history;
  loopItems.push({ role: 'user', content: 'continue loop history' });
}

let concatThread = [{ role: 'user', content: 'start concat history feedback' }];
async function continueConcatHistory(text: string) {
  const concatResult = await run(
    agent,
    concatThread.concat({ role: 'user', content: text }),
  );
  concatThread = concatResult.history;
}

async function continueThroughAgentAlias() {
  let aliasedAgent: Agent<any, any> = agent;
  let aliasedItems = [{ role: 'user', content: 'start aliased agent history feedback' }];
  while (shouldContinue) {
    const aliasedResult = await run(aliasedAgent, aliasedItems);
    aliasedItems = aliasedResult.history;
    aliasedAgent = agent;
  }
}

await withTrace(
  'AgentVerify trace group',
  async () => {
    await run(agent, 'trace grouped turn');
  },
  { groupId: 'agentverify-trace-group' },
);

const traceId = generateTraceId();
await withTrace(
  'AgentVerify trace id',
  async () => {
    await run(agent, 'trace identified turn');
  },
  { traceId },
);

const runnerTraceGroupId = 'agentverify-runner-trace-group';
const traceGroupedRunner = new Runner({
  groupId: runnerTraceGroupId,
});
await traceGroupedRunner.run(agent, 'runner trace grouped turn');

const tracingDisabledRunner = new Runner({ tracingDisabled: true });
await tracingDisabledRunner.run(agent, 'runner tracing disabled turn');
