from agents import Agent, function_tool


@function_tool
def write_file(path: str, content: str) -> None:
    with open(path, "w") as handle:
        handle.write(content)


@function_tool
def write_fixed_log(content: str) -> None:
    with open("/tmp/agentverify-example.log", "a") as handle:
        handle.write(content)


agent = Agent(name="writer", tools=[write_file, write_fixed_log])

