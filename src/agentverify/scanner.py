"""Python AST and TypeScript lexical frontends for AgentVerify."""

from __future__ import annotations

import ast
import json
import os
import re
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .ir import Component, Evidence, Relationship, RepositoryIR, Suppression
from .rules import run_rules

SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}
MAX_SOURCE_BYTES = 2_000_000
SKIP_DIRECTORIES = {
    ".git",
    ".agentverify-cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".next",
    "coverage",
    "vendor",
}

IMPORT_SIGNATURES = {
    "framework": {
        "LangChain": ("langchain",),
        "LangGraph": ("langgraph",),
        "CrewAI": ("crewai",),
        "AutoGen": ("autogen",),
        "OpenAI Agents SDK": ("agents", "@openai/agents"),
        "PydanticAI": ("pydantic_ai",),
        "Cline SDK": ("@cline/sdk",),
    },
    "provider": {
        "OpenAI": ("openai", "@ai-sdk/openai"),
        "Anthropic": ("anthropic", "@ai-sdk/anthropic"),
        "Azure OpenAI": ("azure.ai.openai",),
    },
    "protocol": {
        "MCP": ("mcp", "modelcontextprotocol", "@modelcontextprotocol/"),
    },
}

AGENT_CALLS = {"Agent", "AssistantAgent", "ConversableAgent", "LlmAgent", "StateGraph", "Crew"}
TOOL_DECORATORS = {"tool", "function_tool", "mcp.tool", "server.tool"}
MODEL_CONSTRUCTORS = {
    "OpenAI": {"OpenAI", "AsyncOpenAI", "ChatOpenAI", "OpenAIChatCompletionClient"},
    "Anthropic": {"Anthropic", "AsyncAnthropic", "ChatAnthropic"},
    "Azure OpenAI": {"AzureOpenAI", "AsyncAzureOpenAI", "AzureChatOpenAI"},
}
BUILTIN_TOOL_CAPABILITIES = {
    "ShellTool": ("shell-execution",),
    "ApplyPatchTool": ("filesystem",),
    "CustomTool": ("external-action",),
}
APPROVAL_BYPASS_NAME = re.compile(
    r"(?:^|[._])(?:\w+_)*auto_?approve$|"
    r"(?:^|[._])(?:skip_?confirmation|dangerously_?skip_?(?:permissions?|confirmation|approval))$",
    re.IGNORECASE,
)
APPROVAL_BYPASS_ENV_NAME = re.compile(
    r"(?:^|[._])(?:auto_?approve|auto_?approval|skip_?confirmation|"
    r"dangerously_?skip_?(?:permissions?|confirmation|approval))(?:$|[._])",
    re.IGNORECASE,
)
APPROVAL_GATE_NAME = re.compile(r"approv|confirm|consent|permission", re.IGNORECASE)


@dataclass(frozen=True)
class PythonFilesystemWriteSpec:
    path_index: int
    path_keywords: tuple[str, ...]
    operation: str
    path_role: str


PYTHON_FILESYSTEM_WRITE_FUNCTIONS = {
    "os.mkdir": PythonFilesystemWriteSpec(0, ("path",), "create", "target"),
    "os.makedirs": PythonFilesystemWriteSpec(0, ("name",), "create", "target"),
    "os.remove": PythonFilesystemWriteSpec(0, ("path",), "delete", "target"),
    "os.unlink": PythonFilesystemWriteSpec(0, ("path",), "delete", "target"),
    "os.rmdir": PythonFilesystemWriteSpec(0, ("path",), "delete", "target"),
    "os.removedirs": PythonFilesystemWriteSpec(0, ("name",), "delete", "target"),
    "os.rename": PythonFilesystemWriteSpec(1, ("dst",), "move", "destination"),
    "os.replace": PythonFilesystemWriteSpec(1, ("dst",), "move", "destination"),
    "shutil.copy": PythonFilesystemWriteSpec(1, ("dst",), "copy", "destination"),
    "shutil.copy2": PythonFilesystemWriteSpec(1, ("dst",), "copy", "destination"),
    "shutil.copyfile": PythonFilesystemWriteSpec(1, ("dst",), "copy", "destination"),
    "shutil.copytree": PythonFilesystemWriteSpec(1, ("dst",), "copy", "destination"),
    "shutil.move": PythonFilesystemWriteSpec(1, ("dst",), "move", "destination"),
    "shutil.rmtree": PythonFilesystemWriteSpec(0, ("path",), "delete", "target"),
}


def excerpt(lines: list[str], line: int) -> str:
    return lines[line - 1].strip()[:240] if 0 < line <= len(lines) else ""


def source_scope(path: str) -> str:
    lowered = path.lower()
    parts = set(Path(lowered).parts)
    filename = Path(lowered).name
    if (
        parts & {"test", "tests", "__tests__", "fixtures"}
        or any(marker in filename for marker in (".test.", ".spec."))
        or filename.startswith("test_")
    ):
        return "test"
    if parts & {"example", "examples", "samples"}:
        return "example"
    return "production"


def source_symbol(frontend: str, path: str, kind: str, name: str) -> str:
    return f"{frontend}:{path}#{kind}:{name}"


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def python_expression_names(node: ast.AST | None) -> set[str]:
    if node is None:
        return set()
    return {candidate.id for candidate in ast.walk(node) if isinstance(candidate, ast.Name)}


