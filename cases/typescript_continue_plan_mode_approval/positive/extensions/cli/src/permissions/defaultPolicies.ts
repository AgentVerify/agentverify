export const PLAN_MODE_POLICIES = [
  { tool: "Edit", permission: "exclude" },
  { tool: "MultiEdit", permission: "exclude" },
  { tool: "Write", permission: "exclude" },
  { tool: "Bash", permission: "allow" },
  { tool: "*", permission: "allow" },
];

export function getDefaultToolPolicies() {
  return [
    { tool: "Bash", permission: "ask" },
    { tool: "*", permission: "ask" },
  ];
}
