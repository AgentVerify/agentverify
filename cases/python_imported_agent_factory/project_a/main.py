from crewai import Crew

from factory import ImportedFactory


factory = ImportedFactory()
worker = factory.direct()
positive = Crew(agents=[worker], tasks=[])


indirect_worker = factory.indirect()
indirect = Crew(agents=[indirect_worker], tasks=[])


def receiver_rebound(other):
    local_factory = ImportedFactory()
    local_factory = other
    rebound_worker = local_factory.direct()
    return Crew(agents=[rebound_worker], tasks=[])


def constructor_shadowed(ImportedFactory):
    local_factory = ImportedFactory()
    shadowed_worker = local_factory.direct()
    return Crew(agents=[shadowed_worker], tasks=[])


def result_rebound():
    local_factory = ImportedFactory()
    local_worker = local_factory.direct()
    local_worker = object()
    return Crew(agents=[local_worker], tasks=[])
