from urllib.parse import urlparse


def _is_loopback_host(hostname: str | None) -> bool:
    return hostname == "localhost"


def _url_origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    return scheme, (parsed.hostname or "").lower(), parsed.port


class RemoteA2aAgent:
    async def _validate_agent_card(self, agent_card) -> None:
        card_url = _compat.agent_card_url(agent_card)
        if not card_url:
            raise ValueError("Agent card must have a valid URL")
        self._validate_card_rpc_targets(agent_card)

    def _validate_card_rpc_targets(self, agent_card) -> None:
        source = self._agent_card_source
        if not source or not source.startswith(("http://", "https://")):
            return
        source_origin = _url_origin(source)
        for card_url in _compat.agent_card_rpc_urls(agent_card):
            parsed_card = urlparse(card_url)
            if parsed_card.scheme.lower() != "https" and not _is_loopback_host(
                parsed_card.hostname
            ):
                raise ValueError("Agent card RPC URL must use https")
            card_origin = _url_origin(card_url)
            if card_origin != source_origin:
                raise ValueError("Agent card RPC URL must have the same origin")

    async def _ensure_resolved(self, ctx=None):
        if self.per_invocation_card:
            agent_card = await self._resolve_agent_card(ctx)
            await self._validate_agent_card(agent_card)
            await self._ensure_httpx_client()
            client = self._a2a_client_factory.create(agent_card)
            return client

        if not self._agent_card:
            self._agent_card = await self._resolve_agent_card(ctx)
            await self._validate_agent_card(self._agent_card)
        if self._a2a_client_factory:
            self._a2a_client = self._a2a_client_factory.create(self._agent_card)
        return self._a2a_client
