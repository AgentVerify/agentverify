import {ClientFactory} from '@a2a-js/sdk/client';
import {resolveAgentCard, type AgentCard} from './agent_card.js';

export class A2ARemoteAgent {
  private client?: unknown;
  private card?: AgentCard;

  constructor(
    private readonly a2aConfig: {
      agentCard?: AgentCard | string;
      client?: unknown;
      clientFactory?: ClientFactory;
    },
  ) {}

  private async init() {
    if (this.a2aConfig.client) {
      this.client = this.a2aConfig.client;
    }

    if (this.a2aConfig.agentCard) {
      this.card = await resolveAgentCard(this.a2aConfig.agentCard);

      if (!this.client) {
        const factory = this.a2aConfig.clientFactory || new ClientFactory();
        this.client = await factory.createFromAgentCard(this.card);
      }
    }
  }
}
