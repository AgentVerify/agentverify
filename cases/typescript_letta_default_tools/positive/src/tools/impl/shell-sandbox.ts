import { resolveShellSandboxContext } from "@/permissions/sandbox-gate"

/** OFF by default; set `LETTA_FS_SANDBOX=1` to opt in. */
export function applyShellSandbox(launcher, cwd, env) {
	const unchanged = { launcher, env, backend: null }
	const ctx = resolveShellSandboxContext(cwd, env)
	if (!ctx) return unchanged
	return { launcher: wrapLauncher(launcher), env, backend: ctx.backend }
}
