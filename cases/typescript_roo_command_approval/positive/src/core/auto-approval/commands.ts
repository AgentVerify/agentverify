import { parseCommand } from "../../shared/parse-command"

export function findLongestPrefixMatch(command: string, prefixes: string[]): string | null {
	const trimmedCommand = command.trim().toLowerCase()
	let longestMatch: string | null = null
	for (const prefix of prefixes) {
		const lowerPrefix = prefix.toLowerCase()
		if (lowerPrefix === "*" || trimmedCommand.startsWith(lowerPrefix)) {
			if (!longestMatch || lowerPrefix.length > longestMatch.length) {
				longestMatch = lowerPrefix
			}
		}
	}
	return longestMatch
}

export function getCommandDecision(command, allowedCommands, deniedCommands) {
	const subCommands = parseCommand(command)
	const decisions = subCommands.map((item) =>
		findLongestPrefixMatch(item, allowedCommands) ? "auto_approve" : "ask_user",
	)
	if (decisions.includes("auto_deny")) {
		return "auto_deny"
	}
	if (containsDangerousSubstitution(command)) {
		return "ask_user"
	}
	if (decisions.every((decision) => decision === "auto_approve")) {
		return "auto_approve"
	}
	return "ask_user"
}
