from mcp import ClientSession
import mcp.types as types


async def run(read_stream, write_stream):
    async def decline(context, params):
        return types.ElicitResult(action="decline")

    async with ClientSession(
        read_stream,
        write_stream,
        elicitation_callback=decline,
    ) as session:
        await session.initialize()
