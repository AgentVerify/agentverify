class SdkSessionLifecycle {
  async start() {
    const autoApprovalSettings = StateManager.get().getGlobalSettingsKey("autoApprovalSettings")
    const toolPolicies = autoApprovalSettings ? buildToolPolicies(autoApprovalSettings, this.options.mcpHub) : undefined
    const sdkHost = await this.getOrCreateSharedHost()
    return sdkHost.start({
      ...(toolPolicies ? { toolPolicies } : {}),
    })
  }

  async getOrCreateSharedHost() {
    return VscodeSessionHost.create({
      requestToolApproval: this.options.requestToolApproval,
    })
  }
}
