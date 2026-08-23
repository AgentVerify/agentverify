import { permissionMode as globalPermissionMode } from "@/permissions/mode"

export function getEffectivePermissionModeState(permissionModeState) {
	return permissionModeState ?? {
		get mode() {
			return globalPermissionMode.getMode()
		},
	}
}
