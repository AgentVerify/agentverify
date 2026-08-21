from agents import Agent, ApplyPatchTool


def build_inline_agent(patch: ApplyPatchTool):
    return Agent(name="inline-only", tools=[patch])


def use_inline_agent():
    return build_inline_agent(ApplyPatchTool(editor=object()))
