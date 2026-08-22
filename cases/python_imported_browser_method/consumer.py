from browser_state import (
    BrowserState,
    DecoratedState,
    DuplicateState,
    OrdinaryState,
    ReboundMethodState,
    SyncBrowserState,
)
from playwright.async_api import Page

BrowserReceiver = Page


async def exact_closure(state: BrowserState, script: str):
    async def fingerprint():
        page = await state.get_page()
        if page is None:
            return None
        return await page.evaluate(script)

    return await fingerprint()


def exact_sync(state: SyncBrowserState, script: str):
    page = state.get_page()
    return page.evaluate(script)


async def ordinary_return(state: OrdinaryState, script: str):
    page = await state.get_page()
    return await page.evaluate(script)


async def duplicate_method(state: DuplicateState, script: str):
    page = await state.get_page()
    return await page.evaluate(script)


async def decorated_method(state: DecoratedState, script: str):
    page = await state.get_page()
    return await page.evaluate(script)


async def rebound_method(state: ReboundMethodState, script: str):
    page = await state.get_page()
    return await page.evaluate(script)


async def reassigned_context(state: BrowserState, script: str):
    state = object()
    page = await state.get_page()
    return await page.evaluate(script)


async def reassigned_alias(state: BrowserState, script: str):
    page = await state.get_page()
    page = object()
    return await page.evaluate(script)


async def missing_dominance(state: BrowserState, script: str, enabled: bool):
    if enabled:
        page = await state.get_page()
    return await page.evaluate(script)


async def shadowed_closure(state: BrowserState, script: str):
    async def fingerprint(state=None):
        page = await state.get_page()
        return await page.evaluate(script)

    return await fingerprint()


async def wrong_await_mode(state: SyncBrowserState, script: str):
    page = await state.get_page()
    return await page.evaluate(script)


def wrong_sync_mode(state: BrowserState, script: str):
    page = state.get_page()
    return page.evaluate(script)


async def nonlocal_reassigned(state: BrowserState, script: str):
    async def mutate():
        nonlocal state
        state = object()

    async def fingerprint():
        page = await state.get_page()
        return await page.evaluate(script)

    await mutate()
    return await fingerprint()
