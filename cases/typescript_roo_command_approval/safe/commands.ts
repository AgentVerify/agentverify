import { parseCommand } from "../../shared/parse-command"

export function findLongestPrefixMatch(command: string, prefixes: string[]): string | null {
	const trimmedCommand = command.trim().toLowerCase()
	return (
		prefixes.find((prefix) => {
			const lowerPrefix = prefix.toLowerCase()
			return trimmedCommand === lowerPrefix || trimmedCommand.startsWith(`${lowerPrefix} `)
		}) || null
	)
}

export function getCommandDecision(command, allowedCommands) {
	const subCommands = parseCommand(command)
	return subCommands.every((item) => findLongestPrefixMatch(item, allowedCommands))
		? "auto_approve"
		: "ask_user"
}
