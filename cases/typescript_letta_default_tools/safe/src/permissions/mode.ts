export const DEFAULT_PERMISSION_MODE = "standard"

export function checkModeOverride(mode) {
	if (mode === "unrestricted") return { decision: "allow" }
	return null
}
