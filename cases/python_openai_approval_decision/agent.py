import agents
from agents import Agent, Runner


agent = Agent(name="Python approval decision agent")


async def main() -> None:
    result = await Runner.run(agent, "start approval flow")
    state = result.to_state()
    for interruption in result.interruptions:
        state.approve(interruption)
        state.reject(interruption)

    stream_result = agents.Runner.run_streamed(agent, "start streaming approval flow")
    stream_state = stream_result.to_state()
    for interruption in stream_result.interruptions:
        stream_state.approve(interruption)

    loose_state = object()
    loose_state.approve("not an SDK state")

    rebound_state = result.to_state()
    rebound_state = object()
    rebound_state.approve("not an SDK state after reassignment")

    sticky_result = await Runner.run(agent, "start sticky approval flow")
    sticky_state = sticky_result.to_state()
    always = True
    once = False
    for interruption in sticky_result.interruptions:
        sticky_state.approve(interruption, always_approve=True)
        sticky_state.reject(interruption, always_reject=always)
        sticky_state.approve(interruption, always_approve=once)
