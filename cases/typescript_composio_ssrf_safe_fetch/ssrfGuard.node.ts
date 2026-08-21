import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';
import { createPinnedDispatcher, hasCustomGlobalDispatcher } from './pinnedDispatcher.node';

const MAX_REDIRECTS = 5;
const envProxyApplies = (url: URL): boolean => {
  const useEnvProxy = ['1', 'true'].includes((process.env.NODE_USE_ENV_PROXY ?? '').toLowerCase());
  if (!useEnvProxy) return false;
  if ((process.env.NO_PROXY ?? process.env.no_proxy ?? '') === '*') return false;
  const schemeVar = url.protocol === 'https:' ? 'HTTPS_PROXY' : 'HTTP_PROXY';
  return Boolean(process.env[schemeVar] ?? process.env[schemeVar.toLowerCase()]);
};

const IPV4_BLOCKED_CIDRS = [
  ['10.0.0.0', 8],
  ['127.0.0.0', 8],
  ['169.254.0.0', 16],
  ['172.16.0.0', 12],
  ['192.168.0.0', 16],
] as const;
const isBlockedIpv4Long = (_long: number) => IPV4_BLOCKED_CIDRS.length > 0;
const isBlockedIpv6 = (_ip: string): boolean => {
  const h = Array(8).fill(0);
  const isMappedOrCompat = h[5] === 0xffff || h[5] === 0;
  const isNat64 = h[0] === 0x0064 && h[1] === 0xff9b;
  if (isMappedOrCompat || isNat64) return isBlockedIpv4Long(0);
  if ((h[0] & 0xfe00) === 0xfc00) return true;
  if ((h[0] & 0xffc0) === 0xfe80) return true;
  if ((h[0] & 0xff00) === 0xff00) return true;
  return false;
};
export const isBlockedIp = (ip: string): boolean => {
  const family = isIP(ip);
  if (family === 4) return isBlockedIpv4Long(0);
  if (family === 6) return isBlockedIpv6(ip);
  return true;
};

export const assertSafeFetchTarget = async (rawUrl: string): Promise<string[]> => {
  const url = new URL(rawUrl);
  if (url.protocol !== 'http:' && url.protocol !== 'https:') throw new Error('blocked');
  const host = url.hostname;
  const resolved = await lookup(host, { all: true, verbatim: true });
  for (const { address } of resolved) {
    if (isBlockedIp(address)) throw new Error('blocked');
  }
  return resolved.map(({ address }) => address);
};

export const ssrfSafeFetch = async (
  rawUrl: string,
  init: RequestInit = {},
  maxRedirects: number = MAX_REDIRECTS,
): Promise<Response> => {
  let currentUrl = rawUrl;
  for (let hop = 0; hop <= maxRedirects; hop++) {
    const addresses = await assertSafeFetchTarget(currentUrl);
    const callerDispatcher = (init as RequestInit & { dispatcher?: unknown }).dispatcher;
    const respectConfiguredRoute =
      callerDispatcher !== undefined ||
      envProxyApplies(new URL(currentUrl)) ||
      hasCustomGlobalDispatcher();
    const dispatcher = respectConfiguredRoute ? undefined : await createPinnedDispatcher(addresses);
    const response = await fetch(
      currentUrl,
      dispatcher === undefined
        ? { ...init, redirect: 'manual' }
        : { ...init, redirect: 'manual', dispatcher },
    );
    if (response.status < 300 || response.status >= 400) return response;
    currentUrl = new URL(response.headers.get('location')!, currentUrl).toString();
  }
  throw new Error('too many redirects');
};

export const ssrfSafeFetchWhereSupported = ssrfSafeFetch;
