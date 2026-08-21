const dns = { lookup: () => undefined };
const createResultOk = (_value: undefined) => ({ ok: true });

export function createPassthroughSsrfGuard() {
  return {
    validateUrl: async () => createResultOk(undefined),
    validateRedirectSync: () => {},
    createSecureLookup: () => dns.lookup,
  };
}
