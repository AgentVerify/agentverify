from fastmcp.client.client import Client
from fastmcp.client.elicitation import ElicitResult


async def handle_elicitation(message, response_type, params, context):
    print(message)
    answer = input("Accept, decline, or cancel? ").strip().lower()
    if answer == "decline":
        return ElicitResult(action="decline")
    if answer == "cancel":
        return ElicitResult(action="cancel")
    return ElicitResult(action="accept", content={})


client = Client("server.py", elicitation_handler=handle_elicitation)