def python_static_url_prefix(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        prefix = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                break
            prefix.append(value.value)
        return "".join(prefix)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return python_static_url_prefix(node.left)
    return ""


def python_http_origin_is_dynamic(node: ast.AST | None, dynamic_names: set[str]) -> bool:
    if not python_expression_names(node) & dynamic_names:
        return False
    prefix = python_static_url_prefix(node)
    return re.match(r"^https?://[^/?#]+", prefix, re.IGNORECASE) is None


def component_from_import(ir: RepositoryIR, module: str, evidence: Evidence) -> None:
    for kind, signatures in IMPORT_SIGNATURES.items():
        for name, prefixes in signatures.items():
            if any(
                module == prefix
                or module.startswith(prefix if prefix.endswith("/") else f"{prefix}.")
                for prefix in prefixes
            ):
                ir.add_component(Component(kind, name, evidence, {"module": module}))


def provider_for_model(model: str) -> str:
    lowered = model.lower()
    if lowered.startswith(("gpt-", "o1", "o3", "o4")):
        return "OpenAI"
    if lowered.startswith("claude"):
        return "Anthropic"
    return "unresolved"


def python_approval_environment_names(node: ast.AST) -> set[str]:
    """Return semantic approval env vars compared to an explicit enabled value."""
    names: set[str] = set()
    enabled_values = {"1", "true", "yes", "all"}
    for candidate in ast.walk(node):
        if not isinstance(candidate, ast.Compare) or len(candidate.ops) != 1:
            continue
        if not isinstance(candidate.ops[0], ast.Eq) or len(candidate.comparators) != 1:
            continue
        sides = (candidate.left, candidate.comparators[0])
        for environment_side, value_side in (sides, sides[::-1]):
            if not (
                isinstance(value_side, ast.Constant)
                and isinstance(value_side.value, str)
                and value_side.value.lower() in enabled_values
            ):
                continue
            environment_name = ""
            if isinstance(environment_side, ast.Call) and dotted_name(environment_side.func) in {
                "os.getenv",
                "os.environ.get",
            }:
                if (
                    environment_side.args
                    and isinstance(environment_side.args[0], ast.Constant)
                    and isinstance(environment_side.args[0].value, str)
                ):
                    environment_name = environment_side.args[0].value
            elif (
                isinstance(environment_side, ast.Subscript)
                and dotted_name(environment_side.value) == "os.environ"
                and isinstance(environment_side.slice, ast.Constant)
                and isinstance(environment_side.slice.value, str)
            ):
                environment_name = environment_side.slice.value
            if environment_name and APPROVAL_BYPASS_ENV_NAME.search(environment_name):
                names.add(environment_name)
    return names


RegistryLiteralRequirement = tuple[str, int | None, bool]
RegistryMethodSummary = tuple[
    int | None,
    str,
    Evidence,
    tuple[RegistryLiteralRequirement, ...],
]


@dataclass(frozen=True)
class RegistryClassTarget:
    path: str
    name: str
    methods: dict[str, RegistryMethodSummary]


def resolve_python_import_path(
    root: Path,
    current_path: str,
    node: ast.ImportFrom,
    alias_name: str,
    module_paths: dict[str, str],
) -> str | None:
    """Resolve one absolute or relative Python import to a selected local file."""
    if node.level == 0 and node.module:
        return module_paths.get(node.module)
    if not node.level:
        return None
    base = Path(current_path).parent
    if node.level - 1 >= len(base.parts):
        return None
    for _ in range(node.level - 1):
        base = base.parent
    module_parts = (node.module or alias_name).split(".")
    module_path = base.joinpath(*module_parts)
    candidates = [module_path.with_suffix(".py"), module_path / "__init__.py"]
    resolved = [
        candidate
        for candidate in candidates
        if not candidate.is_absolute()
        and ".." not in candidate.parts
        and (root / candidate).is_file()
        and not (root / candidate).is_symlink()
    ]
    return resolved[0].as_posix() if len(resolved) == 1 else None


@dataclass(frozen=True)
class PythonPathBoundaryProof:
    evidence: Evidence
    boundary_scope: str
    candidate_name: str
    root_name: str
    strict_descendant: bool
    helper: str
    summary: str | None = None
    strength: str = "strong"


@dataclass(frozen=True)
class PythonPathHelperSummary:
    parameter_index: int
    parameter_name: str
    evidence: Evidence
    boundary_scope: str
    root_name: str
    helper: str


@dataclass(frozen=True)
class PythonToolRegistration:
    evidence: Evidence
    registrar: str
    resolution: str
    needs_approval: bool


@dataclass
class PythonPathState:
    dynamic_names: set[str]
    roots: dict[str, str]
    candidates: dict[str, str]
    guards: dict[str, PythonPathBoundaryProof]
    unresolved_candidates: dict[str, str]

    def clone(self) -> PythonPathState:
        return PythonPathState(
            set(self.dynamic_names),
            dict(self.roots),
            dict(self.candidates),
            dict(self.guards),
            dict(self.unresolved_candidates),
        )


def python_assigned_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return {name for element in target.elts for name in python_assigned_names(element)}
    return set()


def python_function_local_bindings(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    bindings = {
        argument.arg
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    }
    if node.args.vararg:
        bindings.add(node.args.vararg.arg)
    if node.args.kwarg:
        bindings.add(node.args.kwarg.arg)

    def collect(candidate: ast.AST) -> None:
        if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings.add(candidate.name)
            return
        if isinstance(candidate, ast.Lambda):
            return
        if isinstance(candidate, (ast.Import, ast.ImportFrom)):
            bindings.update(
                alias.asname or alias.name.split(".", 1)[0]
                for alias in candidate.names
            )
            return
        if isinstance(candidate, ast.ExceptHandler) and candidate.name:
            bindings.add(candidate.name)
        if isinstance(candidate, ast.Name) and isinstance(candidate.ctx, (ast.Store, ast.Del)):
            bindings.add(candidate.id)
        for child in ast.iter_child_nodes(candidate):
            collect(child)

    for statement in node.body:
        collect(statement)
    return bindings


def canonical_python_filesystem_api(
    call_name: str, aliases: dict[str, str]
) -> str | None:
    if canonical := aliases.get(call_name):
        return canonical if python_filesystem_write_spec(canonical) is not None else None
    if "." not in call_name:
        return None
    root, suffix = call_name.split(".", 1)
    module = aliases.get(root)
    if module not in {"os", "shutil"}:
        return None
    canonical = f"{module}.{suffix}"
    return canonical if canonical in PYTHON_FILESYSTEM_WRITE_FUNCTIONS else None


def python_filesystem_write_spec(
    canonical_api: str,
) -> PythonFilesystemWriteSpec | None:
    apis = canonical_api.split("|")
    specs = [PYTHON_FILESYSTEM_WRITE_FUNCTIONS.get(api) for api in apis]
    if not specs or any(spec is None for spec in specs):
        return None
    return specs[0] if all(spec == specs[0] for spec in specs[1:]) else None


def python_filesystem_callable_reference(
    expression: ast.AST, aliases: dict[str, str]
) -> str | None:
    if isinstance(expression, (ast.Name, ast.Attribute)):
        return canonical_python_filesystem_api(dotted_name(expression), aliases)
    if isinstance(expression, ast.IfExp):
        body = python_filesystem_callable_reference(expression.body, aliases)
        alternate = python_filesystem_callable_reference(expression.orelse, aliases)
        if body is None or alternate is None:
            return None
        family = "|".join(sorted(set(body.split("|") + alternate.split("|"))))
        return family if python_filesystem_write_spec(family) is not None else None
    return None


def python_filesystem_callable_calls(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    aliases: dict[str, str],
) -> dict[int, str]:
    """Resolve statement-ordered local aliases of compatible filesystem callables."""
    resolved_calls: dict[int, str] = {}

    def record_expression(expression: ast.AST | None, state: dict[str, str]) -> None:
        if expression is None:
            return

        def collect(candidate: ast.AST) -> None:
            if isinstance(
                candidate,
                (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                return
            if isinstance(candidate, ast.NamedExpr):
                collect(candidate.value)
                invalidate(candidate.target, state)
                if (
                    isinstance(candidate.target, ast.Name)
                    and (
                        canonical := python_filesystem_callable_reference(
                            candidate.value, aliases
                        )
                    )
                ):
                    state[candidate.target.id] = canonical
                return
            if isinstance(candidate, ast.Call):
                call_name = dotted_name(candidate.func)
                if call_name in state:
                    resolved_calls[id(candidate)] = state[call_name]
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        collect(expression)

    def invalidate(target: ast.AST, state: dict[str, str]) -> None:
        for name in python_assigned_names(target):
            state.pop(name, None)

    def merge(state: dict[str, str], branches: list[dict[str, str]]) -> None:
        state.clear()
        if not branches:
            return
        common_names = set(branches[0]).intersection(*(set(branch) for branch in branches[1:]))
        for name in common_names:
            family = "|".join(
                sorted(
                    {
                        api
                        for branch in branches
                        for api in branch[name].split("|")
                    }
                )
            )
            if python_filesystem_write_spec(family) is not None:
                state[name] = family

    def analyze_block(statements: list[ast.stmt], state: dict[str, str]) -> None:
        for statement in statements:
            analyze_statement(statement, state)

    def analyze_statement(statement: ast.stmt, state: dict[str, str]) -> None:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            state.pop(statement.name, None)
            return
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            for alias in statement.names:
                state.pop(alias.asname or alias.name.split(".", 1)[0], None)
            return
        if isinstance(statement, ast.Assign):
            record_expression(statement.value, state)
            for target in statement.targets:
                invalidate(target, state)
            if (
                len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and (
                    canonical := python_filesystem_callable_reference(
                        statement.value, aliases
                    )
                )
            ):
                state[statement.targets[0].id] = canonical
            return
        if isinstance(statement, ast.AnnAssign):
            record_expression(statement.value, state)
            invalidate(statement.target, state)
            if (
                isinstance(statement.target, ast.Name)
                and statement.value is not None
                and (
                    canonical := python_filesystem_callable_reference(
                        statement.value, aliases
                    )
                )
            ):
                state[statement.target.id] = canonical
            return
        if isinstance(statement, ast.AugAssign):
            record_expression(statement.value, state)
            invalidate(statement.target, state)
            return
        if isinstance(statement, ast.Delete):
            for target in statement.targets:
                invalidate(target, state)
            return
        if isinstance(statement, ast.If):
            record_expression(statement.test, state)
            body_state = dict(state)
            else_state = dict(state)
            analyze_block(statement.body, body_state)
            analyze_block(statement.orelse, else_state)
            merge(state, [body_state, else_state])
            return
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            for item in statement.items:
                record_expression(item.context_expr, state)
                if item.optional_vars:
                    invalidate(item.optional_vars, state)
            analyze_block(statement.body, state)
            return
        if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            loop_state = dict(state)
            if isinstance(statement, (ast.For, ast.AsyncFor)):
                record_expression(statement.iter, state)
                invalidate(statement.target, loop_state)
            else:
                record_expression(statement.test, state)
            analyze_block(statement.body, loop_state)
            else_state = dict(state)
            analyze_block(statement.orelse, else_state)
            merge(state, [dict(state), loop_state, else_state])
            return
        if isinstance(statement, ast.Try):
            branches = [dict(state)]
            body_state = dict(state)
            analyze_block(statement.body, body_state)
            branches.append(body_state)
            for handler in statement.handlers:
                handler_state = dict(state)
                if handler.name:
                    handler_state.pop(handler.name, None)
                analyze_block(handler.body, handler_state)
                branches.append(handler_state)
            else_state = dict(body_state)
            analyze_block(statement.orelse, else_state)
            branches.append(else_state)
            final_states = []
            for branch in branches:
                final_state = dict(branch)
                analyze_block(statement.finalbody, final_state)
                final_states.append(final_state)
            merge(state, final_states)
            return
        for child in ast.iter_child_nodes(statement):
            if isinstance(child, ast.expr):
                record_expression(child, state)

    analyze_block(node.body, {})
    return resolved_calls


PYTHON_PATH_DERIVING_ATTRIBUTES = {"parent"}
PYTHON_PATH_DERIVING_METHODS = {
    "absolute",
    "expanduser",
    "joinpath",
    "resolve",
    "with_name",
    "with_suffix",
}


def python_path_annotation(
    annotation: ast.AST | None, path_constructors: set[str]
) -> bool:
    if annotation is None:
        return False
    if dotted_name(annotation) in path_constructors:
        return True
    if (
        isinstance(annotation, ast.Subscript)
        and dotted_name(annotation.value) in {"Annotated", "typing.Annotated"}
    ):
        elements = (
            annotation.slice.elts
            if isinstance(annotation.slice, ast.Tuple)
            else (annotation.slice,)
        )
        return bool(elements) and python_path_annotation(elements[0], path_constructors)
    return False


def python_path_expression_proof(
    expression: ast.AST,
    path_constructors: set[str],
    bindings: dict[str, str],
) -> str | None:
    if isinstance(expression, ast.Name):
        return bindings.get(expression.id)
    if isinstance(expression, ast.Call):
        if dotted_name(expression.func) in path_constructors:
            return "explicit-constructor"
        if (
            isinstance(expression.func, ast.Attribute)
            and expression.func.attr in PYTHON_PATH_DERIVING_METHODS
        ):
            return python_path_expression_proof(
                expression.func.value, path_constructors, bindings
            )
    if (
        isinstance(expression, ast.Attribute)
        and expression.attr in PYTHON_PATH_DERIVING_ATTRIBUTES
    ):
        return python_path_expression_proof(expression.value, path_constructors, bindings)
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div):
        return python_path_expression_proof(expression.left, path_constructors, bindings)
    return None


def python_immutable_path_bindings(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path_constructors: set[str],
) -> dict[str, str]:
    """Return parameter or top-level local names proven to remain pathlib Paths."""
    binding_counts: Counter[str] = Counter()

    def count_bindings(candidate: ast.AST) -> None:
        if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            binding_counts[candidate.name] += 1
            return
        if isinstance(candidate, ast.Lambda):
            return
        if isinstance(candidate, (ast.Import, ast.ImportFrom)):
            binding_counts.update(
                alias.asname or alias.name.split(".", 1)[0]
                for alias in candidate.names
            )
            return
        if isinstance(candidate, ast.ExceptHandler) and candidate.name:
            binding_counts[candidate.name] += 1
        if isinstance(candidate, ast.Name) and isinstance(candidate.ctx, (ast.Store, ast.Del)):
            binding_counts[candidate.id] += 1
        for child in ast.iter_child_nodes(candidate):
            count_bindings(child)

    for statement in node.body:
        count_bindings(statement)

    bindings = {
        argument.arg: "parameter-annotation"
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        if binding_counts[argument.arg] == 0
        and python_path_annotation(argument.annotation, path_constructors)
    }
    for statement in node.body:
        target: ast.Name | None = None
        value: ast.AST | None = None
        annotation: ast.AST | None = None
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            target = statement.targets[0]
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            target = statement.target
            value = statement.value
            annotation = statement.annotation
        if target is None or binding_counts[target.id] != 1:
            continue
        proof = (
            "local-annotation"
            if python_path_annotation(annotation, path_constructors)
            else python_path_expression_proof(value, path_constructors, bindings)
            if value is not None
            else None
        )
        if proof is not None:
            bindings[target.id] = (
                "local-annotation" if proof == "local-annotation" else "immutable-local"
            )
    return bindings


def python_path_method_write(
    node: ast.Call,
    path_constructors: set[str],
    path_bindings: dict[str, str],
) -> tuple[str, PythonFilesystemWriteSpec, ast.AST, str] | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr not in {"rename", "replace"}:
        return None
    receiver_proof = python_path_expression_proof(
        node.func.value, path_constructors, path_bindings
    )
    if receiver_proof is None:
        return None
    destination = python_call_argument(node, 0, ("target",))
    if destination is None:
        return None
    canonical_api = f"pathlib.Path.{node.func.attr}"
    return (
        canonical_api,
        PythonFilesystemWriteSpec(0, ("target",), "move", "destination"),
        destination,
        receiver_proof,
    )


def python_call_argument(
    node: ast.Call, index: int, keywords: tuple[str, ...]
) -> ast.AST | None:
    if len(node.args) > index:
        return node.args[index]
    return next(
        (
            keyword.value
            for keyword in node.keywords
            if keyword.arg is not None and keyword.arg in keywords
        ),
        None,
    )


def python_filesystem_function_write(
    node: ast.Call,
    aliases: dict[str, str],
    local_callable: str | None = None,
) -> tuple[str, PythonFilesystemWriteSpec, ast.AST] | None:
    canonical = local_callable or canonical_python_filesystem_api(
        dotted_name(node.func), aliases
    )
    if canonical is None:
        return None
    spec = python_filesystem_write_spec(canonical)
    if spec is None:
        return None
    path_expression = python_call_argument(node, spec.path_index, spec.path_keywords)
    if path_expression is None:
        return None
    return canonical, spec, path_expression


def python_resolved_path_expression(expression: ast.AST) -> ast.AST | None:
    """Return the receiver of an explicit zero-argument Path.resolve() call."""
    if not isinstance(expression, ast.Call) or expression.args or expression.keywords:
        return None
    if not isinstance(expression.func, ast.Attribute) or expression.func.attr != "resolve":
        return None
    return expression.func.value


def python_path_root_scope(expression: ast.AST, path_constructors: set[str]) -> str | None:
    """Classify an explicitly resolved Path root without trusting relative literals."""
    receiver = python_resolved_path_expression(expression)
    if receiver is None:
        return None
    if (
        isinstance(receiver, ast.Call)
        and not receiver.args
        and not receiver.keywords
        and isinstance(receiver.func, ast.Attribute)
        and receiver.func.attr == "expanduser"
    ):
        receiver = receiver.func.value
    if not isinstance(receiver, ast.Call) or dotted_name(receiver.func) not in path_constructors:
        return None
    if not receiver.args and not receiver.keywords:
        return "unresolved"
    if len(receiver.args) != 1 or receiver.keywords:
        return None
    value = receiver.args[0]
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        return "unresolved"
    root = value.value
    absolute = root.startswith("/") or bool(re.match(r"^[A-Za-z]:[\\/]", root))
    filesystem_root = root in {"/", "\\"} or bool(re.fullmatch(r"[A-Za-z]:[\\/]*", root))
    return "constrained" if absolute and not filesystem_root else "unresolved"


def python_unresolved_candidate_root(
    expression: ast.AST,
    state: PythonPathState,
    path_constructors: set[str],
) -> str | None:
    """Resolve an unresolved `root / dynamic_input` path join to its root."""
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div):
        left_names = python_expression_names(expression.left)
        roots = left_names & state.roots.keys()
        if len(roots) != 1:
            return None
        root = next(iter(roots))
        if not (python_expression_names(expression.right) & state.dynamic_names):
            return None
        return root
    if isinstance(expression, ast.Call) and dotted_name(expression.func) in path_constructors:
        if len(expression.args) < 2:
            return None
        root_names = python_expression_names(expression.args[0]) & state.roots.keys()
        if len(root_names) != 1:
            return None
        if not any(
            python_expression_names(argument) & state.dynamic_names
            for argument in expression.args[1:]
        ):
            return None
        return next(iter(root_names))
    return None


def python_candidate_root(
    expression: ast.AST,
    state: PythonPathState,
    path_constructors: set[str],
) -> str | None:
    """Resolve `(root / dynamic_input).resolve()` to its proven root binding."""
    receiver = python_resolved_path_expression(expression)
    if receiver is None:
        return None
    if isinstance(receiver, ast.Name):
        return state.unresolved_candidates.get(receiver.id)
    return python_unresolved_candidate_root(receiver, state, path_constructors)


def python_boundary_predicate(
    expression: ast.AST, state: PythonPathState
) -> tuple[str, str, bool, bool] | None:
    """Return candidate, root, truth polarity, and strict-descendant proof."""

    def boundary_call(term: ast.AST) -> ast.Call | None:
        if (
            isinstance(term, ast.Call)
            and isinstance(term.func, ast.Attribute)
            and term.func.attr == "is_relative_to"
            and len(term.args) == 1
            and not term.keywords
        ):
            return term
        return None

    positive = True
    strict_terms: list[ast.AST] = []
    call: ast.Call | None = None
    if direct := boundary_call(expression):
        call = direct
    elif isinstance(expression, ast.UnaryOp) and isinstance(expression.op, ast.Not):
        operand = expression.operand
        if direct := boundary_call(operand):
            call = direct
            positive = False
        elif isinstance(operand, ast.BoolOp) and isinstance(operand.op, ast.And):
            calls = [item for term in operand.values if (item := boundary_call(term))]
            if len(calls) == 1:
                call = calls[0]
                positive = False
                strict_terms = list(operand.values)
    elif isinstance(expression, ast.BoolOp) and isinstance(expression.op, ast.And):
        calls = [item for term in expression.values if (item := boundary_call(term))]
        if len(calls) == 1:
            call = calls[0]
            strict_terms = list(expression.values)
    elif isinstance(expression, ast.BoolOp) and isinstance(expression.op, ast.Or):
        negated_calls = [
            item
            for term in expression.values
            if isinstance(term, ast.UnaryOp)
            and isinstance(term.op, ast.Not)
            and (item := boundary_call(term.operand))
        ]
        if len(negated_calls) == 1:
            call = negated_calls[0]
            positive = False
            strict_terms = list(expression.values)
    if call is None:
        return None
    if not isinstance(call.func.value, ast.Name) or not isinstance(call.args[0], ast.Name):
        return None
    candidate_name = call.func.value.id
    root_name = call.args[0].id
    if state.candidates.get(candidate_name) != root_name or root_name not in state.roots:
        return None
    strict_descendant = False
    for term in strict_terms:
        if not isinstance(term, ast.Compare) or len(term.ops) != 1 or len(term.comparators) != 1:
            continue
        names = {dotted_name(term.left), dotted_name(term.comparators[0])}
        if names != {candidate_name, root_name}:
            continue
        strict_descendant = (
            positive and isinstance(term.ops[0], (ast.NotEq, ast.IsNot))
        ) or (not positive and isinstance(term.ops[0], (ast.Eq, ast.Is)))
    return candidate_name, root_name, positive, strict_descendant


def python_path_prefix_predicate(
    expression: ast.AST, state: PythonPathState
) -> tuple[str, str, bool] | None:
    """Recognize a path-derived string prefix test without treating it as containment."""

    def prefix_call(term: ast.AST) -> ast.Call | None:
        if (
            isinstance(term, ast.Call)
            and isinstance(term.func, ast.Attribute)
            and term.func.attr == "startswith"
            and len(term.args) == 1
            and not term.keywords
        ):
            return term
        return None

    positive = True
    call = prefix_call(expression)
    if call is None and isinstance(expression, ast.UnaryOp) and isinstance(
        expression.op, ast.Not
    ):
        call = prefix_call(expression.operand)
        positive = False
    if call is None:
        return None

    def stringified_name(term: ast.AST) -> str | None:
        if (
            isinstance(term, ast.Call)
            and dotted_name(term.func) == "str"
            and len(term.args) == 1
            and not term.keywords
            and isinstance(term.args[0], ast.Name)
        ):
            return term.args[0].id
        return None

    candidate = stringified_name(call.func.value)
    root_name = stringified_name(call.args[0])
    if (
        candidate is None
        or root_name is None
        or state.candidates.get(candidate) != root_name
        or root_name not in state.roots
    ):
        return None
    return candidate, root_name, positive


def python_block_always_terminates(statements: list[ast.stmt]) -> bool:
    if not statements:
        return False
    final = statements[-1]
    if isinstance(final, (ast.Raise, ast.Return)):
        return True
    return (
        isinstance(final, ast.If)
        and python_block_always_terminates(final.body)
        and python_block_always_terminates(final.orelse)
    )


def python_handler_catches_value_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else (handler.type,)
    return any(
        dotted_name(exception_type) in {"ValueError", "Exception", "BaseException"}
        for exception_type in types
    )


def python_relative_to_try_guard(
    statement: ast.Try, state: PythonPathState
) -> tuple[ast.Call, str, str] | None:
    """Return a fail-closed relative_to call whose success is the only continuation."""
    if len(statement.body) != 1:
        return None
    check = statement.body[0]
    expression: ast.AST | None = None
    if isinstance(check, (ast.Expr, ast.Assign, ast.AnnAssign)):
        expression = check.value
    if not (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr == "relative_to"
        and len(expression.args) == 1
        and not expression.keywords
        and isinstance(expression.func.value, ast.Name)
        and isinstance(expression.args[0], ast.Name)
    ):
        return None
    candidate = expression.func.value.id
    root_name = expression.args[0].id
    if state.candidates.get(candidate) != root_name or root_name not in state.roots:
        return None
    if isinstance(check, ast.Assign):
        assigned_names = {
            name for target in check.targets for name in python_assigned_names(target)
        }
    elif isinstance(check, ast.AnnAssign):
        assigned_names = python_assigned_names(check.target)
    else:
        assigned_names = set()
    if assigned_names & {candidate, root_name}:
        return None

    matching_handler = next(
        (
            handler
            for handler in statement.handlers
            if python_handler_catches_value_error(handler)
        ),
        None,
    )
    if matching_handler is None or not python_block_always_terminates(
        matching_handler.body
    ):
        return None
    return expression, candidate, root_name


def python_class_path_helper_summaries(
    node: ast.ClassDef,
    path: str,
    lines: list[str],
    path_constructors: set[str],
) -> dict[str, PythonPathHelperSummary]:
    """Summarize same-class helpers that return an exclusively bounded Path."""
    summaries: dict[str, PythonPathHelperSummary] = {}
    member_definitions: Counter[str] = Counter()
    instance_rebindings: set[str] = set()
    for statement in node.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            member_definitions[statement.name] += 1
        elif isinstance(statement, ast.Assign):
            for target in statement.targets:
                member_definitions.update(python_assigned_names(target))
        elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
            member_definitions.update(python_assigned_names(statement.target))
    for method in node.body:
        if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for candidate in ast.walk(method):
            targets: tuple[ast.AST, ...] = ()
            if isinstance(candidate, ast.Assign):
                targets = tuple(candidate.targets)
            elif isinstance(candidate, (ast.AnnAssign, ast.AugAssign)):
                targets = (candidate.target,)
            elif isinstance(candidate, ast.Delete):
                targets = tuple(candidate.targets)
            instance_rebindings.update(
                target.attr
                for target in targets
                if isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id in {"self", "cls"}
            )
    for method in node.body:
        if not isinstance(method, ast.FunctionDef):
            continue
        if (
            member_definitions[method.name] != 1
            or method.name in instance_rebindings
            or method.decorator_list
            or any(isinstance(child, (ast.Yield, ast.YieldFrom)) for child in ast.walk(method))
        ):
            continue
        positional = [*method.args.posonlyargs, *method.args.args]
        if not positional or positional[0].arg not in {"self", "cls"}:
            continue
        call_parameters = positional[1:]
        final = method.body[-1] if method.body else None
        if not isinstance(final, ast.Return) or not isinstance(final.value, ast.Name):
            continue
        candidate = final.value.id
        if any(
            isinstance(return_node, ast.Return) and return_node is not final
            for return_node in ast.walk(method)
        ):
            continue
        guards = [
            statement
            for statement in method.body
            if isinstance(statement, ast.Try)
            and len(statement.body) == 1
            and isinstance(statement.body[0], ast.Expr)
            and isinstance(statement.body[0].value, ast.Call)
            and isinstance(statement.body[0].value.func, ast.Attribute)
            and statement.body[0].value.func.attr == "relative_to"
            and len(statement.body[0].value.args) == 1
            and not statement.body[0].value.keywords
            and isinstance(statement.body[0].value.func.value, ast.Name)
            and statement.body[0].value.func.value.id == candidate
        ]
        if len(guards) != 1:
            continue
        guard = guards[0]
        check = guard.body[0].value
        assert isinstance(check, ast.Call)
        if guard.orelse or guard.finalbody:
            continue
        matching_handler = next(
            (
                handler
                for handler in guard.handlers
                if python_handler_catches_value_error(handler)
            ),
            None,
        )
        if matching_handler is None or not python_block_always_terminates(
            matching_handler.body
        ):
            continue
        root_expression = check.args[0]
        root_name = dotted_name(root_expression)
        if not root_name or guard.lineno >= final.lineno:
            continue
        if any(
            not isinstance(statement, (ast.Assign, ast.AnnAssign))
            and not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
            for statement in method.body
            if statement.lineno < guard.lineno
        ):
            continue

        assignments: dict[str, list[tuple[int, ast.AST]]] = defaultdict(list)
        for statement in method.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        assignments[target.id].append((statement.lineno, statement.value))
            elif (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
                and statement.value is not None
            ):
                assignments[statement.target.id].append(
                    (statement.lineno, statement.value)
                )

        local_path_constructors = {
            constructor
            for constructor in path_constructors
            if constructor.split(".", 1)[0]
            not in python_function_local_bindings(method)
        }
        parameter_names = {argument.arg for argument in call_parameters}

        def path_dependencies(
            expression: ast.AST,
            before_line: int,
            seen: set[tuple[str, int]],
            root: str = root_name,
            parameters_in_scope: set[str] = parameter_names,
            local_assignments: dict[str, list[tuple[int, ast.AST]]] = assignments,
            constructors: set[str] = local_path_constructors,
        ) -> set[str] | None:
            if dotted_name(expression) == root:
                return {"__root__"}
            if isinstance(expression, ast.Name):
                if expression.id in parameters_in_scope:
                    return {f"parameter:{expression.id}"}
                prior = [
                    (line, value)
                    for line, value in local_assignments.get(expression.id, [])
                    if line < before_line
                ]
                if not prior:
                    return set()
                line, value = prior[-1]
                key = (expression.id, line)
                if key in seen:
                    return None
                return path_dependencies(value, line, seen | {key})
            if (
                isinstance(expression, ast.Call)
                and dotted_name(expression.func) in constructors
            ):
                if len(expression.args) != 1 or expression.keywords:
                    return None
                values = path_dependencies(expression.args[0], before_line, seen)
                return None if values is None else values | {"__path__"}
            if (
                isinstance(expression, ast.Call)
                and not expression.args
                and not expression.keywords
                and isinstance(expression.func, ast.Attribute)
                and expression.func.attr == "resolve"
            ):
                return path_dependencies(expression.func.value, before_line, seen)
            if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div):
                left = path_dependencies(expression.left, before_line, seen)
                right = path_dependencies(expression.right, before_line, seen)
                if left is None or right is None or "__path__" not in left | right:
                    return None
                return left | right
            if isinstance(expression, ast.IfExp):
                body = path_dependencies(expression.body, before_line, seen)
                orelse = path_dependencies(expression.orelse, before_line, seen)
                if (
                    body is None
                    or orelse is None
                    or "__path__" not in body
                    or "__path__" not in orelse
                ):
                    return None
                return body | orelse
            return None

        prior_candidate_assignments = [
            (line, value)
            for line, value in assignments.get(candidate, [])
            if line < guard.lineno
        ]
        if not prior_candidate_assignments:
            continue
        _, resolved_value = prior_candidate_assignments[-1]
        if python_resolved_path_expression(resolved_value) is None:
            continue
        lineage = path_dependencies(resolved_value, guard.lineno, set())
        if lineage is None:
            continue
        parameters = sorted(
            dependency.removeprefix("parameter:")
            for dependency in lineage
            if dependency.startswith("parameter:")
        )
        if "__root__" not in lineage or "__path__" not in lineage or len(parameters) != 1:
            continue
        path_parameter = parameters[0]
        if any(
            isinstance(descendant, ast.Name)
            and descendant.id == candidate
            and isinstance(descendant.ctx, (ast.Store, ast.Del))
            for statement in method.body
            if guard.lineno < statement.lineno < final.lineno
            for descendant in ast.walk(statement)
        ):
            continue
        summaries[method.name] = PythonPathHelperSummary(
            next(
                index
                for index, argument in enumerate(call_parameters)
                if argument.arg == path_parameter
            ),
            path_parameter,
            Evidence(path, check.lineno, excerpt(lines, check.lineno)),
            "unresolved",
            root_name,
            "Path.relative_to",
        )
    return summaries


def python_filesystem_path_name(
    node: ast.Call,
    aliases: dict[str, str],
    local_callable: str | None = None,
    path_constructors: set[str] | None = None,
    path_bindings: dict[str, str] | None = None,
) -> tuple[str, int] | None:
    call_name = dotted_name(node.func)
    short_name = call_name.rsplit(".", 1)[-1]
    expression: ast.AST | None = None
    if function_write := python_filesystem_function_write(
        node, aliases, local_callable
    ):
        expression = function_write[2]
    elif path_write := python_path_method_write(
        node, path_constructors or set(), path_bindings or {}
    ):
        expression = path_write[2]
    elif short_name == "open" and node.args:
        expression = node.args[0]
    elif short_name in {"write_text", "write_bytes", "unlink", "rmdir", "mkdir"} and isinstance(
        node.func, ast.Attribute
    ):
        expression = node.func.value
    if (
        isinstance(expression, ast.Call)
        and len(expression.args) == 1
        and not expression.keywords
        and dotted_name(expression.func) in {"str", "os.fspath"}
    ):
        expression = expression.args[0]
    parent_depth = 0
    while isinstance(expression, ast.Attribute) and expression.attr == "parent":
        parent_depth += 1
        expression = expression.value
    return (expression.id, parent_depth) if isinstance(expression, ast.Name) else None


def python_path_boundary_calls(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path: str,
    lines: list[str],
    path_constructors: set[str],
    filesystem_api_aliases: dict[str, str],
    filesystem_callable_calls: dict[int, str],
    path_bindings: dict[str, str],
    path_helper_summaries: dict[str, PythonPathHelperSummary],
) -> dict[int, PythonPathBoundaryProof]:
    """Prove same-function, statement-ordered Python filesystem boundaries."""
    if not path_constructors:
        return {}
    parameters = {
        argument.arg
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        if argument.arg not in {"self", "cls"}
    }
    if node.args.vararg:
        parameters.add(node.args.vararg.arg)
    if node.args.kwarg:
        parameters.add(node.args.kwarg.arg)
    local_bindings = python_function_local_bindings(node)
    positional_arguments = [*node.args.posonlyargs, *node.args.args]
    helper_receivers: set[str] = set()
    if positional_arguments and positional_arguments[0].arg in {"self", "cls"}:
        helper_receivers.add(positional_arguments[0].arg)
    if any(
        isinstance(candidate, ast.Name)
        and candidate.id in helper_receivers
        and isinstance(candidate.ctx, (ast.Store, ast.Del))
        for statement in node.body
        for candidate in ast.walk(statement)
    ):
        helper_receivers.clear()
    path_constructors = {
        constructor
        for constructor in path_constructors
        if constructor.split(".", 1)[0] not in local_bindings
    }
    if not path_constructors:
        return {}
    filesystem_api_aliases = {
        alias: canonical
        for alias, canonical in filesystem_api_aliases.items()
        if alias.split(".", 1)[0] not in local_bindings
    }
    initial = PythonPathState(parameters, {}, {}, {}, {})
    proofs: dict[int, PythonPathBoundaryProof] = {}

    def install_guard(
        state: PythonPathState, candidate: str, proof: PythonPathBoundaryProof
    ) -> None:
        current = state.guards.get(candidate)
        if current is not None and current.strength == "strong" and proof.strength != "strong":
            return
        state.guards[candidate] = proof

    def record_expression(expression: ast.AST | None, state: PythonPathState) -> None:
        if expression is None:
            return

        def collect(candidate: ast.AST) -> None:
            if isinstance(
                candidate, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                return
            if isinstance(candidate, ast.Call):
                path_target = python_filesystem_path_name(
                    candidate,
                    filesystem_api_aliases,
                    filesystem_callable_calls.get(id(candidate)),
                    path_constructors,
                    path_bindings,
                )
                if (
                    path_target
                    and (proof := state.guards.get(path_target[0]))
                    and (
                        proof.strength == "weak-prefix"
                        or path_target[1] == 0
                        or (path_target[1] == 1 and proof.strict_descendant)
                    )
                ):
                    proofs[id(candidate)] = proof
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        collect(expression)

    def invalidate(names: set[str], state: PythonPathState) -> None:
        for name in names:
            state.dynamic_names.discard(name)
            state.roots.pop(name, None)
            state.candidates.pop(name, None)
            state.guards.pop(name, None)
            state.unresolved_candidates.pop(name, None)
        invalid_roots = names
        invalid_candidates = {
            candidate
            for candidate, root_name in state.candidates.items()
            if root_name in invalid_roots
        }
        for candidate in invalid_candidates:
            state.candidates.pop(candidate, None)
            state.guards.pop(candidate, None)
        invalid_unresolved_candidates = {
            candidate
            for candidate, root_name in state.unresolved_candidates.items()
            if root_name in invalid_roots
        }
        for candidate in invalid_unresolved_candidates:
            state.unresolved_candidates.pop(candidate, None)

    def apply_assignment(target: ast.AST, value: ast.AST, state: PythonPathState) -> None:
        names = python_assigned_names(target)
        value_names = python_expression_names(value)
        value_is_dynamic = bool(value_names & state.dynamic_names)
        invalidate(names, state)
        if value_is_dynamic:
            state.dynamic_names.update(names)
        if len(names) != 1:
            return
        name = next(iter(names))
        if (scope := python_path_root_scope(value, path_constructors)) is not None:
            state.roots[name] = scope
        elif root_name := python_candidate_root(value, state, path_constructors):
            state.candidates[name] = root_name
        elif root_name := python_unresolved_candidate_root(
            value, state, path_constructors
        ):
            state.unresolved_candidates[name] = root_name
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Name)
            and value.func.value.id in helper_receivers
            and (summary := path_helper_summaries.get(value.func.attr))
            and python_call_argument(
                value,
                summary.parameter_index,
                (summary.parameter_name,),
            )
            is not None
        ):
            install_guard(
                state,
                name,
                PythonPathBoundaryProof(
                    summary.evidence,
                    summary.boundary_scope,
                    name,
                    summary.root_name,
                    False,
                    summary.helper,
                    "same-class-return",
                ),
            )

    def analyze_block(statements: list[ast.stmt], state: PythonPathState) -> PythonPathState:
        for statement in statements:
            analyze_statement(statement, state)
        return state

    def merge_states(state: PythonPathState, branches: list[PythonPathState]) -> None:
        """Retain facts that hold after every feasible compound-statement branch."""
        if not branches:
            return
        state.dynamic_names = set().union(
            *(branch.dynamic_names for branch in branches)
        )
        state.roots = {
            name: scope
            for name, scope in branches[0].roots.items()
            if all(branch.roots.get(name) == scope for branch in branches[1:])
        }
        state.candidates = {
            name: root_name
            for name, root_name in branches[0].candidates.items()
            if root_name in state.roots
            and all(
                branch.candidates.get(name) == root_name for branch in branches[1:]
            )
        }
        state.unresolved_candidates = {
            name: root_name
            for name, root_name in branches[0].unresolved_candidates.items()
            if root_name in state.roots
            and all(
                branch.unresolved_candidates.get(name) == root_name
                for branch in branches[1:]
            )
        }
        state.guards = {
            name: proof
            for name, proof in branches[0].guards.items()
            if name in state.candidates
            and all(branch.guards.get(name) == proof for branch in branches[1:])
        }

    def analyze_statement(statement: ast.stmt, state: PythonPathState) -> None:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return
        if isinstance(statement, ast.Assign):
            record_expression(statement.value, state)
            for target in statement.targets:
                apply_assignment(target, statement.value, state)
            return
        if isinstance(statement, ast.AnnAssign):
            record_expression(statement.value, state)
            if statement.value is not None:
                apply_assignment(statement.target, statement.value, state)
            else:
                invalidate(python_assigned_names(statement.target), state)
            return
        if isinstance(statement, (ast.AugAssign, ast.NamedExpr)):
            record_expression(statement.value, state)
            invalidate(python_assigned_names(statement.target), state)
            return
        if isinstance(statement, ast.Delete):
            for target in statement.targets:
                invalidate(python_assigned_names(target), state)
            return
        if isinstance(statement, ast.If):
            record_expression(statement.test, state)
            strong_predicate = python_boundary_predicate(statement.test, state)
            weak_predicate = (
                None
                if strong_predicate is not None
                else python_path_prefix_predicate(statement.test, state)
            )
            predicate = strong_predicate or weak_predicate
            body_state = state.clone()
            else_state = state.clone()
            if predicate is not None:
                candidate, root_name, positive = predicate[:3]
                strict_descendant = (
                    strong_predicate[3] if strong_predicate is not None else False
                )
                proof = PythonPathBoundaryProof(
                    Evidence(path, statement.lineno, excerpt(lines, statement.lineno)),
                    state.roots[root_name],
                    candidate,
                    root_name,
                    strict_descendant,
                    "Path.is_relative_to" if strong_predicate is not None else "str.startswith",
                    strength="strong" if strong_predicate is not None else "weak-prefix",
                )
                install_guard(body_state if positive else else_state, candidate, proof)
            analyze_block(statement.body, body_state)
            analyze_block(statement.orelse, else_state)
            propagated_continuation = False
            if predicate is not None:
                candidate, root_name, positive = predicate[:3]
                strict_descendant = (
                    strong_predicate[3] if strong_predicate is not None else False
                )
                rejecting = statement.orelse if positive else statement.body
                if python_block_always_terminates(rejecting):
                    continuing = body_state if positive else else_state
                    if (
                        continuing.candidates.get(candidate) == root_name
                        and root_name in continuing.roots
                    ):
                        state.dynamic_names = continuing.dynamic_names
                        state.roots = continuing.roots
                        state.candidates = continuing.candidates
                        state.guards = continuing.guards
                        state.unresolved_candidates = continuing.unresolved_candidates
                        install_guard(
                            state,
                            candidate,
                            PythonPathBoundaryProof(
                                Evidence(
                                    path,
                                    statement.lineno,
                                    excerpt(lines, statement.lineno),
                                ),
                                state.roots[root_name],
                                candidate,
                                root_name,
                                strict_descendant,
                                (
                                    "Path.is_relative_to"
                                    if strong_predicate is not None
                                    else "str.startswith"
                                ),
                                strength=(
                                    "strong"
                                    if strong_predicate is not None
                                    else "weak-prefix"
                                ),
                            ),
                        )
                        propagated_continuation = True
            if not propagated_continuation:
                merge_states(state, [body_state, else_state])
            return
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            for item in statement.items:
                record_expression(item.context_expr, state)
                if item.optional_vars:
                    invalidate(python_assigned_names(item.optional_vars), state)
            analyze_block(statement.body, state)
            return
        if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            if isinstance(statement, (ast.For, ast.AsyncFor)):
                record_expression(statement.iter, state)
                loop_state = state.clone()
                invalidate(python_assigned_names(statement.target), loop_state)
            else:
                record_expression(statement.test, state)
                loop_state = state.clone()
            analyze_block(statement.body, loop_state)
            else_state = state.clone()
            analyze_block(statement.orelse, else_state)
            merge_states(state, [state.clone(), loop_state, else_state])
            return
        if isinstance(statement, ast.Try):
            if guard := python_relative_to_try_guard(statement, state):
                check, candidate, root_name = guard
                record_expression(check, state)
                continuing = state.clone()
                continuing.guards[candidate] = PythonPathBoundaryProof(
                    Evidence(path, check.lineno, excerpt(lines, check.lineno)),
                    continuing.roots[root_name],
                    candidate,
                    root_name,
                    False,
                    "Path.relative_to",
                )
                analyze_block(statement.orelse, continuing)
                analyze_block(statement.finalbody, continuing)
                state.dynamic_names = continuing.dynamic_names
                state.roots = continuing.roots
                state.candidates = continuing.candidates
                state.guards = continuing.guards
                state.unresolved_candidates = continuing.unresolved_candidates
                return
            body_state = state.clone()
            analyze_block(statement.body, body_state)
            else_state = body_state.clone()
            analyze_block(statement.orelse, else_state)
            branches = [else_state]
            for handler in statement.handlers:
                handler_state = state.clone()
                if handler.name:
                    invalidate({handler.name}, handler_state)
                analyze_block(handler.body, handler_state)
                if not python_block_always_terminates(handler.body):
                    branches.append(handler_state)
            final_states = []
            for branch in branches:
                final_state = branch.clone()
                analyze_block(statement.finalbody, final_state)
                final_states.append(final_state)
            merge_states(state, final_states)
            return
        for child in ast.iter_child_nodes(statement):
            if isinstance(child, ast.expr):
                record_expression(child, state)

    analyze_block(node.body, initial)
    return proofs


