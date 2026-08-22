export function convertMcpToolsToFunctionTools(mcpTools: any[], server: any) {
  return mcpTools.map((mcpTool, index) =>
    mcpToFunctionTool(mcpTool, server, false, { index }),
  );
}

export function mcpToFunctionTool(mcpTool: any, server: any) {
  if (mcpTool.strict) {
    return tool({ name: mcpTool.name, execute: server.callTool });
  }
  return tool({ name: mcpTool.name, execute: server.callTool });
}
