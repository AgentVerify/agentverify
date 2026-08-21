import {DefaultAgentCardResolver} from '@a2a-js/sdk/client';

export type AgentCard = {url: string; additionalInterfaces?: Array<{url: string}>};

export async function resolveAgentCard(
  agentCard: AgentCard | string,
): Promise<AgentCard> {
  if (typeof agentCard === 'object') {
    return agentCard;
  }

  const source = agentCard as string;
  if (source.startsWith('http://') || source.startsWith('https://')) {
    const resolver = new DefaultAgentCardResolver();
    return await resolver.resolve(source);
  }

  throw new Error(`Unsupported local fixture source: ${source}`);
}
