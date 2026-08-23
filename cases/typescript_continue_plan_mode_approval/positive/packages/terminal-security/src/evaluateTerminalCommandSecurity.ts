import { parse } from "shell-quote";

export function evaluateTerminalCommandSecurity(basePolicy: string, command: string) {
  const normalizedCommand = command.trim();
  const tokens = parse(normalizedCommand);
  return evaluateSingleCommand(tokens as string[], normalizedCommand);
}

function evaluateSingleCommand(commandTokens: string[], originalCommand: string) {
  const baseCommand = commandTokens[0].toLowerCase();
  const args = commandTokens.slice(1);
  if (isCriticalCommand(baseCommand, args)) {
    return "disabled";
  }
  if (isHighRiskCommand(baseCommand, args, originalCommand)) {
    return "allowedWithPermission";
  }
  if (isSafeCommand(baseCommand, args)) {
    return "allowedWithoutPermission";
  }
  // Default: unknown commands require permission
  return "allowedWithPermission";
}

declare function isCriticalCommand(command: string, args: string[]): boolean;
declare function isHighRiskCommand(command: string, args: string[], original: string): boolean;
declare function isSafeCommand(command: string, args: string[]): boolean;
