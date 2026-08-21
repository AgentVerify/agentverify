import uuid


class BasePlugin:
    pass


class BigQueryLoggerConfig:
    enabled: bool = True
    event_allowlist: list[str] | None = None
    event_denylist: list[str] | None = None


class BigQueryAgentAnalyticsPlugin(BasePlugin):
    def get_drop_stats(self):
        return dict(self._dropped)

    def _record_retry_exhaustion(self, count):
        self._dropped["retry_exhausted"] += count

    async def _log_event(self, event_type, callback_context):
        if not self.config.enabled or self._is_shutting_down:
            return
        row = {
            "event_id": uuid.uuid4().hex,
            "agent": callback_context.agent_name,
            "user_id": callback_context.user_id,
            "session_id": callback_context.session.id,
            "invocation_id": callback_context.invocation_id,
            "tool": callback_context.tool_name,
        }
        await self.write_client.append_rows(row)

    async def before_tool_callback(self, callback_context):
        await self._log_event("TOOL_STARTING", callback_context)

    async def after_tool_callback(self, callback_context):
        await self._log_event("TOOL_COMPLETED", callback_context)

    async def on_tool_error_callback(self, callback_context):
        await self._log_event("TOOL_ERROR", callback_context)
