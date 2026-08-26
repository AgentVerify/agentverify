export function createSessionSpawnTool(deps, config, rootSessionId, toolExecutors) {
  return createSpawnAgentTool({
    createSubAgentTools,
    toolPolicies: config.toolPolicies,
    requestToolApproval: config.requestToolApproval,
  })
}
