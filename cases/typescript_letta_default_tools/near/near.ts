import type { ToolReturn } from "@letta-ai/not-letta-client/resources/agents/messages"

export const DEFAULT_PERMISSION_MODE = "unrestricted"
export const tools = ["Bash", "Write"]
export function run(command) {
	return spawn(command)
}
