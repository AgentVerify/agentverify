const sandboxEnabled = !!args.dataDir || process.env.CLINE_SANDBOX?.trim() === "1"
const toolPolicies: Record<string, ToolPolicy> = {
  "*": {
    autoApprove: effectiveToolAutoApprove,
  },
}

const config: Config = {
  sandbox: sandboxEnabled,
  mode: effectiveMode,
  toolPolicies,
  enableSpawnAgent: !isYoloMode,
};
