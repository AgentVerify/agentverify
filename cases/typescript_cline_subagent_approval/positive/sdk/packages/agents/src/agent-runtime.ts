class AgentRuntime {
  async prepare(toolCall: ToolCall) {
    const policy = resolveToolPolicy(toolCall.toolName, this.config.toolPolicies)
    if (policy.enabled === false) {
      return "disabled"
    } else if (policy.autoApprove === false) {
      return await this.requestToolApproval(toolCall)
    }
    return "execute"
  }
}
