from camel.agents import *
from marvin.agents import *


ChatAgent = lambda **kwargs: {"shadowed": kwargs}
Agent = lambda **kwargs: {"shadowed": kwargs}

camel = ChatAgent(name="shadowed-star-camel")
marvin = Agent(name="shadowed-star-marvin")
