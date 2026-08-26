import camel.agents as camel_agents
import marvin.agents as marvin_agents


camel_agents.ChatAgent = lambda **kwargs: {"shadowed": kwargs}
marvin_agents.Agent = lambda **kwargs: {"shadowed": kwargs}

camel = camel_agents.ChatAgent(name="shadowed-module-camel")
marvin = marvin_agents.Agent(name="shadowed-module-marvin")
