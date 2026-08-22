from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.async_api import Page


class BrowserContext:
    page: Page | None = None


class OrdinaryContext:
    page: Any = None


class DuplicateContext:
    def __init__(self):
        self.page: Page | None = None
        self.page: Page | None = None
