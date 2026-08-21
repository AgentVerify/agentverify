from mcp import FastMCP

from .tools import (
    branch_wrapped_write,
    deferred_wrapped_write,
    direct_wrapped_write,
    factory_wrapped_write,
    misleading_wrapped_write,
    nested_wrapped_write,
    nested_write,
    rebound_write,
    wrapped_write,
)
from .tools import (
    imported_write as registered_alias,
)
from .wrappers import branch_only, configured, deferred, misleading, transparent

mcp = FastMCP("fixture")


def local_write(path: str) -> None:
    with open(path, "w") as handle:
        handle.write("local")


def wrapper(function):
    return function


mcp.tool(require_approval=True)(registered_alias)
mcp.tool()(local_write)
mcp.tool()(wrapper(wrapped_write))

rebound_write = local_write  # noqa: F811 - adversarial rebinding fixture
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


mcp.tool()(transparent(direct_wrapped_write))
mcp.tool()(configured("fixture")(factory_wrapped_write))
mcp.tool()(transparent(transparent(nested_wrapped_write)))
mcp.tool()(misleading(misleading_wrapped_write))
mcp.tool()(branch_only(branch_wrapped_write))
mcp.tool()(deferred(deferred_wrapped_write))
mcp.tool()(
    transparent(
        transparent(transparent(transparent(transparent(wrapped_write))))
    )
)
