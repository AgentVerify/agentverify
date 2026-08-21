from mcp import FastMCP

from .tools import (
    imported_write as registered_alias,
    nested_write,
    rebound_write,
    wrapped_write,
)

mcp = FastMCP("fixture")


def local_write(path: str) -> None:
    with open(path, "w") as handle:
        handle.write("local")


def wrapper(function):
    return function


mcp.tool(require_approval=True)(registered_alias)
mcp.tool()(local_write)
mcp.tool()(wrapper(wrapped_write))

rebound_write = local_write
mcp.tool()(rebound_write)


def install_nested() -> None:
    mcp.tool()(nested_write)


other = FastMCP("first")
other = FastMCP("second")
other.tool()(nested_write)


class Factory:
    pass


bogus = Factory()
bogus.tool()(nested_write)
