import { Agent, Runner, run } from '@openai/agents';
import { OpenAI } from 'openai';

const agent = new Agent({
  name: 'Server Conversation Agent',
});

const client = new OpenAI();
const { id: conversationId } = await client.conversations.create({});

await run(agent, 'remember this server-managed thread', {
  conversationId,
});

const runner = new Runner({
  workflowName: 'server-managed conversation example',
});
await runner.run(agent, 'continue this server-managed thread', {
  conversationId,
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
