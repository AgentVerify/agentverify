async function requestTerminalToolApproval(request: ToolApprovalRequest) {
  return {
    approved: false,
    reason: `Tool "${request.toolName}" requires approval in a TTY session`,
  }
}

export async function requestToolApproval(request: ToolApprovalRequest) {
  return requestTerminalToolApproval(request)
}
