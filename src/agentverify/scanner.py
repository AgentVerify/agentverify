"""Python AST and TypeScript lexical frontends for AgentVerify."""

from __future__ import annotations

import ast
import json
import re
import warnings
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .ir import Component, Evidence, Relationship, RepositoryIR
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
APPROVAL_BYPASS_NAME = re.compile(
    r"(?:auto_?approve|skip_?confirmation|dangerously_?skip)", re.IGNORECASE
)


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


class PythonVisitor(ast.NodeVisitor):
    def __init__(
        self, ir: RepositoryIR, path: str, lines: list[str], *, imported_modules: set[str]
    ) -> None:
        self.ir = ir
        self.path = path
        self.lines = lines
        self.current_tool: str | None = None
        self.allowlisted_names: set[str] = set()
        self.has_mcp_import = any(
            module == "mcp" or module.startswith("mcp.") or "modelcontextprotocol" in module
            for module in imported_modules
        )
        self.has_browser_import = any(
            module.startswith(("playwright", "selenium", "puppeteer"))
            for module in imported_modules
        )

    def add_capability(self, name: str, node: ast.AST, attributes: dict | None = None) -> None:
        values = {"scope": source_scope(self.path), **(attributes or {})}
        self.ir.add_component(Component("capability", name, self.ev(node), values))
        if self.current_tool:
            self.ir.add_relationship(
                Relationship("tool", self.current_tool, "uses", "capability", name, self.ev(node))
            )

    def ev(self, node: ast.AST) -> Evidence:
        line = getattr(node, "lineno", 1)
        return Evidence(self.path, line, excerpt(self.lines, line))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            component_from_import(self.ir, alias.name, self.ev(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
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
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        previous_allowlisted_names = self.allowlisted_names
        self.allowlisted_names = self.function_allowlisted_names(node)
        decorators = {
            dotted_name(decorator.func)
            if isinstance(decorator, ast.Call)
            else dotted_name(decorator)
            for decorator in node.decorator_list
        }
        if decorators & TOOL_DECORATORS or any(name.endswith(".tool") for name in decorators):
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
                )
            )
            if needs_approval:
                self.ir.add_component(Component("control", "human-approval", self.ev(node)))
                self.ir.add_relationship(
                    Relationship(
                        "tool", node.name, "governed-by", "control", "human-approval", self.ev(node)
                    )
                )
            previous_tool = self.current_tool
            self.current_tool = node.name
            self.generic_visit(node)
            self.current_tool = previous_tool
        else:
            self.generic_visit(node)
        self.allowlisted_names = previous_allowlisted_names

    visit_AsyncFunctionDef = visit_FunctionDef

    @staticmethod
    def function_allowlisted_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
        guarded = set()
        for statement in node.body:
            if not isinstance(statement, ast.If) or not isinstance(statement.test, ast.Compare):
                continue
            comparison = statement.test
            if (
                isinstance(comparison.left, ast.Name)
                and len(comparison.ops) == 1
                and isinstance(comparison.ops[0], ast.NotIn)
                and any(isinstance(child, (ast.Raise, ast.Return)) for child in statement.body)
            ):
                guarded.add(comparison.left.id)
        return guarded

    def visit_Call(self, node: ast.Call) -> None:
        call_name = dotted_name(node.func)
        short_name = call_name.rsplit(".", 1)[-1]
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
            self.ir.add_component(
                Component("agent", name, self.ev(node), {"constructor": call_name})
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
                    if isinstance(value, ast.Call) and dotted_name(value.func).endswith(".as_tool"):
                        target_name = dotted_name(value.func).removesuffix(".as_tool")
                        target_kind = "agent"
                        relation = "delegates-to"
                    if target_name:
                        self.ir.add_relationship(
                            Relationship(
                                "agent", name, relation, target_kind, target_name, self.ev(node)
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
                allowlist_guard = (
                    isinstance(tool_name, ast.Name) and tool_name.id in self.allowlisted_names
                )
                attributes = {
                    "api": call_name,
                    "dynamic_tool_name": True,
                    "dynamic_arguments": arguments is not None
                    and not isinstance(arguments, ast.Dict),
                    "allowlist_guard": allowlist_guard,
                    "scope": source_scope(self.path),
                }
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
                        )
                    )
                if allowlist_guard:
                    self.ir.add_component(Component("control", "tool-allowlist", self.ev(node)))
                    self.ir.add_relationship(
                        Relationship(
                            "capability",
                            "mcp-tool-forwarding",
                            "governed-by",
                            "control",
                            "tool-allowlist",
                            self.ev(node),
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
        if root_name in {"requests", "httpx", "aiohttp"}:
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


def scan_python(ir: RepositoryIR, root: Path, path: Path, text: str) -> None:
    relative = path.relative_to(root).as_posix()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text, filename=relative)
    except SyntaxError as error:
        ir.errors.append(f"{relative}:{error.lineno}: {error.msg}")
        return
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    PythonVisitor(ir, relative, text.splitlines(), imported_modules=imported_modules).visit(tree)


TS_IMPORT = re.compile(r"(?:from\s+|require\s*\(\s*)['\"]([^'\"]+)['\"]")
TS_AGENT = re.compile(r"\b(?:new\s+)?(Agent|AssistantAgent|StateGraph|Crew)\s*\(")
TS_MCP = re.compile(r"\b(McpServer|Client|StdioClientTransport)\s*\(")
TS_SHELL = re.compile(r"\b(exec|execSync|spawn|spawnSync)\s*\((.+)")
TS_CHILD_PROCESS_IMPORT = re.compile(
    r"import\s*\{([^}]+)\}\s*from\s*['\"](?:node:)?child_process['\"]",
    re.DOTALL,
)
TS_TOOL_ASSIGNMENT = re.compile(r"\b(?:const|let)\s+(\w+)\s*=\s*(?:tool|functionTool)\s*\(")
TS_AGENT_ASSIGNMENT = re.compile(r"\b(?:const|let)\s+(\w+)\s*=\s*new\s+Agent\s*\(")
TS_LITERAL_APPROVAL = re.compile(r"\bneedsApproval\s*:\s*true\b")
TS_AUTO_APPROVAL_ENABLED = re.compile(
    r"\b(?:autoApprove|auto_approve|skipConfirmation|dangerouslySkip\w*)\b"
    r"\s*(?:=|:)\s*(?:true|['\"](?:1|true|all)['\"])",
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
CONTAINER_CONFIG_SUFFIXES = {".yml", ".yaml"}


def line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def balanced_call_end(text: str, opening_parenthesis: int) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(opening_parenthesis, len(text)):
        character = text[index]
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"', "`"}:
            quote = character
        elif character == "(":
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


def typescript_graph(
    ir: RepositoryIR, relative: str, text: str, lines: list[str]
) -> dict[int, str]:
    tool_by_line: dict[int, str] = {}
    for match in TS_TOOL_ASSIGNMENT.finditer(text):
        tool_name = match.group(1)
        start_line = line_at(text, match.start())
        end = balanced_call_end(text, text.find("(", match.start(), match.end()))
        end_line = line_at(text, end)
        body = text[match.end() : end]
        approval_match = TS_LITERAL_APPROVAL.search(typescript_code_mask(body))
        ev = Evidence(relative, start_line, excerpt(lines, start_line))
        ir.add_component(
            Component(
                "tool",
                tool_name,
                ev,
                {"constructor": "tool", "needs_approval": approval_match is not None},
            )
        )
        if approval_match:
            approval_line = line_at(text, match.end() + approval_match.start())
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
                )
            )
        for line_number in range(start_line, end_line + 1):
            tool_by_line[line_number] = tool_name
    for match in TS_AGENT_ASSIGNMENT.finditer(text):
        variable_name = match.group(1)
        start_line = line_at(text, match.start())
        end = balanced_call_end(text, text.find("(", match.start(), match.end()))
        body = text[match.end() : end]
        name_match = re.search(r"\bname\s*:\s*['\"]([^'\"]+)['\"]", body)
        agent_name = name_match.group(1) if name_match else variable_name
        ev = Evidence(relative, start_line, excerpt(lines, start_line))
        ir.add_component(Component("agent", agent_name, ev, {"constructor": "Agent"}))
        tools_match = re.search(r"\btools\s*:\s*\[([^\]]*)\]", body, re.DOTALL)
        if tools_match:
            for tool_name in re.findall(r"\b[A-Za-z_$][\w$]*\b", tools_match.group(1)):
                ir.add_relationship(
                    Relationship("agent", agent_name, "uses", "tool", tool_name, ev)
                )
    return tool_by_line


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
    tool_by_line: dict[int, str],
    name: str,
    attributes: dict | None = None,
) -> None:
    values = {"scope": source_scope(relative), **(attributes or {})}
    ir.add_component(Component("capability", name, evidence, values))
    if tool_name := tool_by_line.get(line_number):
        ir.add_relationship(Relationship("tool", tool_name, "uses", "capability", name, evidence))


def scan_typescript(ir: RepositoryIR, root: Path, path: Path, text: str) -> None:
    relative = path.relative_to(root).as_posix()
    lines = text.splitlines()
    tool_by_line = typescript_graph(ir, relative, text, lines)
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
    for line_number, line in enumerate(lines, start=1):
        ev = Evidence(relative, line_number, line.strip()[:240])
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
        if line_number not in structured_agent_lines and (match := TS_AGENT.search(line)):
            ir.add_component(
                Component("agent", match.group(1), ev, {"constructor": match.group(1)})
            )
        if match := TS_MCP.search(line):
            ir.add_component(Component("mcp", match.group(1), ev, {"constructor": match.group(1)}))
        if (match := TS_SHELL.search(line)) and match.group(1) in shell_bindings:
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
                    "dynamic_command": True,
                },
            )
        if TS_DYNAMIC_EVAL.search(line):
            add_typescript_capability(
                ir,
                relative,
                line_number,
                ev,
                tool_by_line,
                "code-execution",
                {"api": "eval", "dynamic_input": True},
            )
        if match := TS_FILESYSTEM_WRITE.search(line):
            path_argument = match.group(1).strip()
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
        if re.search(r"\b(?:fetch|axios\.(?:get|post|put|patch|delete))\s*\(", line):
            add_typescript_capability(ir, relative, line_number, ev, tool_by_line, "network")
        if re.search(r"\baxios\.(?:post|put|patch|delete)\s*\(", line) or re.search(
            r"\bmethod\s*:\s*['\"](?:POST|PUT|PATCH|DELETE)['\"]", line, re.IGNORECASE
        ):
            add_typescript_capability(
                ir, relative, line_number, ev, tool_by_line, "external-action"
            )
        if has_browser_import and re.search(r"\.(?:click|goto|fill|press|selectOption)\s*\(", line):
            add_typescript_capability(ir, relative, line_number, ev, tool_by_line, "browser")
        if TS_AUTO_APPROVAL_ENABLED.search(line):
            ir.add_component(
                Component(
                    "control-setting",
                    "auto-approval",
                    ev,
                    {"enabled": True, "scope": source_scope(relative)},
                )
            )
        if has_mcp_import and TS_MCP_DYNAMIC_CALL.search(line):
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
    return path.suffix.lower() in CONTAINER_CONFIG_SUFFIXES and (
        "compose" in path.name.lower() or ".devcontainer" in path.parts
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
        if "/var/run/docker.sock" in stripped:
            boundary = "docker-socket"
        elif re.match(r"^privileged\s*:\s*true\s*(?:#.*)?$", stripped, re.IGNORECASE):
            boundary = "privileged-container"
        elif re.match(r"^network_mode\s*:\s*['\"]?host['\"]?\s*(?:#.*)?$", stripped):
            boundary = "host-network"
        elif re.match(r"^-\s*['\"]?/\s*:", stripped) or (
            host_path_pending and re.match(r"^path\s*:\s*['\"]?/['\"]?\s*(?:#.*)?$", stripped)
        ):
            boundary = "root-host-mount"
        host_path_pending = bool(re.match(r"^hostPath\s*:\s*$", stripped))
        if boundary:
            ir.add_component(
                Component(
                    "sandbox-boundary",
                    boundary,
                    Evidence(relative, line_number, stripped[:240]),
                    {"scope": source_scope(relative)},
                )
            )


def scan_repository(root: Path, *, include_tests: bool = False) -> RepositoryIR:
    root = root.resolve()
    ir = RepositoryIR(str(root))
    for path in sorted(root.rglob("*")):
        if (
            path.is_symlink()
            or not path.is_file()
            or set(path.relative_to(root).parts) & SKIP_DIRECTORIES
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
                        f"{path.relative_to(root).as_posix()}: skipped file larger than {MAX_SOURCE_BYTES} bytes"
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
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError as error:
            ir.errors.append(f"{path}: {error}")
            continue
        ir.files_scanned += 1
        if path.suffix.lower() == ".py":
            scan_python(ir, root, path, text)
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
    ir.findings.sort(key=lambda item: (item.evidence.path, item.evidence.line, item.rule_id))
    return ir
