from crewai import Crew

from factory import ImportedFactory
from external import ImportedFactory


factory = ImportedFactory()
worker = factory.direct()
crew = Crew(agents=[worker], tasks=[])
