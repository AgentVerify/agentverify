from fastmcp.client.client import Client
from fastmcp.client.elicitation import ElicitResult


async def handle_elicitation(message, response_type, params, context):
    print(message, params)
    answer = input("Response, decline, or cancel: ")
    if answer == "decline":
        return ElicitResult(action="decline")
    if answer == "cancel":
        return ElicitResult(action="cancel")
    return ElicitResult(action="accept", content={"answer": answer})


client = Client("server.py", elicitation_handler=handle_elicitation)
