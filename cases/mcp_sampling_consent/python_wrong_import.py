from local_mcp import ClientSession
import local_mcp.types as types


async def run(read_stream, write_stream):
    async def sample(context, params):
        return types.CreateMessageResult(role="assistant", content="response", model="host")

    async with ClientSession(
        read_stream,
        write_stream,
        sampling_callback=sample,
    ) as session:
        await session.initialize()
