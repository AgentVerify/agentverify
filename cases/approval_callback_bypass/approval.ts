import { Agent, applyPatchTool, shellTool } from '@openai/agents';

async function promptShellApproval() {
  if (process.env.SHELL_AUTO_APPROVE === '1') {
    return true;
  }
  return false;
}

async function promptPatchApproval() {
  if (process.env.APPLY_PATCH_AUTO_APPROVE === '1') {
    return true;
  }
  return false;
}

async function unusedPrompt() {
  if (process.env.UNUSED_AUTO_APPROVE === '1') {
    return true;
  }
  return false;
}

const operator = new Agent({
  name: 'operator',
  tools: [
    shellTool({
      shell: {},
      needsApproval: true,
      onApproval: async () => ({ approve: await promptShellApproval() }),
    }),
    applyPatchTool({
      editor: {},
      needsApproval: true,
      onApproval: async () => ({ approve: await promptPatchApproval() }),
    }),
    shellTool({
      environment: { type: 'container_auto' },
      needsApproval: true,
      onApproval: async () => ({ approve: await promptShellApproval() }),
    }),
    shellTool({
      shell: {},
      needsApproval: true,
      onApproval: async () => {
        void unusedPrompt;
        return { approve: false };
      },
    }),
  ],
});
