export class LocalRuntimeHost {
  async start() {
    return prepareLocalRuntimeBootstrap({
      createSpawnTool: () =>
        createSessionSpawnTool(
          subAgentDeps,
          bootstrap.config,
          sessionId,
          sessionToolExecutors,
        ),
      createSubAgentLifecycleCallbacks: (config) => callbacks(config),
      toolPolicies: bootstrap.toolPolicies,
      requestToolApproval: bootstrap.requestToolApproval,
    })
  }
}
