import { Agent, RunState, run } from '@openai/agents';
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

const looseState = { opaque: true };
await run(agent, looseState);

const unknownStateResult = await unknownRun(agent, 'unknown state run');
await run(agent, unknownStateResult.state);

let staleStateResult = await run(agent, 'state source before result reassignment');
staleStateResult = await unknownRun(agent, 'reassigned state source');
await run(agent, staleStateResult.state);

const namedStateResult = await run(agent, 'state before reassigned input');
let reassignedState = namedStateResult.state;
reassignedState = { opaque: true };
await run(agent, reassignedState);

const looseApprovalState = {
  approve() {},
  reject() {},
};
looseApprovalState.approve(interruption);
looseApprovalState.reject(interruption);

const unknownApprovalResult = await unknownRun(agent, 'unknown approval state');
unknownApprovalResult.state.approve(interruption);
unknownApprovalResult.state.reject(interruption);

let staleApprovalResult = await run(agent, 'approval source before result reassignment');
staleApprovalResult = await unknownRun(agent, 'reassigned approval state source');
staleApprovalResult.state.approve(interruption);

const reboundApprovalResult = await run(agent, 'approval state before reassigned input');
let reboundApprovalState = reboundApprovalResult.state;
reboundApprovalState = looseApprovalState;
reboundApprovalState.approve(interruption);

const looseSerializedState = '{"not":"from an sdk result"}';
const loosePersistedState = await RunState.fromString(agent, looseSerializedState);
loosePersistedState.approve(interruption);

const unknownSerializedResult = await unknownRun(agent, 'unknown serialized state');
const unknownSerializedState = unknownSerializedResult.state.toString();
const unknownPersistedState = await RunState.fromString(agent, unknownSerializedState);
unknownPersistedState.reject(interruption);

let reassignedSerializedResult = await run(agent, 'serialized source before result reassignment');
reassignedSerializedResult = await unknownRun(agent, 'reassigned serialized source');
const reassignedSerializedState = reassignedSerializedResult.state.toString();
const reassignedPersistedState = await RunState.fromString(agent, reassignedSerializedState);
reassignedPersistedState.approve(interruption);
