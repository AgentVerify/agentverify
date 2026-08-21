import requests
from agents import Agent, function_tool
from playwright.async_api import Page


@function_tool
async def publish(page: Page, payload: dict) -> None:
    await page.click("button.publish")
    requests.post("https://example.invalid/publish", json=payload)


agent = Agent(name="publisher", tools=[publish])

