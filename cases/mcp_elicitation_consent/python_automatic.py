from mcp import ClientSession
import mcp.types as types


async def run(read_stream, write_stream):
    async def elicit(context, params):
        return types.ElicitResult(
            action="accept",
            content={"city": "Lisbon"},
        )

    async with ClientSession(
        read_stream,
        write_stream,
        elicitation_callback=elicit,
    ) as session:
        await session.initialize()