class PythonVisitor(ast.NodeVisitor):
    def __init__(
        self,
        ir: RepositoryIR,
        root: Path,
        path: str,
        lines: list[str],
        *,
        imported_modules: set[str],
        module_paths: dict[str, str],
        local_symbol_ids: dict[tuple[str, str], str],
        ambiguous_local_symbols: set[tuple[str, str]],
        scoped_symbol_ids: dict[tuple[tuple[str, ...], str, str], tuple[int, str]],
        node_scopes: dict[int, tuple[str, ...]],
        call_symbol_ids: dict[int, str],
        definition_symbol_ids: dict[int, str],
        registry_class_exports: dict[tuple[str, str], RegistryClassTarget],
        registered_tool_functions: dict[tuple[str, str], PythonToolRegistration],
        module_rebound_names: set[str],
        path_constructors: set[str],
        filesystem_api_aliases: dict[str, str],
    ) -> None:
        self.ir = ir
        self.root = root
        self.path = path
        self.lines = lines
        self.current_tool: str | None = None
        self.current_tool_id: str | None = None
        self.dynamic_http_origin_names: set[str] = set()
        self.class_stack: list[str] = []
        self.active_audit_controls: list[Evidence] = []
        self.http_client_names: set[str] = set()
        self.allowlisted_names: set[str] = set()
        self.allowlist_evidence: dict[str, Evidence] = {}
        self.allowlist_control_names: dict[str, str] = {}
        self.approval_environment_flags: dict[str, set[str]] = {}
        self.module_approval_environment_flags: dict[str, set[str]] = {}
        self.class_approval_environment_flags: list[dict[str, set[str]]] = []
        self.class_fixed_tool_bindings: list[dict[str, Evidence]] = []
        self.class_fixed_tool_accessors: list[dict[str, Evidence]] = []
        self.class_registry_method_summaries: list[dict[str, RegistryMethodSummary]] = []
        self.class_registry_manager_bindings: list[dict[str, RegistryClassTarget]] = []
        self.class_path_helper_summaries: list[dict[str, PythonPathHelperSummary]] = []
        self.function_fixed_binding_sources: list[dict[str, Evidence]] = []
        self.function_escaping_children: list[set[str]] = []
        self.function_path_boundary_calls: list[dict[int, PythonPathBoundaryProof]] = []
        self.function_filesystem_api_aliases: list[dict[str, str]] = []
        self.function_filesystem_callable_calls: list[dict[int, str]] = []
        self.function_path_bindings: list[dict[str, str]] = []
        self.function_path_constructors: list[set[str]] = []
        self.function_stack: list[str] = []
        self.function_depth = 0
        self.imported_symbol_paths: dict[str, str] = {}
        self.imported_symbol_names: dict[str, str] = {}
        self.module_paths = module_paths
        self.local_symbol_ids = local_symbol_ids
        self.ambiguous_local_symbols = ambiguous_local_symbols
        self.scoped_symbol_ids = scoped_symbol_ids
        self.node_scopes = node_scopes
        self.call_symbol_ids = call_symbol_ids
        self.definition_symbol_ids = definition_symbol_ids
        self.registry_class_exports = registry_class_exports
        self.registered_tool_functions = registered_tool_functions
        self.module_rebound_names = module_rebound_names
        self.path_constructors = path_constructors
        self.filesystem_api_aliases = filesystem_api_aliases
        self.has_mcp_import = any(
            module == "mcp" or module.startswith("mcp.") or "modelcontextprotocol" in module
            for module in imported_modules
        )
        self.has_browser_import = any(
            module.startswith(("playwright", "selenium", "puppeteer"))
            for module in imported_modules
        )
        self.has_docker_import = any(
            module == "docker" or module.startswith("docker.") for module in imported_modules
        )
        self.has_openai_agents_import = any(
            module == "agents" or module.startswith("agents.") for module in imported_modules
        )
        self.has_http_import = any(
            module == prefix or module.startswith(f"{prefix}.")
            for module in imported_modules
            for prefix in ("requests", "httpx", "aiohttp")
        )

    def add_capability(self, name: str, node: ast.AST, attributes: dict | None = None) -> None:
        values = {"scope": source_scope(self.path), **(attributes or {})}
        self.ir.add_component(Component("capability", name, self.ev(node), values))
        if self.current_tool:
            self.ir.add_relationship(
                Relationship(
                    "tool",
                    self.current_tool,
                    "uses",
                    "capability",
                    name,
                    self.ev(node),
                    source_id=self.current_tool_id,
                )
            )
            for control_evidence in self.active_audit_controls:
                self.ir.add_relationship(
                    Relationship(
                        "capability",
                        name,
                        "governed-by",
                        "control",
                        "action-trace",
                        self.ev(node),
                        {
                            "control_path": control_evidence.path,
                            "control_line": control_evidence.line,
                            "durability": "unresolved",
                        },
                    )
                )

    def add_python_path_boundary_control(
        self, capability_node: ast.AST, proof: PythonPathBoundaryProof
    ) -> None:
        policy_effect = (
            "restricts-filesystem-path"
            if proof.boundary_scope == "constrained"
            else "validates-filesystem-path"
        )
        attributes = {
            "scope": source_scope(self.path),
            "policy_effect": policy_effect,
            "frontend": "python",
            "helper": proof.helper,
            "predicate_path": proof.evidence.path,
            "boundary_scope": proof.boundary_scope,
            "candidate": proof.candidate_name,
            "root": proof.root_name,
            "strict_descendant": proof.strict_descendant,
        }
        if proof.summary is not None:
            attributes["summary"] = proof.summary
        self.ir.add_component(Component("control", "path-boundary", proof.evidence, attributes))
        self.ir.add_relationship(
            Relationship(
                "capability",
                "filesystem",
                "governed-by",
                "control",
                "path-boundary",
                self.ev(capability_node),
                {
                    "control_path": proof.evidence.path,
                    "control_line": proof.evidence.line,
                    "policy_effect": policy_effect,
                    "frontend": "python",
                    "helper": proof.helper,
                    "predicate_path": proof.evidence.path,
                    "boundary_scope": proof.boundary_scope,
                    "candidate": proof.candidate_name,
                    "root": proof.root_name,
                    "strict_descendant": proof.strict_descendant,
                    **({"summary": proof.summary} if proof.summary is not None else {}),
                },
            )
        )

    def add_python_path_prefix_control(
        self, capability_node: ast.AST, proof: PythonPathBoundaryProof
    ) -> None:
        attributes = {
            "scope": source_scope(self.path),
            "policy_effect": "weak-string-prefix-validation",
            "frontend": "python",
            "helper": proof.helper,
            "predicate_path": proof.evidence.path,
            "root_scope": proof.boundary_scope,
            "candidate": proof.candidate_name,
            "root": proof.root_name,
            "strength": proof.strength,
        }
        self.ir.add_component(
            Component("control", "path-prefix-check", proof.evidence, attributes)
        )
        self.ir.add_relationship(
            Relationship(
                "capability",
                "filesystem",
                "governed-by",
                "control",
                "path-prefix-check",
                self.ev(capability_node),
                {
                    "control_path": proof.evidence.path,
                    "control_line": proof.evidence.line,
                    **attributes,
                },
            )
        )

    def ev(self, node: ast.AST) -> Evidence:
        line = getattr(node, "lineno", 1)
        return Evidence(self.path, line, excerpt(self.lines, line))

    def resolve_local_symbol(
        self, kind: str, name: str, node: ast.AST
    ) -> tuple[str | None, str | None]:
        scope = self.node_scopes.get(id(node), ())
        if scoped := self.scoped_symbol_ids.get((scope, kind, name)):
            definition_line, symbol_id = scoped
            if definition_line < getattr(node, "lineno", 1):
                return symbol_id, "lexical-single-definition"
        if scope and (module_symbol := self.scoped_symbol_ids.get(((), kind, name))):
            definition_line, symbol_id = module_symbol
            if definition_line < getattr(node, "lineno", 1):
                return symbol_id, "module-single-definition"
        if self.node_scopes:
            return None, None
        if (kind, name) not in self.ambiguous_local_symbols:
            return self.local_symbol_ids.get((kind, name)), None
        return None, None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            component_from_import(self.ir, alias.name, self.ev(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            target = resolve_python_import_path(
                self.root,
                self.path,
                node,
                alias.name,
                self.module_paths,
            )
            if target:
                local_name = alias.asname or alias.name
                self.imported_symbol_paths[local_name] = target
                self.imported_symbol_names[local_name] = alias.name
        if node.module == "openai":
            imported = {alias.name for alias in node.names}
            if any(name.startswith("Azure") for name in imported):
                self.ir.add_component(
                    Component("provider", "Azure OpenAI", self.ev(node), {"module": "openai"})
                )
            if imported & {"OpenAI", "AsyncOpenAI"}:
                self.ir.add_component(
                    Component("provider", "OpenAI", self.ev(node), {"module": "openai"})
                )
        else:
            component_from_import(self.ir, node.module or "", self.ev(node))

    def visit_Assign(self, node: ast.Assign) -> None:
        if self.current_tool:
            dynamic_origin = python_http_origin_is_dynamic(
                node.value, self.dynamic_http_origin_names
            )
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if dynamic_origin:
                    self.dynamic_http_origin_names.add(target.id)
                else:
                    self.dynamic_http_origin_names.discard(target.id)
        if isinstance(node.value, ast.Call):
            constructor = dotted_name(node.value.func)
            if constructor in {
                "httpx.Client",
                "httpx.AsyncClient",
                "aiohttp.ClientSession",
                "requests.Session",
            }:
                self.http_client_names.update(
                    target.id for target in node.targets if isinstance(target, ast.Name)
                )
        if isinstance(node.value, ast.Constant) and node.value.value is True:
            for target in node.targets:
                if APPROVAL_BYPASS_NAME.search(dotted_name(target)):
                    self.ir.add_component(
                        Component(
                            "control-setting",
                            "auto-approval",
                            self.ev(node),
                            {"enabled": True, "scope": source_scope(self.path)},
                        )
                    )
        for target in node.targets:
            name = dotted_name(target)
            environment_names = python_approval_environment_names(node.value)
            if APPROVAL_BYPASS_ENV_NAME.search(name) and environment_names:
                self.approval_environment_flags[name] = environment_names
                if self.function_depth == 0:
                    self.module_approval_environment_flags[name] = environment_names
                if name.startswith("self.") and self.class_approval_environment_flags:
                    self.class_approval_environment_flags[-1][name] = environment_names
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        environment_names = python_approval_environment_names(node.test)
        referenced_flags = {
            name
            for candidate in ast.walk(node.test)
            if isinstance(candidate, (ast.Name, ast.Attribute))
            and (name := dotted_name(candidate)) in self.approval_environment_flags
        }
        class_flags = (
            self.class_approval_environment_flags[-1]
            if self.class_approval_environment_flags
            else {}
        )
        referenced_class_flags = {
            name
            for candidate in ast.walk(node.test)
            if isinstance(candidate, ast.Attribute)
            and (name := dotted_name(candidate)) in class_flags
        }
        all_environment_names = (
            environment_names
            | {
                environment_name
                for flag in referenced_flags
                for environment_name in self.approval_environment_flags[flag]
            }
            | {
                environment_name
                for flag in referenced_class_flags
                for environment_name in class_flags[flag]
            }
        )
        direct_approval_return = bool(
            node.body
            and isinstance(node.body[0], ast.Return)
            and isinstance(node.body[0].value, ast.Constant)
            and node.body[0].value.value is True
        )
        approval_short_circuit = bool(
            all_environment_names
            and self.function_stack
            and APPROVAL_GATE_NAME.search(self.function_stack[-1])
            and node.body
            and isinstance(node.body[-1], ast.Return)
            and node.body[-1].value is None
            and all(isinstance(statement, ast.Expr) for statement in node.body[:-1])
        )
        if (direct_approval_return and all_environment_names) or approval_short_circuit:
            self.ir.add_component(
                Component(
                    "control-setting",
                    "auto-approval",
                    self.ev(node),
                    {
                        "enabled": True,
                        "source": (
                            "environment-approval-short-circuit"
                            if approval_short_circuit
                            else "environment-guard"
                        ),
                        "environment_names": sorted(all_environment_names),
                        "scope": source_scope(self.path),
                    },
                )
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        previous_allowlisted_names = self.allowlisted_names
        previous_allowlist_evidence = self.allowlist_evidence
        previous_allowlist_control_names = self.allowlist_control_names
        previous_http_client_names = self.http_client_names
        previous_approval_environment_flags = self.approval_environment_flags
        self.allowlisted_names = set()
        self.allowlist_evidence = {}
        self.allowlist_control_names = {}
        self.http_client_names = set()
        if self.function_depth == 0:
            self.approval_environment_flags = self.module_approval_environment_flags.copy()
        else:
            self.approval_environment_flags = self.approval_environment_flags.copy()
        self.function_depth += 1
        self.function_stack.append(node.name)
        self.function_fixed_binding_sources.append(self.fixed_function_parameter_bindings(node))
        self.function_escaping_children.append(self.escaping_nested_function_names(node))
        local_bindings = python_function_local_bindings(node)
        function_path_constructors = {
            constructor
            for constructor in self.path_constructors
            if constructor.split(".", 1)[0] not in local_bindings
        }
        function_path_bindings = python_immutable_path_bindings(
            node, function_path_constructors
        )
        function_filesystem_aliases = {
            alias: canonical
            for alias, canonical in self.filesystem_api_aliases.items()
            if alias.split(".", 1)[0] not in local_bindings
        }
        filesystem_callable_calls = python_filesystem_callable_calls(
            node, function_filesystem_aliases
        )
        self.function_filesystem_api_aliases.append(function_filesystem_aliases)
        self.function_filesystem_callable_calls.append(filesystem_callable_calls)
        self.function_path_bindings.append(function_path_bindings)
        self.function_path_constructors.append(function_path_constructors)
        self.function_path_boundary_calls.append(
            python_path_boundary_calls(
                node,
                self.path,
                self.lines,
                self.path_constructors,
                self.filesystem_api_aliases,
                filesystem_callable_calls,
                function_path_bindings,
                (
                    self.class_path_helper_summaries[-1]
                    if self.class_path_helper_summaries
                    else {}
                ),
            )
        )
        decorators = {
            dotted_name(decorator.func)
            if isinstance(decorator, ast.Call)
            else dotted_name(decorator)
            for decorator in node.decorator_list
        }
        registration = (
            self.registered_tool_functions.get((self.path, node.name))
            if self.function_depth == 1 and not self.class_stack
            else None
        )
        if (
            decorators & TOOL_DECORATORS
            or any(name.endswith(".tool") for name in decorators)
            or registration is not None
        ):
            qualified_name = ".".join([*self.class_stack, node.name])
            tool_id = (
                self.definition_symbol_ids.get(id(node))
                or self.local_symbol_ids.get(("tool", qualified_name))
                or source_symbol("py", self.path, "tool", qualified_name)
            )
            needs_approval = registration.needs_approval if registration else False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    needs_approval = needs_approval or any(
                        keyword.arg in {"needs_approval", "require_approval"}
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                        for keyword in decorator.keywords
                    )
            attributes: dict[str, object] = {
                "decorators": sorted(decorators),
                "needs_approval": needs_approval,
            }
            if registration:
                attributes.update(
                    {
                        "registration": "post-definition",
                        "registration_path": registration.evidence.path,
                        "registration_line": registration.evidence.line,
                        "registrar": registration.registrar,
                        "resolution": registration.resolution,
                    }
                )
            self.ir.add_component(
                Component(
                    "tool",
                    node.name,
                    self.ev(node),
                    attributes,
                    tool_id,
                )
            )
            if needs_approval:
                approval_evidence = registration.evidence if registration else self.ev(node)
                self.ir.add_component(
                    Component("control", "human-approval", approval_evidence)
                )
                self.ir.add_relationship(
                    Relationship(
                        "tool",
                        node.name,
                        "governed-by",
                        "control",
                        "human-approval",
                        approval_evidence,
                        source_id=tool_id,
                    )
                )
            previous_tool = self.current_tool
            previous_tool_id = self.current_tool_id
            previous_dynamic_http_origin_names = self.dynamic_http_origin_names
            self.current_tool = node.name
            self.current_tool_id = tool_id
            self.dynamic_http_origin_names = {
                argument.arg
                for argument in (
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                )
                if argument.arg not in {"self", "cls"}
            }
            if node.args.vararg:
                self.dynamic_http_origin_names.add(node.args.vararg.arg)
            if node.args.kwarg:
                self.dynamic_http_origin_names.add(node.args.kwarg.arg)
            self.visit_function_statements(node)
            self.current_tool = previous_tool
            self.current_tool_id = previous_tool_id
            self.dynamic_http_origin_names = previous_dynamic_http_origin_names
        else:
            self.visit_function_statements(node)
        self.allowlisted_names = previous_allowlisted_names
        self.allowlist_evidence = previous_allowlist_evidence
        self.allowlist_control_names = previous_allowlist_control_names
        self.http_client_names = previous_http_client_names
        self.function_depth -= 1
        self.function_stack.pop()
        self.function_fixed_binding_sources.pop()
        self.function_escaping_children.pop()
        self.function_path_boundary_calls.pop()
        self.function_filesystem_api_aliases.pop()
        self.function_filesystem_callable_calls.pop()
        self.function_path_bindings.pop()
        self.function_path_constructors.pop()
        self.approval_environment_flags = previous_approval_environment_flags

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.class_stack.append(node.name)
        fixed_bindings, fixed_accessors = self.fixed_class_tool_bindings(node)
        self.class_fixed_tool_bindings.append(fixed_bindings)
        self.class_fixed_tool_accessors.append(fixed_accessors)
        self.class_registry_method_summaries.append(
            self.registry_method_summaries(node, self.path, self.lines)
        )
        self.class_registry_manager_bindings.append(self.registry_manager_bindings(node))
        self.class_path_helper_summaries.append(
            python_class_path_helper_summaries(
                node, self.path, self.lines, self.path_constructors
            )
        )
        class_environment_flags: dict[str, set[str]] = {}
        for statement in node.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for candidate in ast.walk(statement):
                if not isinstance(candidate, ast.Assign):
                    continue
                environment_names = python_approval_environment_names(candidate.value)
                for target in candidate.targets:
                    name = dotted_name(target)
                    if (
                        name.startswith("self.")
                        and APPROVAL_BYPASS_ENV_NAME.search(name)
                        and environment_names
                    ):
                        class_environment_flags[name] = environment_names
        self.class_approval_environment_flags.append(class_environment_flags)
        for statement in node.body:
            self.visit(statement)
        self.class_approval_environment_flags.pop()
        self.class_fixed_tool_accessors.pop()
        self.class_fixed_tool_bindings.pop()
        self.class_registry_manager_bindings.pop()
        self.class_registry_method_summaries.pop()
        self.class_path_helper_summaries.pop()
        self.class_stack.pop()

    def registry_manager_bindings(self, node: ast.ClassDef) -> dict[str, RegistryClassTarget]:
        """Resolve immutable constructor-bound attributes to imported registry classes."""
        assignments: dict[str, list[tuple[str, ast.AST | None]]] = defaultdict(list)
        for method in node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for candidate in ast.walk(method):
                targets: tuple[ast.AST, ...] = ()
                value: ast.AST | None = None
                if isinstance(candidate, ast.Assign):
                    targets, value = tuple(candidate.targets), candidate.value
                elif isinstance(candidate, ast.AnnAssign):
                    targets, value = (candidate.target,), candidate.value
                elif isinstance(candidate, ast.AugAssign):
                    targets = (candidate.target,)
                elif isinstance(candidate, ast.Delete):
                    targets = tuple(candidate.targets)
                elif (
                    isinstance(candidate, ast.Call)
                    and dotted_name(candidate.func) == "setattr"
                    and len(candidate.args) >= 2
                    and isinstance(candidate.args[0], ast.Name)
                    and candidate.args[0].id == "self"
                    and isinstance(candidate.args[1], ast.Constant)
                    and isinstance(candidate.args[1].value, str)
                ):
                    assignments[candidate.args[1].value].append((method.name, None))
                for target in targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        assignments[target.attr].append((method.name, value))

        bindings: dict[str, RegistryClassTarget] = {}
        for attribute, observations in assignments.items():
            if len(observations) != 1 or observations[0][0] != "__init__":
                continue
            value = observations[0][1]
            if not isinstance(value, ast.Call):
                continue
            constructor = dotted_name(value.func)
            root_name = constructor.split(".", 1)[0]
            if root_name in self.module_rebound_names:
                continue
            target_path = self.imported_symbol_paths.get(root_name, self.path)
            target_name = self.imported_symbol_names.get(root_name, root_name)
            if target := self.registry_class_exports.get((target_path, target_name)):
                bindings[attribute] = target
        return bindings

    def fixed_class_tool_bindings(
        self, node: ast.ClassDef
    ) -> tuple[dict[str, Evidence], dict[str, Evidence]]:
        """Return constructor-only instance bindings and pure accessors over them."""
        assignments: dict[str, list[tuple[ast.AST, str]]] = defaultdict(list)

        def root_self_attribute(target: ast.AST) -> str | None:
            current = target
            while isinstance(current, ast.Attribute):
                if isinstance(current.value, ast.Name) and current.value.id == "self":
                    return current.attr
                current = current.value
            return None

        for statement in node.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for candidate in ast.walk(statement):
                targets: list[ast.AST] = []
                if isinstance(candidate, ast.Assign):
                    targets.extend(candidate.targets)
                elif isinstance(candidate, (ast.AnnAssign, ast.AugAssign)):
                    targets.append(candidate.target)
                elif isinstance(candidate, ast.Delete):
                    targets.extend(candidate.targets)
                for target in targets:
                    if attribute := root_self_attribute(target):
                        assignments[attribute].append((candidate, statement.name))

        fixed = {
            attribute: self.ev(observations[0][0])
            for attribute, observations in assignments.items()
            if len(observations) == 1 and observations[0][1] == "__init__"
        }
        accessors: dict[str, Evidence] = {}
        for statement in node.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            positional = (*statement.args.posonlyargs, *statement.args.args)
            if len(positional) != 1 or positional[0].arg != "self":
                continue
            returns = [
                candidate
                for candidate in ast.walk(statement)
                if isinstance(candidate, ast.Return) and candidate.value is not None
            ]
            if len(returns) != 1:
                continue
            expression = dotted_name(returns[0].value)
            if expression.startswith("self."):
                root = expression.split(".", 2)[1]
                if root in fixed:
                    accessors[statement.name] = fixed[root]
        return fixed, accessors

    def fixed_function_parameter_bindings(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> dict[str, Evidence]:
        """Return parameters whose bindings are not mutated in their lexical function."""
        parameters = {
            argument.arg: argument
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
            if argument.arg not in {"self", "cls"}
        }
        if node.args.vararg:
            parameters[node.args.vararg.arg] = node.args.vararg
        if node.args.kwarg:
            parameters[node.args.kwarg.arg] = node.args.kwarg
        mutated: set[str] = set()

        def collect(candidate: ast.AST) -> None:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if candidate.name in parameters:
                    mutated.add(candidate.name)
                mutated.update(
                    name
                    for nested in ast.walk(candidate)
                    if isinstance(nested, ast.Nonlocal)
                    for name in nested.names
                    if name in parameters
                )
                return
            if isinstance(candidate, ast.Lambda):
                return
            if (
                isinstance(candidate, ast.Name)
                and isinstance(candidate.ctx, (ast.Store, ast.Del))
                and candidate.id in parameters
            ):
                mutated.add(candidate.id)
            if isinstance(candidate, ast.ExceptHandler) and candidate.name in parameters:
                mutated.add(candidate.name)
            if isinstance(candidate, (ast.Import, ast.ImportFrom)):
                for alias in candidate.names:
                    bound = alias.asname or alias.name.split(".", 1)[0]
                    if bound in parameters:
                        mutated.add(bound)
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        for statement in node.body:
            collect(statement)
        return {
            name: self.ev(argument) for name, argument in parameters.items() if name not in mutated
        }

    @staticmethod
    def registry_method_summaries(
        node: ast.ClassDef,
        path: str,
        lines: list[str],
    ) -> dict[str, RegistryMethodSummary]:
        """Summarize class methods that reject names missing from their tool registry."""
        summaries: dict[str, RegistryMethodSummary] = {}

        def rejecting_missing_value(statement: ast.If, local_name: str) -> bool:
            test = statement.test
            missing = (
                isinstance(test, ast.UnaryOp)
                and isinstance(test.op, ast.Not)
                and isinstance(test.operand, ast.Name)
                and test.operand.id == local_name
            ) or (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == local_name
                and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Is, ast.Eq))
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None
            )
            return missing and any(
                isinstance(child, ast.Raise)
                or (
                    isinstance(child, ast.Return)
                    and (
                        child.value is None
                        or (isinstance(child.value, ast.Constant) and child.value.value is None)
                    )
                )
                for child in statement.body
            )

        def safe_registry_reassignment(candidate: ast.AST, local_name: str) -> bool | None:
            """Return whether an assignment preserves registry provenance, or None if unrelated."""
            value: ast.AST | None = None
            assigned = False
            if isinstance(candidate, ast.Assign):
                assigned = any(
                    isinstance(target, ast.Name) and target.id == local_name
                    for target in candidate.targets
                )
                value = candidate.value
            elif isinstance(candidate, ast.AnnAssign):
                assigned = (
                    isinstance(candidate.target, ast.Name) and candidate.target.id == local_name
                )
                value = candidate.value
            elif isinstance(candidate, (ast.AugAssign, ast.NamedExpr)):
                assigned = (
                    isinstance(candidate.target, ast.Name) and candidate.target.id == local_name
                )
            if not assigned:
                return None
            if isinstance(value, ast.Await):
                value = value.value
            if not isinstance(value, ast.Call):
                return False
            assignment_name = dotted_name(value.func)
            short_assignment = assignment_name.rsplit(".", 1)[-1]
            receiver = assignment_name.rsplit(".", 1)[0]
            return (receiver == "self" or receiver.startswith("self.")) and (
                short_assignment.startswith("get_tool")
                or (short_assignment == "get" and "tool" in receiver.lower())
            )

        def lexical_method_nodes(
            method: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> list[ast.AST]:
            result: list[ast.AST] = []

            def collect(candidate: ast.AST) -> None:
                if isinstance(
                    candidate,
                    (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),
                ):
                    return
                result.append(candidate)
                for child in ast.iter_child_nodes(candidate):
                    collect(child)

            for statement in method.body:
                collect(statement)
            return result

        for method in node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            positional_parameters = [
                argument
                for argument in (
                    *method.args.posonlyargs,
                    *method.args.args,
                )
                if argument.arg not in {"self", "cls"}
            ]
            parameter_positions = {
                argument.arg: index for index, argument in enumerate(positional_parameters)
            }
            parameter_names = {
                argument.arg for argument in (*positional_parameters, *method.args.kwonlyargs)
            }
            scope_nodes = lexical_method_nodes(method)
            scope_node_ids = {id(candidate) for candidate in scope_nodes}
            parent_by_id = {
                id(child): candidate
                for candidate in scope_nodes
                for child in ast.iter_child_nodes(candidate)
                if id(child) in scope_node_ids
            }
            lookups: list[tuple[int, str, str, ast.AST | None]] = []
            guards = [candidate for candidate in scope_nodes if isinstance(candidate, ast.If)]
            for candidate in scope_nodes:
                target: ast.AST | None = None
                value: ast.AST | None = None
                if isinstance(candidate, ast.Assign) and len(candidate.targets) == 1:
                    target, value = candidate.targets[0], candidate.value
                elif isinstance(candidate, ast.AnnAssign):
                    target, value = candidate.target, candidate.value
                if not isinstance(target, ast.Name) or value is None:
                    continue
                if isinstance(value, ast.Await):
                    value = value.value
                if not isinstance(value, ast.Call):
                    continue
                lookup_name = dotted_name(value.func)
                short_lookup = lookup_name.rsplit(".", 1)[-1]
                receiver = lookup_name.rsplit(".", 1)[0]
                if not (receiver == "self" or receiver.startswith("self.")) or not (
                    short_lookup == "get_tool"
                    or (short_lookup == "get" and "tool" in receiver.lower())
                ):
                    continue
                name_expression = value.args[0] if value.args else None
                for keyword in value.keywords:
                    if keyword.arg == "name":
                        name_expression = keyword.value
                if not isinstance(name_expression, ast.Name):
                    continue
                if name_expression.id not in parameter_names:
                    continue
                lookups.append(
                    (
                        candidate.lineno,
                        target.id,
                        name_expression.id,
                        parent_by_id.get(id(candidate)),
                    )
                )
            for lookup_line, local_name, parameter_name, lookup_parent in sorted(
                lookups, key=lambda lookup: lookup[0]
            ):
                matching_guards = sorted(
                    (
                        guard
                        for guard in guards
                        if guard.lineno > lookup_line
                        and parent_by_id.get(id(guard)) is lookup_parent
                        and rejecting_missing_value(guard, local_name)
                        and not any(
                            safe_registry_reassignment(candidate, local_name) is False
                            for candidate in scope_nodes
                            if lookup_line < getattr(candidate, "lineno", 0) < guard.lineno
                        )
                    ),
                    key=lambda guard: guard.lineno,
                )
                if matching_guards:
                    required_literals: dict[str, bool] = {}
                    unresolved_early_return = False
                    for early_return in (
                        candidate
                        for candidate in scope_nodes
                        if isinstance(candidate, ast.Return) and candidate.lineno < lookup_line
                    ):
                        child: ast.AST = early_return
                        parent = parent_by_id.get(id(early_return))
                        condition: tuple[str, bool] | None = None
                        while parent is not None:
                            if isinstance(parent, ast.If):
                                in_else_branch = child in parent.orelse
                                if (
                                    isinstance(parent.test, ast.Name)
                                    and parent.test.id in parameter_names
                                ):
                                    condition = (
                                        parent.test.id,
                                        in_else_branch,
                                    )
                                    break
                                if (
                                    isinstance(parent.test, ast.UnaryOp)
                                    and isinstance(parent.test.op, ast.Not)
                                    and isinstance(parent.test.operand, ast.Name)
                                    and parent.test.operand.id in parameter_names
                                ):
                                    condition = (
                                        parent.test.operand.id,
                                        not in_else_branch,
                                    )
                                    break
                            child = parent
                            parent = parent_by_id.get(id(parent))
                        if condition is None:
                            unresolved_early_return = True
                            break
                        condition_name, required_value = condition
                        existing = required_literals.get(condition_name)
                        if existing is not None and existing != required_value:
                            unresolved_early_return = True
                            break
                        required_literals[condition_name] = required_value
                    if unresolved_early_return:
                        continue
                    summaries[method.name] = (
                        parameter_positions.get(parameter_name),
                        parameter_name,
                        Evidence(
                            path,
                            matching_guards[0].lineno,
                            excerpt(lines, matching_guards[0].lineno),
                        ),
                        tuple(
                            sorted(
                                (
                                    name,
                                    parameter_positions.get(name),
                                    value,
                                )
                                for name, value in required_literals.items()
                            )
                        ),
                    )
                    break
        return summaries

    @staticmethod
    def escaping_nested_function_names(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> set[str]:
        """Return nested functions returned or passed to a registration decorator."""
        nested_names: set[str] = set()

        def collect_definitions(candidate: ast.AST) -> None:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nested_names.add(candidate.name)
                return
            if isinstance(candidate, (ast.Lambda, ast.ClassDef)):
                return
            for child in ast.iter_child_nodes(candidate):
                collect_definitions(child)

        for statement in node.body:
            collect_definitions(statement)

        escaping: set[str] = set()
        registration_names = {"action", "add_tool", "register", "register_tool", "tool"}

        def collect_escapes(candidate: ast.AST) -> None:
            if isinstance(
                candidate,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),
            ):
                return
            if isinstance(candidate, ast.Return):
                values: tuple[ast.AST, ...]
                if isinstance(candidate.value, ast.Name):
                    values = (candidate.value,)
                elif isinstance(candidate.value, (ast.List, ast.Tuple, ast.Set)):
                    values = tuple(candidate.value.elts)
                elif isinstance(candidate.value, ast.Dict):
                    values = tuple(candidate.value.values)
                else:
                    values = ()
                escaping.update(
                    value.id
                    for value in values
                    if isinstance(value, ast.Name) and value.id in nested_names
                )
            if isinstance(candidate, ast.Call):
                function = (
                    candidate.func.func if isinstance(candidate.func, ast.Call) else candidate.func
                )
                registration_name = dotted_name(function).rsplit(".", 1)[-1].lower()
                if registration_name in registration_names:
                    escaping.update(
                        argument.id
                        for argument in candidate.args
                        if isinstance(argument, ast.Name) and argument.id in nested_names
                    )
            for child in ast.iter_child_nodes(candidate):
                collect_escapes(child)

        for statement in node.body:
            collect_escapes(statement)
        return escaping

    def fixed_tool_binding(self, expression: ast.AST) -> tuple[Evidence, str] | None:
        """Resolve a class-instance or enclosing-closure MCP tool source."""
        if self.class_fixed_tool_bindings:
            fixed = self.class_fixed_tool_bindings[-1]
            accessors = self.class_fixed_tool_accessors[-1]
            if isinstance(expression, ast.Call) and not expression.args and not expression.keywords:
                accessor = dotted_name(expression.func)
                if accessor.startswith("self.") and (
                    evidence := accessors.get(accessor.removeprefix("self."))
                ):
                    return evidence, "instance"
            name = dotted_name(expression)
            if name.startswith("self."):
                root = name.split(".", 2)[1]
                if evidence := fixed.get(root) or accessors.get(root):
                    return evidence, "instance"

        name = dotted_name(expression)
        root = name.split(".", 1)[0]
        current_function = self.function_stack[-1] if self.function_stack else ""
        for index in range(len(self.function_fixed_binding_sources) - 2, -1, -1):
            if current_function not in self.function_escaping_children[index]:
                continue
            if evidence := self.function_fixed_binding_sources[index].get(root):
                return evidence, "closure"
        return None

    def visit_function_statements(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default:
                self.visit(default)
        for statement in node.body:
            self.visit(statement)
            if guarded_name := self.rejected_allowlist_name(statement):
                self.allowlisted_names.add(guarded_name)
                self.allowlist_evidence[guarded_name] = self.ev(statement)
                self.allowlist_control_names[guarded_name] = "tool-allowlist"
            for guarded_name in self.registry_guarded_tool_names(statement):
                self.allowlisted_names.add(guarded_name)
                self.allowlist_evidence[guarded_name] = self.ev(statement)
                self.allowlist_control_names[guarded_name] = "tool-registry"

    def visit_With(self, node: ast.With | ast.AsyncWith) -> None:
        trace_calls = [
            item.context_expr
            for item in node.items
            if isinstance(item.context_expr, ast.Call)
            and dotted_name(item.context_expr.func).endswith(".start_as_current_span")
        ]
        client_names = {
            item.optional_vars.id
            for item in node.items
            if isinstance(item.context_expr, ast.Call)
            and dotted_name(item.context_expr.func)
            in {"httpx.Client", "httpx.AsyncClient", "aiohttp.ClientSession", "requests.Session"}
            and isinstance(item.optional_vars, ast.Name)
        }
        if (not self.current_tool or not trace_calls) and not client_names:
            self.generic_visit(node)
            return
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self.visit(item.optional_vars)
        previous_http_client_names = self.http_client_names
        self.http_client_names = self.http_client_names | client_names
        evidence = self.ev(trace_calls[0]) if self.current_tool and trace_calls else None
        if evidence:
            self.ir.add_component(
                Component(
                    "control",
                    "action-trace",
                    evidence,
                    {
                        "instrumentation": "opentelemetry",
                        "durability": "unresolved",
                        "scope": source_scope(self.path),
                        "tool": self.current_tool,
                    },
                )
            )
            self.ir.add_relationship(
                Relationship(
                    "tool",
                    self.current_tool,
                    "contains-control",
                    "control",
                    "action-trace",
                    evidence,
                    {"durability": "unresolved"},
                    source_id=self.current_tool_id,
                )
            )
            self.active_audit_controls.append(evidence)
        for statement in node.body:
            self.visit(statement)
        if evidence:
            self.active_audit_controls.pop()
        self.http_client_names = previous_http_client_names

    visit_AsyncWith = visit_With

    @staticmethod
    def rejected_allowlist_name(statement: ast.stmt) -> str | None:
        if not isinstance(statement, ast.If) or not isinstance(statement.test, ast.Compare):
            return None
        comparison = statement.test
        if (
            isinstance(comparison.left, ast.Name)
            and len(comparison.ops) == 1
            and isinstance(comparison.ops[0], ast.NotIn)
            and any(isinstance(child, (ast.Raise, ast.Return)) for child in statement.body)
        ):
            return comparison.left.id
        return None

    @staticmethod
    def registry_guarded_tool_names(statement: ast.stmt) -> set[str]:
        """Names proven to exist by an uncaught internal tool-registry lookup."""
        if not isinstance(statement, ast.Assign):
            return set()
        guarded: set[str] = set()
        for candidate in ast.walk(statement.value):
            if not isinstance(candidate, ast.Subscript) or not isinstance(
                candidate.slice, ast.Name
            ):
                continue
            registry_name = dotted_name(candidate.value)
            if not registry_name.startswith("self.") or "tool" not in registry_name.lower():
                continue
            guarded.add(candidate.slice.id)
            if (
                isinstance(statement.value, ast.Attribute)
                and statement.value.value is candidate
                and statement.value.attr in {"name", "tool_name"}
            ):
                guarded.update(
                    target.id for target in statement.targets if isinstance(target, ast.Name)
                )
        return guarded

    def visit_Call(self, node: ast.Call) -> None:
        call_name = dotted_name(node.func)
        short_name = call_name.rsplit(".", 1)[-1]
        if self.has_openai_agents_import and short_name in BUILTIN_TOOL_CAPABILITIES:
            tool_name = f"{short_name}@{node.lineno}"
            tool_id = self.call_symbol_ids.get(id(node)) or source_symbol(
                "py", self.path, "tool", tool_name
            )
            approval_state = "disabled-default"
            approval_source = "sdk-default"
            approval_handler = "none"
            execution_environment = (
                "local" if short_name == "ShellTool" and node.args else "unresolved"
            )
            approval_evidence = self.ev(node)
            for keyword in node.keywords:
                if keyword.arg in {"needs_approval", "require_approval"}:
                    approval_evidence = self.ev(keyword.value)
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        approval_state = "enabled"
                        approval_source = "literal"
                    elif isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                        approval_state = "disabled-explicit"
                        approval_source = "literal"
                    else:
                        approval_state = "unresolved"
                        approval_source = "callback-or-expression"
                elif keyword.arg == "on_approval" and not (
                    isinstance(keyword.value, ast.Constant) and keyword.value.value is None
                ):
                    approval_handler = "configured"
                elif short_name == "ShellTool" and keyword.arg == "executor":
                    execution_environment = "local"
                elif (
                    short_name == "ShellTool"
                    and keyword.arg == "environment"
                    and isinstance(keyword.value, ast.Dict)
                ):
                    for key, value in zip(keyword.value.keys, keyword.value.values, strict=True):
                        if (
                            isinstance(key, ast.Constant)
                            and key.value == "type"
                            and isinstance(value, ast.Constant)
                            and isinstance(value.value, str)
                        ):
                            execution_environment = "local" if value.value == "local" else "hosted"
            if approval_state == "enabled" and approval_handler == "configured":
                approval_state = "unresolved-handler"
            self.ir.add_component(
                Component(
                    "tool",
                    tool_name,
                    self.ev(node),
                    {
                        "constructor": call_name,
                        "approval_handler": approval_handler,
                        "approval_policy": approval_state,
                        "approval_source": approval_source,
                        "execution_environment": execution_environment,
                        "scope": source_scope(self.path),
                    },
                    tool_id,
                )
            )
            for capability in BUILTIN_TOOL_CAPABILITIES[short_name]:
                attributes = {
                    "api": call_name,
                    "builtin_tool": True,
                    "scope": source_scope(self.path),
                }
                if capability == "shell-execution":
                    attributes.update(
                        {
                            "shell": False,
                            "dynamic_command": False,
                            "execution_environment": execution_environment,
                        }
                    )
                self.ir.add_component(
                    Component("capability", capability, self.ev(node), attributes)
                )
                self.ir.add_relationship(
                    Relationship(
                        "tool",
                        tool_name,
                        "uses",
                        "capability",
                        capability,
                        self.ev(node),
                        source_id=tool_id,
                    )
                )
            if approval_state == "enabled":
                self.ir.add_component(Component("control", "human-approval", approval_evidence))
                self.ir.add_relationship(
                    Relationship(
                        "tool",
                        tool_name,
                        "governed-by",
                        "control",
                        "human-approval",
                        approval_evidence,
                        source_id=tool_id,
                    )
                )
        if self.has_docker_import and call_name.endswith(".containers.run"):
            for keyword in node.keywords:
                if (
                    keyword.arg == "privileged"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    self.ir.add_component(
                        Component(
                            "sandbox-boundary",
                            "privileged-container",
                            self.ev(keyword.value),
                            {"scope": source_scope(self.path), "api": call_name},
                        )
                    )
        constructor_provider = next(
            (
                provider
                for provider, constructors in MODEL_CONSTRUCTORS.items()
                if short_name in constructors
            ),
            None,
        )
        if constructor_provider:
            self.ir.add_component(
                Component(
                    "provider",
                    constructor_provider,
                    self.ev(node),
                    {"constructor": call_name},
                )
            )
            model_value = "unresolved"
            for keyword in node.keywords:
                if (
                    keyword.arg in {"model", "model_name", "azure_deployment", "deployment_name"}
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    model_value = keyword.value.value
            if model_value != "unresolved":
                self.ir.add_component(
                    Component(
                        "model",
                        model_value,
                        self.ev(node),
                        {"provider": constructor_provider, "constructor": call_name},
                    )
                )
        if any(
            keyword.arg
            and APPROVAL_BYPASS_NAME.search(keyword.arg)
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        ):
            self.ir.add_component(
                Component(
                    "control-setting",
                    "auto-approval",
                    self.ev(node),
                    {"enabled": True, "scope": source_scope(self.path)},
                )
            )
        if short_name in AGENT_CALLS:
            name = short_name
            for keyword in node.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    name = str(keyword.value.value)
            agent_id = self.call_symbol_ids.get(id(node)) or source_symbol(
                "py", self.path, "agent", f"{name}@{node.lineno}"
            )
            self.ir.add_component(
                Component("agent", name, self.ev(node), {"constructor": call_name}, agent_id)
            )
            for keyword in node.keywords:
                if keyword.arg == "model" and isinstance(keyword.value, ast.Constant):
                    model_value = str(keyword.value.value)
                    self.ir.add_component(
                        Component(
                            "model",
                            model_value,
                            self.ev(node),
                            {"provider": provider_for_model(model_value), "configured_on": name},
                        )
                    )
            for keyword in node.keywords:
                if keyword.arg not in {"tools", "handoffs", "agents"}:
                    continue
                values = (
                    keyword.value.elts if isinstance(keyword.value, (ast.List, ast.Tuple)) else []
                )
                for value in values:
                    target_kind = "tool" if keyword.arg == "tools" else "agent"
                    relation = "uses" if target_kind == "tool" else "delegates-to"
                    target_name = dotted_name(value)
                    target_id, target_identity = self.resolve_local_symbol(
                        target_kind, target_name, node
                    )
                    if isinstance(value, ast.Call) and dotted_name(value.func).endswith(".as_tool"):
                        target_name = dotted_name(value.func).removesuffix(".as_tool")
                        target_kind = "agent"
                        relation = "delegates-to"
                        target_id, target_identity = self.resolve_local_symbol(
                            "agent", target_name, node
                        )
                    elif (
                        self.has_openai_agents_import
                        and isinstance(value, ast.Call)
                        and dotted_name(value.func).rsplit(".", 1)[-1] in BUILTIN_TOOL_CAPABILITIES
                    ):
                        constructor = dotted_name(value.func).rsplit(".", 1)[-1]
                        target_name = f"{constructor}@{value.lineno}"
                        target_id = self.call_symbol_ids.get(id(value)) or source_symbol(
                            "py", self.path, "tool", target_name
                        )
                    if target_name:
                        attributes = {}
                        root_name, separator, suffix = target_name.partition(".")
                        imported_path = self.imported_symbol_paths.get(
                            target_name
                        ) or self.imported_symbol_paths.get(root_name)
                        if imported_path:
                            attributes["target_path"] = imported_path
                            original = self.imported_symbol_names.get(root_name, root_name)
                            resolved_name = f"{original}.{suffix}" if separator else original
                            target_id = source_symbol(
                                "py", imported_path, target_kind, resolved_name
                            )
                        elif target_id is not None and target_identity:
                            attributes["target_identity"] = target_identity
                        elif (
                            target_id is None
                            and (
                                target_kind,
                                target_name,
                            )
                            in self.ambiguous_local_symbols
                        ):
                            attributes["target_identity"] = "ambiguous-repeated-binding"
                        self.ir.add_relationship(
                            Relationship(
                                "agent",
                                name,
                                relation,
                                target_kind,
                                target_name,
                                self.ev(node),
                                attributes,
                                source_id=agent_id,
                                target_id=target_id,
                            )
                        )
        if short_name in {"FastMCP", "ClientSession", "StdioServerParameters"}:
            self.ir.add_component(
                Component("mcp", short_name, self.ev(node), {"constructor": call_name})
            )
        if self.has_mcp_import and short_name in {"call_tool", "callTool"}:
            tool_name = node.args[0] if node.args else None
            arguments = node.args[1] if len(node.args) > 1 else None
            for keyword in node.keywords:
                if keyword.arg in {"name", "tool_name"}:
                    tool_name = keyword.value
                elif keyword.arg in {"arguments", "params"}:
                    arguments = keyword.value
            if tool_name is not None and not isinstance(tool_name, ast.Constant):
                guarded_name = tool_name.id if isinstance(tool_name, ast.Name) else ""
                resolved_guard = guarded_name in self.allowlisted_names
                fixed_binding = self.fixed_tool_binding(tool_name)
                binding_evidence = fixed_binding[0] if fixed_binding else None
                binding_scope = fixed_binding[1] if fixed_binding else None
                guard_control = self.allowlist_control_names.get(guarded_name, "tool-allowlist")
                guard_evidence = self.allowlist_evidence.get(guarded_name)
                guard_summary = ""
                guard_conditions: dict[str, bool] = {}
                guard_class: RegistryClassTarget | None = None
                method_summary: RegistryMethodSummary | None = None
                call_parts = call_name.split(".")
                if not resolved_guard and len(call_parts) == 2 and call_parts[0] == "self":
                    if self.class_registry_method_summaries:
                        method_summary = self.class_registry_method_summaries[-1].get(short_name)
                    if method_summary:
                        guard_summary = "same-class-method"
                elif (
                    not resolved_guard
                    and len(call_parts) == 3
                    and call_parts[0] == "self"
                    and self.class_registry_manager_bindings
                    and (guard_class := self.class_registry_manager_bindings[-1].get(call_parts[1]))
                ):
                    method_summary = guard_class.methods.get(short_name)
                    if method_summary:
                        guard_summary = "imported-class-method"
                if method_summary:
                    (
                        parameter_index,
                        parameter_name,
                        method_evidence,
                        required_literals,
                    ) = method_summary
                    mapped_argument = (
                        node.args[parameter_index]
                        if parameter_index is not None and parameter_index < len(node.args)
                        else next(
                            (
                                keyword.value
                                for keyword in node.keywords
                                if keyword.arg == parameter_name
                            ),
                            None,
                        )
                    )
                    literal_requirements_met = True
                    for required_name, required_index, required_value in required_literals:
                        required_argument = (
                            node.args[required_index]
                            if required_index is not None and required_index < len(node.args)
                            else next(
                                (
                                    keyword.value
                                    for keyword in node.keywords
                                    if keyword.arg == required_name
                                ),
                                None,
                            )
                        )
                        if not (
                            isinstance(required_argument, ast.Constant)
                            and required_argument.value is required_value
                        ):
                            literal_requirements_met = False
                            break
                    if mapped_argument is tool_name and literal_requirements_met:
                        resolved_guard = True
                        guard_control = "tool-registry"
                        guard_evidence = method_evidence
                        guard_conditions = {name: value for name, _, value in required_literals}
                    else:
                        guard_summary = ""
                allowlist_guard = resolved_guard and guard_control == "tool-allowlist"
                registry_guard = resolved_guard and guard_control == "tool-registry"
                attributes = {
                    "api": call_name,
                    "dynamic_tool_name": True,
                    "dynamic_arguments": arguments is not None
                    and not isinstance(arguments, ast.Dict),
                    "allowlist_guard": allowlist_guard,
                    "registry_guard": registry_guard,
                    "fixed_tool_binding": binding_evidence is not None,
                    "scope": source_scope(self.path),
                }
                if resolved_guard:
                    attributes["guard_control"] = guard_control
                    if guard_summary:
                        attributes["guard_summary"] = guard_summary
                        attributes["guard_method"] = short_name
                        if guard_class:
                            attributes["guard_class"] = guard_class.name
                        if guard_conditions:
                            attributes["guard_conditions"] = guard_conditions
                    if guard_evidence:
                        attributes["guard_path"] = guard_evidence.path
                        attributes["guard_line"] = guard_evidence.line
                if binding_evidence:
                    attributes["binding_path"] = binding_evidence.path
                    attributes["binding_line"] = binding_evidence.line
                    attributes["binding_scope"] = binding_scope
                self.ir.add_component(
                    Component("capability", "mcp-tool-forwarding", self.ev(node), attributes)
                )
                if self.current_tool:
                    self.ir.add_relationship(
                        Relationship(
                            "tool",
                            self.current_tool,
                            "uses",
                            "capability",
                            "mcp-tool-forwarding",
                            self.ev(node),
                            source_id=self.current_tool_id,
                        )
                    )
                if binding_evidence:
                    policy_effect = f"binds-tool-source-per-{binding_scope}"
                    self.ir.add_component(
                        Component(
                            "control",
                            "fixed-tool-binding",
                            binding_evidence,
                            {
                                "scope": source_scope(self.path),
                                "binding_scope": binding_scope,
                                "policy_effect": policy_effect,
                            },
                        )
                    )
                    self.ir.add_relationship(
                        Relationship(
                            "capability",
                            "mcp-tool-forwarding",
                            "governed-by",
                            "control",
                            "fixed-tool-binding",
                            self.ev(node),
                            {
                                "control_path": binding_evidence.path,
                                "control_line": binding_evidence.line,
                                "binding_scope": binding_scope,
                                "policy_effect": policy_effect,
                            },
                        )
                    )
                if resolved_guard:
                    policy_effect = (
                        "routing-only"
                        if guard_control == "tool-registry"
                        else "restricts-tool-name"
                    )
                    guard_relationship_attributes = {
                        "control_path": (guard_evidence or self.ev(node)).path,
                        "control_line": (guard_evidence or self.ev(node)).line,
                        "policy_effect": policy_effect,
                    }
                    if guard_summary:
                        guard_relationship_attributes["summary"] = guard_summary
                        if guard_class:
                            guard_relationship_attributes["summary_class"] = guard_class.name
                            guard_relationship_attributes["summary_path"] = guard_class.path
                        if guard_conditions:
                            guard_relationship_attributes["required_arguments"] = guard_conditions
                    self.ir.add_component(
                        Component(
                            "control",
                            guard_control,
                            guard_evidence or self.ev(node),
                            {
                                "scope": source_scope(self.path),
                                "policy_effect": policy_effect,
                            },
                        )
                    )
                    self.ir.add_relationship(
                        Relationship(
                            "capability",
                            "mcp-tool-forwarding",
                            "governed-by",
                            "control",
                            guard_control,
                            self.ev(node),
                            guard_relationship_attributes,
                        )
                    )
        if call_name in {
            "subprocess.run",
            "subprocess.Popen",
            "subprocess.call",
            "subprocess.check_output",
        }:
            attributes = {
                "api": call_name,
                "shell": False,
                "dynamic_command": False,
                "scope": source_scope(self.path),
            }
            command = node.args[0] if node.args else None
            attributes["dynamic_command"] = command is not None and not isinstance(
                command, (ast.Constant, ast.List, ast.Tuple)
            )
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                    attributes["shell"] = keyword.value.value is True
            self.ir.add_component(
                Component("capability", "shell-execution", self.ev(node), attributes)
            )
            if self.current_tool:
                self.ir.add_relationship(
                    Relationship(
                        "tool",
                        self.current_tool,
                        "uses",
                        "capability",
                        "shell-execution",
                        self.ev(node),
                        source_id=self.current_tool_id,
                    )
                )
        if call_name in {"eval", "exec"}:
            argument = node.args[0] if node.args else None
            self.ir.add_component(
                Component(
                    "capability",
                    "code-execution",
                    self.ev(node),
                    {
                        "api": call_name,
                        "dynamic_input": argument is not None
                        and not isinstance(argument, ast.Constant),
                        "scope": source_scope(self.path),
                    },
                )
            )
            if self.current_tool:
                self.ir.add_relationship(
                    Relationship(
                        "tool",
                        self.current_tool,
                        "uses",
                        "capability",
                        "code-execution",
                        self.ev(node),
                        source_id=self.current_tool_id,
                    )
                )
        filesystem_aliases = (
            self.function_filesystem_api_aliases[-1]
            if self.function_filesystem_api_aliases
            else self.filesystem_api_aliases
        )
        local_filesystem_callable = (
            self.function_filesystem_callable_calls[-1].get(id(node))
            if self.function_filesystem_callable_calls
            else None
        )
        filesystem_function = python_filesystem_function_write(
            node, filesystem_aliases, local_filesystem_callable
        )
        path_method = python_path_method_write(
            node,
            (
                self.function_path_constructors[-1]
                if self.function_path_constructors
                else self.path_constructors
            ),
            self.function_path_bindings[-1] if self.function_path_bindings else {},
        )
        if filesystem_function is not None or path_method is not None:
            receiver_proof = None
            if filesystem_function is not None:
                canonical_api, filesystem_spec, path_expression = filesystem_function
            else:
                assert path_method is not None
                canonical_api, filesystem_spec, path_expression, receiver_proof = path_method
            path_control = (
                self.function_path_boundary_calls[-1].get(id(node))
                if self.function_path_boundary_calls
                else None
            )
            boundary = (
                path_control
                if path_control is not None and path_control.strength == "strong"
                else None
            )
            prefix_check = (
                path_control
                if path_control is not None and path_control.strength == "weak-prefix"
                else None
            )
            self.add_capability(
                "filesystem",
                node,
                {
                    "api": call_name,
                    "canonical_api": canonical_api,
                    "possible_apis": canonical_api.split("|"),
                    "callable_alias": local_filesystem_callable is not None,
                    "receiver_proof": receiver_proof,
                    "write_access": True,
                    "dynamic_path": not isinstance(path_expression, ast.Constant),
                    "operation": filesystem_spec.operation,
                    "path_role": filesystem_spec.path_role,
                    "path_boundary_guard": boundary is not None,
                    "path_boundary_scope": (
                        boundary.boundary_scope if boundary is not None else "unresolved"
                    ),
                    "path_prefix_check": prefix_check is not None,
                },
            )
            if boundary is not None:
                self.add_python_path_boundary_control(node, boundary)
            if prefix_check is not None:
                self.add_python_path_prefix_control(node, prefix_check)
        elif short_name in {"open", "write_text", "write_bytes", "unlink", "rmdir", "mkdir"}:
            path_expression = node.args[0] if short_name == "open" and node.args else None
            mode_expression = node.args[1] if short_name == "open" and len(node.args) > 1 else None
            for keyword in node.keywords:
                if short_name == "open" and keyword.arg == "mode":
                    mode_expression = keyword.value
            mode = str(mode_expression.value) if isinstance(mode_expression, ast.Constant) else "r"
            write_access = short_name != "open" or any(flag in mode for flag in "wax+")
            dynamic_path = short_name != "open" or not isinstance(path_expression, ast.Constant)
            path_control = (
                self.function_path_boundary_calls[-1].get(id(node))
                if self.function_path_boundary_calls and write_access
                else None
            )
            boundary = (
                path_control
                if path_control is not None and path_control.strength == "strong"
                else None
            )
            prefix_check = (
                path_control
                if path_control is not None and path_control.strength == "weak-prefix"
                else None
            )
            self.add_capability(
                "filesystem",
                node,
                {
                    "api": call_name,
                    "write_access": write_access,
                    "dynamic_path": dynamic_path,
                    "path_boundary_guard": boundary is not None,
                    "path_boundary_scope": (
                        boundary.boundary_scope if boundary is not None else "unresolved"
                    ),
                    "path_prefix_check": prefix_check is not None,
                },
            )
            if boundary is not None:
                self.add_python_path_boundary_control(node, boundary)
            if prefix_check is not None:
                self.add_python_path_prefix_control(node, prefix_check)
        root_name = call_name.split(".", 1)[0]
        http_method = short_name.lower() in {"get", "post", "put", "patch", "delete", "request"}
        if http_method and (
            root_name in {"requests", "httpx", "aiohttp"}
            or (self.has_http_import and root_name in self.http_client_names)
        ):
            url_expression = None
            if short_name.lower() == "request":
                if len(node.args) > 1:
                    url_expression = node.args[1]
            elif node.args:
                url_expression = node.args[0]
            for keyword in node.keywords:
                if keyword.arg == "url":
                    url_expression = keyword.value
            self.add_capability(
                "network",
                node,
                {
                    "api": call_name,
                    "dynamic_origin": python_http_origin_is_dynamic(
                        url_expression, self.dynamic_http_origin_names
                    ),
                },
            )
            if short_name.lower() in {"post", "put", "patch", "delete"}:
                self.add_capability("external-action", node, {"api": call_name})
        if self.has_browser_import and short_name in {
            "click",
            "goto",
            "navigate",
            "fill",
            "press",
            "select_option",
        }:
            self.add_capability("browser", node, {"api": call_name})
        self.generic_visit(node)


def scan_python(
    ir: RepositoryIR,
    root: Path,
    path: Path,
    text: str,
    module_paths: dict[str, str],
    registry_class_exports: dict[tuple[str, str], RegistryClassTarget],
    registered_tool_functions: dict[tuple[str, str], PythonToolRegistration],
) -> None:
    relative = path.relative_to(root).as_posix()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text, filename=relative)
    except SyntaxError as error:
        ir.errors.append(f"{relative}:{error.lineno}: {error.msg}")
        return
    nodes = list(ast.walk(tree))
    imported_modules = {
        alias.name for node in nodes if isinstance(node, ast.Import) for alias in node.names
    } | {node.module or "" for node in nodes if isinstance(node, ast.ImportFrom)}
    imported_bindings = {
        alias.asname or alias.name.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    module_mutations: set[str] = set()

    def collect_module_mutations(candidate: ast.AST) -> None:
        if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_mutations.add(candidate.name)
            return
        if isinstance(candidate, (ast.Import, ast.ImportFrom, ast.Lambda)):
            return
        if isinstance(candidate, ast.Name) and isinstance(candidate.ctx, (ast.Store, ast.Del)):
            module_mutations.add(candidate.id)
        for child in ast.iter_child_nodes(candidate):
            collect_module_mutations(child)

    for statement in tree.body:
        if not isinstance(statement, (ast.Import, ast.ImportFrom)):
            collect_module_mutations(statement)
    module_mutations.update(
        name for candidate in nodes if isinstance(candidate, ast.Global) for name in candidate.names
    )
    module_rebound_names = imported_bindings & module_mutations
    path_constructors = {
        alias.asname or alias.name
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom) and statement.module == "pathlib"
        for alias in statement.names
        if alias.name == "Path"
    } | {
        f"{alias.asname or alias.name}.Path"
        for statement in tree.body
        if isinstance(statement, ast.Import)
        for alias in statement.names
        if alias.name == "pathlib"
    }
    path_constructors = {
        constructor
        for constructor in path_constructors
        if constructor.split(".", 1)[0] not in module_rebound_names
    }
    filesystem_api_aliases = {
        alias.asname or alias.name: alias.name
        for statement in tree.body
        if isinstance(statement, ast.Import)
        for alias in statement.names
        if alias.name in {"os", "shutil"}
    }
    filesystem_api_aliases.update(
        {
            alias.asname or alias.name: f"{statement.module}.{alias.name}"
            for statement in tree.body
            if isinstance(statement, ast.ImportFrom)
            and statement.module in {"os", "shutil"}
            for alias in statement.names
            if f"{statement.module}.{alias.name}"
            in PYTHON_FILESYSTEM_WRITE_FUNCTIONS
        }
    )
    filesystem_api_aliases = {
        alias: canonical
        for alias, canonical in filesystem_api_aliases.items()
        if alias.split(".", 1)[0] not in module_rebound_names
    }
    symbol_candidates: dict[tuple[str, str], set[str]] = {}
    call_symbol_ids: dict[int, str] = {}
    definition_symbol_ids: dict[int, str] = {}
    decorated_tools: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]] = []

    def collect_definitions(
        statements: list[ast.stmt],
        class_stack: tuple[str, ...] = (),
        *,
        module_scope: bool = True,
    ) -> None:
        for node in statements:
            if isinstance(node, ast.ClassDef):
                collect_definitions(
                    node.body,
                    (*class_stack, node.name),
                    module_scope=False,
                )
                continue
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = {
                dotted_name(decorator.func)
                if isinstance(decorator, ast.Call)
                else dotted_name(decorator)
                for decorator in node.decorator_list
            }
            if (
                decorators & TOOL_DECORATORS
                or any(name.endswith(".tool") for name in decorators)
                or (
                    module_scope
                    and (relative, node.name) in registered_tool_functions
                )
            ):
                qualified_name = ".".join([*class_stack, node.name])
                decorated_tools.append((node, qualified_name))
            collect_definitions(node.body, class_stack, module_scope=False)

    collect_definitions(tree.body)
    definition_counts = Counter(qualified_name for _, qualified_name in decorated_tools)
    for node, qualified_name in decorated_tools:
        identity = (
            f"{qualified_name}@{node.lineno}"
            if definition_counts[qualified_name] > 1
            else qualified_name
        )
        symbol_id = source_symbol("py", relative, "tool", identity)
        symbol_candidates.setdefault(("tool", qualified_name), set()).add(symbol_id)
        symbol_candidates.setdefault(("tool", node.name), set()).add(symbol_id)
        definition_symbol_ids[id(node)] = symbol_id
    assigned_constructors: list[tuple[ast.Assign, str, str]] = []
    for node in nodes:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            binding = node.targets[0].id
            short_name = dotted_name(node.value.func).rsplit(".", 1)[-1]
            kind = (
                "agent"
                if short_name in AGENT_CALLS
                else "tool"
                if short_name in BUILTIN_TOOL_CAPABILITIES
                else None
            )
            if kind:
                assigned_constructors.append((node, kind, binding))
    assignment_counts = Counter((kind, binding) for _, kind, binding in assigned_constructors)
    for node, kind, binding in assigned_constructors:
        identity = f"{binding}@{node.lineno}" if assignment_counts[(kind, binding)] > 1 else binding
        symbol_id = source_symbol("py", relative, kind, identity)
        symbol_candidates.setdefault((kind, binding), set()).add(symbol_id)
        call_symbol_ids[id(node.value)] = symbol_id
    local_symbol_ids = {
        key: next(iter(candidates))
        for key, candidates in symbol_candidates.items()
        if len(candidates) == 1
    }
    ambiguous_local_symbols = {
        key for key, candidates in symbol_candidates.items() if len(candidates) > 1
    }
    scoped_symbol_candidates: dict[tuple[tuple[str, ...], str, str], list[tuple[int, str]]] = {}
    node_scopes: dict[int, tuple[str, ...]] = {}
    if ambiguous_local_symbols:
        parent_by_id = {
            id(child): parent for parent in nodes for child in ast.iter_child_nodes(parent)
        }
        scope_cache: dict[int, tuple[str, ...]] = {id(tree): ()}

        def lexical_scope(node: ast.AST) -> tuple[str, ...]:
            node_id = id(node)
            if node_id in scope_cache:
                return scope_cache[node_id]
            parent = parent_by_id.get(node_id)
            if parent is None:
                scope = ()
            else:
                scope = lexical_scope(parent)
                if isinstance(parent, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    scope = (*scope, parent.name)
            scope_cache[node_id] = scope
            return scope

        scope_nodes = [
            node
            for node in nodes
            if isinstance(node, (ast.Assign, ast.FunctionDef, ast.AsyncFunctionDef))
            or (
                isinstance(node, ast.Call)
                and dotted_name(node.func).rsplit(".", 1)[-1] in AGENT_CALLS
            )
        ]
        node_scopes = {id(node): lexical_scope(node) for node in scope_nodes}
        for node, qualified_name in decorated_tools:
            if not isinstance(
                parent_by_id.get(id(node)),
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue
            for name in {qualified_name, node.name}:
                scoped_symbol_candidates.setdefault(
                    (node_scopes[id(node)], "tool", name), []
                ).append((node.lineno, definition_symbol_ids[id(node)]))
        for node, kind, binding in assigned_constructors:
            if not isinstance(
                parent_by_id.get(id(node)),
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue
            scoped_symbol_candidates.setdefault((node_scopes[id(node)], kind, binding), []).append(
                (node.lineno, call_symbol_ids[id(node.value)])
            )
    scoped_symbol_ids = {
        key: candidates[0]
        for key, candidates in scoped_symbol_candidates.items()
        if len(candidates) == 1
    }
    PythonVisitor(
        ir,
        root,
        relative,
        text.splitlines(),
        imported_modules=imported_modules,
        module_paths=module_paths,
        local_symbol_ids=local_symbol_ids,
        ambiguous_local_symbols=ambiguous_local_symbols,
        scoped_symbol_ids=scoped_symbol_ids,
        node_scopes=node_scopes,
        call_symbol_ids=call_symbol_ids,
        definition_symbol_ids=definition_symbol_ids,
        registry_class_exports=registry_class_exports,
        registered_tool_functions=registered_tool_functions,
        module_rebound_names=module_rebound_names,
        path_constructors=path_constructors,
        filesystem_api_aliases=filesystem_api_aliases,
    ).visit(tree)


TS_IMPORT = re.compile(r"(?:from\s+|require\s*\(\s*)['\"]([^'\"]+)['\"]")
TS_NAMED_IMPORT = re.compile(r"\bimport\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]", re.DOTALL)
TS_AGENT = re.compile(r"\b(?:new\s+)?(Agent|AssistantAgent|StateGraph|Crew)\s*\(")
TS_MCP = re.compile(r"\b(McpServer|Client|StdioClientTransport)\s*\(")
TS_SHELL = re.compile(r"\b(exec|execSync|spawn|spawnSync)\s*\((.+)")
TS_CHILD_PROCESS_IMPORT = re.compile(
    r"import\s*\{([^}]+)\}\s*from\s*['\"](?:node:)?child_process['\"]",
    re.DOTALL,
)
TS_TOOL_ASSIGNMENT = re.compile(r"\b(?:const|let)\s+(\w+)\s*=\s*([A-Za-z_$][\w$]*)\s*\(")
TS_TOOL_PROPERTY = re.compile(r"\b([A-Za-z_$][\w$]*)\s*:\s*([A-Za-z_$][\w$]*)\s*\(")
TS_MCP_TOOL_REGISTRATION = re.compile(r"\b([A-Za-z_$][\w$]*)\.registerTool\s*\(")
TS_AGENT_TOOL_ASSIGNMENT = re.compile(
    r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"([A-Za-z_$][\w$]*)\.asTool\s*\("
)
TS_AGENT_ASSIGNMENT = re.compile(r"\b(?:const|let)\s+(\w+)\s*=\s*new\s+Agent\s*\(")
TS_LITERAL_APPROVAL = re.compile(r"\bneedsApproval\s*:\s*true\b")
TS_AUTO_APPROVAL_ENABLED = re.compile(
    r"\b(?:autoApprove|auto_approve|skipConfirmation|skip_confirmation|"
    r"dangerouslySkip(?:Permissions?|Confirmation|Approval)|"
    r"dangerously_skip_(?:permissions?|confirmation|approval))\b"
    r"\s*(?:=|:)\s*(?:true|['\"](?:1|true|all)['\"])",
    re.IGNORECASE,
)
TS_APPROVAL_ENV_COMPARISON = re.compile(
    r"\bprocess\.env(?:\.([A-Za-z_$][\w$]*)|\[\s*['\"]([^'\"]+)['\"]\s*\])"
    r"\s*(?:===|==)\s*['\"](?:1|true|yes|all)['\"]",
    re.IGNORECASE,
)
TS_APPROVAL_ENV_ASSIGNMENT = re.compile(
    r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"process\.env(?:\.([A-Za-z_$][\w$]*)|\[\s*['\"]([^'\"]+)['\"]\s*\])"
    r"\s*(?:===|==)\s*['\"](?:1|true|yes|all)['\"]",
    re.IGNORECASE,
)
TS_MODEL_SETTING = re.compile(r"\bmodel\s*:\s*['\"]([^'\"]+)['\"]")
TS_PROVIDER_MODEL_CALL = re.compile(r"\b(openai|anthropic|azure)\s*\(\s*['\"]([^'\"]+)['\"]")
TS_MCP_DYNAMIC_CALL = re.compile(
    r"\.callTool\s*\(\s*\{[^}]*\bname\s*:\s*(?!['\"])([\w$.]+)[^}]*"
    r"\b(?:arguments|params)\s*:\s*([\w$.]+)",
    re.IGNORECASE,
)
TS_FILESYSTEM_WRITE = re.compile(
    r"\b(?:writeFile|unlink|rm|rmdir|mkdir)(?:Sync)?\s*\(\s*([^,\n)]+)"
)
TS_DYNAMIC_EVAL = re.compile(r"(?<![\w$.])eval\s*\(|\bnew\s+Function\s*\(")
TS_BUN_SHELL = re.compile(
    r"\bBun\.spawn\s*\(\s*\[\s*['\"](?:sh|bash|zsh)['\"]\s*,\s*"
    r"['\"]-c['\"]\s*,\s*([^,\]\n]+)"
)
TS_GENERIC_TOOL_FACTORIES = {"tool", "functionTool", "toolNamespace"}
TS_OPENAI_BUILTIN_TOOL_CAPABILITIES = {
    "applyPatchTool": ("filesystem",),
    "codeInterpreterTool": ("code-execution",),
    "computerTool": ("computer-control",),
    "fileSearchTool": ("filesystem",),
    "hostedMcpTool": ("mcp-access",),
    "imageGenerationTool": ("external-action",),
    "programmaticToolCallingTool": ("dynamic-tool-orchestration",),
    "shellTool": ("shell-execution",),
    "toolSearchTool": ("dynamic-tool-discovery",),
    "webSearchTool": ("external-action",),
    "codexTool": ("code-execution",),
}
TS_OPENAI_APPROVAL_BUILTINS = {"applyPatchTool", "computerTool", "shellTool"}
CONTAINER_CONFIG_SUFFIXES = {".yml", ".yaml"}
INLINE_SUPPRESSION = re.compile(
    r"^\s*(?:#|//)\s*agentverify:\s*ignore\s+(AV-[A-Z0-9]+)"
    r"(?:\s+until\s+(\S+))?\s+--\s+(\S(?:.*\S)?)\s*$"
)


@dataclass(frozen=True)
class TypeScriptHelperParameter:
    index: int
    local_name: str
    property_name: str | None = None


@dataclass(frozen=True)
class TypeScriptNetworkHelperSummary:
    name: str
    line: int
    parameters: tuple[TypeScriptHelperParameter, ...]
    controlled_names: frozenset[str]
    network_calls: int


@dataclass(frozen=True)
class TypeScriptPathBoundaryHelper:
    name: str
    evidence: Evidence
    predicate_path: str
    boundary_scope: str


def line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def balanced_call_end(text: str, opening_parenthesis: int) -> int:
    code = typescript_code_mask(text)
    depth = 0
    for index in range(opening_parenthesis, len(code)):
        character = code[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    return len(text)


def typescript_code_mask(text: str) -> str:
    """Mask comments and string contents while preserving offsets and newlines."""
    masked = list(text)
    index = 0
    state = "code"
    quote = ""
    regex_character_class = False

    def regex_can_start(position: int) -> bool:
        previous = position - 1
        while previous >= 0 and text[previous].isspace():
            previous -= 1
        if previous < 0 or text[previous] in "([{=:;,!?&|+-*%^~<>":
            return True
        prefix = text[max(0, previous - 16) : position]
        return bool(re.search(r"(?:\b(?:return|throw|case|yield)|=>)\s*$", prefix))

    while index < len(text):
        character = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if character == "/" and following == "/":
                masked[index] = masked[index + 1] = " "
                index += 2
                state = "line-comment"
                continue
            if character == "/" and following == "*":
                masked[index] = masked[index + 1] = " "
                index += 2
                state = "block-comment"
                continue
            if character == "/" and regex_can_start(index):
                masked[index] = " "
                state = "regex"
                regex_character_class = False
                index += 1
                continue
            if character in {"'", '"', "`"}:
                masked[index] = " "
                quote = character
                state = "string"
        elif state == "line-comment":
            if character == "\n":
                state = "code"
            else:
                masked[index] = " "
        elif state == "block-comment":
            if character == "*" and following == "/":
                masked[index] = masked[index + 1] = " "
                index += 2
                state = "code"
                continue
            if character != "\n":
                masked[index] = " "
        elif state == "string":
            if character == "\\":
                masked[index] = " "
                if index + 1 < len(text):
                    if text[index + 1] != "\n":
                        masked[index + 1] = " "
                    index += 2
                    continue
            elif character == quote:
                masked[index] = " "
                state = "code"
            elif character != "\n":
                masked[index] = " "
        else:
            if character == "\\":
                masked[index] = " "
                if index + 1 < len(text):
                    if text[index + 1] != "\n":
                        masked[index + 1] = " "
                    index += 2
                    continue
            elif character == "[":
                regex_character_class = True
                masked[index] = " "
            elif character == "]":
                regex_character_class = False
                masked[index] = " "
            elif character == "/" and not regex_character_class:
                masked[index] = " "
                state = "code"
            elif character == "\n":
                state = "code"
            else:
                masked[index] = " "
        index += 1
    return "".join(masked)


def typescript_balanced_end(
    code: str, opening_index: int, opening_character: str, closing_character: str
) -> int | None:
    """Return one-past the matching delimiter in already-masked TypeScript code."""
    depth = 0
    for index in range(opening_index, len(code)):
        character = code[index]
        if character == opening_character:
            depth += 1
        elif character == closing_character:
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def typescript_direct_true_return(code: str, consequent_start: int) -> bool:
    """Require an unconditional true return in the immediate TypeScript branch."""
    cursor = consequent_start
    while cursor < len(code) and code[cursor].isspace():
        cursor += 1
    if cursor >= len(code):
        return False
    if code[cursor] != "{":
        return bool(re.match(r"return\s+true\b", code[cursor:]))
    block_end = typescript_balanced_end(code, cursor, "{", "}")
    if block_end is None:
        return False
    body = code[cursor + 1 : block_end - 1]
    depth = 0
    blocked = False
    token = re.compile(r"[{}]|\b(?:if|switch|for|while|try|return)\b")
    for match in token.finditer(body):
        value = match.group(0)
        if value == "{":
            depth += 1
        elif value == "}":
            depth = max(0, depth - 1)
        elif depth == 0 and value in {"if", "switch", "for", "while", "try"}:
            blocked = True
        elif depth == 0 and value == "return":
            return not blocked and bool(re.match(r"\s+true\b", body[match.end() :]))
    return False


def typescript_environment_approval_guards(text: str) -> list[tuple[int, list[str]]]:
    """Locate env-backed approval flags whose immediate branch returns true."""
    code = typescript_code_mask(text)
    flags: dict[str, str] = {}
    for match in TS_APPROVAL_ENV_ASSIGNMENT.finditer(text):
        if not code[match.start() : match.start() + len("const")].strip():
            continue
        if code[: match.start()].count("{") != code[: match.start()].count("}"):
            continue
        flag_name = match.group(1)
        environment_name = match.group(2) or match.group(3) or ""
        if APPROVAL_BYPASS_ENV_NAME.search(flag_name) and APPROVAL_BYPASS_ENV_NAME.search(
            environment_name
        ):
            flags[flag_name] = environment_name

    guards: list[tuple[int, list[str]]] = []
    for match in re.finditer(r"\bif\s*\(", code):
        opening = code.find("(", match.start(), match.end())
        condition_end = typescript_balanced_end(code, opening, "(", ")")
        if condition_end is None or not typescript_direct_true_return(code, condition_end):
            continue
        condition_start = opening + 1
        condition_text = text[condition_start : condition_end - 1]
        condition_code = code[condition_start : condition_end - 1]
        environment_names: set[str] = set()
        for environment_match in TS_APPROVAL_ENV_COMPARISON.finditer(condition_text):
            absolute = condition_start + environment_match.start()
            if not code[absolute : absolute + len("process")].strip():
                continue
            environment_name = environment_match.group(1) or environment_match.group(2) or ""
            if APPROVAL_BYPASS_ENV_NAME.search(environment_name):
                environment_names.add(environment_name)
        for flag_name, environment_name in flags.items():
            if re.search(rf"\b{re.escape(flag_name)}\b", condition_code):
                environment_names.add(environment_name)
        if environment_names:
            guards.append((match.start(), sorted(environment_names)))
    return guards


def typescript_top_level_items(text: str, start_offset: int = 0) -> list[tuple[str, int]]:
    """Split a TypeScript array body on top-level commas without tokenizing nested values."""
    code = typescript_code_mask(text)
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    item_start = 0
    items: list[tuple[str, int]] = []

    def append_item(end: int) -> None:
        code_value = code[item_start:end]
        structural_start = re.search(r"\S", code_value)
        if structural_start:
            leading = structural_start.start()
            items.append(
                (text[item_start + leading : end].rstrip(), start_offset + item_start + leading)
            )

    for index, character in enumerate(code):
        if character in depths:
            depths[character] += 1
        elif character in closing and depths[closing[character]]:
            depths[closing[character]] -= 1
        elif character == "," and not any(depths.values()):
            append_item(index)
            item_start = index + 1
    append_item(len(text))
    return items


def typescript_call_arguments(text: str, start_offset: int = 0) -> list[tuple[str, int]]:
    """Split call arguments while retaining literal-only arguments and source offsets."""
    code = typescript_code_mask(text)
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    argument_start = 0
    arguments: list[tuple[str, int]] = []

    def append_argument(end: int) -> None:
        value = text[argument_start:end]
        leading = len(value) - len(value.lstrip())
        value = value.strip()
        if value:
            arguments.append((value, start_offset + argument_start + leading))

    for index, character in enumerate(code):
        if character in depths:
            depths[character] += 1
        elif character in closing and depths[closing[character]]:
            depths[closing[character]] -= 1
        elif character == "," and not any(depths.values()):
            append_argument(index)
            argument_start = index + 1
    append_argument(len(text))
    return arguments


def typescript_object_items(body: str, body_offset: int = 0) -> list[tuple[str, int]]:
    """Extract top-level properties from a literal object passed as a call argument."""
    code = typescript_code_mask(body)
    opening = len(code) - len(code.lstrip())
    if opening >= len(code) or code[opening] != "{":
        return []
    end = typescript_balanced_end(code, opening, "{", "}")
    if end is None:
        return []
    return typescript_top_level_items(body[opening + 1 : end - 1], body_offset + opening + 1)


def typescript_agent_tool_items(body: str, body_offset: int) -> list[tuple[str, int]]:
    """Extract only the top-level entries of an Agent's literal tools array."""
    for property_text, property_offset in typescript_object_items(body, body_offset):
        code = typescript_code_mask(property_text)
        match = re.match(r"\s*tools\s*:\s*\[", code)
        if not match:
            continue
        opening = match.end() - 1
        end = typescript_balanced_end(code, opening, "[", "]")
        if end is None:
            return []
        return typescript_top_level_items(
            property_text[opening + 1 : end - 1], property_offset + opening + 1
        )
    return []


def typescript_object_string_property(body: str, name: str) -> str | None:
    """Resolve one direct literal string property without inspecting nested objects."""
    value = typescript_object_property_expression(body, name)
    if value is None:
        return None
    match = re.fullmatch(r"(['\"])(.*?)\1", value, re.DOTALL)
    return match.group(2) if match else None


def typescript_object_property_expression(body: str, name: str) -> str | None:
    """Return one unambiguous direct property expression from a literal object."""
    values = []
    for property_text, _ in typescript_object_items(body):
        match = re.match(rf"\s*{re.escape(name)}\s*:", typescript_code_mask(property_text))
        if match:
            values.append(property_text[match.end() :].strip())
    return values[0] if len(values) == 1 else None


def typescript_named_import_bindings(text: str, module_prefix: str) -> dict[str, str]:
    """Return local-to-exported names for named imports under one module prefix."""
    bindings: dict[str, str] = {}
    for match in TS_NAMED_IMPORT.finditer(text):
        module = match.group(2)
        if module != module_prefix and not module.startswith(f"{module_prefix}/"):
            continue
        for imported in match.group(1).split(","):
            parts = imported.strip().removeprefix("type ").split()
            if not parts:
                continue
            original = parts[0]
            local = parts[2] if len(parts) >= 3 and parts[1] == "as" else original
            bindings[local] = original
    return bindings


def typescript_literal_string_bindings(text: str) -> dict[str, str]:
    """Resolve direct module-local const/let string bindings outside comments and strings."""
    code = typescript_code_mask(text)
    candidates: dict[str, list[str]] = defaultdict(list)
    pattern = re.compile(
        r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(['\"])(.*?)\2",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        if code[match.start() : match.start(1)].strip():
            candidates[match.group(1)].append(match.group(3))
    return {name: values[0] for name, values in candidates.items() if len(values) == 1}


def typescript_destructured_names(parameter: str) -> set[str]:
    """Return local binding names from one shallow object-destructuring parameter."""
    code = typescript_code_mask(parameter)
    opening = code.find("{")
    if opening < 0:
        return set()
    end = typescript_balanced_end(code, opening, "{", "}")
    if end is None:
        return set()
    names = set()
    for item, _ in typescript_call_arguments(parameter[opening + 1 : end - 1]):
        value = item.lstrip(".").split("=", 1)[0].strip()
        if ":" in value:
            value = value.split(":", 1)[1].strip()
        if match := re.match(r"[A-Za-z_$][\w$]*", value):
            names.add(match.group(0))
    return names


def typescript_callback_parameter_names(expression: str) -> set[str]:
    """Extract model-input roots from a direct arrow/function callback expression."""
    code = typescript_code_mask(expression)
    arrow = code.find("=>")
    prefix = expression[:arrow].strip() if arrow >= 0 else expression.strip()
    prefix = re.sub(r"^async\s+", "", prefix).strip()
    if prefix.startswith("("):
        prefix_code = typescript_code_mask(prefix)
        end = typescript_balanced_end(prefix_code, 0, "(", ")")
        if end is None:
            return set()
        parameters = typescript_call_arguments(prefix[1 : end - 1])
        first = parameters[0][0] if parameters else ""
    else:
        first = prefix.split(":", 1)[0].strip()
    if first.lstrip().startswith("{"):
        return typescript_destructured_names(first)
    match = re.match(r"[A-Za-z_$][\w$]*", first)
    return {match.group(0)} if match else set()


def typescript_tool_parameter_names(call_body: str, constructor: str) -> set[str]:
    """Extract the first execution-callback parameter for a supported tool form."""
    if constructor == "registerTool":
        arguments = typescript_call_arguments(call_body)
        return (
            typescript_callback_parameter_names(arguments[2][0]) if len(arguments) >= 3 else set()
        )
    if execute := typescript_object_property_expression(call_body, "execute"):
        return typescript_callback_parameter_names(execute)
    code = typescript_code_mask(call_body)
    if match := re.search(r"\b(?:async\s+)?execute\s*\(", code):
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")")
        if end is not None:
            return typescript_callback_parameter_names(f"({call_body[opening + 1 : end - 1]}) =>")
    return set()


def typescript_static_url_prefix(expression: str, literal_bindings: dict[str, str]) -> str:
    value = expression.strip()
    if match := re.match(r"(['\"])(.*?)\1", value, re.DOTALL):
        return match.group(2)
    if value.startswith("`"):
        content = value[1:]
        if not content.startswith("${"):
            return content.split("${", 1)[0]
        if match := re.match(r"\$\{\s*([A-Za-z_$][\w$]*)\s*\}(.*)", content, re.DOTALL):
            return literal_bindings.get(match.group(1), "") + match.group(2).split("${", 1)[0]
    if match := re.match(r"([A-Za-z_$][\w$]*)\b", value):
        return literal_bindings.get(match.group(1), "")
    return ""


def typescript_expression_names(expression: str) -> set[str]:
    value = expression.strip()
    if value.startswith("`"):
        return set(
            re.findall(
                r"(?<![\w$])[A-Za-z_$][\w$]*",
                " ".join(re.findall(r"\$\{(.*?)\}", value, re.DOTALL)),
            )
        )
    code = typescript_code_mask(value)
    return set(re.findall(r"(?<![\w$])[A-Za-z_$][\w$]*", code))


def typescript_http_origin_is_dynamic(
    expression: str,
    dynamic_names: set[str],
    literal_bindings: dict[str, str],
) -> bool:
    if not typescript_expression_names(expression) & dynamic_names:
        return False
    prefix = typescript_static_url_prefix(expression, literal_bindings)
    return re.match(r"^https?://[^/?#]+", prefix, re.IGNORECASE) is None


def typescript_update_dynamic_names(
    line: str,
    dynamic_names: set[str],
    literal_bindings: dict[str, str],
) -> None:
    """Apply one shallow TypeScript assignment to callback-local origin taint."""
    code_line = typescript_code_mask(line)
    if destructuring := re.search(r"\b(?:const|let)\s*\{([^}]*)\}\s*=\s*([^;]+)", code_line):
        source_expression = line[destructuring.start(2) : destructuring.end(2)]
        if typescript_expression_names(source_expression) & dynamic_names:
            dynamic_names.update(
                typescript_destructured_names(
                    "{" + line[destructuring.start(1) : destructuring.end(1)] + "}"
                )
            )
        return
    if assignment := re.search(
        r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)"
        r"(?:\s*:[^=]+)?\s*=",
        code_line,
    ):
        value = line[assignment.end() :].rstrip().removesuffix(";").rstrip()
        if typescript_http_origin_is_dynamic(value, dynamic_names, literal_bindings):
            dynamic_names.add(assignment.group(1))
        else:
            dynamic_names.discard(assignment.group(1))


def typescript_multiline_destructuring_assignments(
    text: str,
) -> dict[int, list[tuple[set[str], str]]]:
    """Collect shallow destructuring assignments that span more than one line."""
    code = typescript_code_mask(text)
    assignments: dict[int, list[tuple[set[str], str]]] = defaultdict(list)
    pattern = re.compile(r"\b(?:const|let)\s*\{([^{}]*)\}\s*=\s*([^;]+)", re.DOTALL)
    for match in pattern.finditer(code):
        if "\n" not in text[match.start() : match.end()]:
            continue
        names = typescript_destructured_names("{" + text[match.start(1) : match.end(1)] + "}")
        source_expression = text[match.start(2) : match.end(2)]
        assignments[line_at(text, match.start())].append((names, source_expression))
    return assignments


def typescript_apply_destructuring_assignments(
    assignments: list[tuple[set[str], str]], dynamic_names: set[str]
) -> None:
    for names, source_expression in assignments:
        if typescript_expression_names(source_expression) & dynamic_names:
            dynamic_names.update(names)


def typescript_network_calls(text: str) -> dict[int, list[tuple[str, str]]]:
    """Return recognized global fetch/Axios calls with their first URL argument."""
    code = typescript_code_mask(text)
    pattern = re.compile(r"(?<![\w$.])fetch\s*\(|\baxios\.(get|post|put|patch|delete)\s*\(")
    calls: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for match in pattern.finditer(code):
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")")
        if end is None:
            continue
        arguments = typescript_call_arguments(text[opening + 1 : end - 1])
        if not arguments:
            continue
        api = f"axios.{match.group(1)}" if match.group(1) else "fetch"
        calls[line_at(text, match.start())].append((api, arguments[0][0]))
    return calls


def typescript_function_parameters(parameter_text: str) -> tuple[TypeScriptHelperParameter, ...]:
    parameters: list[TypeScriptHelperParameter] = []
    for index, (parameter, _) in enumerate(typescript_call_arguments(parameter_text)):
        value = parameter.strip()
        if value.startswith("{"):
            code = typescript_code_mask(value)
            end = typescript_balanced_end(code, 0, "{", "}")
            if end is None:
                continue
            for item, _ in typescript_call_arguments(value[1 : end - 1]):
                binding = item.lstrip(".").split("=", 1)[0].strip()
                if ":" in binding:
                    property_name, local_value = binding.split(":", 1)
                    property_name = property_name.strip()
                    local_value = local_value.strip()
                else:
                    property_name = local_value = binding
                property_match = re.match(r"[A-Za-z_$][\w$]*", property_name)
                local_match = re.match(r"[A-Za-z_$][\w$]*", local_value)
                if property_match and local_match:
                    parameters.append(
                        TypeScriptHelperParameter(
                            index, local_match.group(0), property_match.group(0)
                        )
                    )
            continue
        if match := re.match(r"[A-Za-z_$][\w$]*", value.removeprefix("...")):
            parameters.append(TypeScriptHelperParameter(index, match.group(0)))
    return tuple(parameters)


def typescript_function_definitions(
    text: str,
) -> list[tuple[str, int, tuple[TypeScriptHelperParameter, ...], str]]:
    """Return bounded free/static function bodies with structurally balanced signatures."""
    code = typescript_code_mask(text)
    patterns = (
        re.compile(r"\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\("),
        re.compile(r"\bstatic\s+(?:async\s+)?([A-Za-z_$][\w$]*)\s*\("),
    )
    matches = sorted(
        (match for pattern in patterns for match in pattern.finditer(code)),
        key=lambda match: match.start(),
    )
    definitions = []
    for match in matches:
        opening = code.find("(", match.start(), match.end())
        parameter_end = typescript_balanced_end(code, opening, "(", ")")
        if parameter_end is None:
            continue
        body_opening = code.find("{", parameter_end)
        if body_opening < 0 or body_opening - parameter_end > 500:
            continue
        terminator = code.find(";", parameter_end, body_opening)
        if terminator >= 0:
            continue
        body_end = typescript_balanced_end(code, body_opening, "{", "}")
        if body_end is None:
            continue
        definitions.append(
            (
                match.group(1),
                line_at(text, match.start()),
                typescript_function_parameters(text[opening + 1 : parameter_end - 1]),
                text[body_opening + 1 : body_end - 1],
            )
        )
    return definitions


def typescript_network_helper_summaries(
    text: str, literal_bindings: dict[str, str]
) -> dict[str, TypeScriptNetworkHelperSummary]:
    definitions = typescript_function_definitions(text)
    name_counts = Counter(name for name, _, _, _ in definitions)
    summaries = {}
    for name, line, parameters, body in definitions:
        if name_counts[name] != 1:
            continue
        calls = typescript_network_calls(body)
        if not calls:
            continue
        destructuring_assignments = typescript_multiline_destructuring_assignments(body)
        controlled_names = set()
        for parameter in parameters:
            dynamic_names = {parameter.local_name}
            for body_line_number, body_line in enumerate(body.splitlines(), start=1):
                typescript_apply_destructuring_assignments(
                    destructuring_assignments.get(body_line_number, []), dynamic_names
                )
                typescript_update_dynamic_names(body_line, dynamic_names, literal_bindings)
                if any(
                    typescript_http_origin_is_dynamic(expression, dynamic_names, literal_bindings)
                    for _, expression in calls.get(body_line_number, [])
                ):
                    controlled_names.add(parameter.local_name)
        summaries[name] = TypeScriptNetworkHelperSummary(
            name,
            line,
            parameters,
            frozenset(controlled_names),
            sum(len(items) for items in calls.values()),
        )
    return summaries


def typescript_helper_calls(
    text: str, summaries: dict[str, TypeScriptNetworkHelperSummary]
) -> dict[int, list[tuple[TypeScriptNetworkHelperSummary, list[str]]]]:
    if not summaries:
        return {}
    code = typescript_code_mask(text)
    names = "|".join(re.escape(name) for name in sorted(summaries, key=len, reverse=True))
    pattern = re.compile(rf"(?<![\w$])(?:[A-Za-z_$][\w$]*\.)*({names})\s*\(")
    calls: dict[int, list[tuple[TypeScriptNetworkHelperSummary, list[str]]]] = defaultdict(list)
    for match in pattern.finditer(code):
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")")
        if end is None:
            continue
        arguments = [
            argument for argument, _ in typescript_call_arguments(text[opening + 1 : end - 1])
        ]
        calls[line_at(text, match.start())].append((summaries[match.group(1)], arguments))
    return calls


def typescript_helper_argument_expression(
    arguments: list[str], parameter: TypeScriptHelperParameter
) -> str | None:
    if parameter.index >= len(arguments):
        return None
    argument = arguments[parameter.index]
    if parameter.property_name is None:
        return argument
    if value := typescript_object_property_expression(argument, parameter.property_name):
        return value
    for item, _ in typescript_object_items(argument):
        code = typescript_code_mask(item).strip()
        if code == parameter.property_name:
            return item.strip()
        if code.startswith("..."):
            return item[3:].strip()
    return None


def typescript_unique_function_definition(
    text: str, name: str
) -> tuple[int, tuple[TypeScriptHelperParameter, ...], str] | None:
    definitions = [
        (line, parameters, body)
        for function_name, line, parameters, body in typescript_function_definitions(text)
        if function_name == name
    ]
    return definitions[0] if len(definitions) == 1 else None


def typescript_is_path_boundary_predicate(text: str, name: str) -> bool:
    """Recognize a separator-aware normalized path-within-roots predicate."""
    definition = typescript_unique_function_definition(text, name)
    if definition is None:
        return False
    _, parameters, body = definition
    ordinary_parameters = [item.local_name for item in parameters if item.property_name is None]
    if len(ordinary_parameters) < 2:
        return False
    code = typescript_code_mask(body)
    candidate = re.search(
        r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)"
        r"(?:\s*:[^=]+)?\s*=\s*path\.resolve\s*\(\s*"
        r"path\.normalize\s*\(\s*([^()]*)\s*\)\s*\)",
        code,
    )
    if candidate is None or ordinary_parameters[0] not in typescript_expression_names(
        candidate.group(2)
    ):
        return False
    roots_name = ordinary_parameters[1]
    root_loop = re.search(
        rf"\b{re.escape(roots_name)}\.some\s*\(\s*"
        r"(?:\(\s*)?([A-Za-z_$][\w$]*)[^=]*=>",
        code,
    )
    if root_loop is None:
        return False
    root_item = root_loop.group(1)
    normalized_root = re.search(
        r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)"
        r"(?:\s*:[^=]+)?\s*=\s*path\.resolve\s*\(\s*"
        rf"path\.normalize\s*\(\s*{re.escape(root_item)}\s*\)\s*\)",
        code[root_loop.end() :],
    )
    if normalized_root is None:
        return False
    candidate_name = candidate.group(1)
    root_name = normalized_root.group(1)
    return bool(
        re.search(
            rf"\b{re.escape(candidate_name)}\s*===\s*{re.escape(root_name)}\b",
            code,
        )
        and re.search(
            rf"\b{re.escape(candidate_name)}\.startsWith\s*\(\s*"
            rf"{re.escape(root_name)}\s*\+\s*path\.sep\s*\)",
            code,
        )
        and re.search(r"\breturn\s+false\b", code)
        and re.search(r"\breturn\s+true\b", code)
    )


def typescript_is_path_boundary_guard(
    root: Path,
    path: Path,
    text: str,
    name: str,
) -> tuple[int, str, str] | None:
    """Verify an imported guard that rejects paths outside a proven roots predicate."""
    definition = typescript_unique_function_definition(text, name)
    if definition is None:
        return None
    line, parameters, body = definition
    ordinary_parameters = [item.local_name for item in parameters if item.property_name is None]
    if not ordinary_parameters:
        return None
    imported_predicates = resolve_typescript_imports(root, path, text)
    if not imported_predicates:
        return None
    dynamic_names = {ordinary_parameters[0]}
    body_code = typescript_code_mask(body)
    body_offset = 0
    for body_line in body.splitlines(keepends=True):
        typescript_update_dynamic_names(body_line, dynamic_names, {})
        code_line = typescript_code_mask(body_line)
        for local_name, (target, original) in imported_predicates.items():
            assignment = re.search(
                rf"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*"
                rf"(?:await\s+)?{re.escape(local_name)}\s*\(([^;]*)\)",
                code_line,
            )
            if assignment is None:
                continue
            argument_text = body_line[assignment.start(2) : assignment.end(2)]
            arguments = [argument for argument, _ in typescript_call_arguments(argument_text)]
            if not arguments or not (typescript_expression_names(arguments[0]) & dynamic_names):
                continue
            predicate_path = root / target
            try:
                predicate_text = predicate_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if not typescript_is_path_boundary_predicate(predicate_text, original):
                continue
            result_name = assignment.group(1)
            rejection = re.compile(
                rf"\bif\s*\(\s*!\s*{re.escape(result_name)}\s*\)\s*"
                rf"(?:\{{[\s\S]{{0,500}}?\bthrow\b|\bthrow\b)"
            )
            if rejection.search(body_code, body_offset + assignment.end()):
                boundary_scope = (
                    "constrained"
                    if len(arguments) > 1
                    and typescript_path_roots_are_statically_constrained(text, arguments[1])
                    else "unresolved"
                )
                return line, target, boundary_scope
        body_offset += len(body_line)
    return None


def typescript_path_roots_are_statically_constrained(text: str, expression: str) -> bool:
    """Return true for a non-empty literal list of absolute, non-root directories."""
    value = expression.strip()
    if identifier := re.fullmatch(r"[A-Za-z_$][\w$]*", value):
        code = typescript_code_mask(text)
        pattern = re.compile(
            rf"\b(?:const|let)\s+{re.escape(identifier.group(0))}"
            rf"(?:\s*:[^=]+)?\s*=\s*\["
        )
        matches = list(pattern.finditer(code))
        if len(matches) != 1:
            return False
        opening = code.find("[", matches[0].start(), matches[0].end())
        end = typescript_balanced_end(code, opening, "[", "]")
        if end is None:
            return False
        value = text[opening:end]
    if not (value.startswith("[") and value.endswith("]")):
        return False
    roots = []
    for item, _ in typescript_call_arguments(value[1:-1]):
        literal = re.fullmatch(r"\s*(['\"])(.*?)\1\s*", item, re.DOTALL)
        if literal is None:
            return False
        roots.append(literal.group(2))
    if not roots:
        return False
    return all(
        (root.startswith("/") or bool(re.match(r"^[A-Za-z]:[\\/]", root)))
        and root not in {"/", "\\"}
        and not re.fullmatch(r"[A-Za-z]:[\\/]*", root)
        for root in roots
    )


def typescript_path_boundary_helpers(
    root: Path,
    path: Path,
    imported_symbols: dict[str, tuple[str, str]],
) -> dict[str, TypeScriptPathBoundaryHelper]:
    """Resolve imported path guards only when their nested boundary predicate is proven."""
    helpers = {}
    for local_name, (target, original) in imported_symbols.items():
        target_path = root / target
        try:
            target_text = target_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        proof = typescript_is_path_boundary_guard(root, target_path, target_text, original)
        if proof is None:
            continue
        helper_line, predicate_path, boundary_scope = proof
        helper_evidence = Evidence(
            target,
            helper_line,
            excerpt(target_text.splitlines(), helper_line),
        )
        helpers[local_name] = TypeScriptPathBoundaryHelper(
            local_name,
            helper_evidence,
            predicate_path,
            boundary_scope,
        )
    return helpers


def typescript_path_boundary_assignment(
    line: str,
    helpers: dict[str, TypeScriptPathBoundaryHelper],
    dynamic_names: set[str],
) -> tuple[str, TypeScriptPathBoundaryHelper] | None:
    code = typescript_code_mask(line)
    for local_name, helper in helpers.items():
        assignment = re.search(
            rf"\b(?:const|let)\s+([A-Za-z_$][\w$]*)"
            rf"(?:\s*:[^=]+)?\s*=\s*(?:await\s+)?"
            rf"{re.escape(local_name)}\s*\(([^;]*)\)",
            code,
        )
        if assignment is None:
            continue
        argument = line[assignment.start(2) : assignment.end(2)].split(",", 1)[0]
        if typescript_expression_names(argument) & dynamic_names:
            return assignment.group(1), helper
    return None


def typescript_update_guarded_path_names(
    line: str,
    guarded_names: dict[str, TypeScriptPathBoundaryHelper],
) -> None:
    """Propagate guarded aliases and clear a guard when its binding is reassigned."""
    code = typescript_code_mask(line)
    assignment = re.search(
        r"(?:\b(?:const|let)\s+|(?<![\w$]))([A-Za-z_$][\w$]*)"
        r"(?:\s*:[^=]+)?\s*=(?!=|>)",
        code,
    )
    if assignment is None:
        return
    target = assignment.group(1)
    source_names = typescript_expression_names(line[assignment.end() :])
    sources = [guarded_names[name] for name in source_names if name in guarded_names]
    if sources:
        guarded_names[target] = sources[0]
    else:
        guarded_names.pop(target, None)


def typescript_call_parts(expression: str) -> tuple[str, str, int] | None:
    """Return a simple call's callee, argument body, and body offset within the expression."""
    code = typescript_code_mask(expression)
    match = re.match(r"([A-Za-z_$][\w$]*)\s*\(", code)
    if not match:
        return None
    opening = code.find("(", match.start(), match.end())
    end = typescript_balanced_end(code, opening, "(", ")")
    if end is None or code[end:].strip():
        return None
    return match.group(1), expression[opening + 1 : end - 1], opening + 1


def add_typescript_tool_observation(
    ir: RepositoryIR,
    *,
    relative: str,
    text: str,
    lines: list[str],
    tool_name: str,
    tool_id: str,
    constructor: str,
    call_body: str,
    call_offset: int,
    body_offset: int,
) -> None:
    """Add one structure-backed TypeScript tool, its capabilities, and literal approval control."""
    line = line_at(text, call_offset)
    evidence = Evidence(relative, line, excerpt(lines, line))
    literal_options = typescript_code_mask(call_body).lstrip().startswith("{")
    approval_expression = typescript_object_property_expression(call_body, "needsApproval")
    approval_handler_expression = typescript_object_property_expression(call_body, "onApproval")
    if constructor not in TS_OPENAI_APPROVAL_BUILTINS:
        approval_policy = "not-applicable"
    elif approval_expression == "true":
        approval_policy = "enabled"
    elif approval_expression == "false":
        approval_policy = "disabled-explicit"
    elif approval_expression is not None or approval_handler_expression is not None:
        approval_policy = "unresolved-handler"
    elif literal_options:
        approval_policy = "disabled-default"
    else:
        approval_policy = "unresolved"
    execution_environment = "unresolved"
    if constructor == "shellTool":
        environment = typescript_object_property_expression(call_body, "environment")
        environment_type = (
            typescript_object_string_property(environment, "type") if environment else None
        )
        execution_environment = (
            "hosted"
            if environment_type and environment_type.startswith("container_")
            else "local"
            if literal_options
            else "unresolved"
        )
    attributes = {
        "constructor": constructor,
        "approval_policy": approval_policy,
        "approval_handler": (
            "not-applicable"
            if constructor not in TS_OPENAI_APPROVAL_BUILTINS
            else "configured"
            if approval_handler_expression
            else "none"
        ),
        "execution_environment": execution_environment,
        "scope": source_scope(relative),
    }
    ir.add_component(Component("tool", tool_name, evidence, attributes, tool_id))
    capability_attributes = {
        "builtin_tool": constructor,
        "approval_policy": approval_policy,
        "scope": source_scope(relative),
    }
    if constructor == "shellTool":
        capability_attributes["execution_environment"] = execution_environment
    if constructor == "applyPatchTool":
        capability_attributes["write_access"] = True
    for capability in TS_OPENAI_BUILTIN_TOOL_CAPABILITIES.get(constructor, ()):
        ir.add_component(Component("capability", capability, evidence, capability_attributes))
        ir.add_relationship(
            Relationship(
                "tool",
                tool_name,
                "uses",
                "capability",
                capability,
                evidence,
                source_id=tool_id,
            )
        )
    if approval_expression == "true" and constructor in TS_OPENAI_APPROVAL_BUILTINS:
        body_code = typescript_code_mask(call_body)
        approval_match = re.search(r"\bneedsApproval\s*:\s*true\b", body_code)
        assert approval_match is not None
        approval_offset = body_offset + approval_match.start()
        approval_line = line_at(text, approval_offset)
        approval_evidence = Evidence(relative, approval_line, excerpt(lines, approval_line))
        ir.add_component(Component("control", "human-approval", approval_evidence))
        ir.add_relationship(
            Relationship(
                "tool",
                tool_name,
                "governed-by",
                "control",
                "human-approval",
                approval_evidence,
                source_id=tool_id,
            )
        )


def typescript_first_argument_is_literal(argument_text: str) -> bool:
    """Return true only when the first call argument is one complete string literal."""
    value = argument_text.lstrip()
    if not value or value[0] not in {"'", '"', "`"}:
        return False
    quote = value[0]
    escaped = False
    for index, character in enumerate(value[1:], start=1):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == quote:
            if quote == "`" and "${" in value[1:index]:
                return False
            return value[index + 1 :].lstrip().startswith((",", ")"))
    return False


def typescript_is_generic_tool_factory(
    local_factory: str,
    constructor: str,
    cline_imports: dict[str, str],
    mastra_imports: dict[str, str],
) -> bool:
    return (
        constructor in TS_GENERIC_TOOL_FACTORIES
        or (local_factory in cline_imports and constructor == "createTool")
        or (local_factory in mastra_imports and constructor == "createTool")
    )


def add_typescript_generic_tool(
    ir: RepositoryIR,
    *,
    relative: str,
    lines: list[str],
    text: str,
    tool_by_line: dict[int, tuple[str, str]],
    tool_input_names: dict[str, set[str]],
    tool_name: str,
    tool_id: str,
    constructor: str,
    body: str,
    body_offset: int,
    call_offset: int,
    call_end: int,
    attributes: dict | None = None,
) -> None:
    """Add a generic factory-backed tool and map its callback/configuration span."""
    start_line = line_at(text, call_offset)
    evidence = Evidence(relative, start_line, excerpt(lines, start_line))
    approval_match = (
        TS_LITERAL_APPROVAL.search(typescript_code_mask(body))
        if constructor != "toolNamespace"
        and typescript_object_property_expression(body, "needsApproval") == "true"
        else None
    )
    ir.add_component(
        Component(
            "tool",
            tool_name,
            evidence,
            {
                "constructor": constructor,
                "needs_approval": approval_match is not None,
                **(attributes or {}),
            },
            tool_id,
        )
    )
    tool_input_names[tool_id] = typescript_tool_parameter_names(body, constructor)
    if approval_match:
        approval_line = line_at(text, body_offset + approval_match.start())
        approval_evidence = Evidence(relative, approval_line, excerpt(lines, approval_line))
        ir.add_component(Component("control", "human-approval", approval_evidence))
        ir.add_relationship(
            Relationship(
                "tool",
                tool_name,
                "governed-by",
                "control",
                "human-approval",
                approval_evidence,
                source_id=tool_id,
            )
        )
    for line_number in range(start_line, line_at(text, call_end) + 1):
        tool_by_line[line_number] = (tool_name, tool_id)


def typescript_graph(
    ir: RepositoryIR,
    relative: str,
    text: str,
    lines: list[str],
    imported_symbols: dict[str, tuple[str, str]],
) -> tuple[dict[int, tuple[str, str]], dict[str, set[str]]]:
    tool_by_line: dict[int, tuple[str, str]] = {}
    tool_input_names: dict[str, set[str]] = {}
    local_tool_ids: dict[str, str] = {}
    code = typescript_code_mask(text)
    openai_imports = {
        **typescript_named_import_bindings(text, "@openai/agents"),
        **typescript_named_import_bindings(text, "@openai/agents-extensions"),
    }
    cline_imports = typescript_named_import_bindings(text, "@cline/sdk")
    mastra_imports = typescript_named_import_bindings(text, "@mastra/core/tools")
    literal_bindings = typescript_literal_string_bindings(text)
    has_mcp_import = "@modelcontextprotocol/" in text or bool(
        re.search(r"from\s+['\"][^'\"]*mcp[^'\"]*['\"]", text, re.IGNORECASE)
    )
    tool_matches = list(TS_TOOL_ASSIGNMENT.finditer(code))
    tool_assignment_counts = Counter(match.group(1) for match in tool_matches)
    property_matches = []
    for match in TS_TOOL_PROPERTY.finditer(code):
        local_factory = match.group(2)
        constructor = openai_imports.get(
            local_factory,
            cline_imports.get(local_factory, mastra_imports.get(local_factory, local_factory)),
        )
        if typescript_is_generic_tool_factory(
            local_factory, constructor, cline_imports, mastra_imports
        ):
            property_matches.append((match, constructor))
    registration_matches = [
        match
        for match in TS_MCP_TOOL_REGISTRATION.finditer(code)
        if has_mcp_import
        and (
            "server" in match.group(1).lower()
            or "mcp" in match.group(1).lower()
            or match.group(1) == "s"
        )
    ]

    def registration_name(match: re.Match[str]) -> str:
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")") or len(text)
        body = text[opening + 1 : end - 1]
        direct_literal = re.match(r"\s*(['\"])(.*?)\1\s*(?:,|$)", body, re.DOTALL)
        if direct_literal:
            return direct_literal.group(2)
        identifier = re.match(
            r"\s*([A-Za-z_$][\w$]*)\s*(?:,|$)",
            typescript_code_mask(body),
        )
        if identifier and (literal := literal_bindings.get(identifier.group(1))):
            return literal
        return f"registerTool@{line_at(text, match.start())}"

    registration_names = {match.start(): registration_name(match) for match in registration_matches}
    tool_identity_counts = Counter(
        [match.group(1) for match in tool_matches]
        + [match.group(1) for match, _ in property_matches]
        + list(registration_names.values())
    )
    for match in tool_matches:
        tool_name = match.group(1)
        local_factory = match.group(2)
        constructor = openai_imports.get(
            local_factory,
            cline_imports.get(local_factory, mastra_imports.get(local_factory, local_factory)),
        )
        is_generic = typescript_is_generic_tool_factory(
            local_factory, constructor, cline_imports, mastra_imports
        )
        is_openai_builtin = (
            local_factory in openai_imports and constructor in TS_OPENAI_BUILTIN_TOOL_CAPABILITIES
        )
        if not is_generic and not is_openai_builtin:
            continue
        start_line = line_at(text, match.start())
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")") or len(text)
        end_line = line_at(text, end)
        body = text[opening + 1 : end - 1]
        tool_identity = (
            f"{tool_name}@{start_line}" if tool_identity_counts[tool_name] > 1 else tool_name
        )
        tool_id = source_symbol("ts", relative, "tool", tool_identity)
        if tool_assignment_counts[tool_name] == 1:
            local_tool_ids[tool_name] = tool_id
        if is_openai_builtin:
            add_typescript_tool_observation(
                ir,
                relative=relative,
                text=text,
                lines=lines,
                tool_name=tool_name,
                tool_id=tool_id,
                constructor=constructor,
                call_body=body,
                call_offset=match.start(2),
                body_offset=opening + 1,
            )
        else:
            add_typescript_generic_tool(
                ir,
                relative=relative,
                lines=lines,
                text=text,
                tool_by_line=tool_by_line,
                tool_input_names=tool_input_names,
                tool_name=tool_name,
                tool_id=tool_id,
                constructor=constructor,
                body=body,
                body_offset=opening + 1,
                call_offset=match.start(),
                call_end=end,
            )
        if is_openai_builtin:
            for line_number in range(start_line, end_line + 1):
                tool_by_line[line_number] = (tool_name, tool_id)

    for match, constructor in property_matches:
        tool_name = match.group(1)
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")") or len(text)
        start_line = line_at(text, match.start())
        tool_identity = (
            f"{tool_name}@{start_line}" if tool_identity_counts[tool_name] > 1 else tool_name
        )
        tool_id = source_symbol("ts", relative, "tool", tool_identity)
        add_typescript_generic_tool(
            ir,
            relative=relative,
            lines=lines,
            text=text,
            tool_by_line=tool_by_line,
            tool_input_names=tool_input_names,
            tool_name=tool_name,
            tool_id=tool_id,
            constructor=constructor,
            body=text[opening + 1 : end - 1],
            body_offset=opening + 1,
            call_offset=match.start(),
            call_end=end,
            attributes={"binding": "object-property"},
        )

    for match in registration_matches:
        tool_name = registration_names[match.start()]
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")") or len(text)
        start_line = line_at(text, match.start())
        tool_identity = (
            f"{tool_name}@{start_line}" if tool_identity_counts[tool_name] > 1 else tool_name
        )
        tool_id = source_symbol("ts", relative, "tool", tool_identity)
        add_typescript_generic_tool(
            ir,
            relative=relative,
            lines=lines,
            text=text,
            tool_by_line=tool_by_line,
            tool_input_names=tool_input_names,
            tool_name=tool_name,
            tool_id=tool_id,
            constructor="registerTool",
            body=text[opening + 1 : end - 1],
            body_offset=opening + 1,
            call_offset=match.start(),
            call_end=end,
            attributes={"protocol": "MCP", "registry": match.group(1)},
        )

    agent_matches = list(TS_AGENT_ASSIGNMENT.finditer(code))
    agent_assignment_counts = Counter(match.group(1) for match in agent_matches)
    agent_tool_bindings = {
        match.group(1): match.group(2) for match in TS_AGENT_TOOL_ASSIGNMENT.finditer(code)
    }
    local_agents: dict[str, tuple[str, str]] = {}
    agent_bodies: list[tuple[re.Match[str], int, str, str, str]] = []
    for match in agent_matches:
        variable_name = match.group(1)
        start_line = line_at(text, match.start())
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")") or len(text)
        body = text[opening + 1 : end - 1]
        agent_name = typescript_object_string_property(body, "name") or variable_name
        agent_identity = (
            f"{variable_name}@{start_line}"
            if agent_assignment_counts[variable_name] > 1
            else variable_name
        )
        agent_id = source_symbol("ts", relative, "agent", agent_identity)
        ev = Evidence(relative, start_line, excerpt(lines, start_line))
        ir.add_component(Component("agent", agent_name, ev, {"constructor": "Agent"}, agent_id))
        if agent_assignment_counts[variable_name] == 1:
            local_agents[variable_name] = (agent_name, agent_id)
        agent_bodies.append((match, opening + 1, body, agent_name, agent_id))

    for match, body_offset, body, agent_name, agent_id in agent_bodies:
        ev = Evidence(
            relative, line_at(text, match.start()), excerpt(lines, line_at(text, match.start()))
        )
        for item, item_offset in typescript_agent_tool_items(body, body_offset):
            spread = item.startswith("...")
            expression = item[3:].lstrip() if spread else item
            if spread:
                item_offset += 3 + (len(item[3:]) - len(item[3:].lstrip()))
            attributes = {"spread": True} if spread else {}
            if identifier := re.fullmatch(
                r"[A-Za-z_$][\w$]*", typescript_code_mask(expression).strip()
            ):
                tool_name = identifier.group(0)
                if target_variable := agent_tool_bindings.get(tool_name):
                    target = local_agents.get(target_variable)
                    target_name, target_id = target if target else (target_variable, None)
                    if agent_assignment_counts[target_variable] > 1:
                        attributes["target_identity"] = "ambiguous-repeated-binding"
                    ir.add_relationship(
                        Relationship(
                            "agent",
                            agent_name,
                            "delegates-to",
                            "agent",
                            target_name,
                            ev,
                            {**attributes, "adapter": "asTool", "binding": tool_name},
                            source_id=agent_id,
                            target_id=target_id,
                        )
                    )
                    continue
                target_id = local_tool_ids.get(tool_name)
                if imported := imported_symbols.get(tool_name):
                    attributes.update({"target_path": imported[0], "target_name": imported[1]})
                    target_id = source_symbol("ts", imported[0], "tool", imported[1])
                elif tool_assignment_counts[tool_name] > 1:
                    attributes["target_identity"] = "ambiguous-repeated-binding"
                ir.add_relationship(
                    Relationship(
                        "agent",
                        agent_name,
                        "uses",
                        "tool",
                        tool_name,
                        ev,
                        attributes,
                        source_id=agent_id,
                        target_id=target_id,
                    )
                )
                continue
            as_tool = re.match(r"([A-Za-z_$][\w$]*)\.asTool\s*\(", expression)
            if as_tool and balanced_call_end(expression, expression.find("(")) == len(expression):
                variable_name = as_tool.group(1)
                target = local_agents.get(variable_name)
                target_name, target_id = target if target else (variable_name, None)
                if agent_assignment_counts[variable_name] > 1:
                    attributes["target_identity"] = "ambiguous-repeated-binding"
                ir.add_relationship(
                    Relationship(
                        "agent",
                        agent_name,
                        "delegates-to",
                        "agent",
                        target_name,
                        ev,
                        {**attributes, "adapter": "asTool"},
                        source_id=agent_id,
                        target_id=target_id,
                    )
                )
                continue
            call = typescript_call_parts(expression)
            if not call:
                continue
            local_factory, call_body, relative_body_offset = call
            constructor = openai_imports.get(
                local_factory,
                cline_imports.get(local_factory, mastra_imports.get(local_factory, local_factory)),
            )
            call_line = line_at(text, item_offset)
            tool_name = f"{constructor}@{call_line}"
            target_id = None
            if typescript_is_generic_tool_factory(
                local_factory, constructor, cline_imports, mastra_imports
            ):
                target_id = source_symbol("ts", relative, "tool", tool_name)
                ir.add_component(
                    Component(
                        "tool",
                        tool_name,
                        Evidence(relative, call_line, excerpt(lines, call_line)),
                        {"constructor": constructor, "inline": True},
                        target_id,
                    )
                )
                tool_input_names[target_id] = typescript_tool_parameter_names(
                    call_body, constructor
                )
                call_end_offset = item_offset + len(expression)
                for line_number in range(call_line, line_at(text, call_end_offset) + 1):
                    tool_by_line[line_number] = (tool_name, target_id)
            elif (
                local_factory in openai_imports
                and constructor in TS_OPENAI_BUILTIN_TOOL_CAPABILITIES
            ):
                target_id = source_symbol("ts", relative, "tool", tool_name)
                add_typescript_tool_observation(
                    ir,
                    relative=relative,
                    text=text,
                    lines=lines,
                    tool_name=tool_name,
                    tool_id=target_id,
                    constructor=constructor,
                    call_body=call_body,
                    call_offset=item_offset,
                    body_offset=item_offset + relative_body_offset,
                )
            else:
                tool_name = local_factory
                attributes["factory_call"] = True
            ir.add_relationship(
                Relationship(
                    "agent",
                    agent_name,
                    "uses",
                    "tool",
                    tool_name,
                    ev,
                    attributes,
                    source_id=agent_id,
                    target_id=target_id,
                )
            )
    return tool_by_line, tool_input_names


