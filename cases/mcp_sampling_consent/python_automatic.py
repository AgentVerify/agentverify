from mcp import ClientSession
import mcp.types as types


async def run(read_stream, write_stream):
    async def sample(context, params):
        return types.CreateMessageResult(
            role="assistant",
            content=types.TextContent(type="text", text="automatic response"),
            model="host-model",
        )

    async with ClientSession(
        read_stream,
        write_stream,
        sampling_callback=sample,
    ) as session:
        await session.initialize()
