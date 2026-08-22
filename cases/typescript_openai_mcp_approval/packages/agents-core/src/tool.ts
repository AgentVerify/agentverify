export function tool(options: any) {
  const needsApproval: ToolApprovalFunction<any> =
    typeof options.needsApproval === 'function'
      ? options.needsApproval
      : async () =>
          typeof options.needsApproval === 'boolean'
            ? options.needsApproval
            : false;
  return { ...options, needsApproval };
}
