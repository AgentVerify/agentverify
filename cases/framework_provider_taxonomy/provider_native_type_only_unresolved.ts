import type OpenAI from 'openai';
import type { Anthropic } from '@anthropic-ai/sdk';

type OpenAITool = import('openai').default.Chat.ChatCompletionTool;

async function typedOpenAIOnly(client: OpenAI, _tool: OpenAITool) {
  await client.responses.create({ model: 'gpt-type-only' });
}

async function typedAnthropicOnly(client: Anthropic) {
  await client.messages.create({ model: 'claude-type-only' });
}
