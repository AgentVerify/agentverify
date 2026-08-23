import { PLAN_MODE_POLICIES } from "../permissions/defaultPolicies";

type PermissionMode = "normal" | "plan" | "auto";

export class ToolPermissionService {
  currentState = { currentMode: "normal", permissions: { policies: [] as unknown[] } };

  private generateModePolicies() {
    switch (this.currentState.currentMode) {
      case "plan":
        return [...PLAN_MODE_POLICIES];
      default:
        return [];
    }
  }

  initializeSync() {
    const modePolicies = this.generateModePolicies();
    let allPolicies: unknown[] = [];
    if (
      this.currentState.currentMode === "plan" ||
      this.currentState.currentMode === "auto"
    ) {
      allPolicies = [...modePolicies];
    }
    this.currentState.permissions.policies = allPolicies;
  }

  switchMode(newMode: PermissionMode) {
    this.currentState.currentMode = newMode;
    const modePolicies = this.generateModePolicies();
    let allPolicies: unknown[] = [];
    if (newMode === "plan" || newMode === "auto") {
      allPolicies = [...modePolicies];
    }
    this.currentState.permissions.policies = allPolicies;
  }
}
