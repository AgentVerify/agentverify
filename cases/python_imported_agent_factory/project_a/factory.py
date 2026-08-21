from crewai import Agent


class ImportedFactory:
    def direct(self):
        return Agent(name="imported-worker")

    def indirect(self):
        worker = Agent(name="indirect-worker")
        return worker

    def conditional(self, enabled):
        if enabled:
            return Agent(name="first-worker")
        return Agent(name="second-worker")


class ReboundMethodFactory:
    def direct(self):
        return Agent(name="rebound-worker")

    direct = object()


class InheritedFactory(object):
    def direct(self):
        return Agent(name="inherited-worker")


class InstanceShadowFactory:
    def __init__(self):
        self.direct = lambda: object()

    def direct(self):
        return Agent(name="shadowed-worker")


class DynamicLookupFactory:
    def direct(self):
        return Agent(name="dynamic-worker")

    def __getattribute__(self, name):
        return object.__getattribute__(self, name)


class ModuleReboundFactory:
    def direct(self):
        return Agent(name="module-rebound-worker")


ModuleReboundFactory.direct = lambda self: object()
