import { LlmAgent } from '@google/adk';
import { Kernel } from '@microsoft/semantic-kernel';
import { VectorStoreIndex } from '@llamaindex/core';
import { Agent } from '@mastra/core/agent';
import { GoogleGenAI } from '@google/genai';
import { google } from '@ai-sdk/google';
import { BedrockRuntimeClient } from '@aws-sdk/client-bedrock-runtime';

const agent = new Agent({ model: 'gemini-2.5-flash' });

import { ToolLoopAgent } from 'ai';
import type { ModelMessage } from 'ai/internal';
