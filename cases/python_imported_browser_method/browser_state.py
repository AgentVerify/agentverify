from __future__ import annotations

from typing import Any

from playwright.async_api import Page


class BrowserState:
    async def get_page(self) -> Page | None: ...


class SyncBrowserState:
    def get_page(self) -> Page: ...


class OrdinaryState:
    async def get_page(self) -> Any: ...


class DuplicateState:
    async def get_page(self) -> Page: ...

    async def get_page(self) -> Page: ...  # noqa: F811


class DecoratedState:
    @staticmethod
    async def get_page() -> Page: ...


class ReboundMethodState:
    async def get_page(self) -> Page: ...

    get_page = object()  # noqa: F811
