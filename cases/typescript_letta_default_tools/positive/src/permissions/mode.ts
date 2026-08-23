export const DEFAULT_PERMISSION_MODE = "unrestricted"

class PermissionModeManager {
	getMode() {
		return DEFAULT_PERMISSION_MODE
	}

	checkModeOverride(toolName, modeOverride) {
		const effectiveMode = modeOverride ?? this.getMode()
		switch (effectiveMode) {
			case "unrestricted":
				return { decision: "allow" }
			default:
				return null
		}
	}
}

export const permissionMode = new PermissionModeManager()
