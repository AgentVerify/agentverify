import { ALL_BUILT_IN_TOOLS } from "../tools/allBuiltIns";

export function checkToolPermission(toolCall: any, permissions: any) {
  let basePermission = "ask";
  for (const policy of permissions.policies) {
    if (policy.tool === toolCall.name || policy.tool === "*") {
      basePermission = policy.permission;
      break;
    }
  }
  const tool = ALL_BUILT_IN_TOOLS.find((t) => t.name === toolCall.name);
  if (tool?.evaluateToolCallPolicy) {
    const evaluatedPolicy = tool.evaluateToolCallPolicy(
      basePermission === "allow" ? "allowedWithoutPermission" : "allowedWithPermission",
      toolCall.arguments,
    );
    if (evaluatedPolicy === "disabled") {
      return { permission: "exclude" };
    }
    // Otherwise, user preference wins - return the original base permission
    return { permission: basePermission };
  }
  return { permission: basePermission };
}
