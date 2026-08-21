import {
  ClientFactory,
  ClientFactoryOptions,
  DefaultAgentCardResolver,
  JsonRpcTransportFactory,
  RestTransportFactory,
} from '@a2a-js/sdk/client';
import {Agent as UndiciAgent, ProxyAgent} from 'undici';

type AgentCard = {url: string; additionalInterfaces?: Array<{url: string; transport: string}>};
type LoadOptions = {type: 'url'; url: string} | {type: 'json'; json: string};

const normalizeAgentCard = (value: unknown) => value as AgentCard;

export class A2AClientManager {
  private readonly a2aDispatcher: UndiciAgent | ProxyAgent;
  private readonly a2aFetch: typeof fetch;

  constructor(proxyUrl?: string) {
    this.a2aDispatcher = proxyUrl
      ? new ProxyAgent({uri: proxyUrl})
      : new UndiciAgent({headersTimeout: 30_000});
    this.a2aFetch = (input, init) =>
      fetch(input, {...init, dispatcher: this.a2aDispatcher} as RequestInit);
  }

  async loadAgent(options: LoadOptions) {
    const authFetch = this.a2aFetch;
    const cardFetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const response = await this.a2aFetch(input, init);
      if ((response.status === 401 || response.status === 403) && authFetch) {
        return authFetch(input, init);
      }
      return response;
    };
    const resolver = new DefaultAgentCardResolver({fetchImpl: cardFetch});

    let rawCard: unknown;
    if (options.type === 'json') {
      rawCard = JSON.parse(options.json);
    } else {
      rawCard = await resolver.resolve(options.url, '');
    }
    const agentCard = normalizeAgentCard(rawCard);
    const grpcUrl =
      agentCard.additionalInterfaces?.find((i) => i.transport === 'GRPC')?.url ??
      agentCard.url;
    const clientOptions = ClientFactoryOptions.createFrom(
      ClientFactoryOptions.default,
      {
        transports: [
          new RestTransportFactory({fetchImpl: authFetch}),
          new JsonRpcTransportFactory({fetchImpl: authFetch}),
          {secure: grpcUrl.startsWith('https://')},
        ],
        cardResolver: resolver,
      },
    );
    const factory = new ClientFactory(clientOptions);
    return await factory.createFromAgentCard(agentCard);
  }
}
