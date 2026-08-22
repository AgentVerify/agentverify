from mcp import ClientSession
import mcp.types as types


async def run(read_stream, write_stream, console):
    async def elicit(context, params):
        console.print(params.message)
        console.print(params.requestedSchema)
        decision = console.input("Accept this request? ").strip().lower()
        if decision not in {"y", "yes", "accept"}:
            return types.ElicitResult(action="decline")
        return types.ElicitResult(action="accept", content={"confirmed": True})

    async with ClientSession(
        read_stream,
        write_stream,
        elicitation_callback=elicit,
    ) as session:
        await session.initialize()
