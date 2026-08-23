import { classifyApprovals } from "@/cli/helpers/approval-classification"

export async function classifyApprovalsWithSuggestions(approvals, opts = {}) {
	return classifyApprovals(approvals, {
		...opts,
		getContext: async (toolName, parsedArgs, workingDirectory) =>
			analyzeToolApproval(toolName, parsedArgs, workingDirectory),
	})
}
