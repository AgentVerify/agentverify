function createPassthroughSsrfGuard() {
  return {};
}

function createWebFetchTool(_factory: object, _ssrf: object) {
  return {};
}

export function createDiscovery(config: { ssrf?: object }) {
  const discoverySecurityFactory = {};
  const plannerSecurityFactory = {};
  const ssrf = config.ssrf ?? createPassthroughSsrfGuard();
  return [
    createWebFetchTool(discoverySecurityFactory, ssrf),
    createWebFetchTool(plannerSecurityFactory, ssrf),
  ];
}
