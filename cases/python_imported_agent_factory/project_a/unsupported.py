from crewai import Crew

from factory import (
    DynamicLookupFactory,
    InheritedFactory,
    InstanceShadowFactory,
    ModuleReboundFactory,
    ReboundMethodFactory,
)


inherited = InheritedFactory()
inherited_worker = inherited.direct()
inherited_crew = Crew(agents=[inherited_worker], tasks=[])

rebound = ReboundMethodFactory()
rebound_worker = rebound.direct()
rebound_crew = Crew(agents=[rebound_worker], tasks=[])

shadowed = InstanceShadowFactory()
shadowed_worker = shadowed.direct()
shadowed_crew = Crew(agents=[shadowed_worker], tasks=[])

dynamic = DynamicLookupFactory()
dynamic_worker = dynamic.direct()
dynamic_crew = Crew(agents=[dynamic_worker], tasks=[])

module_rebound = ModuleReboundFactory()
module_rebound_worker = module_rebound.direct()
module_rebound_crew = Crew(agents=[module_rebound_worker], tasks=[])
