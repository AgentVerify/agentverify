from mcp import ClientSession
import mcp.types as types


async def run(read_stream, write_stream, console):
    async def sample(context, params):
        decision = console.input(f"Approve this complete request? {params}")
        if decision != "yes":
            return types.ErrorData(code=-1, message="Sampling rejected")
        return types.CreateMessageResult(
            role="assistant",
            content=types.TextContent(type="text", text="reviewed response"),
            model="host-model",
        )

    async with ClientSession(
        read_stream,
        write_stream,
        sampling_callback=sample,
    ) as session:
        await session.initialize()
