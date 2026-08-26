export async function createCliCore(options?: {
  capabilities?: RuntimeCapabilities
  toolPolicies?: AgentConfig["toolPolicies"]
  forceLocalBackend?: boolean
}) {
  const explicitBackendMode = options?.forceLocalBackend ? "local" : undefined
  return ClineCore.create({
    ...(explicitBackendMode ? { backendMode: explicitBackendMode } : {}),
    capabilities: options?.capabilities,
    toolPolicies: options?.toolPolicies,
  })
}