def resolve_typescript_imports(root: Path, path: Path, text: str) -> dict[str, tuple[str, str]]:
    """Resolve unambiguous named imports that stay inside the repository."""
    resolved: dict[str, tuple[str, str]] = {}
    suffixes = (".ts", ".tsx", ".js", ".jsx")
    for match in TS_NAMED_IMPORT.finditer(text):
        specifier = match.group(2)
        if not specifier.startswith(("./", "../")):
            continue
        unresolved = path.parent / specifier
        candidates = [unresolved]
        stem = unresolved.with_suffix("") if unresolved.suffix in suffixes else unresolved
        candidates.extend(stem.with_suffix(suffix) for suffix in suffixes)
        candidates.extend(stem / f"index{suffix}" for suffix in suffixes)
        existing = []
        for candidate in candidates:
            try:
                canonical = candidate.resolve()
                canonical.relative_to(root)
            except (OSError, ValueError):
                continue
            if canonical.is_file() and not canonical.is_symlink() and canonical not in existing:
                existing.append(canonical)
        if len(existing) != 1:
            continue
        target = existing[0].relative_to(root).as_posix()
        for imported in match.group(1).split(","):
            parts = imported.strip().removeprefix("type ").split()
            if not parts:
                continue
            original = parts[0]
            local = parts[2] if len(parts) >= 3 and parts[1] == "as" else original
            resolved[local] = (target, original)
    return resolved


