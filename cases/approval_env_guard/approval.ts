const AUTO_APPROVE_HITL = process.env.AUTO_APPROVE_HITL === "1";

export function approveHitl(): boolean {
  if (AUTO_APPROVE_HITL) {
    console.log("auto approval enabled");
    return true;
  }
  return false;
}

export function approveShell(): boolean {
  if (process.env.SHELL_AUTO_APPROVE === "1") return true;
  return false;
}

export function safeStatusFlag(): boolean {
  if (process.env.AUTO_APPROVED_WARNING === "1") return true;
  return false;
}

export function conditionalApproval(isSafe: boolean): boolean {
  if (process.env.AUTO_APPROVE_TOOLS === "1") {
    if (isSafe) return true;
  }
  return false;
}

export function locallyConfiguredApproval(): boolean {
  const localAutoApprove = process.env.LOCAL_AUTO_APPROVE === "1";
  if (localAutoApprove) return true;
  return false;
}
