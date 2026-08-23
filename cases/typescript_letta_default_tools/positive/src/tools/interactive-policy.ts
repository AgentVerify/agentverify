const INTERACTIVE_APPROVAL_TOOLS = new Set(["AskUserQuestion"])

export function isInteractiveApprovalTool(toolName: string): boolean {
	return INTERACTIVE_APPROVAL_TOOLS.has(toolName)
}
