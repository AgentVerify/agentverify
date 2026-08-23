import { executeCommandTool } from "../tools/ExecuteCommandTool"

export async function presentAssistantMessage(cline, block) {
	const askApproval = async (
		type,
		partialMessage,
	) => {
		const { response, text, images } = await cline.ask(
			type,
			partialMessage,
		)
		return response === "yesButtonClicked"
	}

	switch (block.name) {
		case "execute_command":
			await executeCommandTool.handle(cline, block as ToolUse<"execute_command">, {
				askApproval,
			})
	}
}
