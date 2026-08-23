export function createSessionSpawnTool(deps, config, rootSessionId, toolExecutors) {
  const createSubAgentTools = () => {
    const tools = createBuiltinTools({
      ...ToolPresets[resolveToolPresetName({ mode: config.mode })],
      executors: toolExecutors,
    })
    return tools
  }

  return createSpawnAgentTool({
    configProvider,
    createSubAgentTools,
  })
}
