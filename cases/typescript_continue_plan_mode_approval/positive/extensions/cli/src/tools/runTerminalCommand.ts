import { spawn } from "node:child_process";
import { evaluateTerminalCommandSecurity } from "@continuedev/terminal-security";

type Tool = Record<string, unknown>;

function getShellCommand(command: string) {
  return { shell: process.env.SHELL || "/bin/bash", args: ["-l", "-c", command] };
}

export const runTerminalCommandTool: Tool = {
  name: "Bash",
  readonly: false,
  evaluateToolCallPolicy: (basePolicy: string, parsedArgs: Record<string, unknown>) =>
    evaluateTerminalCommandSecurity(
      basePolicy,
      parsedArgs.command as string,
    ),
  run: async ({ command }: { command: string }) => {
    const { shell, args } = getShellCommand(command);
    const child = spawn(shell, args);
    return child.pid;
  },
};
