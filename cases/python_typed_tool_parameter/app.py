from agents import Agent, ApplyPatchTool, ShellTool


def build_patch_agent(tool: ApplyPatchTool):
    return Agent(name="positive", tools=[tool])


def use_positive_positionally():
    tool = ApplyPatchTool(editor=object())
    return build_patch_agent(tool)


def use_positive_by_keyword():
    patch = ApplyPatchTool(editor=object())
    return build_patch_agent(tool=patch)


def use_positive_inline():
    return build_patch_agent(ApplyPatchTool(editor=object()))


def mismatched_builder(tool: ApplyPatchTool):
    return Agent(name="mismatched", tools=[tool])


def use_mismatched_builder():
    tool = ShellTool(executor=object())
    return mismatched_builder(tool)


def reassigned_parameter_builder(tool: ApplyPatchTool):
    tool = object()
    return Agent(name="reassigned-parameter", tools=[tool])


def use_reassigned_parameter_builder():
    tool = ApplyPatchTool(editor=object())
    return reassigned_parameter_builder(tool)


def uncalled_builder(tool: ApplyPatchTool):
    return Agent(name="uncalled", tools=[tool])


def identity(value):
    return value


def rebound_builder(tool: ApplyPatchTool):
    return Agent(name="rebound-helper", tools=[tool])


rebound_builder = identity


def use_rebound_builder():
    tool = ApplyPatchTool(editor=object())
    return rebound_builder(tool)


def shadowed_constructor_builder(tool: ApplyPatchTool):
    return Agent(name="shadowed-constructor", tools=[tool])


def use_shadowed_constructor_builder():
    ApplyPatchTool = ShellTool
    tool = ApplyPatchTool(executor=object())
    return shadowed_constructor_builder(tool)


def wrong_annotation_builder(tool: object):
    return Agent(name="wrong-annotation", tools=[tool])


def use_wrong_annotation_builder():
    tool = ApplyPatchTool(editor=object())
    return wrong_annotation_builder(tool)


def union_annotation_builder(tool: ApplyPatchTool | None):
    return Agent(name="union-annotation", tools=[tool])


def use_union_annotation_builder():
    tool = ApplyPatchTool(editor=object())
    return union_annotation_builder(tool)


def shadowed_builder(tool: ApplyPatchTool):
    return Agent(name="shadowed-helper", tools=[tool])


def use_shadowed_builder(shadowed_builder):
    tool = ApplyPatchTool(editor=object())
    return shadowed_builder(tool)


def reassigned_argument_builder(tool: ApplyPatchTool):
    return Agent(name="reassigned-argument", tools=[tool])


def use_reassigned_argument_builder():
    tool = ApplyPatchTool(editor=object())
    tool = ShellTool(executor=object())
    return reassigned_argument_builder(tool)


from external import imported_then_defined_builder


def imported_then_defined_builder(tool: ApplyPatchTool):
    return Agent(name="import-rebound-helper", tools=[tool])


def use_imported_then_defined_builder():
    tool = ApplyPatchTool(editor=object())
    return imported_then_defined_builder(tool)


def class_body_builder(tool: ApplyPatchTool):
    return Agent(name="class-body-shadow", tools=[tool])


class ClassBodyCaller:
    class_body_builder = identity
    tool = ApplyPatchTool(editor=object())
    agent = class_body_builder(tool)


def nested_shadow_builder(tool: ApplyPatchTool):
    return Agent(name="nested-shadow-helper", tools=[tool])


def use_nested_shadow_builder():
    nested_shadow_builder = identity

    def invoke():
        tool = ApplyPatchTool(editor=object())
        return nested_shadow_builder(tool)

    return invoke()


def nested_constructor_builder(tool: ApplyPatchTool):
    return Agent(name="nested-shadow-constructor", tools=[tool])


def use_nested_constructor_builder():
    ApplyPatchTool = ShellTool

    def invoke():
        tool = ApplyPatchTool(executor=object())
        return nested_constructor_builder(tool)

    return invoke()
