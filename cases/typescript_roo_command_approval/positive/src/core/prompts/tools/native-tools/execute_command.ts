import type OpenAI from "openai"

const EXECUTE_COMMAND_DESCRIPTION = `Request to execute a CLI command on the system.`

export default {
	type: "function",
	function: {
		name: "execute_command",
		description: EXECUTE_COMMAND_DESCRIPTION,
		parameters: {
			type: "object",
			properties: {
				command: {
					type: "string",
				},
			},
			required: ["command", "cwd", "timeout"],
		},
	},
} satisfies OpenAI.Chat.ChatCompletionTool
