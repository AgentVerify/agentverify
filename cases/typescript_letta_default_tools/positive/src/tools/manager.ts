import { TOOL_DEFINITIONS } from "./tool-definitions"

export const ANTHROPIC_DEFAULT_TOOLS = [
	"Bash",
	"Write",
]

export async function buildRegistryForModel() {
	let baseToolNames = ANTHROPIC_DEFAULT_TOOLS
	const registry = new Map()
	for (const name of baseToolNames) {
		const definition = TOOL_DEFINITIONS[name]
		registry.set(name, {
			fn: definition.impl,
		})
	}
	return registry
}

export async function executeToolInner(name, enhancedArgs) {
	const tool = toolRegistry.get(name)
	const result = await tool.fn(enhancedArgs)
	return result
}

export async function executeTool(name, args) {
	return executeToolInner(name, args)
}
