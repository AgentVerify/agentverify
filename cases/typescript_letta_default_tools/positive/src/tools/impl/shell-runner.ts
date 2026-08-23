import { spawn } from "node:child_process"

export async function spawnWithLauncher(launcher, options) {
	const [executable, ...args] = launcher
	const childProcess = spawn(executable, args, {
		cwd: options.cwd,
		env: options.env,
		shell: false,
	})
	return childProcess
}