def child_process_bindings(text: str) -> set[str]:
    bindings: set[str] = set()
    for match in TS_CHILD_PROCESS_IMPORT.finditer(text):
        for imported in match.group(1).split(","):
            parts = imported.strip().split()
            if not parts:
                continue
            original = parts[0]
            local = parts[2] if len(parts) >= 3 and parts[1] == "as" else original
            if original in {"exec", "execSync", "spawn", "spawnSync"}:
                bindings.add(local)
    return bindings


def add_typescript_capability(
    ir: RepositoryIR,
    relative: str,
    line_number: int,
    evidence: Evidence,
    tool_by_line: dict[int, tuple[str, str]],
    name: str,
    attributes: dict | None = None,
) -> None:
    values = {"scope": source_scope(relative), **(attributes or {})}
    ir.add_component(Component("capability", name, evidence, values))
    if tool := tool_by_line.get(line_number):
        tool_name, tool_id = tool
        ir.add_relationship(
            Relationship(
                "tool",
                tool_name,
                "uses",
                "capability",
                name,
                evidence,
                source_id=tool_id,
            )
        )


def add_typescript_path_boundary_control(
    ir: RepositoryIR,
    capability_evidence: Evidence,
    helper: TypeScriptPathBoundaryHelper,
) -> None:
    policy_effect = (
        "restricts-filesystem-path"
        if helper.boundary_scope == "constrained"
        else "validates-filesystem-path"
    )
    ir.add_component(
        Component(
            "control",
            "path-boundary",
            helper.evidence,
            {
                "scope": source_scope(helper.evidence.path),
                "policy_effect": policy_effect,
                "helper": helper.name,
                "predicate_path": helper.predicate_path,
                "boundary_scope": helper.boundary_scope,
            },
        )
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "filesystem",
            "governed-by",
            "control",
            "path-boundary",
            capability_evidence,
            {
                "control_path": helper.evidence.path,
                "control_line": helper.evidence.line,
                "policy_effect": policy_effect,
                "helper": helper.name,
                "predicate_path": helper.predicate_path,
                "boundary_scope": helper.boundary_scope,
            },
        )
    )


