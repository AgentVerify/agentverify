import { Agent, run } from '@openai/agents';
import { OpenAI, OpenAI as ReboundOpenAI } from 'openai';

ReboundOpenAI = ReplacementOpenAI;

const agent = new Agent({
  name: 'Unproven Conversation Agent',
});

declare const unknownClient: unknown;
const { id: unknownConversationId } = await unknownClient.conversations.create({});
await run(agent, 'continue unknown server state', {
  conversationId: unknownConversationId,
});

const reboundClient = new ReboundOpenAI();
const { id: reboundConversationId } = await reboundClient.conversations.create({});
await run(agent, 'continue rebound server state', {
  conversationId: reboundConversationId,
});

const client = new OpenAI();
const { id: reassignedConversationId } = await client.conversations.create({});
reassignedConversationId = 'changed';
await run(agent, 'continue reassigned server state', {
  conversationId: reassignedConversationId,
});

const looseConversationId = 'thread_123';
await run(agent, 'continue loose string state', {
  conversationId: looseConversationId,
});
