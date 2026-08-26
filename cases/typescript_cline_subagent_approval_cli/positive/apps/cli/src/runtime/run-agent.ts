import { createCliCore } from "../session/session"
import { requestToolApproval } from "../utils/approval"

export async function runAgent(prompt: string, config: Config): Promise<void> {
  const isYoloMode = config.mode === "yolo"
  const sessionManager = await createCliCore({
    capabilities: {
      requestToolApproval,
    },
    forceLocalBackend: isYoloMode || config.sandbox === true,
    toolPolicies: config.toolPolicies,
  })
}
