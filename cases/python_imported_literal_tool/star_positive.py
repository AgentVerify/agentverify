from agents import Agent
from pkg.star_tools import *


star_operator = Agent(name="star-import-operator", tools=[star_writer])
filtered_operator = Agent(name="star-import-filtered", tools=[filtered_hidden])
