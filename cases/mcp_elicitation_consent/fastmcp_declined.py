from fastmcp.client.client import Client
from fastmcp.client.elicitation import ElicitResult


async def handle_elicitation(message, response_type, params, context):
    return ElicitResult(action="decline")


client = Client("server.py", elicitation_handler=handle_elicitation)
