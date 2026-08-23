import { checkToolPermission } from "../permissions/permissionChecker";

declare function requestUserPermission(toolCall: unknown, callbacks: unknown): Promise<boolean>;
declare function executeToolCall(call: unknown, options: unknown): Promise<string>;

export async function checkToolPermissionApproval(
  permissions: unknown,
  toolCall: any,
  callbacks?: unknown,
) {
  const permissionCheck = checkToolPermission(toolCall, permissions);
  if (permissionCheck.permission === "allow") {
    return { approved: true };
  }
  const userApproved = await requestUserPermission(toolCall, callbacks);
  return { approved: userApproved };
}

export async function execute(call: unknown) {
  const toolResult = await executeToolCall(call, {
    parallelToolCallCount: 1,
  });
  return toolResult;
}
