from fastmcp.client.client import Client


async def handle_elicitation(message, response_type, params, context):
    return build_response()


client = Client("server.py", elicitation_handler=handle_elicitation)
