import { bash } from "./impl/bash"
import { write } from "./impl/write"

export const TOOL_DEFINITIONS = {
	Bash: defineTool({
		impl: bash,
	}),
	Write: defineTool({
		impl: write,
	}),
}
