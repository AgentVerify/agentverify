import { parseCommand } from "../../shared/parse-command"

export function findLongestPrefixMatch(command: string, prefixes: string[]): string | null {
	const trimmedCommand = command.trim().toLowerCase()
	return prefixes.find((prefix) => trimmedCommand.startsWith(prefix)) || null
}

export function getCommandDecision(command, allowedCommands) {
	const subCommands = parseCommand(command)
	return subCommands.every((item) => findLongestPrefixMatch(item, allowedCommands))
		? "auto_approve"
		: "ask_user"
}
