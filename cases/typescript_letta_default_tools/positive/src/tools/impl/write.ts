import { promises as fs } from "node:fs"
import { expandFilePath } from "@/utils/file-path"
import { writeUtf8Text } from "@/utils/text-files"

export async function write(args) {
	validateRequiredParams(args, ["file_path", "content"], "Write")
	const { file_path, content } = args
	const resolvedPath = expandFilePath(file_path, process.cwd())
	const dir = path.dirname(resolvedPath)
	await fs.mkdir(dir, { recursive: true })
	await writeUtf8Text(resolvedPath, content)
}