def scan_typescript(ir: RepositoryIR, root: Path, path: Path, text: str) -> None:
    relative = path.relative_to(root).as_posix()
    lines = text.splitlines()
    imported_symbols = resolve_typescript_imports(root, path, text)
    tool_by_line, tool_input_names = typescript_graph(ir, relative, text, lines, imported_symbols)
    dynamic_names_by_tool = {tool_id: set(names) for tool_id, names in tool_input_names.items()}
    guarded_path_names_by_tool: dict[str, dict[str, TypeScriptPathBoundaryHelper]] = defaultdict(
        dict
    )
    literal_bindings = typescript_literal_string_bindings(text)
    network_calls = typescript_network_calls(text)
    if tool_by_line and network_calls:
        network_helper_summaries = typescript_network_helper_summaries(text, literal_bindings)
        network_helper_calls = typescript_helper_calls(text, network_helper_summaries)
        multiline_destructuring_assignments = typescript_multiline_destructuring_assignments(text)
    else:
        network_helper_calls = {}
        multiline_destructuring_assignments = {}
    path_boundary_helpers = (
        typescript_path_boundary_helpers(root, path, imported_symbols)
        if tool_by_line and TS_FILESYSTEM_WRITE.search(text)
        else {}
    )
    shell_bindings = child_process_bindings(text)
    has_mcp_import = "@modelcontextprotocol/" in text or re.search(
        r"from\s+['\"][^'\"]*mcp[^'\"]*['\"]", text, re.IGNORECASE
    )
    has_browser_import = bool(
        re.search(r"from\s+['\"](?:playwright|puppeteer|selenium)[^'\"]*['\"]", text)
    )
    structured_agent_lines = {
        item.evidence.line
        for item in ir.components
        if item.kind == "agent" and item.evidence.path == relative
    }
    for offset, environment_names in typescript_environment_approval_guards(text):
        line_number = line_at(text, offset)
        ir.add_component(
            Component(
                "control-setting",
                "auto-approval",
                Evidence(relative, line_number, excerpt(lines, line_number)),
                {
                    "enabled": True,
                    "source": "environment-guard",
                    "environment_names": environment_names,
                    "scope": source_scope(relative),
                },
            )
        )
    for line_number, line in enumerate(lines, start=1):
        ev = Evidence(relative, line_number, line.strip()[:240])
        code_line = typescript_code_mask(line)
        dynamic_names: set[str] = set()
        guarded_path_names: dict[str, TypeScriptPathBoundaryHelper] = {}
        if tool := tool_by_line.get(line_number):
            dynamic_names = dynamic_names_by_tool.setdefault(tool[1], set())
            guarded_path_names = guarded_path_names_by_tool.setdefault(tool[1], {})
            typescript_apply_destructuring_assignments(
                multiline_destructuring_assignments.get(line_number, []), dynamic_names
            )
            typescript_update_dynamic_names(line, dynamic_names, literal_bindings)
            typescript_update_guarded_path_names(line, guarded_path_names)
            if boundary_assignment := typescript_path_boundary_assignment(
                line, path_boundary_helpers, dynamic_names
            ):
                guarded_path_names[boundary_assignment[0]] = boundary_assignment[1]
        for match in TS_IMPORT.finditer(line):
            component_from_import(ir, match.group(1), ev)
        for match in TS_MODEL_SETTING.finditer(line):
            model_value = match.group(1)
            ir.add_component(
                Component("model", model_value, ev, {"provider": provider_for_model(model_value)})
            )
        for match in TS_PROVIDER_MODEL_CALL.finditer(line):
            provider = {
                "openai": "OpenAI",
                "anthropic": "Anthropic",
                "azure": "Azure OpenAI",
            }[match.group(1)]
            ir.add_component(Component("model", match.group(2), ev, {"provider": provider}))
        if line_number not in structured_agent_lines and (match := TS_AGENT.search(code_line)):
            name = match.group(1)
            ir.add_component(
                Component(
                    "agent",
                    name,
                    ev,
                    {"constructor": name},
                    source_symbol("ts", relative, "agent", f"{name}@{line_number}"),
                )
            )
        if match := TS_MCP.search(code_line):
            ir.add_component(Component("mcp", match.group(1), ev, {"constructor": match.group(1)}))
        if (match := TS_SHELL.search(code_line)) and match.group(1) in shell_bindings:
            argument_text = line[match.start(2) : match.end(2)]
            add_typescript_capability(
                ir,
                relative,
                line_number,
                ev,
                tool_by_line,
                "shell-execution",
                {
                    "api": match.group(1),
                    "shell": match.group(1) in {"exec", "execSync"},
                    "dynamic_command": not typescript_first_argument_is_literal(argument_text),
                },
            )
        if "Bun.spawn" in code_line and (match := TS_BUN_SHELL.search(line)):
            add_typescript_capability(
                ir,
                relative,
                line_number,
                ev,
                tool_by_line,
                "shell-execution",
                {
                    "api": "Bun.spawn",
                    "shell": True,
                    "dynamic_command": not typescript_first_argument_is_literal(
                        f"{match.group(1)},)"
                    ),
                },
            )
        if TS_DYNAMIC_EVAL.search(code_line):
            add_typescript_capability(
                ir,
                relative,
                line_number,
                ev,
                tool_by_line,
                "code-execution",
                {"api": "eval", "dynamic_input": True},
            )
        if match := TS_FILESYSTEM_WRITE.search(code_line):
            path_argument = line[match.start(1) : match.end(1)].strip()
            guard = next(
                (
                    helper
                    for name, helper in guarded_path_names.items()
                    if name in typescript_expression_names(path_argument)
                ),
                None,
            )
            add_typescript_capability(
                ir,
                relative,
                line_number,
                ev,
                tool_by_line,
                "filesystem",
                {
                    "write_access": True,
                    "dynamic_path": not path_argument.startswith(("'", '"', "`")),
                    "path_boundary_guard": guard is not None,
                    "path_boundary_scope": (
                        guard.boundary_scope if guard is not None else "unresolved"
                    ),
                },
            )
            if guard is not None:
                add_typescript_path_boundary_control(ir, ev, guard)
        for api, url_expression in network_calls.get(line_number, []):
            add_typescript_capability(
                ir,
                relative,
                line_number,
                ev,
                tool_by_line,
                "network",
                {
                    "api": api,
                    "dynamic_origin": typescript_http_origin_is_dynamic(
                        url_expression, dynamic_names, literal_bindings
                    ),
                },
            )
        if line_number in tool_by_line:
            for summary, arguments in network_helper_calls.get(line_number, []):
                dynamic_origin = False
                for parameter in summary.parameters:
                    if parameter.local_name not in summary.controlled_names:
                        continue
                    argument = typescript_helper_argument_expression(arguments, parameter)
                    if argument and typescript_http_origin_is_dynamic(
                        argument, dynamic_names, literal_bindings
                    ):
                        dynamic_origin = True
                        break
                add_typescript_capability(
                    ir,
                    relative,
                    line_number,
                    ev,
                    tool_by_line,
                    "network",
                    {
                        "api": summary.name,
                        "dynamic_origin": dynamic_origin,
                        "summary": "same-file-helper",
                        "helper_line": summary.line,
                        "helper_network_calls": summary.network_calls,
                    },
                )
        if re.search(r"\baxios\.(?:post|put|patch|delete)\s*\(", code_line) or (
            re.search(r"\bmethod\s*:", code_line)
            and re.search(
                r"\bmethod\s*:\s*['\"](?:POST|PUT|PATCH|DELETE)['\"]",
                line,
                re.IGNORECASE,
            )
        ):
            add_typescript_capability(
                ir, relative, line_number, ev, tool_by_line, "external-action"
            )
        if has_browser_import and re.search(
            r"\.(?:click|goto|fill|press|selectOption)\s*\(", code_line
        ):
            add_typescript_capability(ir, relative, line_number, ev, tool_by_line, "browser")
        if TS_AUTO_APPROVAL_ENABLED.search(code_line):
            ir.add_component(
                Component(
                    "control-setting",
                    "auto-approval",
                    ev,
                    {"enabled": True, "scope": source_scope(relative)},
                )
            )
        if has_mcp_import and TS_MCP_DYNAMIC_CALL.search(code_line):
            add_typescript_capability(
                ir,
                relative,
                line_number,
                ev,
                tool_by_line,
                "mcp-tool-forwarding",
                {"dynamic_tool_name": True, "dynamic_arguments": True},
            )


