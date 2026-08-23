import { AutoApprovalHandler, checkAutoApproval } from "../auto-approval"
import { buildNativeToolsArrayWithRestrictions } from "./build-tools"

export class Task extends EventEmitter<TaskEvents> implements TaskLike {
	async ask(type, text, isProtected) {
		const state = await this.provider.getState()
		const approval = await checkAutoApproval({ state, ask: type, text, isProtected })
		if (approval.decision === "approve") {
			this.approveAsk()
		}
	}

	async run() {
		const toolsResult = await buildNativeToolsArrayWithRestrictions({
			provider: this.provider,
		})
		return toolsResult
	}
}
