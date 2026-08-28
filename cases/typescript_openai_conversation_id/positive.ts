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