def scan_mcp_config(ir: RepositoryIR, root: Path, path: Path) -> None:
    relative = path.relative_to(root).as_posix()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    servers = value.get("mcpServers") if isinstance(value, dict) else None
    if not isinstance(servers, dict):
        return
    for name, config in servers.items():
        if not isinstance(config, dict):
            continue
        attributes = {"transport": "unknown"}
        if command := config.get("command"):
            attributes.update({"command": command, "transport": "stdio"})
        if url := config.get("url"):
            try:
                parsed = urlsplit(str(url))
                hostname = parsed.hostname or ""
                port = f":{parsed.port}" if parsed.port else ""
                userinfo = "[REDACTED]@" if parsed.username or parsed.password else ""
                attributes.update(
                    {
                        "url": urlunsplit(
                            (parsed.scheme, f"{userinfo}{hostname}{port}", parsed.path, "", "")
                        ),
                        "transport": parsed.scheme or "remote",
                    }
                )
            except ValueError:
                attributes["url"] = "[INVALID URL REDACTED]"
        args = config.get("args")
        if isinstance(args, list):
            sanitized_args = []
            redact_next = False
            for argument in args:
                value = str(argument)
                if redact_next:
                    sanitized_args.append("[REDACTED]")
                    redact_next = False
                    continue
                if re.search(r"(?:token|secret|password|api[-_]?key)", value, re.IGNORECASE):
                    if "=" in value:
                        sanitized_args.append(f"{value.split('=', 1)[0]}=[REDACTED]")
                    else:
                        sanitized_args.append(value)
                        redact_next = True
                else:
                    sanitized_args.append(value)
            attributes["args"] = sanitized_args
        environment = config.get("env")
        if isinstance(environment, dict):
            attributes["environment_names"] = sorted(str(key) for key in environment)
        ir.add_component(Component("mcp-server", name, Evidence(relative, 1, name), attributes))


