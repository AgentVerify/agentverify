from local_fastmcp import Client


async def handle_elicitation(message, response_type, params, context):
    return {"answer": 42}


client = Client("server.py", elicitation_handler=handle_elicitation)
