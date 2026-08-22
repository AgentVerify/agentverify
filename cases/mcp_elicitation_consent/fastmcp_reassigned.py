from fastmcp.client.client import Client


async def handle_elicitation(message, response_type, params, context):
    return response_type(value=42)


handle_elicitation = external_handler
client = Client("server.py", elicitation_handler=handle_elicitation)
