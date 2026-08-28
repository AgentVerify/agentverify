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

declare const loosePreviousResponseId: string;
await run(agent, 'continue loose previous response state', {
  previousResponseId: loosePreviousResponseId,
});

const unknownFirst = await unknownRun(agent, 'unknown first run');
const unknownPreviousResponseId = unknownFirst.lastResponseId;
await run(agent, 'continue unknown first run state', {
  previousResponseId: unknownPreviousResponseId,
});

const first = await run(agent, 'first run before reassigned result');
first = replacementResult;
const reassignedPreviousResponseId = first.lastResponseId;
await run(agent, 'continue reassigned first run state', {
  previousResponseId: reassignedPreviousResponseId,
});

const looseMessages = [{ role: 'user', content: 'not from a run result' }];
await run(agent, looseMessages);

const unknownHistoryResult = await unknownRun(agent, 'unknown history run');
const unknownMessages = unknownHistoryResult.history;
await run(agent, unknownMessages);

const historyFirst = await run(agent, 'history before reassigned input');
let reassignedMessages = historyFirst.history;
reassignedMessages = [];
await run(agent, reassignedMessages);
