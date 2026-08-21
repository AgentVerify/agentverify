import { isIP } from 'node:net';
import type { Agent } from 'undici';

const GLOBAL_DISPATCHER_SYMBOLS = [
  Symbol.for('undici.globalDispatcher.1'),
  Symbol.for('undici.globalDispatcher.2'),
] as const;

let undici: Promise<typeof import('undici')> | undefined;
const loadUndici = (): Promise<typeof import('undici')> => (undici ??= import('undici'));

export const createPinnedDispatcher = async (addresses: ReadonlyArray<string>): Promise<Agent> => {
  const { Agent } = await loadUndici();
  return new Agent({
    connect: {
      lookup: (_hostname, options, callback) => {
        if (options.all) {
          callback(null, addresses.map(address => ({ address, family: isIP(address) })));
          return;
        }
        const [address] = addresses;
        callback(null, address, isIP(address));
      },
    },
  });
};

export const hasCustomGlobalDispatcher = (): boolean => {
  const slots = globalThis as unknown as Record<symbol, { constructor?: { name?: string } }>;
  const dispatcher = GLOBAL_DISPATCHER_SYMBOLS.map(symbol => slots[symbol]).find(Boolean) ?? {};
  return dispatcher.constructor?.name !== 'Agent';
};
