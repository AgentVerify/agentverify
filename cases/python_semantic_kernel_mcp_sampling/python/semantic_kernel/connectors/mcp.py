class MCPPluginBase:
    def __init__(
        self,
        sampling_consent_callback=None,
        sampling_auto_approve: bool = False,
    ):
        self.sampling_consent_callback = sampling_consent_callback
        self.sampling_auto_approve = sampling_auto_approve

    async def connect(self):
        ClientSession(sampling_callback=self.sampling_callback)

    async def sampling_callback(self, context, params):
        if self.sampling_consent_callback is None:
            if not self.sampling_auto_approve:
                return types.ErrorData(message="Sampling denied")
        elif not await self._is_sampling_approved(params):
            return types.ErrorData(message="Sampling denied by policy")
        chat_history = ChatHistory(system_message=params.systemPrompt)
        completion_settings.max_completion_tokens = params.maxTokens
        result = await service.get_chat_message_content(
            chat_history,
            completion_settings,
        )
        return types.CreateMessageResult(content=result)


class MCPStdioPlugin(MCPPluginBase):
    def __init__(self, sampling_consent_callback=None, sampling_auto_approve: bool = False):
        super().__init__(
            sampling_consent_callback=sampling_consent_callback,
            sampling_auto_approve=sampling_auto_approve,
        )
