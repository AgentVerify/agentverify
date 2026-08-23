import { executeApprovalBatch } from "@/agent/approval-execution"
import { isInteractiveApprovalTool } from "@/tools/interactive-policy"
import { classifyApprovalsWithSuggestions } from "./approval-suggestions"

export async function handleApprovalBranch(approvals, turnPermissionModeState) {
	const { autoAllowed, autoDenied, needsUserInput } = await classifyApprovalsWithSuggestions(
		approvals,
		{
			alwaysRequiresUserInput: isInteractiveApprovalTool,
			permissionModeState: turnPermissionModeState,
		},
	)
	const decisions = [
		...autoAllowed.map((entry) => ({
			type: "approve",
			approval: entry.approval,
		})),
		...autoDenied,
	]
	return executeApprovalBatch(decisions)
}
