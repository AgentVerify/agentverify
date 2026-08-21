import {ClientFactory} from '@a2a-js/sdk/client';

export async function localTrustedCard() {
  const card = {url: 'https://fixed.example/rpc'};
  return await new ClientFactory().createFromAgentCard(card);
}
