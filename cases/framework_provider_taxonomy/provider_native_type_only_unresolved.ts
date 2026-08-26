import type OpenAI from 'openai';
import type { OpenAI as NamedOpenAIType } from 'openai';
import type { Anthropic } from '@anthropic-ai/sdk';

type OpenAITool = import('openai').default.Chat.ChatCompletionTool;

async function typedOpenAIOnly(client: OpenAI, _tool: OpenAITool) {
  await client.responses.create({ model: 'gpt-type-only' });
}

async function typedNamedOpenAIOnly(client: NamedOpenAIType) {
  await client.chat.completions.create({ model: 'gpt-named-type-only' });
}

async function typedAnthropicOnly(client: Anthropic) {
  await client.messages.create({ model: 'claude-type-only' });
}
