from mcp import ClientSession
import mcp.types as types


async def run(read_stream, write_stream):
    async def deny(context, params):
        return types.ErrorData(code=-1, message="Sampling disabled")

    async with ClientSession(
        read_stream,
        write_stream,
        sampling_callback=deny,
    ) as session:
        await session.initialize()
