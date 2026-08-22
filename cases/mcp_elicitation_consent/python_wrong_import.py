from local_mcp import ClientSession
import local_mcp.types as types


async def run(read_stream, write_stream):
    async def elicit(context, params):
        return types.ElicitResult(action="accept", content={"confirmed": True})

    async with ClientSession(
        read_stream,
        write_stream,
        elicitation_callback=elicit,
    ) as session:
        await session.initialize()
