import docker

client = docker.from_env()
client.containers.run("agent", privileged=True)
client.containers.run("agent", privileged=False)
