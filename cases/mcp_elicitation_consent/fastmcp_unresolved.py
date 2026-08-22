from fastmcp.client.client import Client

client = Client("server.py", elicitation_handler=external_handler)
