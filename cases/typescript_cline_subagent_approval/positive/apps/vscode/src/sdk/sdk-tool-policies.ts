/**
 * The SDK defaults unlisted tools to auto-approved. For tools controlled by
 * AutoApproveBar, force the SDK to call requestToolApproval.
 */
export function buildToolPolicies(): Record<string, { autoApprove?: boolean }> {
  const policies: Record<string, { autoApprove?: boolean }> = {}
  const set = (tools: string[]) => {
    for (const tool of tools) policies[tool] = { autoApprove: false }
  }
  set(["editor", "replace_in_file", "write_to_file", "apply_patch", "delete_file"])
  set(["run_commands", "execute_command"])
  return policies
}
