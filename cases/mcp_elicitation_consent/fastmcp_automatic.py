from fastmcp.client.client import Client


async def handle_elicitation(message, response_type, params, context):
    return response_type(value=42)


client = Client("server.py", elicitation_handler=handle_elicitation)
