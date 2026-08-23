import { checkToolPermission } from "@/tools/manager"

export async function classifyApprovals(approvals, opts = {}) {
	const needsUserInput = []
	const autoAllowed = []
	const autoDenied = []
	for (const approval of approvals) {
		const toolName = approval.toolName
		const parsedArgs = JSON.parse(approval.toolArgs)
		const permission = await checkToolPermission(
			toolName,
			parsedArgs,
			opts.workingDirectory,
			opts.permissionModeState,
		)
		let decision = permission.decision
		if (opts.alwaysRequiresUserInput?.(toolName) && decision === "allow") {
			decision = "ask"
		}
		const entry = { approval, permission, parsedArgs }
		const needsHumanApproval = decision === "ask" || decision === "alwaysAsk"
		if (needsHumanApproval) needsUserInput.push(entry)
		else if (decision === "deny") autoDenied.push(entry)
		else autoAllowed.push(entry)
	}
	return { needsUserInput, autoAllowed, autoDenied }
}
