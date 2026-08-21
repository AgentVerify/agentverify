"""Python AST and TypeScript lexical frontends for AgentVerify."""

from __future__ import annotations

import ast
import json
import os
import re
import warnings
from collections import Counter
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
        call_symbol_ids: dict[int, str],
        definition_symbol_ids: dict[int, str],
    ) -> None:
        self.ir = ir
        self.root = root
        self.path = path
        self.lines = lines
        self.current_tool: str | None = None
        self.current_tool_id: str | None = None
        self.class_stack: list[str] = []
        self.active_audit_controls: list[Evidence] = []
        self.http_client_names: set[str] = set()
        self.allowlisted_names: set[str] = set()
        self.allowlist_evidence: dict[str, Evidence] = {}
        self.allowlist_control_names: dict[str, str] = {}
        self.approval_environment_flags: dict[str, set[str]] = {}
        self.module_approval_environment_flags: dict[str, set[str]] = {}
        self.class_approval_environment_flags: list[dict[str, set[str]]] = []
        self.function_stack: list[str] = []
        self.function_depth = 0
        self.imported_symbol_paths: dict[str, str] = {}
        self.imported_symbol_names: dict[str, str] = {}
        self.module_paths = module_paths
        self.local_symbol_ids = local_symbol_ids
        self.ambiguous_local_symbols = ambiguous_local_symbols
        self.call_symbol_ids = call_symbol_ids
        self.definition_symbol_ids = definition_symbol_ids
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

    def ev(self, node: ast.AST) -> Evidence:
        line = getattr(node, "lineno", 1)
        return Evidence(self.path, line, excerpt(self.lines, line))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            component_from_import(self.ir, alias.name, self.ev(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            target = None
            if node.level == 0 and node.module:
                target = self.module_paths.get(node.module)
            elif node.level:
                base = Path(self.path).parent
                if node.level - 1 < len(base.parts):
                    for _ in range(node.level - 1):
                        base = base.parent
                    module_parts = (node.module or alias.name).split(".")
                    module_path = base.joinpath(*module_parts)
                    candidates = [module_path.with_suffix(".py"), module_path / "__init__.py"]
                    resolved = [
                        candidate
                        for candidate in candidates
                        if not candidate.is_absolute()
                        and ".." not in candidate.parts
                        and (self.root / candidate).is_file()
                        and not (self.root / candidate).is_symlink()
                    ]
                    if len(resolved) == 1:
                        target = resolved[0].as_posix()
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
        decorators = {
            dotted_name(decorator.func)
            if isinstance(decorator, ast.Call)
            else dotted_name(decorator)
            for decorator in node.decorator_list
        }
        if decorators & TOOL_DECORATORS or any(name.endswith(".tool") for name in decorators):
            qualified_name = ".".join([*self.class_stack, node.name])
            tool_id = (
                self.definition_symbol_ids.get(id(node))
                or self.local_symbol_ids.get(("tool", qualified_name))
                or source_symbol("py", self.path, "tool", qualified_name)
            )
            needs_approval = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    needs_approval = needs_approval or any(
                        keyword.arg in {"needs_approval", "require_approval"}
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                        for keyword in decorator.keywords
                    )
            self.ir.add_component(
                Component(
                    "tool",
                    node.name,
                    self.ev(node),
                    {"decorators": sorted(decorators), "needs_approval": needs_approval},
                    tool_id,
                )
            )
            if needs_approval:
                self.ir.add_component(Component("control", "human-approval", self.ev(node)))
                self.ir.add_relationship(
                    Relationship(
                        "tool",
                        node.name,
                        "governed-by",
                        "control",
                        "human-approval",
                        self.ev(node),
                        source_id=tool_id,
                    )
                )
            previous_tool = self.current_tool
            previous_tool_id = self.current_tool_id
            self.current_tool = node.name
            self.current_tool_id = tool_id
            self.visit_function_statements(node)
            self.current_tool = previous_tool
            self.current_tool_id = previous_tool_id
        else:
            self.visit_function_statements(node)
        self.allowlisted_names = previous_allowlisted_names
        self.allowlist_evidence = previous_allowlist_evidence
        self.allowlist_control_names = previous_allowlist_control_names
        self.http_client_names = previous_http_client_names
        self.function_depth -= 1
        self.function_stack.pop()
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
        self.class_stack.pop()

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
                    target_id = self.local_symbol_ids.get((target_kind, target_name))
                    if isinstance(value, ast.Call) and dotted_name(value.func).endswith(".as_tool"):
                        target_name = dotted_name(value.func).removesuffix(".as_tool")
                        target_kind = "agent"
                        relation = "delegates-to"
                        target_id = self.local_symbol_ids.get(("agent", target_name))
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
                        elif target_id is None and (
                            target_kind,
                            target_name,
                        ) in self.ambiguous_local_symbols:
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
                guard_control = self.allowlist_control_names.get(guarded_name, "tool-allowlist")
                guard_evidence = self.allowlist_evidence.get(guarded_name)
                allowlist_guard = resolved_guard and guard_control == "tool-allowlist"
                registry_guard = resolved_guard and guard_control == "tool-registry"
                attributes = {
                    "api": call_name,
                    "dynamic_tool_name": True,
                    "dynamic_arguments": arguments is not None
                    and not isinstance(arguments, ast.Dict),
                    "allowlist_guard": allowlist_guard,
                    "registry_guard": registry_guard,
                    "scope": source_scope(self.path),
                }
                if resolved_guard:
                    attributes["guard_control"] = guard_control
                    if guard_evidence:
                        attributes["guard_path"] = guard_evidence.path
                        attributes["guard_line"] = guard_evidence.line
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
                if resolved_guard:
                    policy_effect = (
                        "routing-only"
                        if guard_control == "tool-registry"
                        else "restricts-tool-name"
                    )
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
                            {
                                "control_path": (guard_evidence or self.ev(node)).path,
                                "control_line": (guard_evidence or self.ev(node)).line,
                                "policy_effect": policy_effect,
                            },
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
        if short_name in {"open", "write_text", "write_bytes", "unlink", "rmdir", "mkdir"}:
            path_expression = node.args[0] if short_name == "open" and node.args else None
            mode_expression = node.args[1] if short_name == "open" and len(node.args) > 1 else None
            for keyword in node.keywords:
                if short_name == "open" and keyword.arg == "mode":
                    mode_expression = keyword.value
            mode = str(mode_expression.value) if isinstance(mode_expression, ast.Constant) else "r"
            write_access = short_name != "open" or any(flag in mode for flag in "wax+")
            dynamic_path = short_name != "open" or not isinstance(path_expression, ast.Constant)
            self.add_capability(
                "filesystem",
                node,
                {
                    "api": call_name,
                    "write_access": write_access,
                    "dynamic_path": dynamic_path,
                },
            )
        root_name = call_name.split(".", 1)[0]
        http_method = short_name.lower() in {"get", "post", "put", "patch", "delete", "request"}
        if root_name in {"requests", "httpx", "aiohttp"} or (
            self.has_http_import and root_name in self.http_client_names and http_method
        ):
            self.add_capability("network", node, {"api": call_name})
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
    ir: RepositoryIR, root: Path, path: Path, text: str, module_paths: dict[str, str]
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
    symbol_candidates: dict[tuple[str, str], set[str]] = {}
    call_symbol_ids: dict[int, str] = {}
    definition_symbol_ids: dict[int, str] = {}
    decorated_tools: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]] = []

    def collect_definitions(statements: list[ast.stmt], class_stack: tuple[str, ...] = ()) -> None:
        for node in statements:
            if isinstance(node, ast.ClassDef):
                collect_definitions(node.body, (*class_stack, node.name))
                continue
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = {
                dotted_name(decorator.func)
                if isinstance(decorator, ast.Call)
                else dotted_name(decorator)
                for decorator in node.decorator_list
            }
            if decorators & TOOL_DECORATORS or any(name.endswith(".tool") for name in decorators):
                qualified_name = ".".join([*class_stack, node.name])
                decorated_tools.append((node, qualified_name))
            collect_definitions(node.body, class_stack)

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
        identity = (
            f"{binding}@{node.lineno}"
            if assignment_counts[(kind, binding)] > 1
            else binding
        )
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
    PythonVisitor(
        ir,
        root,
        relative,
        text.splitlines(),
        imported_modules=imported_modules,
        module_paths=module_paths,
        local_symbol_ids=local_symbol_ids,
        ambiguous_local_symbols=ambiguous_local_symbols,
        call_symbol_ids=call_symbol_ids,
        definition_symbol_ids=definition_symbol_ids,
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
        else:
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


def typescript_graph(
    ir: RepositoryIR,
    relative: str,
    text: str,
    lines: list[str],
    imported_symbols: dict[str, tuple[str, str]],
) -> dict[int, tuple[str, str]]:
    tool_by_line: dict[int, tuple[str, str]] = {}
    local_tool_ids: dict[str, str] = {}
    code = typescript_code_mask(text)
    openai_imports = {
        **typescript_named_import_bindings(text, "@openai/agents"),
        **typescript_named_import_bindings(text, "@openai/agents-extensions"),
    }
    cline_imports = typescript_named_import_bindings(text, "@cline/sdk")
    tool_matches = list(TS_TOOL_ASSIGNMENT.finditer(code))
    tool_assignment_counts = Counter(match.group(1) for match in tool_matches)
    for match in tool_matches:
        tool_name = match.group(1)
        local_factory = match.group(2)
        constructor = openai_imports.get(
            local_factory, cline_imports.get(local_factory, local_factory)
        )
        is_generic = constructor in TS_GENERIC_TOOL_FACTORIES or (
            local_factory in cline_imports and constructor == "createTool"
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
        ev = Evidence(relative, start_line, excerpt(lines, start_line))
        tool_identity = (
            f"{tool_name}@{start_line}"
            if tool_assignment_counts[tool_name] > 1
            else tool_name
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
                    ev,
                    {
                        "constructor": constructor,
                        "needs_approval": approval_match is not None,
                    },
                    tool_id,
                )
            )
            if approval_match:
                approval_line = line_at(text, opening + 1 + approval_match.start())
                approval_ev = Evidence(relative, approval_line, excerpt(lines, approval_line))
                ir.add_component(Component("control", "human-approval", approval_ev))
                ir.add_relationship(
                    Relationship(
                        "tool",
                        tool_name,
                        "governed-by",
                        "control",
                        "human-approval",
                        approval_ev,
                        source_id=tool_id,
                    )
                )
        for line_number in range(start_line, end_line + 1):
            tool_by_line[line_number] = (tool_name, tool_id)

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
                local_factory, cline_imports.get(local_factory, local_factory)
            )
            call_line = line_at(text, item_offset)
            tool_name = f"{constructor}@{call_line}"
            target_id = None
            if constructor in TS_GENERIC_TOOL_FACTORIES or (
                local_factory in cline_imports and constructor == "createTool"
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
    return tool_by_line


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


def scan_typescript(ir: RepositoryIR, root: Path, path: Path, text: str) -> None:
    relative = path.relative_to(root).as_posix()
    lines = text.splitlines()
    imported_symbols = resolve_typescript_imports(root, path, text)
    tool_by_line = typescript_graph(ir, relative, text, lines, imported_symbols)
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
                },
            )
        if re.search(r"\b(?:fetch|axios\.(?:get|post|put|patch|delete))\s*\(", code_line):
            add_typescript_capability(ir, relative, line_number, ev, tool_by_line, "network")
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
            scan_python(ir, root, path, text, module_paths)
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
