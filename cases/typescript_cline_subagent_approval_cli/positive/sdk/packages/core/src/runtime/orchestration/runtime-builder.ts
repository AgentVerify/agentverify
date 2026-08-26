function normalizeConfig(config) {
  const preset = ToolPresets.act
  return {
    enableSpawnAgent: config.enableSpawnAgent ?? preset.enableSpawnAgent ?? true,
  }
}

function build(normalized, createSpawnTool, tools) {
  if (normalized.enableSpawnAgent && createSpawnTool) {
    const spawnTool = createSpawnTool()
    tools.push({
      ...spawnTool,
      execute: spawnTool.execute,
    })
  }
}
