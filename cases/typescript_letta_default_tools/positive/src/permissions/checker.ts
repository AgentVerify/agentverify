import { permissionMode } from "./mode"

export function checkPermission(toolName, toolArgs, permissions, modeState) {
	const workspaceGuardResult = evaluateWorkspaceSandboxGuard(toolName, toolArgs)
	if (workspaceGuardResult) {
		return { decision: "deny", matchedRule: workspaceGuardResult.matchedRule }
	}
	const guardResult = evaluateCrossAgentGuard(toolName, toolArgs)
	if (guardResult) {
		return { decision: "deny", matchedRule: guardResult.matchedRule }
	}
	if (permissions.deny) {
		for (const pattern of permissions.deny) {
			if (matchesRule(pattern, true)) {
				return { decision: "deny", matchedRule: pattern }
			}
		}
	}
	const disallowedTools = cliPermissions.getDisallowedTools()
	for (const pattern of disallowedTools) {
		if (matchesRule(pattern, true)) {
			return { decision: "deny", matchedRule: `${pattern} (CLI)` }
		}
	}
	if (permissions.alwaysAsk) {
		for (const pattern of permissions.alwaysAsk) {
			if (matchesRule(pattern, true)) {
				return { decision: "alwaysAsk", matchedRule: pattern }
			}
		}
	}

	const effectiveMode = modeState?.mode ?? permissionMode.getMode()
	const modeOverride = permissionMode.checkModeOverride(toolName, effectiveMode)
	if (modeOverride) {
		return {
			decision: modeOverride.decision,
			matchedRule: `${effectiveMode} mode`,
		}
	}
	return { decision: "ask" }
}

export async function checkPermissionWithHooks(toolName, toolArgs, permissions, workingDirectory, modeState) {
	return checkPermission(toolName, toolArgs, permissions, modeState)
}
