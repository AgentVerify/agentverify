from mcp import ClientSession


async def run(read_stream, write_stream, callback):
    async with ClientSession(
        read_stream,
        write_stream,
        sampling_callback=callback,
    ) as session:
        await session.initialize()
