import executeCommand from "./execute_command"

export interface NativeToolsOptions {}

export function getNativeTools(options: NativeToolsOptions = {}) {
	return [
		executeCommand,
	]
}

export const nativeTools = getNativeTools()
