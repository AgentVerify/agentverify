from crewai import Crew

from factory import MissingFactory


factory = MissingFactory()
worker = factory.direct()
crew = Crew(agents=[worker], tasks=[])
