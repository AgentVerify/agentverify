import { getNativeTools, getMcpServerTools } from "../prompts/tools/native-tools"

export async function buildNativeToolsArrayWithRestrictions(options: BuildToolsOptions) {
	const nativeTools = getNativeTools({
		supportsImages: false,
	})
	const filteredNativeTools = filterNativeToolsForMode(
		nativeTools,
	)
	const filteredTools = [...filteredNativeTools]
	return {
		tools: filteredTools,
	}
}
