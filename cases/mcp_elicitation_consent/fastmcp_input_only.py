from fastmcp.client.client import Client


async def handle_elicitation(message, response_type, params, context):
    value = input(f"{message}: ")
    return response_type(value=value)


client = Client("server.py", elicitation_handler=handle_elicitation)
