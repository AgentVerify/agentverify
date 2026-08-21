class MCPServer:
    def __init__(self, require_approval=None):
        self._needs_approval_policy = self._normalize_needs_approval(
            require_approval=require_approval
        )

    @staticmethod
    def _normalize_needs_approval(*, require_approval):
        if require_approval is None:
            return False
        return bool(require_approval)

    def _get_needs_approval_for_tool(self, tool, agent):
        policy = self._needs_approval_policy
        if isinstance(policy, dict):
            return bool(policy.get(tool.name, False))
        return bool(policy)


class MCPServerStdio(MCPServer):
    def __init__(self, params, require_approval=None):
        super().__init__(require_approval=require_approval)
        self.params = params
