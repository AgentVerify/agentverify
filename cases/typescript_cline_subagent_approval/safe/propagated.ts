export function createSessionSpawnTool(config) {
  return createSpawnAgentTool({
    createSubAgentTools,
    toolPolicies: config.toolPolicies,
    requestToolApproval: config.requestToolApproval,
  })
}
