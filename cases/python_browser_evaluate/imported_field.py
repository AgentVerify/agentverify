from imported_field_context import BrowserContext, DuplicateContext, OrdinaryContext
from playwright.async_api import Page

BrowserReceiver = Page


async def exact_imported_field(ctx: BrowserContext):
    popup = ctx.page
    ctx.page = None
    if popup is None:
        return None
    return await popup.evaluate("document.title")


async def ordinary_imported_field(ctx: OrdinaryContext):
    popup = ctx.page
    return await popup.evaluate("document.title")


async def duplicate_imported_field(ctx: DuplicateContext):
    popup = ctx.page
    return await popup.evaluate("document.title")


async def reassigned_context(ctx: BrowserContext):
    ctx = object()
    popup = ctx.page
    return await popup.evaluate("document.title")


async def reassigned_alias(ctx: BrowserContext):
    popup = ctx.page
    popup = object()
    return await popup.evaluate("document.title")
