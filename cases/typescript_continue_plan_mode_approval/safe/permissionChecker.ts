export function checkToolPermission(toolCall: any, permissions: any) {
  const basePermission = permissions.defaultPermission;
  const evaluatedPolicy = toolCall.evaluateToolCallPolicy(basePermission, toolCall.arguments);
  if (evaluatedPolicy === "disabled") {
    return { permission: "exclude" };
  }
  if (evaluatedPolicy === "allowedWithPermission") {
    return { permission: "ask" };
  }
  return { permission: basePermission };
}
