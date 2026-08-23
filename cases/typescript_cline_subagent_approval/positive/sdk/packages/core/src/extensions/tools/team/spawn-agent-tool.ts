export function createSpawnAgentTool(config: SpawnAgentToolConfig) {
  return createTool({
    name: "spawn_agent",
    execute: async (input, context) => {
      const subAgent = createDelegatedAgent({
        tools: await config.createSubAgentTools(input, context),
        toolPolicies: config.toolPolicies,
        requestToolApproval: config.requestToolApproval,
      })
      return subAgent.run(input.task)
    },
  })
}
