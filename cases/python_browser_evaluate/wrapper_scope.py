from typing import Any

from playwright.async_api import Page
from skyvern.cli.mcp_tools._session import get_page

BrowserReceiver = Page


async def exact_wrapper_scope(selector: str):
    page, context = await get_page()
    if selector:
        scope: Any = getattr(page, "_locator_scope", None) or getattr(page, "page", page)
        return await scope.locator(selector).first.evaluate("el => el.tagName")
    return context


async def wrong_private_attribute(selector: str):
    page, context = await get_page()
    if selector:
        scope: Any = getattr(page, "_scope", None) or getattr(page, "page", page)
        return await scope.locator(selector).first.evaluate("el => el.tagName")
    return context


async def wrong_fallback(selector: str):
    page, context = await get_page()
    if selector:
        scope: Any = getattr(page, "_locator_scope", None) or getattr(page, "page", object())
        return await scope.locator(selector).first.evaluate("el => el.tagName")
    return context


async def shadowed_getattr(selector: str, getattr):
    page, context = await get_page()
    if selector:
        scope: Any = getattr(page, "_locator_scope", None) or getattr(page, "page", page)
        return await scope.locator(selector).first.evaluate("el => el.tagName")
    return context


async def no_branch_dominance(selector: str):
    page, _context = await get_page()
    if selector:
        scope: Any = getattr(page, "_locator_scope", None) or getattr(page, "page", page)
    return await scope.locator(selector).first.evaluate("el => el.tagName")
