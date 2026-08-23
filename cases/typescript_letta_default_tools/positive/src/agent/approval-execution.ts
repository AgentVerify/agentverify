import { ToolReturn } from "@letta-ai/letta-client/resources/agents/messages"
import { executeTool } from "@/tools/manager"

async function executeSingleDecision(decision) {
	if (decision.type === "approve") {
		const parsedArgs = JSON.parse(decision.approval.toolArgs)
		const toolResult = await executeTool(
			decision.approval.toolName,
			parsedArgs,
		)
		return toolResult
	}
}

export async function executeApprovalBatch(decisions): Promise<ToolReturn[]> {
	return Promise.all(decisions.map(executeSingleDecision))
}
