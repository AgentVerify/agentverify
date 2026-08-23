import { SERVICE_NAMES, serviceContainer, services } from "../services";

export async function getAllAvailableTools() {
  const mcpState = await serviceContainer.get(SERVICE_NAMES.MCP);
  return mcpState.tools.map(convertMcpToolToContinueTool);
}

export function convertMcpToolToContinueTool(mcpTool: any) {
  return {
    name: mcpTool.name,
    readonly: undefined,
    isBuiltIn: false,
    run: async (args: any) => {
      const result = await services.mcp?.runTool(mcpTool.name, args);
      return JSON.stringify(result?.content) ?? "";
    },
  };
}

export async function executeToolCall(toolCall: any) {
  return toolCall.tool.run(toolCall.arguments, {});
}