def is_container_config(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    kubernetes_path = any(
        word in part
        for word in ("chart", "deploy", "helm", "k8s", "kubernetes")
        for part in lowered_parts
    )
    return path.suffix.lower() in CONTAINER_CONFIG_SUFFIXES and (
        "compose" in path.name.lower() or ".devcontainer" in lowered_parts or kubernetes_path
    )


def scan_container_config(ir: RepositoryIR, root: Path, path: Path) -> None:
    relative = path.relative_to(root).as_posix()
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    except OSError as error:
        ir.errors.append(f"{relative}: {error}")
        return
    host_path_pending = False
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            host_path_pending = False
            continue
        boundary = None
        attributes = {"scope": source_scope(relative)}
        if "/var/run/docker.sock" in stripped:
            boundary = "docker-socket"
        elif re.match(r"^privileged\s*:\s*true\s*(?:#.*)?$", stripped, re.IGNORECASE):
            boundary = "privileged-container"
        elif re.match(r"^network_mode\s*:\s*['\"]?host['\"]?\s*(?:#.*)?$", stripped) or re.match(
            r"^hostNetwork\s*:\s*true\s*(?:#.*)?$", stripped, re.IGNORECASE
        ):
            boundary = "host-network"
        elif re.match(r"^hostPID\s*:\s*true\s*(?:#.*)?$", stripped, re.IGNORECASE):
            boundary = "host-pid"
        elif re.match(r"^hostIPC\s*:\s*true\s*(?:#.*)?$", stripped, re.IGNORECASE):
            boundary = "host-ipc"
        elif re.match(
            r"^automountServiceAccountToken\s*:\s*true\s*(?:#.*)?$",
            stripped,
            re.IGNORECASE,
        ):
            boundary = "service-account-token"
        elif re.match(
            r"^allowPrivilegeEscalation\s*:\s*true\s*(?:#.*)?$",
            stripped,
            re.IGNORECASE,
        ):
            boundary = "privilege-escalation"
        elif re.match(r"^-\s*['\"]?/\s*:", stripped):
            boundary = "root-host-mount"
        elif host_path_pending and (
            host_path_match := re.match(
                r"^path\s*:\s*['\"]?(/[^'\"#\s]*)['\"]?\s*(?:#.*)?$", stripped
            )
        ):
            host_path = host_path_match.group(1)
            boundary = "root-host-mount" if host_path == "/" else "host-path-mount"
            attributes["host_path"] = host_path
        host_path_pending = bool(re.match(r"^hostPath\s*:\s*$", stripped))
        if boundary:
            ir.add_component(
                Component(
                    "sandbox-boundary",
                    boundary,
                    Evidence(relative, line_number, stripped[:240]),
                    attributes,
                )
            )


def apply_inline_suppressions(
    ir: RepositoryIR,
    source_lines: dict[str, list[str]],
    *,
    require_expiry: bool = False,
    current_date: date | None = None,
) -> None:
    """Apply rule-scoped suppressions from a reason-bearing comment on the previous line."""
    retained = []
    for finding in ir.findings:
        lines = source_lines.get(finding.evidence.path, [])
        directive_line = finding.evidence.line - 1
        directive = lines[directive_line - 1] if 0 < directive_line <= len(lines) else ""
        match = INLINE_SUPPRESSION.match(directive)
        if not match or match.group(1) != finding.rule_id:
            retained.append(finding)
            continue
        expires_on = match.group(2)
        status = "active"
        if expires_on:
            try:
                expiry_date = date.fromisoformat(expires_on)
            except ValueError:
                status = "invalid-expiry"
            else:
                if expiry_date < (current_date or datetime.now(UTC).date()):
                    status = "expired"
        elif require_expiry:
            status = "missing-expiry"
        ir.suppressions.append(
            Suppression(
                finding.rule_id,
                match.group(3).strip(),
                finding.evidence,
                Evidence(finding.evidence.path, directive_line, directive.strip()[:240]),
                expires_on,
                status,
            )
        )
        if status != "active":
            retained.append(finding)
    ir.suppressed_findings += len(ir.findings) - len(retained)
    ir.findings = retained


def build_python_module_index(root: Path, paths: list[Path]) -> dict[str, str]:
    candidates: dict[str, set[str]] = {}
    for path in paths:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix.lower() != ".py"
            or set(path.relative_to(root).parts) & SKIP_DIRECTORIES
        ):
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
        except OSError:
            continue
        relative = path.relative_to(root)
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        module_parts = [parts]
        for source_root in ("src", "python"):
            if source_root in parts:
                module_parts.append(parts[parts.index(source_root) + 1 :])
        for candidate_parts in module_parts:
            if candidate_parts:
                module = ".".join(candidate_parts)
                candidates.setdefault(module, set()).add(relative.as_posix())
    return {
        module: next(iter(locations))
        for module, locations in candidates.items()
        if len(locations) == 1
    }


def build_python_registry_class_exports(
    root: Path,
    paths: list[Path],
    module_paths: dict[str, str],
) -> dict[tuple[str, str], RegistryClassTarget]:
    """Index selected registry classes and package-level reexports without importing code."""
    direct: dict[tuple[str, str], RegistryClassTarget] = {}
    export_references: list[tuple[str, str, str, str]] = []
    for path in paths:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix.lower() != ".py"
            or set(path.relative_to(root).parts) & SKIP_DIRECTORIES
        ):
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        is_export_module = path.name == "__init__.py"
        if not is_export_module and not (
            "call_tool" in text and ("get_tool" in text or ".get(" in text)
        ):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(text, filename=relative)
        except SyntaxError:
            continue
        lines = text.splitlines()
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = PythonVisitor.registry_method_summaries(node, relative, lines)
                if methods:
                    direct[(relative, node.name)] = RegistryClassTarget(
                        relative,
                        node.name,
                        methods,
                    )
            if not (is_export_module and isinstance(node, ast.ImportFrom)):
                continue
            for alias in node.names:
                target_path = resolve_python_import_path(
                    root,
                    relative,
                    node,
                    alias.name,
                    module_paths,
                )
                if target_path:
                    export_references.append(
                        (
                            relative,
                            alias.asname or alias.name,
                            target_path,
                            alias.name,
                        )
                    )

    exports = dict(direct)
    references_by_export: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for path, local_name, target_path, target_name in export_references:
        references_by_export[(path, local_name)].append((target_path, target_name))
    changed = True
    while changed:
        changed = False
        for export_key, references in references_by_export.items():
            if export_key in exports:
                continue
            targets = [exports.get(reference) for reference in references]
            if any(target is None for target in targets):
                continue
            target_identities = {
                (target.path, target.name) for target in targets if target is not None
            }
            if len(target_identities) != 1:
                continue
            exports[export_key] = next(target for target in targets if target is not None)
            changed = True
    return exports


def build_python_tool_registrations(
    root: Path,
    paths: list[Path],
    module_paths: dict[str, str],
) -> dict[tuple[str, str], PythonToolRegistration]:
    """Resolve exact module-level ``server.tool(...)(function)`` registrations.

    This intentionally models only direct, immutable bindings. Wrapper expressions,
    nested registrations, wildcard imports, reassignments, and ambiguous targets are
    left unresolved instead of being guessed by name.
    """
    parsed: dict[str, tuple[ast.Module, list[str]]] = {}
    binding_counts: dict[str, Counter[str]] = {}

    def collect_bindings(tree: ast.Module) -> Counter[str]:
        counts: Counter[str] = Counter()

        def collect(candidate: ast.AST) -> None:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                counts[candidate.name] += 1
                return
            if isinstance(candidate, ast.Lambda):
                return
            if isinstance(candidate, (ast.Import, ast.ImportFrom)):
                counts.update(
                    alias.asname or alias.name.split(".", 1)[0]
                    for alias in candidate.names
                    if alias.name != "*"
                )
                return
            if isinstance(candidate, ast.Name) and isinstance(
                candidate.ctx, (ast.Store, ast.Del)
            ):
                counts[candidate.id] += 1
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        for statement in tree.body:
            collect(statement)
        return counts

    def module_imports(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
        imports: list[ast.Import | ast.ImportFrom] = []

        def collect(candidate: ast.AST) -> None:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            if isinstance(candidate, (ast.Import, ast.ImportFrom)):
                imports.append(candidate)
                return
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        for statement in tree.body:
            collect(statement)
        return imports

    selected_python_paths = {
        path.relative_to(root).as_posix(): path
        for path in paths
        if not path.is_symlink()
        and path.is_file()
        and path.suffix.lower() == ".py"
        and not (set(path.relative_to(root).parts) & SKIP_DIRECTORIES)
    }

    def parse_selected(path: Path, *, require_registration_signal: bool) -> None:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix.lower() != ".py"
            or set(path.relative_to(root).parts) & SKIP_DIRECTORIES
        ):
            return
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                return
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            return
        if require_registration_signal and not (
            "FastMCP" in text and ".tool" in text
        ):
            return
        relative = path.relative_to(root).as_posix()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(text, filename=relative)
        except SyntaxError:
            return
        parsed[relative] = (tree, text.splitlines())
        binding_counts[relative] = collect_bindings(tree)

    for path in selected_python_paths.values():
        parse_selected(path, require_registration_signal=True)

    referenced_paths: set[str] = set()
    for registrar_path, (tree, _) in list(parsed.items()):
        for node in module_imports(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                if target_path := resolve_python_import_path(
                    root,
                    registrar_path,
                    node,
                    alias.name,
                    module_paths,
                ):
                    referenced_paths.add(target_path)
    for referenced_path in referenced_paths:
        if referenced_path not in parsed and (
            path := selected_python_paths.get(referenced_path)
        ):
            parse_selected(path, require_registration_signal=False)

    definitions: dict[tuple[str, str], ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for path, (tree, _) in parsed.items():
        for statement in tree.body:
            if (
                isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
                and binding_counts[path][statement.name] == 1
            ):
                definitions[(path, statement.name)] = statement

    proposals: dict[tuple[str, str], list[PythonToolRegistration]] = defaultdict(list)
    for path, (tree, lines) in parsed.items():
        imports = module_imports(tree)
        direct_imports = [
            statement for statement in tree.body if isinstance(statement, ast.ImportFrom)
        ]
        constructor_aliases = {
            alias.asname or alias.name
            for node in imports
            if isinstance(node, ast.ImportFrom)
            and node.module
            and (
                node.module in {"fastmcp", "mcp"}
                or node.module.startswith(("fastmcp.", "mcp."))
            )
            for alias in node.names
            if alias.name == "FastMCP"
        }
        module_aliases = {
            alias.asname or alias.name.split(".", 1)[0]
            for node in imports
            if isinstance(node, ast.Import)
            for alias in node.names
            if alias.name in {"fastmcp", "mcp"}
            or alias.name.startswith(("fastmcp.", "mcp."))
        }
        if not constructor_aliases and not module_aliases:
            continue

        imported_targets: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
        for node in direct_imports:
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                if binding_counts[path][local_name] != 1:
                    continue
                target_path = resolve_python_import_path(
                    root,
                    path,
                    node,
                    alias.name,
                    module_paths,
                )
                if target_path:
                    imported_targets[local_name].append(
                        (target_path, alias.name, node.lineno)
                    )

        servers: dict[str, int] = {}
        for statement in tree.body:
            if not (
                isinstance(statement, (ast.Assign, ast.AnnAssign))
                and isinstance(statement.value, ast.Call)
            ):
                continue
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                continue
            binding = targets[0].id
            constructor = dotted_name(statement.value.func)
            module_root = constructor.split(".", 1)[0]
            if not (
                constructor in constructor_aliases
                or (
                    constructor.endswith(".FastMCP")
                    and module_root in module_aliases
                )
            ):
                continue
            if binding_counts[path][binding] == 1:
                servers[binding] = statement.lineno

        for statement in tree.body:
            if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
                continue
            outer = statement.value
            if len(outer.args) != 1 or outer.keywords or not isinstance(outer.args[0], ast.Name):
                continue
            if not isinstance(outer.func, ast.Call):
                continue
            decorator = outer.func
            if not (
                isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "tool"
                and isinstance(decorator.func.value, ast.Name)
            ):
                continue
            registrar = decorator.func.value.id
            if registrar not in servers or servers[registrar] >= statement.lineno:
                continue
            local_name = outer.args[0].id
            target: tuple[str, str] | None = None
            resolution = "same-module-single-definition"
            imported = imported_targets.get(local_name, [])
            if len(imported) == 1 and imported[0][2] < statement.lineno:
                target = (imported[0][0], imported[0][1])
                resolution = "relative-import-single-definition"
            elif (
                (path, local_name) in definitions
                and definitions[(path, local_name)].lineno < statement.lineno
            ):
                target = (path, local_name)
            if target not in definitions:
                continue
            needs_approval = any(
                keyword.arg in {"needs_approval", "require_approval"}
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in decorator.keywords
            )
            proposals[target].append(
                PythonToolRegistration(
                    Evidence(path, statement.lineno, excerpt(lines, statement.lineno)),
                    f"{registrar}.tool",
                    resolution,
                    needs_approval,
                )
            )

    return {
        target: registrations[0]
        for target, registrations in proposals.items()
        if len(registrations) == 1
    }


def repository_files(root: Path) -> list[Path]:
    paths = []
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in SKIP_DIRECTORIES and not (directory_path / name).is_symlink()
        )
        paths.extend(directory_path / name for name in sorted(file_names))
    return paths


def scan_repository(
    root: Path,
    *,
    include_tests: bool = False,
    selected_paths: list[str] | set[str] | tuple[str, ...] | None = None,
    require_suppression_expiry: bool = False,
    current_date: date | None = None,
) -> RepositoryIR:
    root = root.resolve()
    ir = RepositoryIR(str(root))
    source_lines: dict[str, list[str]] = {}
    paths = repository_files(root)
    module_paths = build_python_module_index(root, paths)
    selectors: list[Path] | None = None
    if selected_paths is not None:
        selectors = []
        for value in selected_paths:
            if value == "":
                continue
            selector = Path(value)
            if selector.is_absolute() or ".." in selector.parts:
                raise ValueError(f"selected path must stay inside the scan root: {value}")
            normalized = Path(*[part for part in selector.parts if part not in {"", "."}])
            selectors.append(normalized)
        selectors = sorted(set(selectors), key=lambda item: item.as_posix())
        ir.scan_scope = "selected-paths"
        ir.path_filters = [selector.as_posix() for selector in selectors]
    registry_paths = [
        path
        for path in paths
        if selectors is None
        or any(
            path.relative_to(root) == selector or selector in path.relative_to(root).parents
            for selector in selectors
        )
    ]
    registry_class_exports = build_python_registry_class_exports(
        root,
        registry_paths,
        module_paths,
    )
    registered_tool_functions = build_python_tool_registrations(
        root,
        registry_paths,
        module_paths,
    )
    for path in paths:
        relative_path = path.relative_to(root)
        if path.is_symlink() or not path.is_file() or set(relative_path.parts) & SKIP_DIRECTORIES:
            continue
        if selectors is not None and not any(
            relative_path == selector or selector in relative_path.parents for selector in selectors
        ):
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                if path.suffix.lower() in SOURCE_SUFFIXES or path.name in {
                    "mcp.json",
                    ".mcp.json",
                    "claude_desktop_config.json",
                }:
                    ir.errors.append(
                        f"{relative_path.as_posix()}: skipped file larger than {MAX_SOURCE_BYTES} bytes"
                    )
                continue
        except OSError as error:
            ir.errors.append(f"{path}: {error}")
            continue
        if path.name in {"mcp.json", ".mcp.json", "claude_desktop_config.json"}:
            scan_mcp_config(ir, root, path)
            ir.config_files_scanned += 1
        if is_container_config(path):
            scan_container_config(ir, root, path)
            ir.config_files_scanned += 1
            try:
                source_lines[relative_path.as_posix()] = path.read_text(
                    encoding="utf-8-sig", errors="ignore"
                ).splitlines()
            except OSError:
                pass
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError as error:
            ir.errors.append(f"{path}: {error}")
            continue
        ir.files_scanned += 1
        source_lines[relative_path.as_posix()] = text.splitlines()
        if path.suffix.lower() == ".py":
            scan_python(
                ir,
                root,
                path,
                text,
                module_paths,
                registry_class_exports,
                registered_tool_functions,
            )
        else:
            scan_typescript(ir, root, path, text)
    ir.components.sort(
        key=lambda item: (item.evidence.path, item.evidence.line, item.kind, item.name)
    )
    ir.relationships.sort(
        key=lambda item: (
            item.evidence.path,
            item.evidence.line,
            item.source_kind,
            item.source_name,
            item.relation,
            item.target_kind,
            item.target_name,
        )
    )
    run_rules(ir, include_tests=include_tests)
    apply_inline_suppressions(
        ir,
        source_lines,
        require_expiry=require_suppression_expiry,
        current_date=current_date,
    )
    ir.findings.sort(key=lambda item: (item.evidence.path, item.evidence.line, item.rule_id))
    return ir
