from crewai import Agent


class ImportedFactory:
    def direct(self):
        return Agent(name="outer-worker")
