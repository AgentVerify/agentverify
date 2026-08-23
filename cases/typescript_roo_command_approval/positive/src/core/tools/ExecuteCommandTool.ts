export class ExecuteCommandTool extends BaseTool<"execute_command"> {
	readonly name = "execute_command" as const

	async execute(params, task, callbacks) {
		const { command, cwd: customCwd, timeout: timeoutSeconds } = params
		const canonicalCommand = command
		const didApprove = await askApproval("command", canonicalCommand)
		if (!didApprove) {
			return
		}
		return executeCommandInTerminal(task, { command: canonicalCommand })
	}
}

export async function executeCommandInTerminal(task, { command }) {
	const callbacks = {}
	const terminal = await task.getTerminal()
	const process = terminal.runCommand(command, callbacks)
	return process
}
