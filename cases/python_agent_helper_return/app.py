from crewai import Agent, Crew


class FactoryCases:
    @staticmethod
    def direct_agent() -> Agent:
        return Agent(role="direct", goal="g", backstory="b")

    def use_direct(self):
        agent = self.direct_agent()
        return Crew(agents=[agent], tasks=[])

    def agent_and_task(self):
        agent = Agent(role="tuple", goal="g", backstory="b")
        task = object()
        return agent, task

    def use_tuple(self):
        agent, task = self.agent_and_task()
        return Crew(agents=[agent], tasks=[task])

    def conditional_return(self, enabled: bool):
        if enabled:
            return Agent(role="first", goal="g", backstory="b")
        return Agent(role="second", goal="g", backstory="b")

    def use_conditional(self):
        agent = self.conditional_return(True)
        return Crew(agents=[agent], tasks=[])

    def reassigned_return(self):
        agent = Agent(role="reassigned", goal="g", backstory="b")
        agent = object()
        return agent

    def use_reassigned(self):
        agent = self.reassigned_return()
        return Crew(agents=[agent], tasks=[])

    def transformed_return(self):
        agent = Agent(role="transformed", goal="g", backstory="b")
        return identity(agent)

    def use_transformed(self):
        agent = self.transformed_return()
        return Crew(agents=[agent], tasks=[])

    def use_cross_branch(self, enabled: bool):
        if enabled:
            agent, task = self.agent_and_task()
        return Crew(agents=[agent], tasks=[task])

    def rebound_self(self, factory):
        self = factory
        agent = self.direct_agent()
        return Crew(agents=[agent], tasks=[])


class OtherFactory:
    @staticmethod
    def direct_agent() -> Agent:
        return Agent(role="other", goal="g", backstory="b")


def wrong_receiver(factory: OtherFactory):
    agent = factory.direct_agent()
    return Crew(agents=[agent], tasks=[])


def identity(value):
    return value


class ReboundHelper:
    def direct_agent(self) -> Agent:
        return Agent(role="rebound-helper", goal="g", backstory="b")

    direct_agent = identity

    def use_rebound_helper(self):
        agent = self.direct_agent()
        return Crew(agents=[agent], tasks=[])
