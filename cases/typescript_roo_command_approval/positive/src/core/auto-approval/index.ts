import { getCommandDecision } from "./commands"
import type { ExtensionState } from "@roo-code/types"

export async function checkAutoApproval({ state, ask, text, isProtected }) {
	if (!state || !state.autoApprovalEnabled) {
		return { decision: "ask" }
	}
	if (ask === "command") {
		if (state.alwaysAllowExecute === true) {
			const decision = getCommandDecision(text, state.allowedCommands || [], state.deniedCommands || [])
			if (decision === "auto_approve") {
				return { decision: "approve" }
			}
		}
	}
	return { decision: "ask" }
}
