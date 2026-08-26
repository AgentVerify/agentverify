const SAFE_AUTO_APPROVE_TOOL_NAMES = [
  "ask_question",
  "read_files",
  "search_codebase",
]

const SAFE_AUTO_APPROVE_TOOLS = new Set<string>(SAFE_AUTO_APPROVE_TOOL_NAMES)

export function resolveInteractiveAutoApprovePolicy(input: {
  toolName: string
  baselinePolicies: Record<string, ToolPolicy>
  enabled: boolean
}): ToolPolicy {
  const toolPolicy = input.baselinePolicies[input.toolName] ?? {}
  const baselinePolicy = {
    ...(input.baselinePolicies["*"] ?? {}),
    ...toolPolicy,
  }
  return {
    ...baselinePolicy,
    autoApprove: input.enabled
      ? true
      : SAFE_AUTO_APPROVE_TOOLS.has(input.toolName)
        ? (toolPolicy.autoApprove ?? true)
        : false,
  }
}

export function applyInteractiveAutoApproveOverride(input: {
  targetPolicies: Record<string, ToolPolicy>
  baselinePolicies: Record<string, ToolPolicy>
  enabled: boolean
}): void {
  const globalPolicy = { ...(input.baselinePolicies["*"] ?? {}) }
  globalPolicy.autoApprove = input.enabled
}
