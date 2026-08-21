from pathlib import Path
from metagpt.tools.tool_registry import register_tool as meta_register
from metagpt.utils.file import MemoryFileSystem
from playwright.async_api import Page

@meta_register(tags=["execution"])
def direct_tool(page: Page, code: str):
    return page.evaluate(code)


@meta_register(include_functions=["run"])
class Runner:
    def run(self, page: Page, code: str):
        return page.evaluate(code)

    def helper(self, page: Page, code: str):
        return page.evaluate(code)


ENTRYPOINTS = ["run"]


@meta_register(include_functions=ENTRYPOINTS)
class OpaqueRunner:
    def run(self, page: Page, code: str):
        return page.evaluate(code)


@meta_register()
def memory_write(name: str, content: str):
    memory = MemoryFileSystem()
    with memory.open(name, "w") as handle:
        handle.write(content)


@meta_register()
def fixed_write(content: str):
    Path("/tmp/agentverify-fixed.txt").write_text(content)
