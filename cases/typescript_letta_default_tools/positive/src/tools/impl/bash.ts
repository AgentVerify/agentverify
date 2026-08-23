import { spawnWithLauncher } from "./shell-runner"
import { applyShellSandbox } from "./shell-sandbox"

export async function spawnCommand(command, options) {
	const commandToRun = command
	const executable = "/bin/zsh"
	const innerLauncher = [executable, "-c", commandToRun]
	const sandboxed = applyShellSandbox(innerLauncher, options.cwd, options.env)
	return spawnWithLauncher(sandboxed.launcher, {
		cwd: options.cwd,
		env: sandboxed.env,
		sourceCommand: command,
	})
}

export async function bash(args) {
	validateRequiredParams(args, ["command"], "Bash")
	const { command } = args
	return spawnCommand(command, {
		cwd: process.cwd(),
		env: process.env,
	})
}
