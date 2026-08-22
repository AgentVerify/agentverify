"""Python AST and TypeScript lexical frontends for AgentVerify."""

from __future__ import annotations

import ast
import json
import os
import re
import shlex
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
        "Google ADK": ("google.adk", "@google/adk", "@google/adk/"),
        "Semantic Kernel": (
            "semantic_kernel",
            "@microsoft/semantic-kernel",
            "@microsoft/semantic-kernel/",
        ),
        "LlamaIndex": ("llama_index", "@llamaindex/"),
        "Agno": ("agno",),
        "Mastra": ("@mastra/",),
        "smolagents": ("smolagents",),
    },
    "provider": {
        "OpenAI": ("openai", "@ai-sdk/openai"),
        "Anthropic": ("anthropic", "@ai-sdk/anthropic"),
        "Azure OpenAI": ("azure.ai.openai",),
        "Google": (
            "google.genai",
            "google.generativeai",
            "@google/genai",
            "@google/genai/",
            "@google/generative-ai",
            "@ai-sdk/google",
            "@ai-sdk/google/",
            "@google-cloud/vertexai",
            "@google-cloud/vertexai/",
        ),
        "AWS Bedrock": (
            "@aws-sdk/client-bedrock-runtime",
            "@aws-sdk/client-bedrock-runtime/",
        ),
    },
    "protocol": {
        "MCP": ("mcp", "modelcontextprotocol", "@modelcontextprotocol/"),
    },
}

FRONTEND_IMPORT_SIGNATURES = {
    # Keep short ecosystem package names frontend-scoped. In particular, Python
    # `import ai` must not be treated as evidence for the TypeScript Vercel SDK.
    "python": {
        "framework": {
            "Microsoft Agent Framework": ("agent_framework",),
            "CAMEL": ("camel.agents",),
            "Qwen-Agent": ("qwen_agent",),
            "Lagent": ("lagent",),
            "MetaGPT": ("metagpt",),
            "Marvin": ("marvin.agents",),
            "AgentScope": ("agentscope",),
        },
        "provider": {
            "Mistral": ("mistralai",),
            "Groq": ("groq",),
            "Cohere": ("cohere",),
            "Ollama": ("ollama",),
        },
    },
    "typescript": {
        "framework": {
            "Vercel AI SDK": ("ai", "ai/"),
        },
        "provider": {
            "Mistral": ("@ai-sdk/mistral",),
            "Groq": ("@ai-sdk/groq",),
            "Cohere": ("@ai-sdk/cohere",),
        },
    },
}

AGENT_CALLS = {
    "Agent",
    "AssistantAgent",
    "ConversableAgent",
    "LlmAgent",
    "StateGraph",
    "Crew",
}
TOOL_DECORATORS = {"tool", "function_tool", "mcp.tool", "server.tool"}
MODEL_CONSTRUCTORS = {
    "OpenAI": {"OpenAI", "AsyncOpenAI", "ChatOpenAI", "OpenAIChatCompletionClient"},
    "Anthropic": {"Anthropic", "AsyncAnthropic", "ChatAnthropic"},
    "Azure OpenAI": {"AzureOpenAI", "AsyncAzureOpenAI", "AzureChatOpenAI"},
}
PYTHON_PROVIDER_SDK_CALLS = {
    "mistralai": ("Mistral",),
    "mistralai.client": ("Mistral",),
    "groq": ("AsyncGroq", "Groq"),
    "cohere": ("AsyncClient", "AsyncClientV2", "Client", "ClientV2"),
    "ollama": ("AsyncClient", "Client", "chat", "generate"),
    "langchain_mistralai": ("ChatMistralAI", "MistralAIEmbeddings"),
    "langchain_groq": ("ChatGroq",),
    "langchain_cohere": ("ChatCohere", "CohereEmbeddings", "CohereRerank"),
    "langchain_ollama": ("ChatOllama", "OllamaEmbeddings", "OllamaLLM"),
    "agentscope.model": (
        "AnthropicChatModel",
        "GeminiChatModel",
        "OllamaChatModel",
        "OpenAIChatModel",
        "OpenAIResponseModel",
    ),
    "pydantic_ai.models.groq": ("GroqModel",),
    "pydantic_ai.models.mistral": ("MistralModel",),
    "pydantic_ai.models.cohere": ("CohereModel",),
    "pydantic_ai.models.ollama": ("OllamaModel",),
    "pydantic_ai.embeddings.cohere": ("CohereEmbeddingModel",),
    "pydantic_ai.providers.groq": ("GroqProvider",),
    "pydantic_ai.providers.mistral": ("MistralProvider",),
    "pydantic_ai.providers.cohere": ("CohereProvider",),
    "pydantic_ai.providers.ollama": ("OllamaProvider",),
}
PYTHON_PROVIDER_MODULES = {
    "mistralai": "Mistral",
    "mistralai.client": "Mistral",
    "groq": "Groq",
    "cohere": "Cohere",
    "ollama": "Ollama",
    "langchain_mistralai": "Mistral",
    "langchain_groq": "Groq",
    "langchain_cohere": "Cohere",
    "langchain_ollama": "Ollama",
    "agentscope.model": "Ollama",
    "pydantic_ai.models.groq": "Groq",
    "pydantic_ai.models.mistral": "Mistral",
    "pydantic_ai.models.cohere": "Cohere",
    "pydantic_ai.models.ollama": "Ollama",
    "pydantic_ai.embeddings.cohere": "Cohere",
    "pydantic_ai.providers.groq": "Groq",
    "pydantic_ai.providers.mistral": "Mistral",
    "pydantic_ai.providers.cohere": "Cohere",
    "pydantic_ai.providers.ollama": "Ollama",
}
# Most supported modules have one provider identity. Public wrapper modules that
# span providers override that default for each exact exported symbol.
PYTHON_PROVIDER_SYMBOL_PROVIDERS = {
    ("agentscope.model", "AnthropicChatModel"): "Anthropic",
    ("agentscope.model", "GeminiChatModel"): "Google",
    ("agentscope.model", "OllamaChatModel"): "Ollama",
    ("agentscope.model", "OpenAIChatModel"): "OpenAI",
    ("agentscope.model", "OpenAIResponseModel"): "OpenAI",
}
PYTHON_PROVIDER_SDK_FUNCTIONS = {("ollama", "chat"), ("ollama", "generate")}
PYTHON_PROVIDER_WRAPPER_MODULE_PREFIXES = ("agentscope.", "langchain_", "pydantic_ai.")
PYTHON_PROVIDER_POSITIONAL_MODEL_CALLS = {
    ("ollama", "chat"),
    ("ollama", "generate"),
    ("pydantic_ai.models.groq", "GroqModel"),
    ("pydantic_ai.models.mistral", "MistralModel"),
    ("pydantic_ai.models.cohere", "CohereModel"),
    ("pydantic_ai.models.ollama", "OllamaModel"),
    ("pydantic_ai.embeddings.cohere", "CohereEmbeddingModel"),
}
TYPESCRIPT_AI_SDK_PROVIDER_EXPORTS = {
    "@ai-sdk/mistral": {
        "provider": "Mistral",
        "instance": "mistral",
        "factory": "createMistral",
    },
    "@ai-sdk/groq": {
        "provider": "Groq",
        "instance": "groq",
        "factory": "createGroq",
    },
    "@ai-sdk/cohere": {
        "provider": "Cohere",
        "instance": "cohere",
        "factory": "createCohere",
    },
}
BUILTIN_TOOL_CAPABILITIES = {
    "ShellTool": ("shell-execution",),
    "LocalShellTool": ("shell-execution",),
    "CodeInterpreterTool": ("code-execution",),
    "FileSearchTool": ("data-retrieval",),
    "ImageGenerationTool": ("media-generation",),
    "WebSearchTool": ("network",),
    "ApplyPatchTool": ("filesystem",),
    "ComputerTool": ("computer-control",),
    "CustomTool": ("external-action",),
}
EXACT_IMPORT_OPENAI_BUILTINS = frozenset(
    {
        "CodeInterpreterTool",
        "FileSearchTool",
        "ImageGenerationTool",
        "LocalShellTool",
        "WebSearchTool",
    }
)
OPENAI_BUILTINS_WITHOUT_APPROVAL = EXACT_IMPORT_OPENAI_BUILTINS
OPENAI_PROVIDER_HOSTED_BUILTINS = frozenset(
    {"FileSearchTool", "ImageGenerationTool", "WebSearchTool"}
)
EXACT_TOOL_CONSTRUCTOR_IMPORTS = {
    ("agents", "HostedMCPTool"),
    ("google.adk.integrations.langchain", "LangchainTool"),
}
IMPORTED_TOOL_FACTORY_METHODS = {"from_settings"}
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
MCP_PACKAGE_LAUNCHERS = {"npx", "uvx"}
MCP_LAUNCHER_CONSTRUCTORS = {
    "MCPServer",
    "MCPServerStdio",
    "MCPTools",
    "StdioServerParameters",
}
MCP_IN_PROCESS_SERVER_CONSTRUCTORS = {"FastMCP"}


def is_mcp_server_constructor_module(module: str, constructor: str) -> bool:
    if constructor in MCP_IN_PROCESS_SERVER_CONSTRUCTORS:
        return bool(
            module in {"fastmcp", "mcp.server"}
            or module.startswith(("fastmcp.", "mcp.server."))
        )
    return bool(
        re.search(r"(?:^|[._])mcp(?:[._]|$)", module, re.IGNORECASE)
        or "modelcontextprotocol" in module.lower()
    )


def literal_string_arguments(node: ast.AST | None) -> list[str | None] | None:
    """Return a literal-preserving argument sequence, including an unresolved suffix."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return [
            item.value
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
            else None
            for item in node.elts
        ]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        prefix = literal_string_arguments(node.left)
        return [*prefix, None] if prefix is not None else None
    return None


def mcp_package_reference(
    command: str,
    arguments: list[str | None],
) -> dict[str, object] | None:
    """Resolve the package selected by a literal npx/uvx MCP launcher."""
    if command not in MCP_PACKAGE_LAUNCHERS:
        return None
    automatic = command == "uvx"
    no_install = False
    package_spec: str | None = None
    uvx_source_spec: str | None = None
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value is None:
            return None
        if command == "npx":
            if value in {"-y", "--yes"}:
                automatic = True
                index += 1
                continue
            if value == "--no-install":
                no_install = True
                index += 1
                continue
            if value in {"--quiet", "-q"}:
                index += 1
                continue
            if value in {"-p", "--package", "-c", "--call"} or value.startswith(
                ("--package=", "--call=")
            ):
                return None
        else:
            if value in {"--isolated", "--no-cache", "--refresh", "--offline"}:
                index += 1
                continue
            if value in {
                "--with",
                "--with-editable",
                "--python",
                "--index",
                "--default-index",
                "--index-url",
                "--extra-index-url",
                "--find-links",
            }:
                if index + 1 >= len(arguments) or arguments[index + 1] is None:
                    return None
                index += 2
                continue
            if value == "--from":
                if index + 1 >= len(arguments) or arguments[index + 1] is None:
                    return None
                uvx_source_spec = arguments[index + 1]
                index += 2
                continue
            if value.startswith("--from="):
                uvx_source_spec = value.split("=", 1)[1]
                index += 1
                continue
            if value.startswith(
                (
                    "--with=",
                    "--with-editable=",
                    "--python=",
                    "--index=",
                    "--default-index=",
                    "--index-url=",
                    "--extra-index-url=",
                    "--find-links=",
                )
            ):
                index += 1
                continue
        if value.startswith("-"):
            return None
        package_spec = uvx_source_spec or value
        break
    if package_spec is None:
        return None

    package_name = package_spec
    reference = ""
    if command == "npx":
        if package_spec.startswith("@"):
            slash = package_spec.find("/")
            separator = package_spec.rfind("@")
            if slash <= 1 or separator <= slash:
                separator = -1
        else:
            separator = package_spec.rfind("@")
        if separator > 0:
            package_name = package_spec[:separator]
            reference = package_spec[separator + 1 :]
        if not re.fullmatch(r"(?:@[\w.-]+/)?[\w.-]+", package_name):
            return None
    else:
        exact = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^=<>!~]+)", package_spec)
        if exact:
            package_name, reference = exact.groups()
        elif not re.fullmatch(r"[A-Za-z0-9_.-]+", package_spec):
            return None

    exact_version = bool(
        reference
        and (
            command == "uvx"
            or re.fullmatch(
                r"v?\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.-]+)?",
                reference,
            )
        )
    )
    return {
        "package": package_name,
        "package_spec": package_spec,
        "version_scope": (
            "exact" if exact_version else "floating" if reference else "unpinned"
        ),
        "auto_install": automatic and not no_install,
        "install_mode": (
            "disabled"
            if no_install
            else "automatic"
            if automatic
            else "prompt-or-local-cache"
        ),
    }


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


def python_static_url_prefix(
    node: ast.AST | None, known_prefixes: dict[str, str] | None = None
) -> str:
    known_prefixes = known_prefixes or {}
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, (ast.Name, ast.Attribute)):
        return known_prefixes.get(dotted_name(node), "")
    if isinstance(node, ast.JoinedStr):
        prefix = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                break
            prefix.append(value.value)
        return "".join(prefix)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return python_static_url_prefix(node.left, known_prefixes)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    ):
        return python_static_url_prefix(node.func.value, known_prefixes)
    return ""


def python_http_origin_is_dynamic(
    node: ast.AST | None,
    dynamic_names: set[str],
    known_prefixes: dict[str, str] | None = None,
) -> bool:
    if not python_expression_names(node) & dynamic_names:
        return False
    prefix = python_static_url_prefix(node, known_prefixes)
    return re.match(r"^https?://[^/?#]+", prefix, re.IGNORECASE) is None


def python_urllib_request_url(
    node: ast.AST | None,
    request_constructors: set[str],
) -> ast.AST | None:
    """Unwrap an import-proven urllib Request to its original URL expression."""
    if not (
        isinstance(node, ast.Call)
        and dotted_name(node.func) in request_constructors
    ):
        return node
    if node.args:
        return node.args[0]
    return next(
        (
            keyword.value
            for keyword in node.keywords
            if keyword.arg in {"url", "full_url"}
        ),
        None,
    )


def component_from_import(
    ir: RepositoryIR,
    module: str,
    evidence: Evidence,
    frontend: str,
) -> None:
    for signature_set in (
        IMPORT_SIGNATURES,
        FRONTEND_IMPORT_SIGNATURES.get(frontend, {}),
    ):
        for kind, signatures in signature_set.items():
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
    if lowered.startswith(("gemini-", "models/gemini-", "google/gemini-")):
        return "Google"
    if lowered.startswith(
        (
            "codestral-",
            "devstral-",
            "magistral-",
            "ministral-",
            "mistral-",
            "open-codestral-",
            "open-mistral-",
            "open-mixtral-",
            "pixtral-",
            "shieldstral-",
            "voxtral-",
        )
    ):
        return "Mistral"
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


def python_approval_bypass_function_summaries(
    tree: ast.Module,
) -> dict[str, tuple[str, ...]]:
    """Resolve same-file approval callbacks that can return true from an env flag."""
    module_flags: dict[str, set[str]] = {}
    for statement in tree.body:
        value = None
        targets: list[ast.expr] = []
        if isinstance(statement, ast.Assign):
            value = statement.value
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            value = statement.value
            targets = [statement.target]
        if value is None:
            continue
        environment_names = python_approval_environment_names(value)
        if not environment_names:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and APPROVAL_BYPASS_ENV_NAME.search(target.id):
                module_flags[target.id] = environment_names

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    name_counts = Counter(node.name for node in functions)
    functions_by_name = {node.name: node for node in functions if name_counts[node.name] == 1}

    class OwnedBodyVisitor(ast.NodeVisitor):
        def __init__(self, root: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            self.root = root
            self.nodes: list[ast.AST] = []

        def generic_visit(self, node: ast.AST) -> None:
            self.nodes.append(node)
            super().generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node is self.root:
                self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if node is self.root:
                self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            return

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

    direct: dict[str, set[str]] = {}
    calls: dict[str, set[str]] = {}
    for name, function in functions_by_name.items():
        visitor = OwnedBodyVisitor(function)
        visitor.visit(function)
        environment_names: set[str] = set()
        called_functions: set[str] = set()
        for node in visitor.nodes:
            if isinstance(node, ast.If):
                branch_returns_true = bool(
                    node.body
                    and isinstance(node.body[0], ast.Return)
                    and isinstance(node.body[0].value, ast.Constant)
                    and node.body[0].value.value is True
                )
                if branch_returns_true:
                    environment_names.update(python_approval_environment_names(node.test))
                    for candidate in ast.walk(node.test):
                        if isinstance(candidate, (ast.Name, ast.Attribute)):
                            environment_names.update(
                                module_flags.get(dotted_name(candidate), set())
                            )
            elif isinstance(node, ast.Call):
                called_functions.add(dotted_name(node.func).rsplit(".", 1)[-1])
        if environment_names:
            direct[name] = environment_names
        calls[name] = called_functions

    resolved = {name: set(values) for name, values in direct.items()}
    changed = True
    while changed:
        changed = False
        for name, called_functions in calls.items():
            inherited = {
                environment_name
                for called in called_functions
                for environment_name in resolved.get(called, set())
            }
            if inherited - resolved.get(name, set()):
                resolved.setdefault(name, set()).update(inherited)
                changed = True
    return {name: tuple(sorted(values)) for name, values in resolved.items()}


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


@dataclass(frozen=True)
class PythonAgentFactoryClassTarget:
    path: str
    name: str
    methods: dict[str, str]


@dataclass(frozen=True)
class PythonMCPServerSubclassTarget:
    path: str
    name: str
    line: int
    base_module: str
    base_name: str


@dataclass(frozen=True)
class PythonSecureNetworkPolicy:
    evidence: Evidence
    schemes: tuple[str, ...]
    redirect_scope: str
    dns_scope: str
    proxy_scope: str
    enforcement_default: str
    escape_hatch: str
    policy_effect: str = "restricts-http-origin-and-peer"
    initial_origin_scope: str = "public-addresses"
    bypass_environment: str | None = None
    force_safe_environment: str | None = None
    bypass_environments: tuple[str, ...] = ()


@dataclass(frozen=True)
class PythonNetworkHelperSummary:
    path: str
    name: str
    positional_parameters: tuple[str, ...]
    keyword_only_parameters: tuple[str, ...]
    controlled_parameters: tuple[str, ...]
    line: int
    network_lines: tuple[int, ...]
    secure_policy: PythonSecureNetworkPolicy | None = None


@dataclass(frozen=True)
class PythonClassNetworkSummary:
    path: str
    class_name: str
    method: str
    parameter: str
    parameter_key: str | None
    line: int
    network_lines: tuple[int, ...]


@dataclass(frozen=True)
class PythonImportResolution:
    path: str
    basis: str


@dataclass(frozen=True)
class PythonToolRoleReference:
    registration_path: str
    registration_line: int
    resolution: str
    import_line: int | None = None


@dataclass(frozen=True)
class PythonImportedToolReference:
    importer_path: str
    local_name: str
    original_name: str
    module: str
    import_line: int
    agent_line: int
    agent_col: int
    import_resolution: str | None = None
    target_path: str | None = None


def resolve_python_import(
    root: Path,
    current_path: str,
    node: ast.ImportFrom,
    alias_name: str,
    module_paths: dict[str, str],
) -> PythonImportResolution | None:
    """Resolve one absolute or relative Python import to a selected local file."""
    if node.level == 0 and node.module:
        if target := module_paths.get(node.module):
            return PythonImportResolution(target, "repository-module-single-path")
        module_parts = node.module.split(".")
        base = Path(current_path).parent
        candidates: set[str] = set()
        while True:
            module_path = base.joinpath(*module_parts)
            for candidate in (module_path.with_suffix(".py"), module_path / "__init__.py"):
                if (
                    not candidate.is_absolute()
                    and ".." not in candidate.parts
                    and (root / candidate).is_file()
                    and not (root / candidate).is_symlink()
                ):
                    candidates.add(candidate.as_posix())
            if base == Path("."):
                break
            base = base.parent
        if len(candidates) == 1:
            return PythonImportResolution(
                next(iter(candidates)),
                "contextual-absolute-import-single-path",
            )
        return None
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
    if len(resolved) == 1:
        return PythonImportResolution(
            resolved[0].as_posix(),
            "filesystem-relative-import-single-path",
        )
    return None


def resolve_python_import_path(
    root: Path,
    current_path: str,
    node: ast.ImportFrom,
    alias_name: str,
    module_paths: dict[str, str],
) -> str | None:
    """Return only the selected path for callers that do not need provenance."""
    resolution = resolve_python_import(root, current_path, node, alias_name, module_paths)
    return resolution.path if resolution is not None else None


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
class PythonNetworkOriginProof:
    evidence: Evidence
    url_name: str
    parser_name: str
    schemes: tuple[str, ...]
    hosts: tuple[str, ...]


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
    wrappers: tuple[str, ...] = ()


@dataclass(frozen=True)
class PythonFunctionToolWrapper:
    binding: str
    assignment: ast.Assign
    call: ast.Call
    function: ast.FunctionDef | ast.AsyncFunctionDef
    agent_call: ast.Call
    registrar: str


@dataclass(frozen=True)
class PythonRegistryTool:
    framework: str
    name: str
    registrar: str
    entrypoints: tuple[str, ...] = ()


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


def python_browser_annotation_is_type(
    annotation: ast.AST | None, browser_type_names: set[str]
) -> bool:
    """Return whether an annotation resolves to one exact imported browser receiver type."""
    if annotation is None:
        return False
    if dotted_name(annotation) in browser_type_names:
        return True
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        pairs = ((annotation.left, annotation.right), (annotation.right, annotation.left))
        return any(
            python_browser_annotation_is_type(candidate, browser_type_names)
            and isinstance(nullable, ast.Constant)
            and nullable.value is None
            for candidate, nullable in pairs
        )
    if not isinstance(annotation, ast.Subscript):
        return False
    wrapper = dotted_name(annotation.value).rsplit(".", 1)[-1]
    elements = (
        annotation.slice.elts
        if isinstance(annotation.slice, ast.Tuple)
        else [annotation.slice]
    )
    if wrapper in {"Annotated", "Optional"}:
        return bool(elements) and python_browser_annotation_is_type(
            elements[0], browser_type_names
        )
    if wrapper == "Union":
        browser_elements = [
            item
            for item in elements
            if python_browser_annotation_is_type(item, browser_type_names)
        ]
        nullable_elements = [
            item
            for item in elements
            if isinstance(item, ast.Constant) and item.value is None
        ]
        return len(browser_elements) == 1 and len(browser_elements) + len(
            nullable_elements
        ) == len(elements)
    return False


def python_class_browser_receiver_attributes(
    node: ast.ClassDef, browser_type_names: set[str]
) -> set[str]:
    """Resolve uniquely annotated Playwright receiver attributes in one class."""
    annotations: dict[str, list[ast.AST]] = defaultdict(list)

    def collect(candidate: ast.AST, initializer: ast.AST) -> None:
        if candidate is not initializer and isinstance(
            candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            return
        if (
            isinstance(candidate, ast.AnnAssign)
            and isinstance(candidate.target, ast.Attribute)
            and isinstance(candidate.target.value, ast.Name)
            and candidate.target.value.id == "self"
        ):
            annotations[candidate.target.attr].append(candidate.annotation)
        for child in ast.iter_child_nodes(candidate):
            collect(child, initializer)

    for statement in node.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            annotations[statement.target.id].append(statement.annotation)
        if not (
            isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            and statement.name == "__init__"
        ):
            continue
        collect(statement, statement)
    return {
        name
        for name, candidates in annotations.items()
        if len(candidates) == 1
        and python_browser_annotation_is_type(candidates[0], browser_type_names)
    }


def python_class_constructor_browser_receivers(
    node: ast.ClassDef, browser_runtime_factories: set[str]
) -> set[str]:
    """Resolve immutable Playwright pages constructed directly in ``__init__``."""
    initializers = [
        statement
        for statement in node.body
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        and statement.name == "__init__"
        and statement.args.args
        and statement.args.args[0].arg == "self"
    ]
    if len(initializers) != 1:
        return set()
    initializer = initializers[0]
    initializer_bindings = python_function_local_bindings(initializer)
    browser_runtime_factories = {
        factory
        for factory in browser_runtime_factories
        if factory.split(".", 1)[0] not in initializer_bindings
    }

    def self_attributes(target: ast.AST) -> set[str]:
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            return {target.attr}
        if isinstance(target, (ast.Tuple, ast.List)):
            return {
                name for element in target.elts for name in self_attributes(element)
            }
        return set()

    attribute_mutations: Counter[str] = Counter()
    for candidate in ast.walk(node):
        targets: list[ast.AST] = []
        if isinstance(candidate, ast.Assign):
            targets.extend(candidate.targets)
        elif isinstance(
            candidate,
            (ast.AnnAssign, ast.AugAssign, ast.NamedExpr, ast.For, ast.AsyncFor),
        ):
            targets.append(candidate.target)
        elif isinstance(candidate, ast.Delete):
            targets.extend(candidate.targets)
        elif isinstance(candidate, (ast.With, ast.AsyncWith)):
            targets.extend(
                item.optional_vars
                for item in candidate.items
                if item.optional_vars is not None
            )
        for target in targets:
            attribute_mutations.update(self_attributes(target))

    local_mutations: Counter[str] = Counter()
    for candidate in ast.walk(initializer):
        targets: list[ast.AST] = []
        if isinstance(candidate, ast.Assign):
            targets.extend(candidate.targets)
        elif isinstance(
            candidate,
            (ast.AnnAssign, ast.AugAssign, ast.NamedExpr, ast.For, ast.AsyncFor),
        ):
            targets.append(candidate.target)
        elif isinstance(candidate, ast.Delete):
            targets.extend(candidate.targets)
        elif isinstance(candidate, (ast.With, ast.AsyncWith)):
            targets.extend(
                item.optional_vars
                for item in candidate.items
                if item.optional_vars is not None
            )
        for target in targets:
            local_mutations.update(python_assigned_names(target))

    bindings: dict[str, str] = {}

    def unwrap(expression: ast.AST | None) -> ast.AST | None:
        return expression.value if isinstance(expression, ast.Await) else expression

    def resolve(expression: ast.AST | None) -> str | None:
        expression = unwrap(expression)
        if expression is None:
            return None
        name = dotted_name(expression)
        if name in bindings:
            return bindings[name]
        if not isinstance(expression, ast.Call):
            return None
        call_name = dotted_name(expression.func)
        if (
            call_name in browser_runtime_factories
            and not expression.args
            and not expression.keywords
        ):
            return "playwright-context-manager"
        if not isinstance(expression.func, ast.Attribute):
            return None
        receiver = expression.func.value
        if (
            expression.func.attr == "start"
            and not expression.args
            and not expression.keywords
            and resolve(receiver) == "playwright-context-manager"
        ):
            return "playwright-runtime"
        if (
            expression.func.attr == "launch"
            and isinstance(receiver, ast.Attribute)
            and receiver.attr in {"chromium", "firefox", "webkit"}
            and resolve(receiver.value) == "playwright-runtime"
        ):
            return "playwright-browser"
        receiver_kind = resolve(receiver)
        if expression.func.attr == "new_context" and receiver_kind == "playwright-browser":
            return "playwright-context"
        if expression.func.attr == "new_page" and receiver_kind in {
            "playwright-browser",
            "playwright-context",
        }:
            return "playwright-page"
        return None

    for statement in initializer.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        value = statement.value
        if len(targets) != 1 or value is None:
            continue
        target = targets[0]
        target_name = dotted_name(target)
        if isinstance(target, ast.Name):
            if local_mutations[target.id] != 1:
                continue
        elif (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            if attribute_mutations[target.attr] != 1:
                continue
        else:
            continue
        if binding := resolve(value):
            bindings[target_name] = binding

    return {
        name.removeprefix("self.")
        for name, binding in bindings.items()
        if name.startswith("self.") and binding == "playwright-page"
    }


def python_browser_receiver_proofs(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    browser_type_names: set[str],
    browser_page_factories: set[str],
    class_browser_attributes: dict[str, str],
) -> dict[int, str]:
    """Prove direct browser-page evaluate receivers without semantic name matching."""
    parents = {
        id(child): parent
        for parent in ast.walk(node)
        for child in ast.iter_child_nodes(parent)
    }

    def belongs_to_function(candidate: ast.AST) -> bool:
        parent = parents.get(id(candidate))
        while parent is not None:
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return parent is node
            parent = parents.get(id(parent))
        return False

    bindings = {
        argument.arg: "parameter-annotation"
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        if python_browser_annotation_is_type(argument.annotation, browser_type_names)
    }
    binding_lines = {name: 0 for name in bindings}
    mutation_counts: Counter[str] = Counter()
    for candidate in ast.walk(node):
        if not belongs_to_function(candidate):
            continue
        targets: list[ast.AST] = []
        if isinstance(candidate, ast.Assign):
            targets.extend(candidate.targets)
        elif isinstance(
            candidate,
            (ast.AnnAssign, ast.AugAssign, ast.NamedExpr, ast.For, ast.AsyncFor),
        ):
            targets.append(candidate.target)
        elif isinstance(candidate, ast.Delete):
            targets.extend(candidate.targets)
        elif isinstance(candidate, (ast.With, ast.AsyncWith)):
            targets.extend(
                item.optional_vars
                for item in candidate.items
                if item.optional_vars is not None
            )
        for target in targets:
            mutation_counts.update(python_assigned_names(target))

    bindings = {
        name: proof for name, proof in bindings.items() if mutation_counts[name] == 0
    }
    binding_lines = {name: binding_lines[name] for name in bindings}

    def assignment_dominates_continuation(candidate: ast.Assign) -> bool:
        child: ast.AST = candidate
        parent = parents.get(id(child))
        while parent is not None and parent is not node:
            if isinstance(parent, (ast.With, ast.AsyncWith)):
                child = parent
                parent = parents.get(id(parent))
                continue
            if isinstance(parent, ast.Try):
                if child not in parent.body or not parent.handlers or not all(
                    python_block_always_terminates(handler.body)
                    for handler in parent.handlers
                ):
                    return False
                child = parent
                parent = parents.get(id(parent))
                continue
            if isinstance(
                parent,
                (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Match, ast.TryStar),
            ):
                return False
            child = parent
            parent = parents.get(id(parent))
        return parent is node

    for candidate in sorted(ast.walk(node), key=lambda item: getattr(item, "lineno", 0)):
        if not (
            belongs_to_function(candidate)
            and isinstance(candidate, ast.Assign)
            and assignment_dominates_continuation(candidate)
        ):
            continue
        value = candidate.value.value if isinstance(candidate.value, ast.Await) else candidate.value
        factory_call = (
            value
            if isinstance(value, ast.Call) and dotted_name(value.func) in browser_page_factories
            else None
        )
        for target in candidate.targets:
            if (
                isinstance(target, ast.Name)
                and mutation_counts[target.id] == 1
                and isinstance(value, ast.Name)
                and value.id in bindings
            ):
                bindings[target.id] = "typed-parameter-alias"
                binding_lines[target.id] = candidate.lineno
            elif (
                isinstance(target, ast.Name)
                and mutation_counts[target.id] == 1
                and isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id == "self"
                and class_browser_attributes.get(value.attr)
                == "constructor-bound-playwright-page"
            ):
                bindings[target.id] = "constructor-bound-playwright-page-alias"
                binding_lines[target.id] = candidate.lineno
            elif (
                factory_call is not None
                and isinstance(target, (ast.Tuple, ast.List))
                and target.elts
                and isinstance(target.elts[0], ast.Name)
                and mutation_counts[target.elts[0].id] == 1
            ):
                bindings[target.elts[0].id] = "imported-browser-factory"
                binding_lines[target.elts[0].id] = candidate.lineno

    proofs: dict[int, str] = {}
    for candidate in ast.walk(node):
        if not (
            belongs_to_function(candidate)
            and isinstance(candidate, ast.Call)
            and isinstance(candidate.func, ast.Attribute)
            and candidate.func.attr == "evaluate"
        ):
            continue
        receiver_node = candidate.func.value
        if isinstance(receiver_node, ast.Name):
            receiver = receiver_node.id
            proof = bindings.get(receiver)
            if proof and binding_lines[receiver] < candidate.lineno:
                proofs[id(candidate)] = proof
        elif (
            isinstance(receiver_node, ast.Attribute)
            and isinstance(receiver_node.value, ast.Name)
            and receiver_node.value.id == "self"
            and receiver_node.attr in class_browser_attributes
            and node.args.args
            and node.args.args[0].arg == "self"
            and not any(
                dotted_name(decorator).rsplit(".", 1)[-1]
                in {"classmethod", "staticmethod"}
                for decorator in node.decorator_list
            )
        ):
            proofs[id(candidate)] = class_browser_attributes[receiver_node.attr]
    return proofs


def python_network_origin_guard_proofs(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path: str,
    lines: list[str],
    url_parser_names: set[str],
    module_literal_string_sets: dict[str, tuple[str, ...]],
) -> dict[int, PythonNetworkOriginProof]:
    """Resolve fail-closed scheme and hostname allowlists before direct URL calls."""
    parameters = {
        argument.arg
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        if argument.arg not in {"self", "cls"}
    }
    if not parameters or not url_parser_names:
        return {}

    mutation_counts: Counter[str] = Counter()

    def collect_mutations(candidate: ast.AST) -> None:
        if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        if isinstance(candidate, ast.Name) and isinstance(candidate.ctx, (ast.Store, ast.Del)):
            mutation_counts[candidate.id] += 1
        for child in ast.iter_child_nodes(candidate):
            collect_mutations(child)

    for statement in node.body:
        collect_mutations(statement)
    if any(mutation_counts[name] for name in parameters):
        parameters = {name for name in parameters if mutation_counts[name] == 0}
    if not parameters:
        return {}

    literal_sets = dict(module_literal_string_sets)
    url_aliases = {name: name for name in parameters}
    parsed_urls: dict[str, tuple[str, str]] = {}
    guarded: dict[str, dict[str, tuple[str, ...] | Evidence]] = {}
    proofs: dict[int, PythonNetworkOriginProof] = {}

    def literal_strings(expression: ast.AST) -> tuple[str, ...] | None:
        if isinstance(expression, ast.Name):
            return literal_sets.get(expression.id)
        if not isinstance(expression, (ast.List, ast.Tuple, ast.Set)):
            return None
        values = tuple(
            element.value
            for element in expression.elts
            if isinstance(element, ast.Constant)
            and isinstance(element.value, str)
        )
        return tuple(sorted(set(values))) if len(values) == len(expression.elts) else None

    def guard_terms(expression: ast.AST) -> list[tuple[str, str, tuple[str, ...]]]:
        if isinstance(expression, ast.BoolOp) and isinstance(expression.op, ast.Or):
            return [term for value in expression.values for term in guard_terms(value)]
        if not (
            isinstance(expression, ast.Compare)
            and len(expression.ops) == 1
            and len(expression.comparators) == 1
            and isinstance(expression.left, ast.Attribute)
            and isinstance(expression.left.value, ast.Name)
            and expression.left.attr in {"scheme", "hostname"}
        ):
            return []
        parser_name = expression.left.value.id
        operator = expression.ops[0]
        comparator = expression.comparators[0]
        values: tuple[str, ...] | None = None
        if isinstance(operator, ast.NotIn):
            values = literal_strings(comparator)
        elif (
            isinstance(operator, ast.NotEq)
            and isinstance(comparator, ast.Constant)
            and isinstance(comparator.value, str)
        ):
            values = (comparator.value,)
        if not values:
            return []
        normalized = tuple(sorted(set(values)))
        if any(value != value.lower().rstrip(".") for value in normalized):
            return []
        if expression.left.attr == "scheme":
            if any(value not in {"http", "https"} for value in normalized):
                return []
        elif any(
            not value
            or value.startswith(".")
            or any(character in value for character in "/*:@[]")
            for value in normalized
        ):
            return []
        return [(parser_name, expression.left.attr, normalized)]

    def lexical_calls(statement: ast.stmt) -> list[ast.Call]:
        calls: list[ast.Call] = []

        def collect(candidate: ast.AST) -> None:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            if isinstance(candidate, ast.Call):
                calls.append(candidate)
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        collect(statement)
        return calls

    def call_url_name(call: ast.Call) -> str | None:
        call_name = dotted_name(call.func)
        short_name = call_name.rsplit(".", 1)[-1].lower()
        expression: ast.AST | None = None
        if short_name == "request" and len(call.args) > 1:
            expression = call.args[1]
        elif call.args:
            expression = call.args[0]
        for keyword in call.keywords:
            if keyword.arg == "url":
                expression = keyword.value
        return expression.id if isinstance(expression, ast.Name) else None

    for statement in node.body:
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            value = statement.value
            if len(targets) == 1 and isinstance(targets[0], ast.Name) and value is not None:
                target = targets[0].id
                static_values = literal_strings(value)
                if (
                    mutation_counts[target] == 1
                    and isinstance(value, ast.Tuple)
                    and static_values
                ):
                    literal_sets[target] = static_values
                if (
                    mutation_counts[target] == 1
                    and isinstance(value, ast.Name)
                    and value.id in url_aliases
                ):
                    url_aliases[target] = url_aliases[value.id]
                if (
                    mutation_counts[target] == 1
                    and isinstance(value, ast.Call)
                    and dotted_name(value.func) in url_parser_names
                    and value.args
                    and isinstance(value.args[0], ast.Name)
                    and value.args[0].id in url_aliases
                ):
                    parsed_urls[target] = (
                        url_aliases[value.args[0].id],
                        dotted_name(value.func),
                    )
        for call in lexical_calls(statement):
            url_name = call_url_name(call)
            if url_name not in url_aliases:
                continue
            source_name = url_aliases[url_name]
            matches = [
                (parser_name, parser_call, state)
                for parser_name, (parsed_source, parser_call) in parsed_urls.items()
                if parsed_source == source_name
                and (state := guarded.get(parser_name)) is not None
                and isinstance(state.get("scheme"), tuple)
                and isinstance(state.get("hostname"), tuple)
                and isinstance(state.get("evidence"), Evidence)
            ]
            if len(matches) != 1:
                continue
            parser_name, parser_call, state = matches[0]
            proofs[id(call)] = PythonNetworkOriginProof(
                state["evidence"],
                source_name,
                parser_call,
                state["scheme"],
                state["hostname"],
            )
        if (
            isinstance(statement, ast.If)
            and python_block_always_terminates(statement.body)
            and not statement.orelse
        ):
            terms = guard_terms(statement.test)
            for parser_name, field, values in terms:
                if parser_name not in parsed_urls:
                    continue
                state = guarded.setdefault(parser_name, {})
                state[field] = values
                state.setdefault(
                    "evidence",
                    Evidence(path, statement.lineno, excerpt(lines, statement.lineno)),
                )
    return proofs


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
    elif call_name == "open" and node.args:
        expression = node.args[0]
    elif isinstance(node.func, ast.Attribute) and (
        (
            short_name == "open"
            and python_path_expression_proof(
                node.func.value,
                path_constructors or set(),
                path_bindings or {},
            )
            is not None
        )
        or short_name in {"write_text", "write_bytes", "unlink", "rmdir", "mkdir"}
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
        dominating_symbol_ids: dict[tuple[int, str, str], tuple[str, str]],
        scope_bound_names: set[tuple[tuple[str, ...], str]],
        node_scopes: dict[int, tuple[str, ...]],
        call_symbol_ids: dict[int, str],
        mcp_server_symbol_names: dict[str, str],
        mcp_server_binding_resolutions: dict[int, str],
        mcp_in_process_server_bindings: dict[str, tuple[str, str]],
        agent_constructor_bindings: set[str],
        exact_openai_builtin_call_names: dict[int, str],
        observed_mcp_server_ids: set[str],
        definition_symbol_ids: dict[int, str],
        referenced_tool_functions: dict[int, PythonToolRoleReference],
        wrapped_tool_functions: dict[int, PythonFunctionToolWrapper],
        inline_usage_tool_calls: dict[int, tuple[str, str]],
        decorated_tool_exports: dict[tuple[str, str], str],
        imported_tool_export_usages: dict[
            tuple[int, int, str], PythonImportedToolReference
        ],
        imported_tool_promoted_exports: set[tuple[str, str]],
        imported_agent_factory_target_paths: dict[str, str],
        registry_class_exports: dict[tuple[str, str], RegistryClassTarget],
        network_helper_summaries: dict[tuple[str, str], PythonNetworkHelperSummary],
        registered_tool_functions: dict[tuple[str, str], PythonToolRegistration],
        registry_function_tools: dict[int, PythonRegistryTool],
        registry_class_tools: dict[int, PythonRegistryTool],
        module_static_http_prefixes: dict[str, str],
        module_rebound_names: set[str],
        path_constructors: set[str],
        filesystem_api_aliases: dict[str, str],
        urllib_openers: set[str],
        urllib_request_constructors: set[str],
        browser_type_names: set[str],
        browser_page_factories: set[str],
        browser_runtime_factories: set[str],
        url_parser_names: set[str],
        module_literal_string_sets: dict[str, tuple[str, ...]],
        approval_bypass_function_summaries: dict[str, tuple[str, ...]],
    ) -> None:
        self.ir = ir
        self.root = root
        self.path = path
        self.lines = lines
        self.current_tool: str | None = None
        self.current_tool_id: str | None = None
        self.dynamic_http_origin_names: set[str] = set()
        self.dynamic_tool_input_names: set[str] = set()
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
        self.class_browser_receiver_attributes: list[dict[str, str]] = []
        self.function_fixed_binding_sources: list[dict[str, Evidence]] = []
        self.function_escaping_children: list[set[str]] = []
        self.function_path_boundary_calls: list[dict[int, PythonPathBoundaryProof]] = []
        self.function_filesystem_api_aliases: list[dict[str, str]] = []
        self.function_filesystem_callable_calls: list[dict[int, str]] = []
        self.function_path_bindings: list[dict[str, str]] = []
        self.function_path_constructors: list[set[str]] = []
        self.function_browser_receiver_proofs: list[dict[int, str]] = []
        self.function_network_origin_guards: list[dict[int, PythonNetworkOriginProof]] = []
        self.urllib_openers = urllib_openers
        self.urllib_request_constructors = urllib_request_constructors
        self.browser_type_names = browser_type_names
        self.browser_page_factories = browser_page_factories
        self.browser_runtime_factories = browser_runtime_factories
        self.url_parser_names = url_parser_names
        self.module_literal_string_sets = module_literal_string_sets
        self.approval_bypass_function_summaries = approval_bypass_function_summaries
        self.function_stack: list[str] = []
        self.function_depth = 0
        self.imported_symbol_paths: dict[str, str] = {}
        self.imported_symbol_names: dict[str, str] = {}
        self.imported_symbol_resolutions: dict[str, str] = {}
        self.mcp_server_constructors: dict[str, tuple[str, str]] = {}
        self.observed_mcp_server_ids = set(observed_mcp_server_ids)
        self.provider_call_bindings: dict[str, tuple[str, str, str]] = {}
        self.provider_module_bindings: dict[str, tuple[str, str]] = {}
        self.network_helper_bindings: dict[str, PythonNetworkHelperSummary] = {}
        self.module_paths = module_paths
        self.local_symbol_ids = local_symbol_ids
        self.ambiguous_local_symbols = ambiguous_local_symbols
        self.scoped_symbol_ids = scoped_symbol_ids
        self.dominating_symbol_ids = dominating_symbol_ids
        self.scope_bound_names = scope_bound_names
        self.node_scopes = node_scopes
        self.call_symbol_ids = call_symbol_ids
        self.mcp_server_symbol_names = mcp_server_symbol_names
        self.mcp_server_binding_resolutions = mcp_server_binding_resolutions
        self.mcp_in_process_server_bindings = mcp_in_process_server_bindings
        self.agent_constructor_bindings = agent_constructor_bindings
        self.exact_openai_builtin_call_names = exact_openai_builtin_call_names
        self.definition_symbol_ids = definition_symbol_ids
        self.referenced_tool_functions = referenced_tool_functions
        self.wrapped_tool_functions = wrapped_tool_functions
        self.inline_usage_tool_calls = inline_usage_tool_calls
        self.decorated_tool_exports = decorated_tool_exports
        self.imported_tool_export_usages = imported_tool_export_usages
        self.imported_tool_promoted_exports = imported_tool_promoted_exports
        self.imported_agent_factory_target_paths = imported_agent_factory_target_paths
        self.registry_class_exports = registry_class_exports
        self.network_helper_summaries = network_helper_summaries
        self.registered_tool_functions = registered_tool_functions
        self.registry_function_tools = registry_function_tools
        self.registry_class_tools = registry_class_tools
        self.active_registry_class_tools: list[tuple[PythonRegistryTool, str] | None] = []
        self.module_static_http_prefixes = module_static_http_prefixes
        self.class_static_http_prefixes: list[dict[str, str]] = []
        self.static_http_prefixes = dict(module_static_http_prefixes)
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

    def add_python_network_origin_control(
        self, capability_node: ast.Call, proof: PythonNetworkOriginProof
    ) -> None:
        redirect_scope = "unresolved"
        for keyword in capability_node.keywords:
            if (
                keyword.arg in {"allow_redirects", "follow_redirects"}
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is False
            ):
                redirect_scope = "disabled"
        attributes = {
            "scope": source_scope(self.path),
            "policy_effect": "restricts-initial-http-origin",
            "frontend": "python",
            "parser": proof.parser_name,
            "url": proof.url_name,
            "schemes": list(proof.schemes),
            "hosts": list(proof.hosts),
            "initial_origin_scope": "allowlisted",
            "redirect_scope": redirect_scope,
            "dns_scope": "unresolved",
        }
        self.ir.add_component(
            Component("control", "network-origin-allowlist", proof.evidence, attributes)
        )
        self.ir.add_relationship(
            Relationship(
                "capability",
                "network",
                "governed-by",
                "control",
                "network-origin-allowlist",
                self.ev(capability_node),
                {
                    "control_path": proof.evidence.path,
                    "control_line": proof.evidence.line,
                    **attributes,
                },
            )
        )

    def add_python_secure_network_control(
        self,
        capability_node: ast.Call,
        summary: PythonNetworkHelperSummary,
        policy: PythonSecureNetworkPolicy,
    ) -> None:
        attributes = {
            "scope": source_scope(self.path),
            "policy_effect": policy.policy_effect,
            "frontend": "python",
            "helper": summary.name,
            "helper_path": summary.path,
            "schemes": list(policy.schemes),
            "initial_origin_scope": policy.initial_origin_scope,
            "redirect_scope": policy.redirect_scope,
            "dns_scope": policy.dns_scope,
            "proxy_scope": policy.proxy_scope,
            "enforcement_default": policy.enforcement_default,
            "escape_hatch": policy.escape_hatch,
        }
        if policy.bypass_environment is not None:
            attributes["bypass_environment"] = policy.bypass_environment
        if policy.force_safe_environment is not None:
            attributes["force_safe_environment"] = policy.force_safe_environment
        if policy.bypass_environments:
            attributes["bypass_environments"] = list(policy.bypass_environments)
        self.ir.add_component(
            Component("control", "network-ssrf-policy", policy.evidence, attributes)
        )
        self.ir.add_relationship(
            Relationship(
                "capability",
                "network",
                "governed-by",
                "control",
                "network-ssrf-policy",
                self.ev(capability_node),
                {
                    "control_path": policy.evidence.path,
                    "control_line": policy.evidence.line,
                    **attributes,
                },
            )
        )

    def ev(self, node: ast.AST) -> Evidence:
        line = getattr(node, "lineno", 1)
        return Evidence(self.path, line, excerpt(self.lines, line))

    def add_mcp_stdio_server(
        self,
        node: ast.AST,
        *,
        name: str,
        command: str | None,
        arguments: list[str | None],
        constructor: str,
        analysis: str,
    ) -> None:
        """Record an import-proven stdio server and optional literal package proof."""
        package = mcp_package_reference(command, arguments) if command is not None else None
        symbol_id = self.call_symbol_ids.get(id(node))
        attributes: dict[str, object] = {
            "transport": "stdio",
            "constructor": constructor,
            "analysis": analysis,
            "frontend": "python",
            "scope": source_scope(self.path),
        }
        if command is not None:
            attributes["command"] = command
        else:
            attributes["command_resolution"] = "unresolved"
        if resolution := self.mcp_server_binding_resolutions.get(id(node)):
            attributes["binding_resolution"] = resolution
        if package is not None:
            attributes.update({"package_manager": command, **package})
        self.ir.add_component(
            Component(
                "mcp-server",
                name,
                self.ev(node),
                attributes,
                symbol_id,
            )
        )
        if symbol_id is not None:
            self.observed_mcp_server_ids.add(symbol_id)

    def add_mcp_in_process_server(
        self,
        node: ast.AST,
        *,
        name: str,
        constructor: str,
    ) -> None:
        """Record an import-proven in-process MCP server constructor."""
        symbol_id = self.call_symbol_ids.get(id(node))
        self.ir.add_component(
            Component(
                "mcp-server",
                name,
                self.ev(node),
                {
                    "transport": "in-process",
                    "constructor": constructor,
                    "analysis": "python-import-bound-mcp-server-constructor",
                    "frontend": "python",
                    "scope": source_scope(self.path),
                    **(
                        {"binding_resolution": resolution}
                        if (
                            resolution := self.mcp_server_binding_resolutions.get(
                                id(node)
                            )
                        )
                        else {}
                    ),
                },
                symbol_id,
            )
        )
        if symbol_id is not None:
            self.observed_mcp_server_ids.add(symbol_id)

    def visit_Dict(self, node: ast.Dict) -> None:
        entries = {
            key.value: value
            for key, value in zip(node.keys, node.values, strict=True)
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        servers = entries.get("mcpServers")
        if isinstance(servers, ast.Dict):
            for key, config in zip(servers.keys, servers.values, strict=True):
                if not (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and isinstance(config, ast.Dict)
                ):
                    continue
                config_entries = {
                    config_key.value: config_value
                    for config_key, config_value in zip(
                        config.keys, config.values, strict=True
                    )
                    if isinstance(config_key, ast.Constant)
                    and isinstance(config_key.value, str)
                }
                command_node = config_entries.get("command")
                if not (
                    isinstance(command_node, ast.Constant)
                    and isinstance(command_node.value, str)
                ):
                    continue
                arguments = literal_string_arguments(config_entries.get("args"))
                if arguments is None:
                    continue
                self.add_mcp_stdio_server(
                    config,
                    name=key.value,
                    command=command_node.value,
                    arguments=arguments,
                    constructor="mcpServers",
                    analysis="python-mcp-config-literal",
                )
        self.generic_visit(node)

    def resolve_local_symbol(
        self, kind: str, name: str, node: ast.AST
    ) -> tuple[str | None, str | None]:
        scope = self.node_scopes.get(id(node), ())
        repeated = (kind, name) in self.ambiguous_local_symbols
        dominating = self.dominating_symbol_ids.get((id(node), kind, name))
        if scoped := self.scoped_symbol_ids.get((scope, kind, name)):
            definition_line, symbol_id = scoped
            if definition_line < getattr(node, "lineno", 1):
                if dominating and dominating[0] != symbol_id:
                    return dominating if repeated else (dominating[0], None)
                if dominating and dominating[1] == "agent-as-tool-adapter":
                    return dominating
                return symbol_id, "lexical-single-definition" if repeated else None
        if dominating:
            return (
                dominating
                if repeated
                or dominating[1]
                in {
                    "same-class-helper-return",
                    "same-block-function-factory-return",
                    "typed-parameter-callsite-consensus",
                }
                or dominating[1]
                in {
                    "imported-class-factory-return",
                    "contextual-imported-class-factory-return",
                    "literal-tools-list-context-manager",
                    "literal-tools-list-import-binding",
                    "agent-as-tool-adapter",
                }
                else (dominating[0], None)
            )
        if (
            scope
            and (scope, name) not in self.scope_bound_names
            and (module_symbol := self.scoped_symbol_ids.get(((), kind, name)))
        ):
            definition_line, symbol_id = module_symbol
            if definition_line < getattr(node, "lineno", 1):
                return symbol_id, "module-single-definition" if repeated else None
        if self.node_scopes:
            return None, None
        if (kind, name) not in self.ambiguous_local_symbols:
            return self.local_symbol_ids.get((kind, name)), None
        return None, None

    def invalidate_imported_symbol(self, name: str) -> None:
        self.imported_symbol_paths.pop(name, None)
        self.imported_symbol_names.pop(name, None)
        self.imported_symbol_resolutions.pop(name, None)
        self.mcp_server_constructors.pop(name, None)
        self.provider_call_bindings.pop(name, None)
        self.provider_module_bindings.pop(name, None)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            self.invalidate_imported_symbol(local_name)
            if provider := PYTHON_PROVIDER_MODULES.get(alias.name):
                self.provider_module_bindings[local_name] = (provider, alias.name)
            if not self.class_stack or self.function_depth > 0:
                self.network_helper_bindings.pop(
                    local_name, None
                )
            component_from_import(self.ir, alias.name, self.ev(node), "python")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name
            self.invalidate_imported_symbol(local_name)
            module = node.module or ""
            if (
                (provider := PYTHON_PROVIDER_SYMBOL_PROVIDERS.get(
                    (module, alias.name), PYTHON_PROVIDER_MODULES.get(module)
                ))
                and alias.name in PYTHON_PROVIDER_SDK_CALLS[module]
            ):
                self.provider_call_bindings[local_name] = (
                    provider,
                    module,
                    alias.name,
                )
            if (
                self.function_depth == 0
                and not self.class_stack
                and alias.name
                in MCP_LAUNCHER_CONSTRUCTORS | MCP_IN_PROCESS_SERVER_CONSTRUCTORS
                and is_mcp_server_constructor_module(module, alias.name)
            ):
                self.mcp_server_constructors[local_name] = (module, alias.name)
            helper_import_scope = not self.class_stack or self.function_depth > 0
            if helper_import_scope:
                self.network_helper_bindings.pop(local_name, None)
            resolution = resolve_python_import(
                self.root,
                self.path,
                node,
                alias.name,
                self.module_paths,
            )
            if resolution:
                target = resolution.path
                self.imported_symbol_paths[local_name] = target
                self.imported_symbol_names[local_name] = alias.name
                self.imported_symbol_resolutions[local_name] = resolution.basis
                if helper_import_scope and (
                    summary := self.network_helper_summaries.get((target, alias.name))
                ):
                    self.network_helper_bindings[local_name] = summary
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
            component_from_import(self.ir, node.module or "", self.ev(node), "python")
            if node.module == "google":
                for alias in node.names:
                    if alias.name in {"genai", "generativeai"}:
                        component_from_import(
                            self.ir,
                            f"google.{alias.name}",
                            self.ev(node),
                            "python",
                        )
            if node.module == "langchain_aws" and {
                alias.name for alias in node.names
            } & {"ChatBedrock", "ChatBedrockConverse", "BedrockEmbeddings"}:
                self.ir.add_component(
                    Component(
                        "provider",
                        "AWS Bedrock",
                        self.ev(node),
                        {"module": "langchain_aws"},
                    )
                )

    def visit_Assign(self, node: ast.Assign) -> None:
        if not self.class_stack or self.function_depth > 0:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.network_helper_bindings.pop(target.id, None)
        if self.current_tool:
            origin_value = python_urllib_request_url(
                node.value,
                self.urllib_request_constructors,
            )
            dynamic_origin = python_http_origin_is_dynamic(
                origin_value,
                self.dynamic_http_origin_names,
                self.static_http_prefixes,
            )
            dynamic_tool_input = bool(
                python_expression_names(node.value) & self.dynamic_tool_input_names
            )
            static_http_prefix = python_static_url_prefix(
                origin_value, self.static_http_prefixes
            )
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if dynamic_origin:
                    self.dynamic_http_origin_names.add(target.id)
                else:
                    self.dynamic_http_origin_names.discard(target.id)
                if dynamic_tool_input:
                    self.dynamic_tool_input_names.add(target.id)
                else:
                    self.dynamic_tool_input_names.discard(target.id)
                if static_http_prefix:
                    self.static_http_prefixes[target.id] = static_http_prefix
                else:
                    self.static_http_prefixes.pop(target.id, None)
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
        if not self.class_stack or self.function_depth > 0:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.invalidate_imported_symbol(target.id)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if (
            not self.class_stack or self.function_depth > 0
        ) and isinstance(node.target, ast.Name):
            self.network_helper_bindings.pop(node.target.id, None)
        self.generic_visit(node)
        if (
            not self.class_stack or self.function_depth > 0
        ) and isinstance(node.target, ast.Name):
            self.invalidate_imported_symbol(node.target.id)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if (
            not self.class_stack or self.function_depth > 0
        ) and isinstance(node.target, ast.Name):
            self.network_helper_bindings.pop(node.target.id, None)
        self.generic_visit(node)
        if (
            not self.class_stack or self.function_depth > 0
        ) and isinstance(node.target, ast.Name):
            self.invalidate_imported_symbol(node.target.id)

    def visit_Delete(self, node: ast.Delete) -> None:
        if not self.class_stack or self.function_depth > 0:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.invalidate_imported_symbol(target.id)
                    self.network_helper_bindings.pop(target.id, None)
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
        if not self.class_stack or self.function_depth > 0:
            self.invalidate_imported_symbol(node.name)
            self.network_helper_bindings.pop(node.name, None)
        previous_allowlisted_names = self.allowlisted_names
        previous_allowlist_evidence = self.allowlist_evidence
        previous_allowlist_control_names = self.allowlist_control_names
        previous_http_client_names = self.http_client_names
        previous_approval_environment_flags = self.approval_environment_flags
        previous_static_http_prefixes = self.static_http_prefixes
        previous_network_helper_bindings = self.network_helper_bindings
        self.network_helper_bindings = dict(self.network_helper_bindings)
        self.allowlisted_names = set()
        self.allowlist_evidence = {}
        self.allowlist_control_names = {}
        self.http_client_names = set()
        if self.function_depth == 0:
            self.static_http_prefixes = {
                **self.module_static_http_prefixes,
                **(
                    self.class_static_http_prefixes[-1]
                    if self.class_static_http_prefixes
                    else {}
                ),
            }
        else:
            self.static_http_prefixes = dict(self.static_http_prefixes)
        if self.function_depth == 0:
            self.approval_environment_flags = self.module_approval_environment_flags.copy()
        else:
            self.approval_environment_flags = self.approval_environment_flags.copy()
        self.function_depth += 1
        self.function_stack.append(node.name)
        self.function_fixed_binding_sources.append(self.fixed_function_parameter_bindings(node))
        self.function_escaping_children.append(self.escaping_nested_function_names(node))
        local_bindings = python_function_local_bindings(node)
        previous_imported_symbol_paths = self.imported_symbol_paths
        previous_imported_symbol_names = self.imported_symbol_names
        previous_imported_symbol_resolutions = self.imported_symbol_resolutions
        previous_mcp_server_constructors = self.mcp_server_constructors
        previous_provider_call_bindings = self.provider_call_bindings
        previous_provider_module_bindings = self.provider_module_bindings
        self.imported_symbol_paths = {
            name: target
            for name, target in self.imported_symbol_paths.items()
            if name not in local_bindings
        }
        self.imported_symbol_names = {
            name: original
            for name, original in self.imported_symbol_names.items()
            if name not in local_bindings
        }
        self.imported_symbol_resolutions = {
            name: basis
            for name, basis in self.imported_symbol_resolutions.items()
            if name not in local_bindings
        }
        self.mcp_server_constructors = {
            name: constructor
            for name, constructor in self.mcp_server_constructors.items()
            if name not in local_bindings
        }
        self.provider_call_bindings = {
            name: binding
            for name, binding in self.provider_call_bindings.items()
            if name not in local_bindings
        }
        self.provider_module_bindings = {
            name: binding
            for name, binding in self.provider_module_bindings.items()
            if name not in local_bindings
        }
        previous_urllib_openers = self.urllib_openers
        previous_urllib_request_constructors = self.urllib_request_constructors
        self.urllib_openers = {
            opener
            for opener in self.urllib_openers
            if opener.split(".", 1)[0] not in local_bindings
        }
        self.urllib_request_constructors = {
            constructor
            for constructor in self.urllib_request_constructors
            if constructor.split(".", 1)[0] not in local_bindings
        }
        function_browser_types = {
            type_name
            for type_name in self.browser_type_names
            if type_name.split(".", 1)[0] not in local_bindings
        }
        function_browser_factories = {
            factory
            for factory in self.browser_page_factories
            if factory.split(".", 1)[0] not in local_bindings
        }
        class_browser_attributes = (
            self.class_browser_receiver_attributes[-1]
            if self.class_browser_receiver_attributes
            else {}
        )
        if node.name == "__init__":
            class_browser_attributes = {
                name: proof
                for name, proof in class_browser_attributes.items()
                if proof != "constructor-bound-playwright-page"
            }
        self.function_browser_receiver_proofs.append(
            python_browser_receiver_proofs(
                node,
                function_browser_types,
                function_browser_factories,
                class_browser_attributes,
            )
            if self.has_browser_import
            else {}
        )
        function_url_parsers = {
            parser
            for parser in self.url_parser_names
            if parser.split(".", 1)[0] not in local_bindings
        }
        function_literal_string_sets = {
            name: values
            for name, values in self.module_literal_string_sets.items()
            if name not in local_bindings
        }
        self.function_network_origin_guards.append(
            python_network_origin_guard_proofs(
                node,
                self.path,
                self.lines,
                function_url_parsers,
                function_literal_string_sets,
            )
        )
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
        registry_function = self.registry_function_tools.get(id(node))
        tool_reference = self.referenced_tool_functions.get(id(node))
        wrapped_tool = self.wrapped_tool_functions.get(id(node))
        direct_tool = bool(
            decorators & TOOL_DECORATORS
            or any(name.endswith(".tool") for name in decorators)
            or registration is not None
            or registry_function is not None
            or tool_reference is not None
            or wrapped_tool is not None
        )
        active_class_tool = (
            self.active_registry_class_tools[-1]
            if self.active_registry_class_tools
            and self.function_depth == 1
            and self.active_registry_class_tools[-1] is not None
            and node.name in self.active_registry_class_tools[-1][0].entrypoints
            else None
        )
        if direct_tool or active_class_tool is not None:
            qualified_name = ".".join([*self.class_stack, node.name])
            tool_name = (
                active_class_tool[0].name
                if active_class_tool is not None
                else registry_function.name
                if registry_function is not None
                else wrapped_tool.binding
                if wrapped_tool is not None
                else node.name
            )
            tool_id = (
                active_class_tool[1]
                if active_class_tool is not None
                else self.definition_symbol_ids.get(id(node))
                or self.local_symbol_ids.get(("tool", qualified_name))
                or source_symbol("py", self.path, "tool", qualified_name)
            )
            needs_approval = registration.needs_approval if registration else False
            if wrapped_tool is not None:
                needs_approval = needs_approval or any(
                    keyword.arg in {"needs_approval", "require_approval"}
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                    for keyword in wrapped_tool.call.keywords
                )
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
            if registry_function:
                attributes.update(
                    {
                        "registration": "registry-decorator",
                        "registration_target": "function",
                        "registrar": registry_function.registrar,
                        "framework": registry_function.framework,
                    }
                )
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
                if registration.wrappers:
                    attributes.update(
                        {
                            "wrappers": list(registration.wrappers),
                            "wrapper_summary": "metadata-preserving-forwarder",
                        }
                    )
            if wrapped_tool is not None:
                attributes.update(
                    {
                        "registration": "function-tool-wrapper",
                        "registration_path": self.path,
                        "registration_line": wrapped_tool.agent_call.lineno,
                        "wrapper_factory": wrapped_tool.registrar,
                        "wrapper_line": wrapped_tool.assignment.lineno,
                        "wrapped_function": node.name,
                        "resolution": "same-block-single-definition",
                    }
                )
            if (
                tool_reference is not None
                and not decorators & TOOL_DECORATORS
                and not any(name.endswith(".tool") for name in decorators)
                and registration is None
                and registry_function is None
                and wrapped_tool is None
            ):
                attributes.update(
                    {
                        "registration": "agent-tool-reference",
                        "registration_path": tool_reference.registration_path,
                        "registration_line": tool_reference.registration_line,
                        "resolution": tool_reference.resolution,
                    }
                )
                if tool_reference.import_line is not None:
                    attributes["import_line"] = tool_reference.import_line
            if active_class_tool is None:
                self.ir.add_component(
                    Component(
                        "tool",
                        tool_name,
                        self.ev(wrapped_tool.assignment) if wrapped_tool else self.ev(node),
                        attributes,
                        tool_id,
                    )
                )
                fastmcp_registrations: dict[str, Evidence] = {}
                for decorator in node.decorator_list:
                    decorator_name = (
                        dotted_name(decorator.func)
                        if isinstance(decorator, ast.Call)
                        else dotted_name(decorator)
                    )
                    if decorator_name.endswith(".tool"):
                        fastmcp_registrations[
                            decorator_name.removesuffix(".tool")
                        ] = self.ev(decorator)
                if registration and registration.registrar.endswith(".tool"):
                    fastmcp_registrations[
                        registration.registrar.removesuffix(".tool")
                    ] = registration.evidence
                for registrar, registration_evidence in sorted(
                    fastmcp_registrations.items()
                ):
                    server = self.mcp_in_process_server_bindings.get(registrar)
                    if server is None:
                        continue
                    server_name, server_id = server
                    self.ir.add_relationship(
                        Relationship(
                            "mcp-server",
                            server_name,
                            "uses",
                            "tool",
                            tool_name,
                            registration_evidence,
                            {
                                "registrar": f"{registrar}.tool",
                                "target_identity": "exact-fastmcp-registrar",
                            },
                            server_id,
                            tool_id,
                        )
                    )
            if needs_approval:
                approval_evidence = (
                    registration.evidence
                    if registration
                    else self.ev(wrapped_tool.call)
                    if wrapped_tool
                    else self.ev(node)
                )
                self.ir.add_component(
                    Component("control", "human-approval", approval_evidence)
                )
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
            previous_tool = self.current_tool
            previous_tool_id = self.current_tool_id
            previous_dynamic_http_origin_names = self.dynamic_http_origin_names
            previous_dynamic_tool_input_names = self.dynamic_tool_input_names
            self.current_tool = tool_name
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
            self.dynamic_tool_input_names = set(self.dynamic_http_origin_names)
            if node.args.vararg:
                self.dynamic_http_origin_names.add(node.args.vararg.arg)
                self.dynamic_tool_input_names.add(node.args.vararg.arg)
            if node.args.kwarg:
                self.dynamic_http_origin_names.add(node.args.kwarg.arg)
                self.dynamic_tool_input_names.add(node.args.kwarg.arg)
            self.visit_function_statements(node)
            self.current_tool = previous_tool
            self.current_tool_id = previous_tool_id
            self.dynamic_http_origin_names = previous_dynamic_http_origin_names
            self.dynamic_tool_input_names = previous_dynamic_tool_input_names
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
        self.function_browser_receiver_proofs.pop()
        self.function_network_origin_guards.pop()
        self.approval_environment_flags = previous_approval_environment_flags
        self.static_http_prefixes = previous_static_http_prefixes
        self.network_helper_bindings = previous_network_helper_bindings
        self.imported_symbol_paths = previous_imported_symbol_paths
        self.imported_symbol_names = previous_imported_symbol_names
        self.imported_symbol_resolutions = previous_imported_symbol_resolutions
        self.mcp_server_constructors = previous_mcp_server_constructors
        self.provider_call_bindings = previous_provider_call_bindings
        self.provider_module_bindings = previous_provider_module_bindings
        self.urllib_openers = previous_urllib_openers
        self.urllib_request_constructors = previous_urllib_request_constructors

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if not self.class_stack or self.function_depth > 0:
            self.invalidate_imported_symbol(node.name)
            self.network_helper_bindings.pop(node.name, None)
        registry_tool = self.registry_class_tools.get(id(node))
        active_registry_tool: tuple[PythonRegistryTool, str] | None = None
        if registry_tool is not None:
            tool_id = self.definition_symbol_ids.get(id(node)) or source_symbol(
                "py", self.path, "tool", registry_tool.name
            )
            self.ir.add_component(
                Component(
                    "tool",
                    registry_tool.name,
                    self.ev(node),
                    {
                        "decorators": [registry_tool.registrar],
                        "needs_approval": False,
                        "registration": "registry-decorator",
                        "registration_target": "class",
                        "class_name": node.name,
                        "registrar": registry_tool.registrar,
                        "framework": registry_tool.framework,
                        "entrypoints": list(registry_tool.entrypoints),
                        "entrypoint_resolution": (
                            "literal" if registry_tool.entrypoints else "unresolved"
                        ),
                    },
                    tool_id,
                )
            )
            active_registry_tool = (registry_tool, tool_id)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.class_stack.append(node.name)
        self.active_registry_class_tools.append(active_registry_tool)
        class_url_assignments: dict[str, list[ast.AST | None]] = defaultdict(list)
        for method in node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) or method.name != "__init__":
                continue
            for candidate in ast.walk(method):
                if isinstance(candidate, ast.Assign):
                    for target in candidate.targets:
                        if dotted_name(target).startswith("self."):
                            class_url_assignments[dotted_name(target)].append(candidate.value)
                elif isinstance(candidate, ast.AnnAssign) and dotted_name(
                    candidate.target
                ).startswith("self."):
                    class_url_assignments[dotted_name(candidate.target)].append(candidate.value)
        self.class_static_http_prefixes.append(
            {
                name: prefix
                for name, values in class_url_assignments.items()
                if len(values) == 1
                and (
                    prefix := python_static_url_prefix(
                        values[0], self.module_static_http_prefixes
                    )
                )
            }
        )
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
        annotated_browser_attributes = python_class_browser_receiver_attributes(
            node, self.browser_type_names
        )
        constructed_browser_attributes = python_class_constructor_browser_receivers(
            node, self.browser_runtime_factories
        )
        self.class_browser_receiver_attributes.append(
            {
                **{
                    name: "constructor-bound-playwright-page"
                    for name in constructed_browser_attributes
                },
                **{
                    name: "class-attribute-annotation"
                    for name in annotated_browser_attributes
                },
            }
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
        self.class_browser_receiver_attributes.pop()
        self.class_path_helper_summaries.pop()
        self.class_static_http_prefixes.pop()
        self.active_registry_class_tools.pop()
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

    def imported_network_helper(
        self, node: ast.Call
    ) -> tuple[PythonNetworkHelperSummary, list[ast.AST], str | None] | None:
        if not isinstance(node.func, ast.Name):
            return None
        local_name = node.func.id
        summary = self.network_helper_bindings.get(local_name)
        if summary is None or (self.current_tool is None and summary.secure_policy is None):
            return None
        arguments: list[ast.AST] = []
        keywords = {
            keyword.arg: keyword.value for keyword in node.keywords if keyword.arg is not None
        }
        for parameter in summary.controlled_parameters:
            argument = keywords.get(parameter)
            if argument is None and parameter in summary.positional_parameters:
                index = summary.positional_parameters.index(parameter)
                if index < len(node.args):
                    argument = node.args[index]
            if argument is not None:
                arguments.append(argument)
        return summary, arguments, self.imported_symbol_resolutions.get(local_name)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = dotted_name(node.func)
        short_name = call_name.rsplit(".", 1)[-1]
        imported_mcp_constructor = (
            self.mcp_server_constructors.get(node.func.id)
            if isinstance(node.func, ast.Name)
            and (not self.class_stack or self.function_depth > 0)
            else None
        )
        if imported_mcp_constructor is not None:
            _, constructor = imported_mcp_constructor
            server_name = self.mcp_server_symbol_names.get(
                self.call_symbol_ids.get(id(node), ""),
                f"{constructor}@{node.lineno}",
            )
            if constructor in MCP_IN_PROCESS_SERVER_CONSTRUCTORS:
                self.add_mcp_in_process_server(
                    node,
                    name=server_name,
                    constructor=constructor,
                )
            keywords = {
                keyword.arg: keyword.value
                for keyword in node.keywords
                if keyword.arg is not None
            }
            if constructor == "MCPTools":
                command_node = node.args[0] if node.args else keywords.get("command")
                if (
                    isinstance(command_node, ast.Constant)
                    and isinstance(command_node.value, str)
                ):
                    try:
                        invocation = shlex.split(command_node.value)
                    except ValueError:
                        invocation = []
                    if invocation:
                        self.add_mcp_stdio_server(
                            node,
                            name=f"{constructor}@{node.lineno}",
                            command=invocation[0],
                            arguments=list(invocation[1:]),
                            constructor=constructor,
                            analysis="python-import-bound-mcp-constructor",
                        )
            elif constructor not in MCP_IN_PROCESS_SERVER_CONSTRUCTORS:
                command_node = keywords.get("command")
                if command_node is None and node.args:
                    command_node = node.args[0]
                arguments_node = keywords.get("args")
                if arguments_node is None and len(node.args) > 1:
                    arguments_node = node.args[1]
                params_node = keywords.get("params")
                if isinstance(params_node, ast.Dict):
                    params = {
                        key.value: value
                        for key, value in zip(
                            params_node.keys, params_node.values, strict=True
                        )
                        if isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                    }
                    command_node = params.get("command", command_node)
                    arguments_node = params.get("args", arguments_node)
                arguments = literal_string_arguments(arguments_node)
                command = (
                    command_node.value
                    if isinstance(command_node, ast.Constant)
                    and isinstance(command_node.value, str)
                    else None
                )
                if command is not None and arguments is not None:
                    self.add_mcp_stdio_server(
                        node,
                        name=server_name,
                        command=command,
                        arguments=arguments,
                        constructor=constructor,
                        analysis="python-import-bound-mcp-constructor",
                    )
                elif (
                    constructor == "MCPServerStdio"
                    and self.call_symbol_ids.get(id(node)) is not None
                ):
                    self.add_mcp_stdio_server(
                        node,
                        name=server_name,
                        command=command,
                        arguments=arguments or [],
                        constructor=constructor,
                        analysis="python-import-bound-mcp-constructor",
                    )
        builtin_name = self.exact_openai_builtin_call_names.get(id(node), short_name)
        exact_builtin_call = (
            builtin_name in BUILTIN_TOOL_CAPABILITIES
            and (
                builtin_name not in EXACT_IMPORT_OPENAI_BUILTINS
                or id(node) in self.exact_openai_builtin_call_names
            )
        )
        if self.has_openai_agents_import and exact_builtin_call:
            tool_name = f"{builtin_name}@{node.lineno}"
            tool_id = self.call_symbol_ids.get(id(node)) or source_symbol(
                "py", self.path, "tool", tool_name
            )
            approval_state = (
                "not-applicable"
                if builtin_name == "ComputerTool"
                else "unavailable"
                if builtin_name in OPENAI_BUILTINS_WITHOUT_APPROVAL
                else "disabled-default"
            )
            approval_source = (
                "sdk-computer-safety-check"
                if builtin_name == "ComputerTool"
                else "sdk-no-approval-parameter"
                if builtin_name in OPENAI_BUILTINS_WITHOUT_APPROVAL
                else "sdk-default"
            )
            approval_handler = "none"
            approval_bypass_environment_names: tuple[str, ...] = ()
            safety_check_handler = "none"
            execution_environment = (
                "hosted-sandbox"
                if builtin_name == "CodeInterpreterTool"
                else "hosted"
                if builtin_name in OPENAI_PROVIDER_HOSTED_BUILTINS
                else "local"
                if builtin_name in {"ComputerTool", "LocalShellTool"}
                or (builtin_name == "ShellTool" and node.args)
                else "unresolved"
            )
            container_policy = "unresolved"
            external_web_access = "sdk-default"
            vector_store_scope = "unresolved"
            if builtin_name == "FileSearchTool" and node.args:
                vector_store_ids = node.args[0]
                if isinstance(vector_store_ids, (ast.List, ast.Tuple)) and all(
                    isinstance(item, ast.Constant) and isinstance(item.value, str)
                    for item in vector_store_ids.elts
                ):
                    vector_store_scope = (
                        "literal-ids" if vector_store_ids.elts else "literal-empty"
                    )
            approval_evidence = self.ev(node)
            for keyword in node.keywords:
                if (
                    builtin_name not in OPENAI_BUILTINS_WITHOUT_APPROVAL
                    and keyword.arg in {"needs_approval", "require_approval"}
                ):
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
                elif (
                    builtin_name not in OPENAI_BUILTINS_WITHOUT_APPROVAL
                    and keyword.arg == "on_approval"
                    and not (
                        isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is None
                    )
                ):
                    approval_handler = "configured"
                    handler_name = dotted_name(keyword.value).rsplit(".", 1)[-1]
                    approval_bypass_environment_names = (
                        self.approval_bypass_function_summaries.get(handler_name, ())
                    )
                elif (
                    builtin_name == "ComputerTool"
                    and keyword.arg == "on_safety_check"
                    and not (
                        isinstance(keyword.value, ast.Constant) and keyword.value.value is None
                    )
                ):
                    safety_check_handler = "configured"
                elif builtin_name == "ShellTool" and keyword.arg == "executor":
                    execution_environment = "local"
                elif (
                    builtin_name == "ShellTool"
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
                elif (
                    builtin_name == "CodeInterpreterTool"
                    and keyword.arg == "tool_config"
                    and isinstance(keyword.value, ast.Dict)
                ):
                    container = next(
                        (
                            value
                            for key, value in zip(
                                keyword.value.keys, keyword.value.values, strict=True
                            )
                            if isinstance(key, ast.Constant) and key.value == "container"
                        ),
                        None,
                    )
                    if isinstance(container, ast.Constant) and isinstance(
                        container.value, str
                    ):
                        container_policy = (
                            "auto" if container.value == "auto" else "existing-reference"
                        )
                    elif isinstance(container, ast.Dict):
                        container_type = next(
                            (
                                value.value
                                for key, value in zip(
                                    container.keys, container.values, strict=True
                                )
                                if isinstance(key, ast.Constant)
                                and key.value == "type"
                                and isinstance(value, ast.Constant)
                                and isinstance(value.value, str)
                            ),
                            None,
                        )
                        if container_type is not None:
                            container_policy = (
                                "auto"
                                if container_type == "auto"
                                else "existing-reference"
                            )
                elif builtin_name == "WebSearchTool" and keyword.arg == "external_web_access":
                    if isinstance(keyword.value, ast.Constant) and isinstance(
                        keyword.value.value, bool
                    ):
                        external_web_access = (
                            "enabled-explicit"
                            if keyword.value.value
                            else "disabled-explicit"
                        )
                    else:
                        external_web_access = "unresolved"
                elif builtin_name == "FileSearchTool" and keyword.arg == "vector_store_ids":
                    if isinstance(keyword.value, (ast.List, ast.Tuple)) and all(
                        isinstance(item, ast.Constant) and isinstance(item.value, str)
                        for item in keyword.value.elts
                    ):
                        vector_store_scope = (
                            "literal-ids" if keyword.value.elts else "literal-empty"
                        )
                    else:
                        vector_store_scope = "unresolved"
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
                        **(
                            {
                                "container_policy": container_policy,
                                "sandbox_policy": "sdk-hosted",
                            }
                            if builtin_name == "CodeInterpreterTool"
                            else {}
                        ),
                        **(
                            {"hosting_policy": "sdk-provider-hosted"}
                            if builtin_name in OPENAI_PROVIDER_HOSTED_BUILTINS
                            else {}
                        ),
                        **(
                            {"external_web_access": external_web_access}
                            if builtin_name == "WebSearchTool"
                            else {}
                        ),
                        **(
                            {"vector_store_scope": vector_store_scope}
                            if builtin_name == "FileSearchTool"
                            else {}
                        ),
                        **(
                            {
                                "approval_bypass_environment_names": list(
                                    approval_bypass_environment_names
                                ),
                                "approval_bypass_resolution": "same-file-transitive-callback",
                            }
                            if approval_bypass_environment_names
                            else {}
                        ),
                        **(
                            {"safety_check_handler": safety_check_handler}
                            if builtin_name == "ComputerTool"
                            else {}
                        ),
                    },
                    tool_id,
                )
            )
            for capability in BUILTIN_TOOL_CAPABILITIES[builtin_name]:
                attributes = {
                    "api": (
                        builtin_name
                        if builtin_name in EXACT_IMPORT_OPENAI_BUILTINS
                        else call_name
                    ),
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
                elif capability == "computer-control":
                    attributes["execution_environment"] = execution_environment
                elif (
                    builtin_name == "CodeInterpreterTool"
                    and capability == "code-execution"
                ):
                    attributes.update(
                        {
                            "container_policy": container_policy,
                            "execution_environment": execution_environment,
                            "sandbox_policy": "sdk-hosted",
                        }
                    )
                elif builtin_name in OPENAI_PROVIDER_HOSTED_BUILTINS:
                    attributes.update(
                        {
                            "execution_environment": execution_environment,
                            "hosting_policy": "sdk-provider-hosted",
                        }
                    )
                    if builtin_name == "WebSearchTool":
                        attributes.update(
                            {
                                "dynamic_origin": False,
                                "external_web_access": external_web_access,
                                "network_scope": "provider-hosted-web-search",
                            }
                        )
                    elif builtin_name == "FileSearchTool":
                        attributes.update(
                            {
                                "data_scope": "hosted-vector-store",
                                "vector_store_scope": vector_store_scope,
                            }
                        )
                    elif builtin_name == "ImageGenerationTool":
                        attributes["generation_scope"] = "provider-hosted-image"
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
            if approval_bypass_environment_names:
                self.ir.add_relationship(
                    Relationship(
                        "tool",
                        tool_name,
                        "configured-by",
                        "control-setting",
                        "auto-approval",
                        approval_evidence,
                        {
                            "environment_names": list(
                                approval_bypass_environment_names
                            ),
                            "resolution": "same-file-transitive-callback",
                        },
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
        service_name = None
        if node.args and isinstance(node.args[0], ast.Constant):
            service_name = node.args[0].value
        for keyword in node.keywords:
            if keyword.arg == "service_name" and isinstance(
                keyword.value, ast.Constant
            ):
                service_name = keyword.value.value
        bedrock_client_call = call_name.endswith(".client") or short_name in {
            "AwsClient",
            "BedrockRuntimeClient",
        }
        if bedrock_client_call and service_name == "bedrock-runtime":
            self.ir.add_component(
                Component(
                    "provider",
                    "AWS Bedrock",
                    self.ev(node),
                    {"constructor": call_name, "service": "bedrock-runtime"},
                )
            )
        imported_provider: tuple[str, str, str] | None = None
        if call_name in self.provider_call_bindings:
            imported_provider = self.provider_call_bindings[call_name]
        else:
            root_name, separator, call_suffix = call_name.partition(".")
            module_binding = self.provider_module_bindings.get(root_name)
            if separator and module_binding:
                default_provider, module = module_binding
                expected_prefix = (
                    f"{module.split('.', 1)[1]}."
                    if "." in module and root_name == module.split(".", 1)[0]
                    else ""
                )
                expected_call = f"{expected_prefix}{short_name}"
                if (
                    call_suffix == expected_call
                    and short_name in PYTHON_PROVIDER_SDK_CALLS[module]
                ):
                    provider = PYTHON_PROVIDER_SYMBOL_PROVIDERS.get(
                        (module, short_name), default_provider
                    )
                    imported_provider = (provider, module, short_name)
        if imported_provider:
            provider, module, imported_symbol = imported_provider
            call_kind = (
                "wrapper-constructor"
                if module.startswith(PYTHON_PROVIDER_WRAPPER_MODULE_PREFIXES)
                else "sdk-function"
                if (module, imported_symbol) in PYTHON_PROVIDER_SDK_FUNCTIONS
                else "sdk-constructor"
            )
            self.ir.add_component(
                Component(
                    "provider",
                    provider,
                    self.ev(node),
                    {
                        "call": call_name,
                        "call_kind": call_kind,
                        "module": module,
                        "imported_symbol": imported_symbol,
                        "resolution": "exact-provider-sdk-import",
                    },
                )
            )
            model_value = next(
                (
                    keyword.value.value
                    for keyword in node.keywords
                    if keyword.arg in {"model", "model_id", "model_name"}
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ),
                None,
            )
            if (
                model_value is None
                and (module, imported_symbol) in PYTHON_PROVIDER_POSITIONAL_MODEL_CALLS
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                model_value = node.args[0].value
            if model_value is not None:
                self.ir.add_component(
                    Component(
                        "model",
                        model_value,
                        self.ev(node),
                        {
                            "provider": provider,
                            "configured_on": call_name,
                            "call_kind": call_kind,
                            "module": module,
                            "resolution": "exact-provider-sdk-import",
                        },
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
        if short_name in AGENT_CALLS or call_name in self.agent_constructor_bindings:
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
                if keyword.arg != "mcp_servers" or not isinstance(
                    keyword.value, (ast.List, ast.Tuple)
                ):
                    continue
                for value in keyword.value.elts:
                    binding = dotted_name(value)
                    dominating = self.dominating_symbol_ids.get(
                        (id(node), "mcp-server", binding)
                    )
                    if dominating is None:
                        continue
                    target_id, resolution_basis = dominating
                    target_name = self.mcp_server_symbol_names.get(target_id)
                    if target_name is None or target_id not in self.observed_mcp_server_ids:
                        continue
                    target_identity = {
                        "immutable-module-binding": (
                            "literal-mcp-servers-list-module-binding"
                        ),
                        "context-manager-binding": (
                            "literal-mcp-servers-list-context-manager"
                        ),
                    }.get(
                        resolution_basis,
                        "literal-mcp-servers-list-binding",
                    )
                    self.ir.add_relationship(
                        Relationship(
                            "agent",
                            name,
                            "uses",
                            "mcp-server",
                            target_name,
                            self.ev(node),
                            {
                                "binding": binding,
                                "target_identity": target_identity,
                            },
                            agent_id,
                            target_id,
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
                        and (
                            id(value) in self.exact_openai_builtin_call_names
                            or (
                                dotted_name(value.func).rsplit(".", 1)[-1]
                                in BUILTIN_TOOL_CAPABILITIES
                                and dotted_name(value.func).rsplit(".", 1)[-1]
                                not in EXACT_IMPORT_OPENAI_BUILTINS
                            )
                        )
                    ):
                        constructor = self.exact_openai_builtin_call_names.get(
                            id(value), dotted_name(value.func).rsplit(".", 1)[-1]
                        )
                        target_name = f"{constructor}@{value.lineno}"
                        target_id = self.call_symbol_ids.get(id(value)) or source_symbol(
                            "py", self.path, "tool", target_name
                        )
                        target_identity = None
                    elif (
                        isinstance(value, ast.Call)
                        and (inline_tool := self.inline_usage_tool_calls.get(id(value)))
                    ):
                        target_name, target_id = inline_tool
                        target_identity = "literal-tools-list-inline-constructor"
                    if target_name:
                        attributes = {}
                        root_name, separator, suffix = target_name.partition(".")
                        imported_path = self.imported_symbol_paths.get(
                            target_name
                        ) or self.imported_symbol_paths.get(root_name)
                        if imported_path:
                            original = self.imported_symbol_names.get(root_name, root_name)
                            resolved_name = f"{original}.{suffix}" if separator else original
                            import_basis = self.imported_symbol_resolutions.get(root_name)
                            imported_callable_usage = self.imported_tool_export_usages.get(
                                (node.lineno, node.col_offset, root_name)
                            )
                            contextual_export_id = self.decorated_tool_exports.get(
                                (imported_path, resolved_name)
                            )
                            if (
                                target_kind == "tool"
                                and imported_callable_usage is not None
                                and imported_callable_usage.target_path == imported_path
                                and imported_callable_usage.original_name == resolved_name
                            ):
                                attributes.update(
                                    {
                                        "target_path": imported_path,
                                        "target_identity": (
                                            "contextual-imported-callable-single-export"
                                            if imported_callable_usage.import_resolution
                                            == "contextual-absolute-import-single-path"
                                            else "imported-callable-single-export"
                                        ),
                                    }
                                )
                                target_id = source_symbol(
                                    "py",
                                    imported_path,
                                    "tool",
                                    resolved_name,
                                )
                            elif import_basis != "contextual-absolute-import-single-path" and not (
                                target_kind == "tool"
                                and (imported_path, resolved_name)
                                in self.imported_tool_promoted_exports
                            ):
                                attributes["target_path"] = imported_path
                                target_id = source_symbol(
                                    "py", imported_path, target_kind, resolved_name
                                )
                            elif target_kind == "tool" and contextual_export_id is not None:
                                attributes.update(
                                    {
                                        "target_path": imported_path,
                                        "target_identity": (
                                            "contextual-absolute-import-single-export"
                                        ),
                                    }
                                )
                                target_id = contextual_export_id
                            else:
                                target_id = None
                        elif target_id is not None and target_identity:
                            attributes["target_identity"] = target_identity
                            if target_path := self.imported_agent_factory_target_paths.get(
                                target_id
                            ):
                                attributes["target_path"] = target_path
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
        browser_evaluate = (
            self.has_browser_import
            and short_name == "evaluate"
            and "." in call_name
        )
        browser_receiver_proof = (
            self.function_browser_receiver_proofs[-1].get(id(node))
            if browser_evaluate and self.function_browser_receiver_proofs
            else None
        )
        if call_name in {"eval", "exec"} or browser_evaluate:
            argument = node.args[0] if node.args else None
            dynamic_input = argument is not None and not isinstance(
                argument, ast.Constant
            )
            if browser_evaluate:
                dynamic_input = bool(
                    argument is not None
                    and python_expression_names(argument)
                    & self.dynamic_tool_input_names
                )
            if browser_evaluate and dynamic_input and browser_receiver_proof is None:
                return self.generic_visit(node)
            self.ir.add_component(
                Component(
                    "capability",
                    "code-execution",
                    self.ev(node),
                    {
                        "api": call_name,
                        "execution_context": (
                            "browser-page" if browser_evaluate else "python-process"
                        ),
                        "dynamic_input": dynamic_input,
                        **(
                            {
                                "receiver_proof": browser_receiver_proof
                                or "unresolved-browser-import-context"
                            }
                            if browser_evaluate
                            else {}
                        ),
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
                    "tool_input_path": bool(
                        python_expression_names(path_expression)
                        & self.dynamic_tool_input_names
                    ),
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
        proven_path_open = (
            short_name == "open"
            and isinstance(node.func, ast.Attribute)
            and python_path_expression_proof(
                node.func.value,
                self.path_constructors,
                self.function_path_bindings[-1] if self.function_path_bindings else {},
            )
            is not None
        )
        if filesystem_function is None and path_method is None and (
            call_name == "open"
            or proven_path_open
            or short_name in {
                "write_text",
                "write_bytes",
                "unlink",
                "rmdir",
                "mkdir",
            }
        ):
            path_expression = (
                node.func.value
                if proven_path_open and isinstance(node.func, ast.Attribute)
                else node.args[0]
                if call_name == "open" and node.args
                else node.func.value
                if isinstance(node.func, ast.Attribute)
                else None
            )
            mode_expression = (
                node.args[0]
                if proven_path_open and node.args
                else node.args[1]
                if call_name == "open" and len(node.args) > 1
                else None
            )
            for keyword in node.keywords:
                if short_name == "open" and keyword.arg == "mode":
                    mode_expression = keyword.value
            mode = str(mode_expression.value) if isinstance(mode_expression, ast.Constant) else "r"
            write_access = short_name != "open" or any(flag in mode for flag in "wax+")
            dynamic_path = short_name != "open" or not isinstance(path_expression, ast.Constant)
            tool_input_path = bool(
                python_expression_names(path_expression) & self.dynamic_tool_input_names
            )
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
                    "tool_input_path": tool_input_path,
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
            origin_guard = (
                self.function_network_origin_guards[-1].get(id(node))
                if self.function_network_origin_guards
                else None
            )
            if (
                origin_guard is not None
                and origin_guard.url_name not in self.dynamic_http_origin_names
            ):
                origin_guard = None
            self.add_capability(
                "network",
                node,
                {
                    "api": call_name,
                    "dynamic_origin": python_http_origin_is_dynamic(
                        url_expression,
                        self.dynamic_http_origin_names,
                        self.static_http_prefixes,
                    ),
                    **(
                        {
                            "network_origin_guard": True,
                            "initial_origin_scope": "allowlisted",
                        }
                        if origin_guard is not None
                        else {}
                    ),
                },
            )
            if origin_guard is not None:
                self.add_python_network_origin_control(node, origin_guard)
            if short_name.lower() in {"post", "put", "patch", "delete"}:
                self.add_capability("external-action", node, {"api": call_name})
        if call_name in self.urllib_openers:
            raw_url_expression = (
                node.args[0]
                if node.args
                else next(
                    (
                        keyword.value
                        for keyword in node.keywords
                        if keyword.arg == "url"
                    ),
                    None,
                )
            )
            url_expression = python_urllib_request_url(
                raw_url_expression,
                self.urllib_request_constructors,
            )
            origin_guard = (
                self.function_network_origin_guards[-1].get(id(node))
                if self.function_network_origin_guards
                else None
            )
            if (
                origin_guard is not None
                and origin_guard.url_name not in self.dynamic_http_origin_names
            ):
                origin_guard = None
            self.add_capability(
                "network",
                node,
                {
                    "api": call_name,
                    "canonical_api": "urllib.request.urlopen",
                    "dynamic_origin": python_http_origin_is_dynamic(
                        url_expression,
                        self.dynamic_http_origin_names,
                        self.static_http_prefixes,
                    ),
                    **(
                        {
                            "network_origin_guard": True,
                            "initial_origin_scope": "allowlisted",
                        }
                        if origin_guard is not None
                        else {}
                    ),
                },
            )
            if origin_guard is not None:
                self.add_python_network_origin_control(node, origin_guard)
        if helper := self.imported_network_helper(node):
            summary, arguments, import_resolution = helper
            secure_policy = summary.secure_policy
            self.add_capability(
                "network",
                node,
                {
                    "api": summary.name,
                    "dynamic_origin": any(
                        (
                            re.match(
                                r"^https?://[^/?#]+",
                                python_static_url_prefix(
                                    argument, self.static_http_prefixes
                                ),
                                re.IGNORECASE,
                            )
                            is None
                            if secure_policy is not None
                            else python_http_origin_is_dynamic(
                                argument,
                                self.dynamic_http_origin_names,
                                self.static_http_prefixes,
                            )
                        )
                        for argument in arguments
                    ),
                    "summary": (
                        "secure-imported-function"
                        if secure_policy is not None
                        else "imported-function"
                    ),
                    "helper_path": summary.path,
                    "helper_line": summary.line,
                    "helper_network_lines": list(summary.network_lines),
                    **(
                        {"import_resolution": import_resolution}
                        if import_resolution
                        == "contextual-absolute-import-single-path"
                        else {}
                    ),
                    **(
                        {
                            "network_origin_policy": True,
                            "initial_origin_scope": secure_policy.initial_origin_scope,
                            "redirect_scope": secure_policy.redirect_scope,
                            "dns_scope": secure_policy.dns_scope,
                            "proxy_scope": secure_policy.proxy_scope,
                            "enforcement_default": secure_policy.enforcement_default,
                        }
                        if secure_policy is not None
                        else {}
                    ),
                },
            )
            if secure_policy is not None:
                self.add_python_secure_network_control(node, summary, secure_policy)
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
    decorated_tool_exports: dict[tuple[str, str], str],
    imported_tool_references: dict[str, tuple[PythonImportedToolReference, ...]],
    imported_tool_export_references: dict[
        tuple[str, str], tuple[PythonImportedToolReference, ...]
    ],
    agent_factory_class_exports: dict[
        tuple[str, str], PythonAgentFactoryClassTarget
    ],
    mcp_server_subclass_exports: dict[
        tuple[str, str], PythonMCPServerSubclassTarget
    ],
    registry_class_exports: dict[tuple[str, str], RegistryClassTarget],
    network_helper_summaries: dict[tuple[str, str], PythonNetworkHelperSummary],
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
    module_mutation_counts: Counter[str] = Counter()

    def collect_module_mutations(candidate: ast.AST) -> None:
        if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_mutations.add(candidate.name)
            module_mutation_counts[candidate.name] += 1
            return
        if isinstance(candidate, (ast.Import, ast.ImportFrom, ast.Lambda)):
            return
        if isinstance(candidate, ast.Name) and isinstance(candidate.ctx, (ast.Store, ast.Del)):
            module_mutations.add(candidate.id)
            module_mutation_counts[candidate.id] += 1
        for child in ast.iter_child_nodes(candidate):
            collect_module_mutations(child)

    for statement in tree.body:
        if not isinstance(statement, (ast.Import, ast.ImportFrom)):
            collect_module_mutations(statement)
    module_global_mutations = {
        name
        for candidate in nodes
        if isinstance(candidate, ast.Global)
        for name in candidate.names
    }
    module_mutations.update(module_global_mutations)
    module_mutation_counts.update(module_global_mutations)
    module_rebound_names = imported_bindings & module_mutations
    module_assignment_counts = Counter(
        target.id
        for statement in tree.body
        if isinstance(statement, (ast.Assign, ast.AnnAssign))
        for target in (
            statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        )
        if isinstance(target, ast.Name)
    )
    module_static_http_prefixes: dict[str, str] = {}
    for statement in tree.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        target = targets[0].id
        if module_assignment_counts[target] != 1:
            continue
        prefix = python_static_url_prefix(statement.value, module_static_http_prefixes)
        if prefix:
            module_static_http_prefixes[target] = prefix

    def literal_string_collection(expression: ast.AST) -> tuple[str, ...] | None:
        container: ast.AST
        if (
            isinstance(expression, ast.Call)
            and dotted_name(expression.func) == "frozenset"
            and dotted_name(expression.func) not in module_mutations
            and len(expression.args) == 1
            and not expression.keywords
        ):
            container = expression.args[0]
        elif isinstance(expression, ast.Tuple):
            container = expression
        else:
            return None
        if not isinstance(container, (ast.List, ast.Tuple, ast.Set)):
            return None
        values = tuple(
            element.value
            for element in container.elts
            if isinstance(element, ast.Constant)
            and isinstance(element.value, str)
        )
        return tuple(sorted(set(values))) if len(values) == len(container.elts) else None

    module_literal_string_sets: dict[str, tuple[str, ...]] = {}
    for statement in tree.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        target = targets[0].id
        values = literal_string_collection(statement.value)
        if module_mutation_counts[target] == 1 and values:
            module_literal_string_sets[target] = values
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
    browser_receiver_type_exports = {
        "ElementHandle",
        "Frame",
        "JSHandle",
        "Locator",
        "Page",
    }
    type_checking_names = {
        alias.asname or alias.name
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom)
        and statement.module == "typing"
        for alias in statement.names
        if alias.name == "TYPE_CHECKING"
        and (alias.asname or alias.name) not in module_rebound_names
    }
    browser_import_statements: list[ast.Import | ast.ImportFrom] = [
        statement
        for statement in tree.body
        if isinstance(statement, (ast.Import, ast.ImportFrom))
    ]
    browser_import_statements.extend(
        child
        for statement in tree.body
        if isinstance(statement, ast.If)
        and isinstance(statement.test, ast.Name)
        and statement.test.id in type_checking_names
        and not statement.orelse
        for child in statement.body
        if isinstance(child, (ast.Import, ast.ImportFrom))
    )
    browser_import_binding_counts = Counter(
        alias.asname
        or (
            alias.name
            if isinstance(statement, ast.ImportFrom)
            else alias.name.split(".", 1)[0]
        )
        for statement in browser_import_statements
        for alias in statement.names
    )
    browser_type_import_counts = Counter(
        alias.asname or alias.name
        for statement in browser_import_statements
        if isinstance(statement, ast.ImportFrom)
        and statement.module is not None
        and statement.module.startswith("playwright.")
        for alias in statement.names
        if alias.name in browser_receiver_type_exports
    )
    browser_type_import_counts.update(
        f"{alias.asname or alias.name}.{export}"
        for statement in browser_import_statements
        if isinstance(statement, ast.Import)
        for alias in statement.names
        if alias.name.startswith("playwright.")
        for export in browser_receiver_type_exports
    )
    browser_type_names = set(browser_type_import_counts)
    browser_type_names = {
        type_name
        for type_name in browser_type_names
        if browser_type_import_counts[type_name] == 1
        if browser_import_binding_counts[type_name.split(".", 1)[0]] == 1
        if type_name.split(".", 1)[0] not in module_mutations
    }
    browser_runtime_import_counts = Counter(
        alias.asname or alias.name
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom)
        and statement.module == "playwright.sync_api"
        for alias in statement.names
        if alias.name == "sync_playwright"
    )
    browser_runtime_import_counts.update(
        f"{alias.asname or alias.name}.sync_playwright"
        for statement in tree.body
        if isinstance(statement, ast.Import)
        for alias in statement.names
        if alias.name == "playwright.sync_api"
    )
    browser_runtime_factories = {
        factory
        for factory, count in browser_runtime_import_counts.items()
        if count == 1
        if browser_import_binding_counts[factory.split(".", 1)[0]] == 1
        if factory.split(".", 1)[0] not in module_mutations
    }
    browser_page_factories: set[str] = set()
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom):
            continue
        for alias in statement.names:
            if alias.name != "get_page":
                continue
            target_path = resolve_python_import_path(
                root,
                relative,
                statement,
                alias.name,
                module_paths,
            )
            if target_path and target_path.endswith("skyvern/cli/mcp_tools/_session.py"):
                browser_page_factories.add(alias.asname or alias.name)
    browser_page_factories = {
        factory
        for factory in browser_page_factories
        if factory.split(".", 1)[0] not in module_rebound_names
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
    urllib_openers: set[str] = set()
    urllib_request_constructors: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name == "urllib.request":
                    binding = alias.asname or alias.name
                    urllib_openers.add(f"{binding}.urlopen")
                    urllib_request_constructors.add(f"{binding}.Request")
                elif alias.name == "urllib":
                    binding = alias.asname or alias.name
                    urllib_openers.add(f"{binding}.request.urlopen")
                    urllib_request_constructors.add(f"{binding}.request.Request")
        elif isinstance(statement, ast.ImportFrom):
            if statement.module == "urllib":
                for alias in statement.names:
                    if alias.name != "request":
                        continue
                    binding = alias.asname or alias.name
                    urllib_openers.add(f"{binding}.urlopen")
                    urllib_request_constructors.add(f"{binding}.Request")
            elif statement.module == "urllib.request":
                for alias in statement.names:
                    binding = alias.asname or alias.name
                    if alias.name == "urlopen":
                        urllib_openers.add(binding)
                    elif alias.name == "Request":
                        urllib_request_constructors.add(binding)
    urllib_openers = {
        opener
        for opener in urllib_openers
        if opener.split(".", 1)[0] not in module_rebound_names
    }
    urllib_request_constructors = {
        constructor
        for constructor in urllib_request_constructors
        if constructor.split(".", 1)[0] not in module_rebound_names
    }
    url_parser_names: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                binding = alias.asname or alias.name
                if alias.name == "urllib":
                    url_parser_names.update(
                        {f"{binding}.parse.urlparse", f"{binding}.parse.urlsplit"}
                    )
                elif alias.name == "urllib.parse":
                    url_parser_names.update(
                        {f"{binding}.urlparse", f"{binding}.urlsplit"}
                    )
        elif isinstance(statement, ast.ImportFrom):
            if statement.module == "urllib":
                for alias in statement.names:
                    if alias.name == "parse":
                        binding = alias.asname or alias.name
                        url_parser_names.update(
                            {f"{binding}.urlparse", f"{binding}.urlsplit"}
                        )
            elif statement.module == "urllib.parse":
                for alias in statement.names:
                    if alias.name in {"urlparse", "urlsplit"}:
                        url_parser_names.add(alias.asname or alias.name)
    url_parser_names = {
        parser
        for parser in url_parser_names
        if parser.split(".", 1)[0] not in module_rebound_names
    }
    registry_decorator_origins = {
        "metagpt.tools.tool_registry": "MetaGPT",
        "qwen_agent.tools.base": "Qwen-Agent",
    }
    registry_decorator_bindings = {
        alias.asname or alias.name: (registry_decorator_origins[statement.module], statement.module)
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom)
        and statement.level == 0
        and statement.module in registry_decorator_origins
        for alias in statement.names
        if alias.name == "register_tool"
        and (alias.asname or alias.name) not in module_rebound_names
    }

    def registry_decorator(
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    ) -> tuple[str, str, ast.Call] | None:
        matches: list[tuple[str, str, ast.Call]] = []
        for decorator in node.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id in registry_decorator_bindings
            ):
                continue
            framework, module = registry_decorator_bindings[decorator.func.id]
            matches.append((framework, f"{module}.register_tool", decorator))
        return matches[0] if len(matches) == 1 else None

    registry_function_tools: dict[int, PythonRegistryTool] = {}
    registry_class_tools: dict[int, PythonRegistryTool] = {}
    for node in nodes:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        resolved_decorator = registry_decorator(node)
        if resolved_decorator is None:
            continue
        framework, registrar, decorator = resolved_decorator
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if framework == "MetaGPT":
                registry_function_tools[id(node)] = PythonRegistryTool(
                    framework, node.name, registrar
                )
            continue
        methods = Counter(
            statement.name
            for statement in node.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        entrypoints: tuple[str, ...] = ()
        tool_name = node.name
        if framework == "Qwen-Agent":
            if not (
                len(decorator.args) == 1
                and isinstance(decorator.args[0], ast.Constant)
                and isinstance(decorator.args[0].value, str)
            ):
                continue
            tool_name = decorator.args[0].value
            if methods["call"] == 1:
                entrypoints = ("call",)
        else:
            include_values = [
                keyword.value
                for keyword in decorator.keywords
                if keyword.arg == "include_functions"
            ]
            if len(include_values) == 1 and isinstance(
                include_values[0], (ast.List, ast.Tuple)
            ):
                names = [
                    element.value
                    for element in include_values[0].elts
                    if isinstance(element, ast.Constant)
                    and isinstance(element.value, str)
                    and methods[element.value] == 1
                ]
                if len(names) == len(include_values[0].elts):
                    entrypoints = tuple(names)
        registry_class_tools[id(node)] = PythonRegistryTool(
            framework, tool_name, registrar, entrypoints
        )
    parent_by_id = {
        id(child): parent for parent in nodes for child in ast.iter_child_nodes(parent)
    }

    def enclosing_statement_block(node: ast.AST) -> tuple[list[ast.stmt], int] | None:
        current = node
        while parent := parent_by_id.get(id(current)):
            for _field, value in ast.iter_fields(parent):
                if not isinstance(value, list):
                    continue
                for index, item in enumerate(value):
                    if item is current and isinstance(item, ast.stmt):
                        return value, index
            current = parent
        return None

    mutation_cache: dict[int, set[str]] = {}

    def statement_mutations(statement: ast.stmt) -> set[str]:
        if id(statement) in mutation_cache:
            return mutation_cache[id(statement)]
        mutations: set[str] = set()

        def collect(candidate: ast.AST) -> None:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                mutations.add(candidate.name)
                return
            if isinstance(candidate, (ast.Import, ast.ImportFrom)):
                mutations.update(
                    alias.asname or alias.name.split(".", 1)[0]
                    for alias in candidate.names
                )
                return
            if isinstance(candidate, ast.ExceptHandler) and candidate.name:
                mutations.add(candidate.name)
            if isinstance(candidate, ast.Name) and isinstance(
                candidate.ctx, (ast.Store, ast.Del)
            ):
                mutations.add(candidate.id)
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        collect(statement)
        mutation_cache[id(statement)] = mutations
        return mutations

    function_tool_factories: dict[str, str] = {}
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module in {
            "agents",
            "agents.tool",
        }:
            for alias in statement.names:
                if alias.name == "function_tool":
                    binding = alias.asname or alias.name
                    function_tool_factories[binding] = (
                        f"{statement.module}.function_tool"
                    )
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name == "agents":
                    binding = alias.asname or "agents"
                    function_tool_factories[f"{binding}.function_tool"] = (
                        "agents.function_tool"
                    )
                elif alias.name == "agents.tool":
                    if alias.asname:
                        function_tool_factories[f"{alias.asname}.function_tool"] = (
                            "agents.tool.function_tool"
                        )
                    else:
                        function_tool_factories["agents.tool.function_tool"] = (
                            "agents.tool.function_tool"
                        )
    function_tool_factories = {
        name: registrar
        for name, registrar in function_tool_factories.items()
        if name.split(".", 1)[0] not in module_rebound_names
    }

    def function_tool_registrar(call: ast.Call) -> str | None:
        call_name = dotted_name(call.func)
        registrar = function_tool_factories.get(call_name)
        if registrar is None:
            return None
        root_name = call_name.split(".", 1)[0]
        parent = parent_by_id.get(id(call))
        while parent is not None and not isinstance(
            parent, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            parent = parent_by_id.get(id(parent))
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            root_name in python_function_local_bindings(parent)
        ):
            return None
        return registrar

    import_binding_counts: Counter[str] = Counter()
    tool_constructor_import_candidates: dict[str, list[ast.ImportFrom]] = defaultdict(list)
    mcp_constructor_import_candidates: dict[str, list[ast.ImportFrom]] = defaultdict(list)

    def module_mcp_constructor_import(statement: ast.ImportFrom) -> bool:
        if statement in tree.body:
            return True
        parent = parent_by_id.get(id(statement))
        return bool(
            isinstance(parent, ast.Try)
            and parent in tree.body
            and statement in parent.body
            and parent.handlers
            and all(
                python_block_always_terminates(handler.body)
                for handler in parent.handlers
            )
        )

    for statement in (candidate for candidate in nodes if isinstance(candidate, ast.ImportFrom)):
        module_parts = re.split(r"[._]", statement.module or "")
        for alias in statement.names:
            local_name = alias.asname or alias.name
            import_binding_counts[local_name] += 1
            if any("tool" in part.lower() for part in module_parts) or (
                statement.module or "",
                alias.name,
            ) in EXACT_TOOL_CONSTRUCTOR_IMPORTS:
                tool_constructor_import_candidates[local_name].append(statement)
            if (
                module_mcp_constructor_import(statement)
                and alias.name
                in MCP_LAUNCHER_CONSTRUCTORS | MCP_IN_PROCESS_SERVER_CONSTRUCTORS
                and is_mcp_server_constructor_module(
                    statement.module or "", alias.name
                )
            ):
                mcp_constructor_import_candidates[local_name].append(statement)
    for statement in (candidate for candidate in nodes if isinstance(candidate, ast.Import)):
        import_binding_counts.update(
            alias.asname or alias.name.split(".", 1)[0]
            for alias in statement.names
        )

    nonimport_binding_counts: Counter[str] = Counter()
    for candidate in nodes:
        if isinstance(candidate, ast.Name) and isinstance(candidate.ctx, (ast.Store, ast.Del)):
            nonimport_binding_counts[candidate.id] += 1
        elif isinstance(candidate, ast.arg):
            nonimport_binding_counts[candidate.arg] += 1
        elif isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nonimport_binding_counts[candidate.name] += 1
    imported_tool_constructors = {
        name: imports[0]
        for name, imports in tool_constructor_import_candidates.items()
        if len(imports) == 1
        and import_binding_counts[name] == 1
        and nonimport_binding_counts[name] == 0
    }
    imported_mcp_constructors = {
        name: imports[0]
        for name, imports in mcp_constructor_import_candidates.items()
        if len(imports) == 1
        and import_binding_counts[name] == 1
        and nonimport_binding_counts[name] == 0
    }
    imported_mcp_constructor_names = {
        name: next(
            alias.name
            for alias in statement.names
            if (alias.asname or alias.name) == name
        )
        for name, statement in imported_mcp_constructors.items()
    }
    agent_constructor_bindings = {
        alias.asname or alias.name
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom)
        and statement.module == "agents.sandbox"
        for alias in statement.names
        if alias.name == "SandboxAgent"
        and import_binding_counts[alias.asname or alias.name] == 1
        and nonimport_binding_counts[alias.asname or alias.name] == 0
    }
    python_framework_modules = {
        prefix
        for prefix in (
            *(
                prefix
                for prefixes in IMPORT_SIGNATURES["framework"].values()
                for prefix in prefixes
            ),
            *(
                prefix
                for prefixes in FRONTEND_IMPORT_SIGNATURES["python"][
                    "framework"
                ].values()
                for prefix in prefixes
            ),
        )
        if not prefix.startswith("@")
    }
    local_agent_factory_constructors = agent_constructor_bindings | {
        alias.asname or alias.name
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom)
        and statement.level == 0
        and statement.module is not None
        and any(
            statement.module == prefix
            or statement.module.startswith(f"{prefix}.")
            for prefix in python_framework_modules
        )
        for alias in statement.names
        if alias.asname is None
        and alias.name in AGENT_CALLS
        and import_binding_counts[alias.asname or alias.name] == 1
        and nonimport_binding_counts[alias.asname or alias.name] == 0
    }
    exact_openai_builtin_imports = {
        alias.asname or alias.name: (alias.name, statement.lineno)
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom)
        and statement.level == 0
        and statement.module in {"agents", "agents.tool"}
        for alias in statement.names
        if alias.name in EXACT_IMPORT_OPENAI_BUILTINS
        and import_binding_counts[alias.asname or alias.name] == 1
        and nonimport_binding_counts[alias.asname or alias.name] == 0
    }
    exact_openai_builtin_call_names = {
        id(candidate): exact_openai_builtin_imports[candidate.func.id][0]
        for candidate in nodes
        if isinstance(candidate, ast.Call)
        and isinstance(candidate.func, ast.Name)
        and candidate.func.id in exact_openai_builtin_imports
        and exact_openai_builtin_imports[candidate.func.id][1] < candidate.lineno
    }

    def is_agent_call(call: ast.Call) -> bool:
        call_name = dotted_name(call.func)
        return (
            call_name.rsplit(".", 1)[-1] in AGENT_CALLS
            or call_name in agent_constructor_bindings
        )

    def lexical_owner(node: ast.AST) -> ast.AST:
        current = node
        while parent := parent_by_id.get(id(current)):
            if isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                return parent
            current = parent
        return tree

    mcp_adapter_import_candidates: dict[
        str,
        list[tuple[PythonMCPServerSubclassTarget, ast.ImportFrom, ast.AST, str]],
    ] = defaultdict(list)
    for statement in (
        candidate for candidate in nodes if isinstance(candidate, ast.ImportFrom)
    ):
        for alias in statement.names:
            resolution = resolve_python_import(
                root,
                relative,
                statement,
                alias.name,
                module_paths,
            )
            if resolution is None:
                continue
            target = mcp_server_subclass_exports.get((resolution.path, alias.name))
            if target is None:
                continue
            mcp_adapter_import_candidates[alias.asname or alias.name].append(
                (target, statement, lexical_owner(statement), resolution.basis)
            )
    imported_mcp_adapter_constructors = {
        name: candidates[0]
        for name, candidates in mcp_adapter_import_candidates.items()
        if len(candidates) == 1
        and import_binding_counts[name] == 1
        and nonimport_binding_counts[name] == 0
    }

    local_tool_constructor_classes = {
        statement.name
        for statement in tree.body
        if isinstance(statement, ast.ClassDef)
        and not statement.decorator_list
        and module_mutation_counts[statement.name] == 1
        and any(
            isinstance(base, ast.Name) and base.id in imported_tool_constructors
            for base in statement.bases
        )
    }

    def usage_proven_tool_constructor(call: ast.Call) -> bool:
        if isinstance(call.func, ast.Name):
            constructor = call.func.id
        elif (
            isinstance(call.func, ast.Attribute)
            and call.func.attr in IMPORTED_TOOL_FACTORY_METHODS
            and isinstance(call.func.value, ast.Name)
        ):
            constructor = call.func.value.id
        else:
            return False
        if constructor in local_tool_constructor_classes:
            return isinstance(call.func, ast.Name)
        imported_at = imported_tool_constructors.get(constructor)
        return imported_at is not None and imported_at.lineno < call.lineno

    module_tool_definitions: dict[str, list[ast.stmt]] = defaultdict(list)
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if module_mutation_counts[statement.name] == 1:
                module_tool_definitions[statement.name].append(statement)
            continue
        if not (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and isinstance(statement.value, ast.Call)
        ):
            continue
        binding = statement.targets[0].id
        if module_mutation_counts[binding] == 1:
            module_tool_definitions[binding].append(statement)

    def shadowed_tool_reference(node: ast.AST, name: str) -> bool:
        parent = parent_by_id.get(id(node))
        while parent is not None:
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                name in python_function_local_bindings(parent)
            ):
                return True
            parent = parent_by_id.get(id(parent))
        return False

    def direct_context_tool_binding(
        call: ast.Call,
        name: str,
    ) -> tuple[ast.With | ast.AsyncWith, ast.Call] | None:
        current: ast.AST = call
        while parent := parent_by_id.get(id(current)):
            if isinstance(parent, (ast.With, ast.AsyncWith)) and current in parent.body:
                if not isinstance(current, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Return)):
                    return None
                use_index = parent.body.index(current)
                if any(
                    name in statement_mutations(statement)
                    for statement in parent.body[:use_index]
                ):
                    return None
                matches = [
                    item.context_expr
                    for item in parent.items
                    if isinstance(item.optional_vars, ast.Name)
                    and item.optional_vars.id == name
                    and isinstance(item.context_expr, ast.Call)
                ]
                return (parent, matches[0]) if len(matches) == 1 else None
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return None
            current = parent
        return None

    current_imported_tool_references = imported_tool_references.get(relative, ())
    referenced_tool_functions: dict[int, PythonToolRoleReference] = {}
    for statement in tree.body:
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        references = imported_tool_export_references.get(
            (relative, statement.name), ()
        )
        if not references:
            continue
        reference = references[0]
        referenced_tool_functions[id(statement)] = PythonToolRoleReference(
            registration_path=reference.importer_path,
            registration_line=reference.agent_line,
            resolution=(
                "contextual-imported-callable-single-export"
                if reference.import_resolution
                == "contextual-absolute-import-single-path"
                else "imported-callable-single-export"
            ),
            import_line=reference.import_line,
        )
    usage_tool_assignments: dict[int, tuple[ast.Assign, ast.Call, str]] = {}
    inline_usage_tool_candidates: dict[int, tuple[ast.Call, ast.Call]] = {}
    context_usage_tool_bindings: dict[
        tuple[int, str], tuple[ast.With | ast.AsyncWith, ast.Call, list[ast.Call]]
    ] = {}
    agent_as_tool_assignments: dict[
        int, tuple[ast.Assign, ast.Call, ast.Assign]
    ] = {}
    wrapper_candidates: dict[int, PythonFunctionToolWrapper] = {}
    openai_agents_context = any(
        module == "agents" or module.startswith("agents.")
        for module in imported_modules
    )
    for call in (
        candidate
        for candidate in nodes
        if isinstance(candidate, ast.Call) and is_agent_call(candidate)
    ):
        block = enclosing_statement_block(call)
        if block is None:
            continue
        statements, use_index = block
        for keyword in call.keywords:
            if keyword.arg != "tools" or not isinstance(keyword.value, (ast.List, ast.Tuple)):
                continue
            for value in keyword.value.elts:
                if isinstance(value, ast.Call):
                    call_name = dotted_name(value.func)
                    short_name = call_name.rsplit(".", 1)[-1]
                    if (
                        call_name
                        and not call_name.endswith(".as_tool")
                        and usage_proven_tool_constructor(value)
                        and not (
                            openai_agents_context
                            and (
                                id(value) in exact_openai_builtin_call_names
                                or (
                                    short_name in BUILTIN_TOOL_CAPABILITIES
                                    and short_name not in EXACT_IMPORT_OPENAI_BUILTINS
                                )
                            )
                        )
                    ):
                        inline_usage_tool_candidates.setdefault(
                            id(value), (value, call)
                        )
                    continue
                if not isinstance(value, ast.Name):
                    continue
                mutations = [
                    statement
                    for statement in statements[:use_index]
                    if value.id in statement_mutations(statement)
                ]
                resolution = "same-block-single-definition"
                definition: ast.stmt | None = mutations[0] if len(mutations) == 1 else None
                if not mutations:
                    if context_binding := direct_context_tool_binding(call, value.id):
                        context_node, context_call = context_binding
                        if not usage_proven_tool_constructor(context_call):
                            continue
                        key = (id(context_node), value.id)
                        existing = context_usage_tool_bindings.get(key)
                        if existing is None:
                            context_usage_tool_bindings[key] = (
                                context_node,
                                context_call,
                                [call],
                            )
                        else:
                            existing[2].append(call)
                        continue
                    if not shadowed_tool_reference(call, value.id):
                        module_definitions = [
                            candidate
                            for candidate in module_tool_definitions.get(value.id, [])
                            if candidate.lineno < call.lineno
                        ]
                        if len(module_definitions) == 1:
                            definition = module_definitions[0]
                            resolution = "module-single-definition"
                if definition is None:
                    continue
                if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    definition.name == value.id
                ):
                    referenced_tool_functions.setdefault(
                        id(definition),
                        PythonToolRoleReference(
                            registration_path=relative,
                            registration_line=call.lineno,
                            resolution=resolution,
                        ),
                    )
                    continue
                if (
                    isinstance(definition, ast.Assign)
                    and len(definition.targets) == 1
                    and isinstance(definition.targets[0], ast.Name)
                    and definition.targets[0].id == value.id
                    and isinstance(definition.value, ast.Call)
                    and usage_proven_tool_constructor(definition.value)
                ):
                    usage_tool_assignments.setdefault(
                        id(definition), (definition, call, resolution)
                    )
                if (
                    isinstance(definition, ast.Assign)
                    and len(definition.targets) == 1
                    and isinstance(definition.targets[0], ast.Name)
                    and definition.targets[0].id == value.id
                    and isinstance(definition.value, ast.Call)
                    and isinstance(definition.value.func, ast.Attribute)
                    and definition.value.func.attr == "as_tool"
                    and isinstance(definition.value.func.value, ast.Name)
                ):
                    adapter_block = enclosing_statement_block(definition)
                    if adapter_block is not None:
                        adapter_statements, adapter_index = adapter_block
                        receiver = definition.value.func.value.id
                        receiver_mutations = [
                            statement
                            for statement in adapter_statements[:adapter_index]
                            if receiver in statement_mutations(statement)
                        ]
                        if (
                            len(receiver_mutations) == 1
                            and isinstance(receiver_mutations[0], ast.Assign)
                            and len(receiver_mutations[0].targets) == 1
                            and isinstance(receiver_mutations[0].targets[0], ast.Name)
                            and receiver_mutations[0].targets[0].id == receiver
                            and isinstance(receiver_mutations[0].value, ast.Call)
                            and is_agent_call(receiver_mutations[0].value)
                        ):
                            agent_as_tool_assignments.setdefault(
                                id(definition),
                                (definition, call, receiver_mutations[0]),
                            )
                if not (
                    isinstance(definition, ast.Assign)
                    and len(definition.targets) == 1
                    and isinstance(definition.targets[0], ast.Name)
                    and definition.targets[0].id == value.id
                    and isinstance(definition.value, ast.Call)
                    and len(definition.value.args) == 1
                    and isinstance(definition.value.args[0], ast.Name)
                ):
                    continue
                registrar = function_tool_registrar(definition.value)
                if registrar is None:
                    continue
                wrapper_block = enclosing_statement_block(definition)
                if wrapper_block is None:
                    continue
                wrapper_statements, wrapper_index = wrapper_block
                function_name = definition.value.args[0].id
                function_mutations = [
                    statement
                    for statement in wrapper_statements[:wrapper_index]
                    if function_name in statement_mutations(statement)
                ]
                if len(function_mutations) != 1 or not isinstance(
                    function_mutations[0], (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    continue
                function = function_mutations[0]
                if function.name != function_name or function.decorator_list:
                    continue
                wrapper_candidates.setdefault(
                    id(definition),
                    PythonFunctionToolWrapper(
                        value.id,
                        definition,
                        definition.value,
                        function,
                        call,
                        registrar,
                    ),
                )
    wrappers_by_function: dict[int, list[PythonFunctionToolWrapper]] = defaultdict(list)
    for wrapper in wrapper_candidates.values():
        wrappers_by_function[id(wrapper.function)].append(wrapper)
    wrapped_tool_functions = {
        function_id: wrappers[0]
        for function_id, wrappers in wrappers_by_function.items()
        if len(wrappers) == 1 and function_id not in referenced_tool_functions
    }
    wrapped_tool_assignments = {
        id(wrapper.assignment): wrapper for wrapper in wrapped_tool_functions.values()
    }
    usage_tool_assignments = {
        assignment_id: reference
        for assignment_id, reference in usage_tool_assignments.items()
        if assignment_id not in wrapped_tool_assignments
    }
    symbol_candidates: dict[tuple[str, str], set[str]] = {}
    call_symbol_ids: dict[int, str] = {}
    definition_symbol_ids: dict[int, str] = {}
    decorated_tools: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]] = []
    registered_class_tools: list[tuple[ast.ClassDef, PythonRegistryTool]] = []
    external_import_tool_ids: dict[tuple[str, int], str] = {}
    external_import_groups: dict[
        tuple[str, int, str, str], list[PythonImportedToolReference]
    ] = defaultdict(list)
    for reference in current_imported_tool_references:
        if reference.import_resolution is None:
            external_import_groups[
                (
                    reference.local_name,
                    reference.import_line,
                    reference.module,
                    reference.original_name,
                )
            ].append(reference)
    for (
        local_name,
        import_line,
        module,
        original_name,
    ), references in external_import_groups.items():
        symbol_id = source_symbol("py", relative, "tool", local_name)
        external_import_tool_ids[(local_name, import_line)] = symbol_id
        symbol_candidates.setdefault(("tool", local_name), set()).add(symbol_id)
        ir.add_component(
            Component(
                "tool",
                local_name,
                Evidence(relative, import_line, excerpt(text.splitlines(), import_line)),
                {
                    "binding": "literal-tools-list-import",
                    "module": module,
                    "imported_name": original_name,
                    "registration": "agent-tool-reference",
                    "registration_lines": sorted(
                        {reference.agent_line for reference in references}
                    ),
                    "resolution": "literal-import-binding",
                    "scope": source_scope(relative),
                },
                symbol_id,
            )
        )

    def collect_definitions(
        statements: list[ast.stmt],
        class_stack: tuple[str, ...] = (),
        *,
        module_scope: bool = True,
    ) -> None:
        for node in statements:
            if isinstance(node, ast.ClassDef):
                if registry_tool := registry_class_tools.get(id(node)):
                    registered_class_tools.append((node, registry_tool))
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
                or id(node) in registry_function_tools
                or id(node) in referenced_tool_functions
                or (
                    module_scope
                    and (relative, node.name) in registered_tool_functions
                )
            ):
                qualified_name = ".".join([*class_stack, node.name])
                decorated_tools.append((node, qualified_name))
            collect_definitions(node.body, class_stack, module_scope=False)

    collect_definitions(tree.body)
    collected_tool_definition_ids = {id(node) for node, _name in decorated_tools}
    for node in nodes:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if id(node) not in referenced_tool_functions or id(node) in collected_tool_definition_ids:
            continue
        class_names: list[str] = []
        parent = parent_by_id.get(id(node))
        while parent is not None:
            if isinstance(parent, ast.ClassDef):
                class_names.append(parent.name)
            parent = parent_by_id.get(id(parent))
        decorated_tools.append((node, ".".join([*reversed(class_names), node.name])))
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
    class_tool_counts = Counter(tool.name for _, tool in registered_class_tools)
    for node, tool in registered_class_tools:
        identity = f"{tool.name}@{node.lineno}" if class_tool_counts[tool.name] > 1 else tool.name
        symbol_id = source_symbol("py", relative, "tool", identity)
        symbol_candidates.setdefault(("tool", tool.name), set()).add(symbol_id)
        symbol_candidates.setdefault(("tool", node.name), set()).add(symbol_id)
        definition_symbol_ids[id(node)] = symbol_id
    assigned_constructors: list[tuple[ast.Assign, str, str]] = []
    mcp_adapter_assignments: dict[
        int, tuple[PythonMCPServerSubclassTarget, str]
    ] = {}
    for node in nodes:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            binding = node.targets[0].id
            short_name = dotted_name(node.value.func).rsplit(".", 1)[-1]
            adapter_import = (
                imported_mcp_adapter_constructors.get(node.value.func.id)
                if isinstance(node.value.func, ast.Name)
                else None
            )
            adapter_target = (
                adapter_import[0]
                if adapter_import is not None
                and adapter_import[1].lineno < node.lineno
                and adapter_import[2] is lexical_owner(node)
                else None
            )
            kind = (
                "agent"
                if is_agent_call(node.value)
                else "tool"
                if (
                    short_name in BUILTIN_TOOL_CAPABILITIES
                    and short_name not in EXACT_IMPORT_OPENAI_BUILTINS
                )
                or id(node.value) in exact_openai_builtin_call_names
                or id(node) in wrapped_tool_assignments
                or id(node) in usage_tool_assignments
                or id(node) in agent_as_tool_assignments
                else "mcp-server"
                if isinstance(node.value.func, ast.Name)
                and (
                    node.value.func.id in imported_mcp_constructors
                    or adapter_target is not None
                )
                else None
            )
            if kind:
                assigned_constructors.append((node, kind, binding))
                if kind == "mcp-server" and adapter_target is not None:
                    mcp_adapter_assignments[id(node)] = (
                        adapter_target,
                        adapter_import[3],
                    )
    context_mcp_servers: list[
        tuple[ast.With | ast.AsyncWith, ast.Call, str, str]
    ] = []
    for node in nodes:
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            if (
                not isinstance(item.context_expr, ast.Call)
                or not isinstance(item.context_expr.func, ast.Name)
                or item.context_expr.func.id not in imported_mcp_constructors
                or not isinstance(item.optional_vars, ast.Name)
            ):
                continue
            constructor = imported_mcp_constructor_names[item.context_expr.func.id]
            context_mcp_servers.append(
                (node, item.context_expr, item.optional_vars.id, constructor)
            )
    definition_counts = Counter(
        (kind, binding) for _, kind, binding in assigned_constructors
    )
    definition_counts.update(
        ("mcp-server", binding)
        for _with_node, _call, binding, _constructor in context_mcp_servers
    )
    for node, kind, binding in assigned_constructors:
        identity = f"{binding}@{node.lineno}" if definition_counts[(kind, binding)] > 1 else binding
        symbol_id = source_symbol("py", relative, kind, identity)
        symbol_candidates.setdefault((kind, binding), set()).add(symbol_id)
        call_symbol_ids[id(node.value)] = symbol_id
        if wrapper := wrapped_tool_assignments.get(id(node)):
            definition_symbol_ids[id(wrapper.function)] = symbol_id
    for _with_node, call, binding, _constructor in context_mcp_servers:
        identity = (
            f"{binding}@{call.lineno}"
            if definition_counts[("mcp-server", binding)] > 1
            else binding
        )
        symbol_id = source_symbol("py", relative, "mcp-server", identity)
        symbol_candidates.setdefault(("mcp-server", binding), set()).add(symbol_id)
        call_symbol_ids[id(call)] = symbol_id

    def mcp_server_constructor(call: ast.Call) -> str:
        constructor_binding = dotted_name(call.func)
        if adapter := imported_mcp_adapter_constructors.get(constructor_binding):
            return adapter[0].name
        return imported_mcp_constructor_names.get(
            constructor_binding, constructor_binding.rsplit(".", 1)[-1]
        )

    def assigned_mcp_server_name(node: ast.Assign) -> str:
        if not isinstance(node.value, ast.Call):
            raise TypeError("assigned MCP server must originate from a call")
        constructor = mcp_server_constructor(node.value)
        return f"{constructor}@{node.value.lineno}"

    def context_mcp_server_name(call: ast.Call, constructor: str) -> str:
        configured_name = next(
            (
                keyword.value.value
                for keyword in call.keywords
                if keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ),
            None,
        )
        return configured_name or f"{constructor}@{call.lineno}"

    mcp_server_symbol_names = {
        call_symbol_ids[id(node.value)]: assigned_mcp_server_name(node)
        for node, kind, _binding in assigned_constructors
        if kind == "mcp-server"
    }
    mcp_server_symbol_names.update(
        {
            call_symbol_ids[id(call)]: context_mcp_server_name(call, constructor)
            for _with_node, call, _binding, constructor in context_mcp_servers
        }
    )
    mcp_server_binding_resolutions = {
        id(node.value): "assignment"
        for node, kind, _binding in assigned_constructors
        if kind == "mcp-server"
    }
    mcp_server_binding_resolutions.update(
        {
            id(call): "context-manager-binding"
            for _with_node, call, _binding, _constructor in context_mcp_servers
        }
    )
    observed_mcp_server_ids: set[str] = set()
    for node, kind, _binding in assigned_constructors:
        adapter = mcp_adapter_assignments.get(id(node))
        if kind != "mcp-server" or adapter is None:
            continue
        target, import_resolution = adapter
        symbol_id = call_symbol_ids[id(node.value)]
        observed_mcp_server_ids.add(symbol_id)
        ir.add_component(
            Component(
                "mcp-server",
                mcp_server_symbol_names[symbol_id],
                Evidence(
                    relative,
                    node.value.lineno,
                    excerpt(text.splitlines(), node.value.lineno),
                ),
                {
                    "transport": "adapter",
                    "constructor": target.name,
                    "adapter_definition_path": target.path,
                    "adapter_definition_line": target.line,
                    "adapter_base_module": target.base_module,
                    "adapter_base_name": target.base_name,
                    "import_resolution": import_resolution,
                    "binding_resolution": "assignment",
                    "analysis": "python-imported-mcp-server-subclass",
                    "frontend": "python",
                    "scope": source_scope(relative),
                },
                symbol_id,
            )
        )
    context_mcp_server_scope_candidates: dict[
        tuple[int, str], list[tuple[ast.Call, str]]
    ] = defaultdict(list)
    for with_node, call, binding, _constructor in context_mcp_servers:
        context_mcp_server_scope_candidates[(id(with_node), binding)].append(
            (call, call_symbol_ids[id(call)])
        )
    context_mcp_servers_by_scope = {
        key: candidates[0]
        for key, candidates in context_mcp_server_scope_candidates.items()
        if len(candidates) == 1
    }

    def direct_context_mcp_server(
        agent_call: ast.Call,
        binding: str,
    ) -> tuple[ast.Call, str] | None:
        current: ast.AST = agent_call
        while parent := parent_by_id.get(id(current)):
            if isinstance(parent, (ast.With, ast.AsyncWith)) and current in parent.body:
                if not isinstance(current, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Return)):
                    return None
                use_index = parent.body.index(current)
                if any(
                    binding in statement_mutations(statement)
                    for statement in parent.body[:use_index]
                ):
                    return None
                return context_mcp_servers_by_scope.get((id(parent), binding))
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return None
            current = parent
        return None

    context_usage_mcp_resolutions: list[tuple[ast.Call, str, str]] = []
    for agent_call in (
        candidate
        for candidate in nodes
        if isinstance(candidate, ast.Call) and is_agent_call(candidate)
    ):
        for keyword in agent_call.keywords:
            if keyword.arg != "mcp_servers" or not isinstance(
                keyword.value, (ast.List, ast.Tuple)
            ):
                continue
            for value in keyword.value.elts:
                if not isinstance(value, ast.Name):
                    continue
                if resolved := direct_context_mcp_server(agent_call, value.id):
                    _context_call, symbol_id = resolved
                    context_usage_mcp_resolutions.append(
                        (agent_call, value.id, symbol_id)
                    )
    mcp_in_process_server_bindings = {
        binding: (
            mcp_server_symbol_names[call_symbol_ids[id(node.value)]],
            call_symbol_ids[id(node.value)],
        )
        for node, kind, binding in assigned_constructors
        if kind == "mcp-server"
        and mcp_server_constructor(node.value)
        in MCP_IN_PROCESS_SERVER_CONSTRUCTORS
        and isinstance(parent_by_id.get(id(node)), ast.Module)
        and module_mutation_counts[binding] == 1
    }
    immutable_module_mcp_servers = {
        binding: (node.lineno, call_symbol_ids[id(node.value)])
        for node, kind, binding in assigned_constructors
        if kind == "mcp-server"
        and isinstance(parent_by_id.get(id(node)), ast.Module)
        and module_mutation_counts[binding] == 1
    }

    usage_tool_assignment_ids = set(usage_tool_assignments)
    for node, kind, binding in assigned_constructors:
        if id(node) not in usage_tool_assignment_ids or kind != "tool":
            continue
        constructor = dotted_name(node.value.func)
        if (
            openai_agents_context
            and (
                id(node.value) in exact_openai_builtin_call_names
                or (
                    constructor.rsplit(".", 1)[-1] in BUILTIN_TOOL_CAPABILITIES
                    and constructor.rsplit(".", 1)[-1]
                    not in EXACT_IMPORT_OPENAI_BUILTINS
                )
            )
        ):
            continue
        symbol_id = call_symbol_ids[id(node.value)]
        ir.add_component(
            Component(
                "tool",
                binding,
                Evidence(relative, node.lineno, excerpt(text.splitlines(), node.lineno)),
                {
                    "binding": "literal-tools-list-constructor",
                    "constructor": constructor,
                    "registration": "agent-tool-reference",
                    "registration_line": usage_tool_assignments[id(node)][1].lineno,
                    "resolution": usage_tool_assignments[id(node)][2],
                    "scope": source_scope(relative),
                },
                symbol_id,
            )
        )
        constructor_root = constructor.split(".", 1)[0]
        constructor_import = imported_tool_constructors.get(constructor_root)
        is_hosted_mcp_tool = constructor_import is not None and any(
            alias.name == "HostedMCPTool"
            and (alias.asname or alias.name) == constructor_root
            for alias in constructor_import.names
        )
        if (
            constructor_import is not None
            and constructor_import.module == "agents"
            and is_hosted_mcp_tool
        ):
            evidence = Evidence(
                relative,
                node.value.lineno,
                excerpt(text.splitlines(), node.value.lineno),
            )
            ir.add_component(
                Component(
                    "capability",
                    "mcp-access",
                    evidence,
                    {
                        "api": constructor,
                        "hosted": True,
                        "scope": source_scope(relative),
                    },
                )
            )
            ir.add_relationship(
                Relationship(
                    "tool",
                    binding,
                    "uses",
                    "capability",
                    "mcp-access",
                    evidence,
                    source_id=symbol_id,
                )
            )

    for (
        assignment,
        agent_call,
        receiver_assignment,
    ) in agent_as_tool_assignments.values():
        binding = assignment.targets[0].id
        receiver = receiver_assignment.targets[0].id
        tool_id = call_symbol_ids[id(assignment.value)]
        agent_id = call_symbol_ids[id(receiver_assignment.value)]
        evidence = Evidence(
            relative,
            assignment.lineno,
            excerpt(text.splitlines(), assignment.lineno),
        )
        ir.add_component(
            Component(
                "tool",
                binding,
                evidence,
                {
                    "binding": "agent-as-tool-adapter",
                    "adapter": dotted_name(assignment.value.func),
                    "registration": "agent-tool-reference",
                    "registration_line": agent_call.lineno,
                    "target_agent": receiver,
                    "target_agent_id": agent_id,
                    "resolution": "same-block-agent-as-tool",
                    "scope": source_scope(relative),
                },
                tool_id,
            )
        )
        ir.add_relationship(
            Relationship(
                "tool",
                binding,
                "delegates-to",
                "agent",
                receiver,
                evidence,
                {
                    "adapter": "as_tool",
                    "target_identity": "same-block-agent-as-tool",
                },
                source_id=tool_id,
                target_id=agent_id,
            )
        )

    inline_usage_tool_calls: dict[int, tuple[str, str]] = {}
    inline_name_counts = Counter(
        (dotted_name(call.func).rsplit(".", 1)[-1], call.lineno)
        for call, _agent_call in inline_usage_tool_candidates.values()
    )
    for call, agent_call in inline_usage_tool_candidates.values():
        constructor = dotted_name(call.func)
        short_name = constructor.rsplit(".", 1)[-1]
        occurrence = f"{short_name}@{call.lineno}"
        if inline_name_counts[(short_name, call.lineno)] > 1:
            occurrence = f"{occurrence}:{call.col_offset}"
        symbol_id = source_symbol("py", relative, "tool", occurrence)
        inline_usage_tool_calls[id(call)] = (occurrence, symbol_id)
        call_symbol_ids[id(call)] = symbol_id
        ir.add_component(
            Component(
                "tool",
                occurrence,
                Evidence(relative, call.lineno, excerpt(text.splitlines(), call.lineno)),
                {
                    "binding": "literal-tools-list-inline-constructor",
                    "constructor": constructor,
                    "registration": "agent-tool-reference",
                    "registration_line": agent_call.lineno,
                    "resolution": "literal-inline-constructor",
                    "scope": source_scope(relative),
                },
                symbol_id,
            )
        )

    context_usage_tool_resolutions: list[tuple[ast.Call, str, str]] = []
    context_binding_counts = Counter(
        name for _node_id, name in context_usage_tool_bindings
    )
    for (_node_id, binding), (
        context_node,
        context_call,
        agent_calls,
    ) in context_usage_tool_bindings.items():
        identity = (
            f"{binding}@{context_node.lineno}"
            if context_binding_counts[binding] > 1
            else binding
        )
        symbol_id = source_symbol("py", relative, "tool", identity)
        symbol_candidates.setdefault(("tool", binding), set()).add(symbol_id)
        call_symbol_ids[id(context_call)] = symbol_id
        ir.add_component(
            Component(
                "tool",
                identity,
                Evidence(
                    relative,
                    context_node.lineno,
                    excerpt(text.splitlines(), context_node.lineno),
                ),
                {
                    "binding": "literal-tools-list-context-manager",
                    "constructor": dotted_name(context_call.func),
                    "registration": "agent-tool-reference",
                    "registration_lines": sorted(
                        {agent_call.lineno for agent_call in agent_calls}
                    ),
                    "resolution": "direct-context-manager-binding",
                    "scope": source_scope(relative),
                },
                symbol_id,
            )
        )
        context_usage_tool_resolutions.extend(
            (agent_call, binding, symbol_id) for agent_call in agent_calls
        )

    builtin_tool_type_candidates: dict[str, set[str]] = defaultdict(set)
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module in {
            "agents",
            "agents.tool",
        }:
            for alias in statement.names:
                if alias.name in BUILTIN_TOOL_CAPABILITIES:
                    builtin_tool_type_candidates[alias.asname or alias.name].add(
                        alias.name
                    )
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name == "agents":
                    prefix = alias.asname or "agents"
                elif alias.name == "agents.tool":
                    prefix = alias.asname or "agents.tool"
                else:
                    continue
                for constructor in BUILTIN_TOOL_CAPABILITIES:
                    builtin_tool_type_candidates[f"{prefix}.{constructor}"].add(
                        constructor
                    )
    builtin_tool_types = {
        binding: next(iter(constructors))
        for binding, constructors in builtin_tool_type_candidates.items()
        if len(constructors) == 1
        and binding.split(".", 1)[0] not in module_rebound_names
    }
    function_local_bindings_cache: dict[int, set[str]] = {}

    enclosing_function_cache: dict[
        int, ast.FunctionDef | ast.AsyncFunctionDef | None
    ] = {}

    def enclosing_function(
        node: ast.AST,
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        if id(node) in enclosing_function_cache:
            return enclosing_function_cache[id(node)]
        parent = parent_by_id.get(id(node))
        while parent is not None and not isinstance(
            parent, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            parent = parent_by_id.get(id(parent))
        function = (
            parent
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
            else None
        )
        enclosing_function_cache[id(node)] = function
        return function

    def function_local_bindings(
        function: ast.FunctionDef | ast.AsyncFunctionDef | None,
    ) -> set[str]:
        if function is None:
            return set()
        if id(function) not in function_local_bindings_cache:
            function_local_bindings_cache[id(function)] = python_function_local_bindings(
                function
            )
        return function_local_bindings_cache[id(function)]

    def enclosed_by_lambda(node: ast.AST) -> bool:
        parent = parent_by_id.get(id(node))
        while parent is not None:
            if isinstance(parent, ast.Lambda):
                return True
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            parent = parent_by_id.get(id(parent))
        return False

    def shadowed_in_enclosing_functions(node: ast.AST, name: str) -> bool:
        parent = parent_by_id.get(id(node))
        while parent is not None:
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                name in function_local_bindings(parent)
            ):
                return True
            parent = parent_by_id.get(id(parent))
        return False

    def builtin_tool_constructor(
        call: ast.Call,
    ) -> str | None:
        call_name = dotted_name(call.func)
        constructor = builtin_tool_types.get(call_name)
        if (
            constructor is None
            or call_name.rsplit(".", 1)[-1] != constructor
            or enclosed_by_lambda(call)
            or shadowed_in_enclosing_functions(call, call_name.split(".", 1)[0])
        ):
            return None
        return constructor

    def call_argument_for_parameter(
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        parameter: ast.arg,
        call: ast.Call,
    ) -> ast.AST | None:
        if any(isinstance(argument, ast.Starred) for argument in call.args) or any(
            keyword.arg is None for keyword in call.keywords
        ):
            return None
        keyword_values = [
            keyword.value for keyword in call.keywords if keyword.arg == parameter.arg
        ]
        if len(keyword_values) > 1:
            return None
        if parameter in function.args.posonlyargs and keyword_values:
            return None
        positional = (*function.args.posonlyargs, *function.args.args)
        if parameter in positional:
            index = positional.index(parameter)
            if index < len(call.args):
                return None if keyword_values else call.args[index]
        return keyword_values[0] if len(keyword_values) == 1 else None

    def concrete_builtin_tool_argument(
        expression: ast.AST,
        call: ast.Call,
    ) -> tuple[str, str] | None:
        constructor_call: ast.Call | None = None
        if isinstance(expression, ast.Call):
            constructor_call = expression
        elif isinstance(expression, ast.Name):
            block = enclosing_statement_block(call)
            if block is None:
                return None
            statements, call_index = block
            mutations = [
                statement
                for statement in statements[:call_index]
                if expression.id in statement_mutations(statement)
            ]
            if len(mutations) != 1:
                return None
            assignment = mutations[0]
            if not (
                isinstance(assignment, ast.Assign)
                and len(assignment.targets) == 1
                and isinstance(assignment.targets[0], ast.Name)
                and assignment.targets[0].id == expression.id
                and isinstance(assignment.value, ast.Call)
            ):
                return None
            constructor_call = assignment.value
        constructor = builtin_tool_constructor(constructor_call)
        if constructor is None:
            return None
        symbol_id = call_symbol_ids.get(id(constructor_call)) or source_symbol(
            "py", relative, "tool", f"{constructor}@{constructor_call.lineno}"
        )
        return constructor, symbol_id

    direct_name_calls: dict[str, list[ast.Call]] = defaultdict(list)
    agent_calls_by_function: dict[int, list[ast.Call]] = defaultdict(list)
    for candidate in (node for node in nodes if isinstance(node, ast.Call)):
        if isinstance(candidate.func, ast.Name):
            direct_name_calls[candidate.func.id].append(candidate)
        if (
            is_agent_call(candidate)
            and (owner := enclosing_function(candidate))
        ):
            agent_calls_by_function[id(owner)].append(candidate)

    typed_tool_parameter_resolutions: list[tuple[ast.Call, str, str]] = []
    typed_tool_parameter_components: list[Component] = []
    top_level_functions = [
        statement
        for statement in tree.body
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    def resolves_to_top_level_function(
        call: ast.Call,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> bool:
        if enclosed_by_lambda(call):
            return False
        if enclosing_function(call):
            return not shadowed_in_enclosing_functions(call, function.name)
        parent = parent_by_id.get(id(call))
        while parent is not None:
            if isinstance(parent, ast.ClassDef):
                return False
            parent = parent_by_id.get(id(parent))
        return call.lineno > function.lineno

    for function in top_level_functions:
        if (
            function.decorator_list
            or module_mutation_counts[function.name] != 1
            or function.name in module_rebound_names
        ):
            continue
        direct_calls = [
            candidate
            for candidate in direct_name_calls.get(function.name, [])
            if resolves_to_top_level_function(candidate, function)
        ]
        if not direct_calls:
            continue
        parameters = (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
        for parameter in parameters:
            annotation = dotted_name(parameter.annotation) if parameter.annotation else ""
            declared_constructor = builtin_tool_types.get(annotation)
            if declared_constructor is None or any(
                parameter.arg in statement_mutations(statement)
                for statement in function.body
            ):
                continue
            concrete_targets: list[str] = []
            call_sites_valid = True
            for call in direct_calls:
                argument = call_argument_for_parameter(function, parameter, call)
                concrete = (
                    concrete_builtin_tool_argument(argument, call)
                    if argument is not None
                    else None
                )
                if concrete is None or concrete[0] != declared_constructor:
                    call_sites_valid = False
                    break
                concrete_targets.append(concrete[1])
            if not call_sites_valid:
                continue
            agent_calls = [
                candidate
                for candidate in agent_calls_by_function.get(id(function), [])
                if any(
                    keyword.arg == "tools"
                    and isinstance(keyword.value, (ast.List, ast.Tuple))
                    and any(
                        isinstance(value, ast.Name) and value.id == parameter.arg
                        for value in keyword.value.elts
                    )
                    for keyword in candidate.keywords
                )
            ]
            if not agent_calls:
                continue
            parameter_id = source_symbol(
                "py", relative, "tool", f"{parameter.arg}@{parameter.lineno}"
            )
            typed_tool_parameter_components.append(
                Component(
                    "tool",
                    (
                        f"{declared_constructor} parameter "
                        f"{parameter.arg}@{parameter.lineno}"
                    ),
                    Evidence(
                        relative,
                        parameter.lineno,
                        excerpt(text.splitlines(), parameter.lineno),
                    ),
                    {
                        "binding": "typed-parameter",
                        "constructor": declared_constructor,
                        "callsite_proof": "same-module-constructor-consensus",
                        "verified_call_sites": len(direct_calls),
                        "callsite_target_ids": sorted(set(concrete_targets)),
                        "scope": source_scope(relative),
                    },
                    parameter_id,
                )
            )
            typed_tool_parameter_resolutions.extend(
                (agent_call, parameter.arg, parameter_id)
                for agent_call in agent_calls
            )
    for component in typed_tool_parameter_components:
        ir.add_component(component)

    def agent_call_symbol_id(call: ast.Call) -> str:
        name = dotted_name(call.func).rsplit(".", 1)[-1]
        for keyword in call.keywords:
            if (
                keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is not None
            ):
                name = str(keyword.value.value)
        return call_symbol_ids.get(id(call)) or source_symbol(
            "py", relative, "agent", f"{name}@{call.lineno}"
        )

    def direct_method_returns(
        method: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[ast.Return]:
        returns: list[ast.Return] = []

        def collect(candidate: ast.AST) -> None:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return
            if isinstance(candidate, ast.Return):
                returns.append(candidate)
                return
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        for statement in method.body:
            if isinstance(statement, ast.Return):
                returns.append(statement)
            else:
                collect(statement)
        return returns

    def returned_agent_id(
        method: ast.FunctionDef | ast.AsyncFunctionDef,
        returned: ast.AST,
        return_statement: ast.Return,
    ) -> str | None:
        if (
            isinstance(returned, ast.Call) and is_agent_call(returned)
        ):
            return agent_call_symbol_id(returned)
        if not isinstance(returned, ast.Name):
            return None
        try:
            return_index = method.body.index(return_statement)
        except ValueError:
            return None
        mutations = [
            statement
            for statement in method.body[:return_index]
            if returned.id in statement_mutations(statement)
        ]
        if len(mutations) != 1:
            return None
        assignment = mutations[0]
        if not (
            isinstance(assignment, ast.Assign)
            and len(assignment.targets) == 1
            and isinstance(assignment.targets[0], ast.Name)
            and assignment.targets[0].id == returned.id
            and isinstance(assignment.value, ast.Call)
            and is_agent_call(assignment.value)
        ):
            return None
        return agent_call_symbol_id(assignment.value)

    agent_factory_returns: dict[tuple[int, str], tuple[str | None, ...]] = {}
    for class_node in (node for node in nodes if isinstance(node, ast.ClassDef)):
        methods = [
            statement
            for statement in class_node.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        method_counts = Counter(method.name for method in methods)
        for method in methods:
            if method_counts[method.name] != 1 or sum(
                method.name in statement_mutations(statement)
                for statement in class_node.body
            ) != 1:
                continue
            returns = direct_method_returns(method)
            if len(returns) != 1 or parent_by_id.get(id(returns[0])) is not method:
                continue
            return_statement = returns[0]
            if return_statement.value is None:
                continue
            returned_values = (
                tuple(return_statement.value.elts)
                if isinstance(return_statement.value, (ast.Tuple, ast.List))
                else (return_statement.value,)
            )
            returned_ids = tuple(
                returned_agent_id(method, value, return_statement)
                for value in returned_values
            )
            if any(returned_ids):
                agent_factory_returns[(id(class_node), method.name)] = returned_ids

    helper_agent_assignments: list[tuple[ast.Assign, str, str, str]] = []
    local_function_agent_returns: dict[int, str] = {}
    for function in (
        node for node in nodes if isinstance(node, ast.FunctionDef)
    ):
        if (
            function.decorator_list
            or not isinstance(
                parent_by_id.get(id(function)),
                (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef),
            )
        ):
            continue
        block = enclosing_statement_block(function)
        if block is None:
            continue
        statements, _definition_index = block
        if sum(
            function.name in statement_mutations(statement)
            for statement in statements
        ) != 1:
            continue
        returns = direct_method_returns(function)
        if (
            len(returns) != 1
            or parent_by_id.get(id(returns[0])) is not function
            or not isinstance(returns[0].value, ast.Call)
            or not isinstance(returns[0].value.func, ast.Name)
            or returns[0].value.func.id not in local_agent_factory_constructors
            or returns[0].value.func.id in python_function_local_bindings(function)
            or shadowed_in_enclosing_functions(
                function, returns[0].value.func.id
            )
        ):
            continue
        local_function_agent_returns[id(function)] = agent_call_symbol_id(
            returns[0].value
        )

    for assignment in (node for node in nodes if isinstance(node, ast.Assign)):
        if not (
            len(assignment.targets) == 1
            and isinstance(assignment.targets[0], ast.Name)
            and isinstance(assignment.value, ast.Call)
            and isinstance(assignment.value.func, ast.Name)
        ):
            continue
        block = enclosing_statement_block(assignment)
        if block is None:
            continue
        statements, assignment_index = block
        factory_name = assignment.value.func.id
        factory_mutations = [
            statement
            for statement in statements[:assignment_index]
            if factory_name in statement_mutations(statement)
        ]
        if len(factory_mutations) != 1:
            continue
        factory = factory_mutations[0]
        if not isinstance(factory, ast.FunctionDef):
            continue
        returned_id = local_function_agent_returns.get(id(factory))
        if returned_id is None:
            continue
        binding = assignment.targets[0].id
        helper_agent_assignments.append(
            (
                assignment,
                binding,
                returned_id,
                "same-block-function-factory-return",
            )
        )
        symbol_candidates.setdefault(("agent", binding), set()).add(returned_id)

    for assignment in (node for node in nodes if isinstance(node, ast.Assign)):
        if not (
            isinstance(assignment.value, ast.Call)
            and isinstance(assignment.value.func, ast.Attribute)
            and isinstance(assignment.value.func.value, ast.Name)
        ):
            continue
        method = parent_by_id.get(id(assignment))
        while method is not None and not isinstance(
            method, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            method = parent_by_id.get(id(method))
        if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        parent = parent_by_id.get(id(method))
        if not isinstance(parent, ast.ClassDef):
            continue
        receiver = assignment.value.func.value.id
        if receiver not in {"self", "cls", parent.name}:
            continue
        positional_arguments = (*method.args.posonlyargs, *method.args.args)
        if receiver in {"self", "cls"}:
            if not positional_arguments or positional_arguments[0].arg != receiver:
                continue
            if any(
                receiver in statement_mutations(statement)
                for statement in method.body
            ):
                continue
        elif receiver in python_function_local_bindings(method):
            continue
        returned_ids = agent_factory_returns.get(
            (id(parent), assignment.value.func.attr)
        )
        if returned_ids is None or len(assignment.targets) != 1:
            continue
        target = assignment.targets[0]
        targets = tuple(target.elts) if isinstance(target, (ast.Tuple, ast.List)) else (target,)
        if len(targets) != len(returned_ids):
            continue
        for target_item, returned_id in zip(targets, returned_ids, strict=True):
            if isinstance(target_item, ast.Name) and returned_id is not None:
                helper_agent_assignments.append(
                    (
                        assignment,
                        target_item.id,
                        returned_id,
                        "same-class-helper-return",
                    )
                )
                symbol_candidates.setdefault(("agent", target_item.id), set()).add(
                    returned_id
                )

    imported_factory_classes: dict[
        str, tuple[PythonAgentFactoryClassTarget, str, int]
    ] = {}
    imported_agent_factory_target_paths: dict[str, str] = {}
    top_level_import_counts = Counter(
        alias.asname or alias.name.split(".", 1)[0]
        for statement in tree.body
        if isinstance(statement, (ast.Import, ast.ImportFrom))
        for alias in statement.names
        if alias.name != "*"
    )
    imported_factory_candidates: dict[
        str, list[tuple[PythonAgentFactoryClassTarget, str, int]]
    ] = defaultdict(list)
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom):
            continue
        for alias in statement.names:
            local_name = alias.asname or alias.name
            resolution = resolve_python_import(
                root,
                relative,
                statement,
                alias.name,
                module_paths,
            )
            if resolution is None:
                continue
            target = agent_factory_class_exports.get(
                (resolution.path, alias.name)
            )
            if target is not None:
                imported_factory_candidates[local_name].append(
                    (target, resolution.basis, statement.lineno)
                )
    for local_name, candidates in imported_factory_candidates.items():
        if (
            len(candidates) == 1
            and top_level_import_counts[local_name] == 1
            and local_name not in module_rebound_names
        ):
            imported_factory_classes[local_name] = candidates[0]

    for assignment in (node for node in nodes if isinstance(node, ast.Assign)):
        if not (
            len(assignment.targets) == 1
            and isinstance(assignment.targets[0], ast.Name)
            and isinstance(assignment.value, ast.Call)
            and isinstance(assignment.value.func, ast.Attribute)
            and isinstance(assignment.value.func.value, ast.Name)
        ):
            continue
        block = enclosing_statement_block(assignment)
        if block is None:
            continue
        statements, assignment_index = block
        receiver = assignment.value.func.value.id
        receiver_mutations = [
            statement
            for statement in statements[:assignment_index]
            if receiver in statement_mutations(statement)
        ]
        if len(receiver_mutations) != 1:
            continue
        constructor_assignment = receiver_mutations[0]
        if not (
            isinstance(constructor_assignment, ast.Assign)
            and len(constructor_assignment.targets) == 1
            and isinstance(constructor_assignment.targets[0], ast.Name)
            and constructor_assignment.targets[0].id == receiver
            and isinstance(constructor_assignment.value, ast.Call)
            and isinstance(constructor_assignment.value.func, ast.Name)
        ):
            continue
        constructor_name = constructor_assignment.value.func.id
        imported_factory = imported_factory_classes.get(constructor_name)
        if imported_factory is None:
            continue
        target, import_basis, import_line = imported_factory
        if (
            import_line >= constructor_assignment.lineno
            or enclosed_by_lambda(constructor_assignment)
            or shadowed_in_enclosing_functions(
                constructor_assignment, constructor_name
            )
        ):
            continue
        returned_id = target.methods.get(assignment.value.func.attr)
        if returned_id is None:
            continue
        binding = assignment.targets[0].id
        target_identity = (
            "contextual-imported-class-factory-return"
            if import_basis == "contextual-absolute-import-single-path"
            else "imported-class-factory-return"
        )
        helper_agent_assignments.append(
            (assignment, binding, returned_id, target_identity)
        )
        imported_agent_factory_target_paths[returned_id] = target.path
        symbol_candidates.setdefault(("agent", binding), set()).add(returned_id)
    local_symbol_ids = {
        key: next(iter(candidates))
        for key, candidates in symbol_candidates.items()
        if len(candidates) == 1
    }
    ambiguous_local_symbols = {
        key for key, candidates in symbol_candidates.items() if len(candidates) > 1
    }
    scoped_symbol_candidates: dict[tuple[tuple[str, ...], str, str], list[tuple[int, str]]] = {}
    dominating_symbol_ids: dict[tuple[int, str, str], tuple[str, str]] = {
        (id(call), "tool", parameter): (
            symbol_id,
            "typed-parameter-callsite-consensus",
        )
        for call, parameter, symbol_id in typed_tool_parameter_resolutions
    }
    agent_calls_by_location = {
        (call.lineno, call.col_offset): call
        for call in nodes
        if isinstance(call, ast.Call) and is_agent_call(call)
    }
    dominating_symbol_ids.update(
        {
            (id(agent_calls_by_location[(reference.agent_line, reference.agent_col)]), "tool", reference.local_name): (
                external_import_tool_ids[(reference.local_name, reference.import_line)],
                "literal-tools-list-import-binding",
            )
            for reference in current_imported_tool_references
            if reference.import_resolution is None
            and (reference.agent_line, reference.agent_col) in agent_calls_by_location
            and (reference.local_name, reference.import_line) in external_import_tool_ids
        }
    )
    dominating_symbol_ids.update(
        {
            (id(call), "tool", binding): (
                symbol_id,
                "literal-tools-list-context-manager",
            )
            for call, binding, symbol_id in context_usage_tool_resolutions
        }
    )
    dominating_symbol_ids.update(
        {
            (id(call), "mcp-server", binding): (
                symbol_id,
                "context-manager-binding",
            )
            for call, binding, symbol_id in context_usage_mcp_resolutions
        }
    )
    scope_bound_names: set[tuple[tuple[str, ...], str]] = set()
    node_scopes: dict[int, tuple[str, ...]] = {}
    if symbol_candidates:
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
            if isinstance(node, (ast.Assign, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            or (
                isinstance(node, ast.Call) and is_agent_call(node)
            )
        ]
        node_scopes = {id(node): lexical_scope(node) for node in scope_nodes}
        for node in nodes:
            scope = lexical_scope(node)
            if not scope:
                continue
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                scope_bound_names.add((scope, node.id))
            elif isinstance(node, ast.arg):
                scope_bound_names.add((scope, node.arg))
            elif isinstance(node, ast.alias):
                scope_bound_names.add((scope, node.asname or node.name.split(".", 1)[0]))
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ) or (isinstance(node, ast.ExceptHandler) and node.name):
                scope_bound_names.add((scope, node.name))
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
        for node, tool in registered_class_tools:
            if not isinstance(parent_by_id.get(id(node)), (ast.Module, ast.ClassDef)):
                continue
            for name in {tool.name, node.name}:
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

        definition_by_statement = {
            (id(node), kind, binding): (
                call_symbol_ids[id(node.value)],
                "agent-as-tool-adapter"
                if id(node) in agent_as_tool_assignments
                else "block-dominating-definition",
            )
            for node, kind, binding in assigned_constructors
        }
        definition_by_statement.update(
            {
                (id(node), "tool", node.name): (
                    definition_symbol_ids[id(node)],
                    "block-dominating-definition",
                )
                for node, _qualified_name in decorated_tools
            }
        )
        definition_by_statement.update(
            {
                (id(node), "agent", binding): (
                    symbol_id,
                    target_identity,
                )
                for node, binding, symbol_id, target_identity in helper_agent_assignments
            }
        )
        for call in (
            candidate
            for candidate in nodes
            if isinstance(candidate, ast.Call) and is_agent_call(candidate)
        ):
            block = enclosing_statement_block(call)
            if block is None:
                continue
            statements, use_index = block
            references: set[tuple[str, str]] = set()
            for keyword in call.keywords:
                if keyword.arg not in {
                    "tools",
                    "handoffs",
                    "agents",
                    "mcp_servers",
                } or not isinstance(
                    keyword.value, (ast.List, ast.Tuple)
                ):
                    continue
                for value in keyword.value.elts:
                    kind = (
                        "tool"
                        if keyword.arg == "tools"
                        else "mcp-server"
                        if keyword.arg == "mcp_servers"
                        else "agent"
                    )
                    name = dotted_name(value)
                    if isinstance(value, ast.Call) and dotted_name(value.func).endswith(".as_tool"):
                        kind = "agent"
                        name = dotted_name(value.func).removesuffix(".as_tool")
                    if (kind, name) in symbol_candidates:
                        references.add((kind, name))
            for kind, name in references:
                mutations = [
                    statement
                    for statement in statements[:use_index]
                    if name in statement_mutations(statement)
                ]
                if len(mutations) == 1:
                    definition = definition_by_statement.get(
                        (id(mutations[0]), kind, name)
                    )
                    if definition:
                        dominating_symbol_ids[(id(call), kind, name)] = definition
                        continue
                if kind != "mcp-server" or name not in immutable_module_mcp_servers:
                    continue
                call_scope = node_scopes[id(call)]
                if any(
                    (call_scope[:depth], name) in scope_bound_names
                    for depth in range(1, len(call_scope) + 1)
                ):
                    continue
                definition_line, symbol_id = immutable_module_mcp_servers[name]
                if definition_line < call.lineno:
                    dominating_symbol_ids[(id(call), kind, name)] = (
                        symbol_id,
                        "immutable-module-binding",
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
        dominating_symbol_ids=dominating_symbol_ids,
        scope_bound_names=scope_bound_names,
        node_scopes=node_scopes,
        call_symbol_ids=call_symbol_ids,
        mcp_server_symbol_names=mcp_server_symbol_names,
        mcp_server_binding_resolutions=mcp_server_binding_resolutions,
        mcp_in_process_server_bindings=mcp_in_process_server_bindings,
        agent_constructor_bindings=agent_constructor_bindings,
        exact_openai_builtin_call_names=exact_openai_builtin_call_names,
        observed_mcp_server_ids=observed_mcp_server_ids,
        definition_symbol_ids=definition_symbol_ids,
        referenced_tool_functions=referenced_tool_functions,
        wrapped_tool_functions=wrapped_tool_functions,
        inline_usage_tool_calls=inline_usage_tool_calls,
        decorated_tool_exports=decorated_tool_exports,
        imported_tool_export_usages={
            (
                reference.agent_line,
                reference.agent_col,
                reference.local_name,
            ): reference
            for reference in current_imported_tool_references
            if reference.target_path is not None
        },
        imported_tool_promoted_exports=set(imported_tool_export_references),
        imported_agent_factory_target_paths=imported_agent_factory_target_paths,
        registry_class_exports=registry_class_exports,
        network_helper_summaries=network_helper_summaries,
        registered_tool_functions=registered_tool_functions,
        registry_function_tools=registry_function_tools,
        registry_class_tools=registry_class_tools,
        module_static_http_prefixes=module_static_http_prefixes,
        module_rebound_names=module_rebound_names,
        path_constructors=path_constructors,
        filesystem_api_aliases=filesystem_api_aliases,
        urllib_openers=urllib_openers,
        urllib_request_constructors=urllib_request_constructors,
        browser_type_names=browser_type_names,
        browser_page_factories=browser_page_factories,
        browser_runtime_factories=browser_runtime_factories,
        url_parser_names=url_parser_names,
        module_literal_string_sets=module_literal_string_sets,
        approval_bypass_function_summaries=(
            python_approval_bypass_function_summaries(tree)
            if "on_approval" in text
            and re.search(r"\b(?:from|import)\s+agents\b", text)
            else {}
        ),
    ).visit(tree)


TS_IMPORT = re.compile(r"(?:from\s+|require\s*\(\s*)['\"]([^'\"]+)['\"]")
TS_NAMED_IMPORT = re.compile(r"\bimport\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]", re.DOTALL)
TS_DYNAMIC_NAMED_IMPORT = re.compile(
    r"\bconst\s*\{([^}]+)\}\s*=\s*(?:await\s*)?"
    r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    re.DOTALL,
)
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
class TypeScriptAxiosInstance:
    name: str
    line: int
    base_url_scope: str
    allow_absolute_urls: bool


@dataclass(frozen=True)
class TypeScriptNetworkCall:
    api: str
    url_expression: str
    summary: str | None = None
    receiver: str | None = None
    base_url_scope: str | None = None
    absolute_url_override: str | None = None


@dataclass(frozen=True)
class TypeScriptProviderImportBinding:
    local_name: str
    imported_symbol: str
    module: str
    provider: str


@dataclass(frozen=True)
class TypeScriptProviderCall:
    offset: int
    call: str
    call_kind: str
    module: str
    imported_symbol: str
    provider: str
    model: str | None = None
    model_method: str | None = None
    configured_by: str | None = None


@dataclass(frozen=True)
class TypeScriptNetworkOriginHelper:
    name: str
    evidence: Evidence
    schemes: tuple[str, ...]
    environment_name: str
    hostname_match: str


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


def typescript_literal_object_items(
    body: str, body_offset: int = 0
) -> list[tuple[str, int]]:
    """Extract literal object properties while retaining quoted property names."""
    code = typescript_code_mask(body)
    opening = len(code) - len(code.lstrip())
    if opening >= len(code) or code[opening] != "{":
        return []
    end = typescript_balanced_end(code, opening, "{", "}")
    if end is None:
        return []
    return typescript_call_arguments(body[opening + 1 : end - 1], body_offset + opening + 1)


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


def typescript_named_object_property(property_text: str) -> tuple[str, str] | None:
    """Return a direct literal property name and value with a structural colon."""
    match = re.match(
        r"\s*(?:(?P<identifier>[A-Za-z_$][\w$]*)|(?P<quote>['\"])(?P<quoted>.*?)\2)\s*:",
        property_text,
        re.DOTALL,
    )
    if match is None:
        return None
    colon = match.end() - 1
    code = typescript_code_mask(property_text)
    if colon >= len(code) or code[colon] != ":":
        return None
    return match.group("identifier") or match.group("quoted"), property_text[match.end() :].strip()


def typescript_object_property_expression(body: str, name: str) -> str | None:
    """Return one unambiguous direct property expression from a literal object."""
    values = []
    for property_text, _ in typescript_object_items(body):
        match = re.match(rf"\s*{re.escape(name)}\s*:", typescript_code_mask(property_text))
        if match:
            values.append(property_text[match.end() :].strip())
    return values[0] if len(values) == 1 else None


def typescript_literal_object_property_expression(body: str, name: str) -> str | None:
    """Return a direct identifier- or string-keyed property from a literal object."""
    values = []
    for property_text, _ in typescript_literal_object_items(body):
        property_value = typescript_named_object_property(property_text)
        if property_value is not None and property_value[0] == name:
            values.append(property_value[1])
    return values[0] if len(values) == 1 else None


def typescript_literal_object_string_property(body: str, name: str) -> str | None:
    """Resolve one identifier- or string-keyed direct literal string property."""
    value = typescript_literal_object_property_expression(body, name)
    if value is None:
        return None
    match = re.fullmatch(r"(['\"])(.*?)\1", value, re.DOTALL)
    return match.group(2) if match else None


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


def typescript_literal_string_arguments(expression: str) -> list[str | None] | None:
    """Return literal TypeScript array items while retaining unresolved positions."""
    code = typescript_code_mask(expression)
    opening = len(code) - len(code.lstrip())
    if opening >= len(code) or code[opening] != "[":
        return None
    end = typescript_balanced_end(code, opening, "[", "]")
    if end is None:
        return None
    suffix = code[end:].strip()
    if suffix and not re.fullmatch(r"as\s+const", suffix):
        return None
    arguments: list[str | None] = []
    for item, _ in typescript_call_arguments(expression[opening + 1 : end - 1]):
        item = item.strip()
        match = re.fullmatch(r"(['\"`])([^\\]*?)\1", item, re.DOTALL)
        arguments.append(
            match.group(2)
            if match is not None and not (match.group(1) == "`" and "${" in match.group(2))
            else None
        )
    return arguments


def typescript_literal_identifier_arguments(expression: str) -> list[str] | None:
    """Return a literal TypeScript array only when every item is an identifier."""
    code = typescript_code_mask(expression)
    opening = len(code) - len(code.lstrip())
    if opening >= len(code) or code[opening] != "[":
        return None
    end = typescript_balanced_end(code, opening, "[", "]")
    if end is None:
        return None
    suffix = code[end:].strip()
    if suffix and not re.fullmatch(r"as\s+const", suffix):
        return None
    arguments = typescript_call_arguments(expression[opening + 1 : end - 1])
    identifiers = [item.strip() for item, _ in arguments]
    if any(re.fullmatch(r"[A-Za-z_$][\w$]*", item) is None for item in identifiers):
        return None
    return identifiers


def typescript_import_binding_is_shadowed(text: str, name: str) -> bool:
    """Conservatively reject imported constructor aliases shadowed in local code."""
    code = typescript_code_mask(text)
    escaped = re.escape(name)
    return bool(
        re.search(rf"\b(?:const|let|var|function|class)\s+{escaped}\b", code)
        or re.search(rf"(?<![\w$.]){escaped}\s*=(?!=)", code)
        or re.search(rf"\bfunction\s+\w*\s*\([^)]*\b{escaped}\b", code)
        or re.search(rf"\([^)]*\b{escaped}\b[^)]*\)\s*=>", code)
    )


def typescript_ai_sdk_provider_imports(
    text: str,
) -> dict[str, TypeScriptProviderImportBinding]:
    """Return unambiguous official AI SDK provider imports, including dynamic imports."""
    candidates: dict[str, list[TypeScriptProviderImportBinding]] = defaultdict(list)

    def add_bindings(imports: str, module: str, *, dynamic: bool) -> None:
        provider_exports = TYPESCRIPT_AI_SDK_PROVIDER_EXPORTS.get(module)
        if provider_exports is None:
            return
        supported = {provider_exports["instance"], provider_exports["factory"]}
        for imported in imports.split(","):
            imported = imported.strip()
            if not imported or imported.startswith("type "):
                continue
            if dynamic:
                parts = [part.strip() for part in imported.split(":", 1)]
                original = parts[0]
                local = parts[1] if len(parts) == 2 else original
            else:
                parts = imported.split()
                original = parts[0]
                local = parts[2] if len(parts) >= 3 and parts[1] == "as" else original
            if original not in supported or re.fullmatch(r"[A-Za-z_$][\w$]*", local) is None:
                continue
            candidates[local].append(
                TypeScriptProviderImportBinding(
                    local,
                    original,
                    module,
                    str(provider_exports["provider"]),
                )
            )

    for match in TS_NAMED_IMPORT.finditer(text):
        add_bindings(match.group(1), match.group(2), dynamic=False)
    for match in TS_DYNAMIC_NAMED_IMPORT.finditer(text):
        add_bindings(match.group(1), match.group(2), dynamic=True)
    return {
        local: values[0]
        for local, values in candidates.items()
        if len(values) == 1 and not typescript_import_binding_is_shadowed(text, local)
    }


def typescript_literal_first_call_argument(text: str, opening: int, end: int) -> str | None:
    """Return a direct literal first argument from one balanced TypeScript call."""
    arguments = typescript_call_arguments(text[opening + 1 : end - 1])
    if not arguments:
        return None
    value = arguments[0][0].strip()
    match = re.fullmatch(r"(['\"`])(.*?)\1", value, re.DOTALL)
    if match is None or (match.group(1) == "`" and "${" in match.group(2)):
        return None
    return match.group(2)


def typescript_const_provider_binding_is_stable(
    text: str,
    name: str,
    initializer_end: int,
) -> bool:
    """Conservatively accept one immutable provider instance without local shadowing."""
    code = typescript_code_mask(text)
    escaped = re.escape(name)
    declarations = re.findall(rf"\b(?:const|let|var|function|class)\s+{escaped}\b", code)
    if len(declarations) != 1:
        return False
    return not (
        re.search(rf"(?<![\w$.]){escaped}\s*=(?!=)", code[initializer_end:])
        or re.search(rf"\bfunction\s+\w*\s*\([^)]*\b{escaped}\b", code)
        or re.search(rf"\([^)]*\b{escaped}\b[^)]*\)\s*=>", code)
    )


def typescript_ai_sdk_provider_calls(text: str) -> list[TypeScriptProviderCall]:
    """Resolve exact official AI SDK factories and model calls through stable bindings."""
    code = typescript_code_mask(text)
    imports = typescript_ai_sdk_provider_imports(text)
    observations: list[TypeScriptProviderCall] = []
    configured_instances: list[tuple[str, TypeScriptProviderImportBinding, int]] = []

    for local_name, binding in imports.items():
        provider_exports = TYPESCRIPT_AI_SDK_PROVIDER_EXPORTS[binding.module]
        is_factory = binding.imported_symbol == provider_exports["factory"]
        methods = "" if is_factory else r"(?:\.(embedding|reranking))?"
        call_pattern = re.compile(rf"(?<![\w$.]){re.escape(local_name)}{methods}\s*\(")
        for match in call_pattern.finditer(code):
            opening = code.find("(", match.start(), match.end())
            end = typescript_balanced_end(code, opening, "(", ")")
            if end is None:
                continue
            model_method = None if is_factory else (match.group(1) or "language")
            observations.append(
                TypeScriptProviderCall(
                    match.start(),
                    code[match.start() : opening].strip(),
                    "ai-sdk-provider-factory" if is_factory else "ai-sdk-provider-model",
                    binding.module,
                    binding.imported_symbol,
                    binding.provider,
                    None
                    if is_factory
                    else typescript_literal_first_call_argument(text, opening, end),
                    model_method,
                )
            )
            if not is_factory:
                continue
            prefix = code[max(0, match.start() - 240) : match.start()]
            assignment = re.search(
                r"\bconst\s+([A-Za-z_$][\w$]*)\s*(?:\:\s*[^=;\n]+)?=\s*$",
                prefix,
            )
            if assignment is None:
                continue
            instance_name = assignment.group(1)
            if instance_name in imports or not typescript_const_provider_binding_is_stable(
                text, instance_name, end
            ):
                continue
            configured_instances.append((instance_name, binding, end))

    for instance_name, binding, initializer_end in configured_instances:
        call_pattern = re.compile(
            rf"(?<![\w$.]){re.escape(instance_name)}(?:\.(embedding|reranking))?\s*\("
        )
        for match in call_pattern.finditer(code, initializer_end):
            opening = code.find("(", match.start(), match.end())
            end = typescript_balanced_end(code, opening, "(", ")")
            if end is None:
                continue
            observations.append(
                TypeScriptProviderCall(
                    match.start(),
                    code[match.start() : opening].strip(),
                    "ai-sdk-provider-model",
                    binding.module,
                    binding.imported_symbol,
                    binding.provider,
                    typescript_literal_first_call_argument(text, opening, end),
                    match.group(1) or "language",
                    binding.local_name,
                )
            )
    return sorted(observations, key=lambda item: item.offset)


def add_typescript_mcp_package_launcher(
    ir: RepositoryIR,
    *,
    relative: str,
    text: str,
    lines: list[str],
    offset: int,
    name: str,
    command: str,
    arguments: list[str | None],
    constructor: str,
    analysis: str,
) -> None:
    package = mcp_package_reference(command, arguments)
    if package is None:
        return
    line = line_at(text, offset)
    ir.add_component(
        Component(
            "mcp-server",
            name,
            Evidence(relative, line, excerpt(lines, line)),
            {
                "transport": "stdio",
                "command": command,
                "package_manager": command,
                "constructor": constructor,
                "analysis": analysis,
                "frontend": "typescript",
                "scope": source_scope(relative),
                **package,
            },
        )
    )


def typescript_mcp_package_launchers(
    ir: RepositoryIR,
    relative: str,
    text: str,
    lines: list[str],
) -> None:
    """Resolve literal MCP stdio package launchers without executing code."""
    code = typescript_code_mask(text)
    imports = {
        **typescript_named_import_bindings(text, "@modelcontextprotocol/sdk"),
        **typescript_named_import_bindings(text, "@modelcontextprotocol/client"),
    }
    for local_name, original_name in imports.items():
        if original_name != "StdioClientTransport" or typescript_import_binding_is_shadowed(
            text, local_name
        ):
            continue
        pattern = re.compile(rf"\bnew\s+{re.escape(local_name)}\s*\(")
        for match in pattern.finditer(code):
            opening = code.find("(", match.start(), match.end())
            end = typescript_balanced_end(code, opening, "(", ")")
            if end is None:
                continue
            call_arguments = typescript_call_arguments(
                text[opening + 1 : end - 1], opening + 1
            )
            if not call_arguments:
                continue
            config, _ = call_arguments[0]
            command = typescript_literal_object_string_property(config, "command")
            arguments_expression = typescript_literal_object_property_expression(config, "args")
            arguments = (
                typescript_literal_string_arguments(arguments_expression)
                if arguments_expression is not None
                else None
            )
            if command is None or arguments is None:
                continue
            line = line_at(text, match.start())
            add_typescript_mcp_package_launcher(
                ir,
                relative=relative,
                text=text,
                lines=lines,
                offset=match.start(),
                name=f"StdioClientTransport@{line}",
                command=command,
                arguments=arguments,
                constructor="StdioClientTransport",
                analysis="typescript-import-bound-mcp-transport",
            )

    property_pattern = re.compile(r"(?:\bmcpServers\b|(['\"])mcpServers\1)\s*:")
    for match in property_pattern.finditer(text):
        colon = match.end() - 1
        if colon >= len(code) or code[colon] != ":":
            continue
        opening = colon + 1
        while opening < len(code) and code[opening].isspace():
            opening += 1
        if opening >= len(code) or code[opening] != "{":
            continue
        end = typescript_balanced_end(code, opening, "{", "}")
        if end is None:
            continue
        servers_expression = text[opening:end]
        for server_property, server_offset in typescript_literal_object_items(
            servers_expression, opening
        ):
            server = typescript_named_object_property(server_property)
            if server is None:
                continue
            server_name, config = server
            command = typescript_literal_object_string_property(config, "command")
            arguments_expression = typescript_literal_object_property_expression(config, "args")
            arguments = (
                typescript_literal_string_arguments(arguments_expression)
                if arguments_expression is not None
                else None
            )
            if command is None or arguments is None:
                continue
            add_typescript_mcp_package_launcher(
                ir,
                relative=relative,
                text=text,
                lines=lines,
                offset=server_offset,
                name=server_name,
                command=command,
                arguments=arguments,
                constructor="mcpServers",
                analysis="typescript-mcp-config-literal",
            )


def typescript_axios_default_bindings(text: str) -> set[str]:
    """Return immutable default/CommonJS bindings proven to come from Axios."""
    code = typescript_code_mask(text)
    bindings: set[str] = set()
    patterns = (
        re.compile(
            r"\bimport\s+([A-Za-z_$][\w$]*)\s*"
            r"(?:,\s*\{[^}]*\})?\s+from\s*['\"]axios['\"]",
            re.DOTALL,
        ),
        re.compile(
            r"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*"
            r"require\s*\(\s*['\"]axios['\"]\s*\)",
        ),
    )
    for pattern in patterns:
        for match in pattern.finditer(text):
            structural = code[match.start() : match.start(1)]
            if not structural.strip():
                continue
            name = match.group(1)
            assignment_count = len(
                re.findall(rf"(?<![\w$.]){re.escape(name)}\s*=", code)
            )
            expected = 1 if structural.lstrip().startswith("const") else 0
            if assignment_count == expected:
                bindings.add(name)
    return bindings


def typescript_axios_instances(
    text: str,
    axios_bindings: set[str],
) -> dict[str, TypeScriptAxiosInstance]:
    """Resolve immutable same-file instances created from an import-proven Axios binding."""
    if not axios_bindings:
        return {}
    code = typescript_code_mask(text)
    aliases = "|".join(re.escape(name) for name in sorted(axios_bindings, key=len, reverse=True))
    pattern = re.compile(
        rf"\bconst\s+([A-Za-z_$][\w$]*)\s*(?:\:\s*[^=;]+)?=\s*"
        rf"(?:{aliases})\.create\s*\("
    )
    candidates: dict[str, list[TypeScriptAxiosInstance]] = defaultdict(list)
    literal_bindings = typescript_literal_string_bindings(text)
    for match in pattern.finditer(code):
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")")
        if end is None:
            continue
        arguments = typescript_call_arguments(text[opening + 1 : end - 1])
        config = arguments[0][0] if arguments else "{}"
        if not typescript_code_mask(config).lstrip().startswith("{"):
            continue
        base_url = typescript_object_property_expression(config, "baseURL")
        allow_absolute = typescript_object_property_expression(config, "allowAbsoluteUrls")
        if allow_absolute is not None and allow_absolute not in {"true", "false"}:
            continue
        if base_url is None:
            base_url_scope = "absent"
        elif re.match(
            r"^https?://[^/?#]+",
            typescript_static_url_prefix(base_url, literal_bindings),
            re.IGNORECASE,
        ):
            base_url_scope = "fixed-origin"
        else:
            base_url_scope = "configured"
        candidates[match.group(1)].append(
            TypeScriptAxiosInstance(
                match.group(1),
                line_at(text, match.start()),
                base_url_scope,
                allow_absolute != "false",
            )
        )
    instances = {}
    for name, values in candidates.items():
        if len(values) != 1:
            continue
        assignments = len(re.findall(rf"(?<![\w$.]){re.escape(name)}\s*=", code))
        if assignments == 1:
            instances[name] = values[0]
    return instances


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


def typescript_network_calls(
    text: str,
    axios_bindings: set[str] | None = None,
    axios_instances: dict[str, TypeScriptAxiosInstance] | None = None,
) -> dict[int, list[TypeScriptNetworkCall]]:
    """Return recognized global fetch and import-proven Axios calls."""
    code = typescript_code_mask(text)
    axios_bindings = axios_bindings or {"axios"}
    axios_instances = axios_instances or {}
    direct_names = "|".join(
        re.escape(name) for name in sorted(axios_bindings, key=len, reverse=True)
    )
    instance_names = "|".join(
        re.escape(name) for name in sorted(axios_instances, key=len, reverse=True)
    )
    alternatives = [r"(?<![\w$.])fetch\s*\("]
    if direct_names:
        alternatives.append(
            rf"(?<![\w$.])(?:{direct_names})\.(get|post|put|patch|delete)\s*\("
        )
    if instance_names:
        alternatives.append(
            rf"(?<![\w$.])({instance_names})\.(request|get|post|put|patch|delete)\s*\("
        )
    pattern = re.compile("|".join(alternatives))
    calls: dict[int, list[TypeScriptNetworkCall]] = defaultdict(list)
    for match in pattern.finditer(code):
        opening = code.find("(", match.start(), match.end())
        end = typescript_balanced_end(code, opening, "(", ")")
        if end is None:
            continue
        arguments = typescript_call_arguments(text[opening + 1 : end - 1])
        if not arguments:
            continue
        matched_code = code[match.start() : opening]
        instance_match = re.search(
            r"([A-Za-z_$][\w$]*)\.(request|get|post|put|patch|delete)\s*$",
            matched_code,
        )
        if instance_match and instance_match.group(1) in axios_instances:
            receiver, method = instance_match.groups()
            url_expression = arguments[0][0]
            if method == "request":
                request_object = url_expression
                url_expression = (
                    typescript_object_property_expression(request_object, "url") or ""
                )
                if not url_expression:
                    shorthand_urls = [
                        item.strip()
                        for item, _ in typescript_object_items(request_object)
                        if typescript_code_mask(item).strip() == "url"
                    ]
                    if len(shorthand_urls) == 1:
                        url_expression = shorthand_urls[0]
                if not url_expression:
                    continue
            instance = axios_instances[receiver]
            calls[line_at(text, match.start())].append(
                TypeScriptNetworkCall(
                    f"axios.instance.{method}",
                    url_expression,
                    "same-file-axios-instance",
                    receiver,
                    instance.base_url_scope,
                    "allowed" if instance.allow_absolute_urls else "disabled",
                )
            )
            continue
        direct_method = re.search(
            r"\.(get|post|put|patch|delete)\s*$",
            matched_code,
        )
        api = f"axios.{direct_method.group(1)}" if direct_method else "fetch"
        calls[line_at(text, match.start())].append(
            TypeScriptNetworkCall(api, arguments[0][0])
        )
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


def typescript_approval_bypass_function_summaries(
    text: str,
) -> dict[str, tuple[str, ...]]:
    """Resolve unique same-file functions that transitively return env-backed approval."""
    definitions = typescript_function_definitions(text)
    name_counts = Counter(name for name, _, _, _ in definitions)
    unique_definitions = {
        name: body for name, _, _, body in definitions if name_counts[name] == 1
    }
    resolved: dict[str, set[str]] = {}
    calls: dict[str, set[str]] = {}
    for name, body in unique_definitions.items():
        environment_names = {
            environment_name
            for _, names in typescript_environment_approval_guards(body)
            for environment_name in names
        }
        if environment_names:
            resolved[name] = environment_names
        body_code = typescript_code_mask(body)
        calls[name] = {
            candidate
            for candidate in unique_definitions
            if re.search(rf"\b{re.escape(candidate)}\s*\(", body_code)
        }

    changed = True
    while changed:
        changed = False
        for name, called_functions in calls.items():
            inherited = {
                environment_name
                for called in called_functions
                for environment_name in resolved.get(called, set())
            }
            if inherited - resolved.get(name, set()):
                resolved.setdefault(name, set()).update(inherited)
                changed = True
    return {name: tuple(sorted(values)) for name, values in resolved.items()}


def typescript_network_helper_summaries(
    text: str,
    literal_bindings: dict[str, str],
    axios_bindings: set[str] | None = None,
) -> dict[str, TypeScriptNetworkHelperSummary]:
    definitions = typescript_function_definitions(text)
    name_counts = Counter(name for name, _, _, _ in definitions)
    summaries = {}
    for name, line, parameters, body in definitions:
        if name_counts[name] != 1:
            continue
        calls = typescript_network_calls(body, axios_bindings)
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
                    typescript_http_origin_is_dynamic(
                        call.url_expression, dynamic_names, literal_bindings
                    )
                    for call in calls.get(body_line_number, [])
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


def typescript_if_blocks(text: str) -> list[tuple[str, str]]:
    """Return structurally balanced TypeScript if conditions and braced bodies."""
    code = typescript_code_mask(text)
    blocks = []
    for match in re.finditer(r"\bif\s*\(", code):
        opening = code.find("(", match.start(), match.end())
        condition_end = typescript_balanced_end(code, opening, "(", ")")
        if condition_end is None:
            continue
        body_opening = condition_end
        while body_opening < len(code) and code[body_opening].isspace():
            body_opening += 1
        if body_opening >= len(code) or code[body_opening] != "{":
            continue
        body_end = typescript_balanced_end(code, body_opening, "{", "}")
        if body_end is None:
            continue
        blocks.append(
            (
                text[opening + 1 : condition_end - 1],
                text[body_opening + 1 : body_end - 1],
            )
        )
    return blocks


def typescript_optional_domain_bindings(text: str) -> dict[str, str]:
    """Resolve immutable normalized domain arrays whose environment default is open."""
    code = typescript_code_mask(text)
    pattern = re.compile(
        r"\bconst\s+(?P<binding>[A-Za-z_$][\w$]*)\s*=\s*\(\s*"
        r"process\.env\.(?P<environment>[A-Za-z_$][\w$]*)\s*\?\?\s*"
        r"(?P<empty_quote>['\"])(?P=empty_quote)\s*\)\s*"
        r"\.split\(\s*(?P<comma_quote>['\"]),(?P=comma_quote)\s*\)\s*"
        r"\.map\(\s*\((?P<map_name>[A-Za-z_$][\w$]*)\)\s*=>\s*"
        r"(?P=map_name)\.trim\(\)\.toLowerCase\(\)\s*\)\s*"
        r"\.filter\(\s*\((?P<filter_name>[A-Za-z_$][\w$]*)\)\s*=>\s*"
        r"(?P=filter_name)\.length\s*>\s*0\s*\)\s*;",
        re.DOTALL,
    )
    candidates: dict[str, list[str]] = defaultdict(list)
    for match in pattern.finditer(text):
        if code[match.start() : match.start() + len("const")].strip() != "const":
            continue
        if code[: match.start()].count("{") != code[: match.start()].count("}"):
            continue
        binding = match.group("binding")
        assignment = re.compile(
            rf"(?<![\w$]){re.escape(binding)}\s*=(?!=|>)"
        )
        if len(list(assignment.finditer(code))) != 1:
            continue
        unexpected_use = any(
            not (match.start() <= use.start() < match.end())
            and not code[use.end() :].lstrip().startswith((".length", ".some"))
            for use in re.finditer(rf"\b{re.escape(binding)}\b", code)
        )
        if unexpected_use:
            continue
        candidates[binding].append(match.group("environment"))
    return {
        binding: environments[0]
        for binding, environments in candidates.items()
        if len(environments) == 1
    }


def typescript_rejected_scheme_set(
    condition: str, parsed_name: str
) -> tuple[str, ...] | None:
    parts = re.split(r"\s*&&\s*", condition.strip())
    if not parts:
        return None
    schemes = []
    for part in parts:
        match = re.fullmatch(
            rf"\s*{re.escape(parsed_name)}\.protocol\s*!==\s*(['\"])(.*?)\1\s*",
            part,
            re.DOTALL,
        )
        if match is None:
            return None
        scheme = match.group(2)
        if scheme not in {"data:", "http:", "https:"}:
            return None
        schemes.append(scheme.removesuffix(":"))
    normalized = tuple(sorted(set(schemes)))
    return normalized if {"http", "https"} <= set(normalized) else None


def typescript_configured_hostname_policy(
    body: str,
    parsed_name: str,
    domain_bindings: dict[str, str],
) -> tuple[str, str] | None:
    matches: list[tuple[str, str]] = []
    for condition, block in typescript_if_blocks(body):
        condition_code = typescript_code_mask(condition)
        block_code = typescript_code_mask(block)
        for binding, environment_name in domain_bindings.items():
            if not re.search(
                rf"\b{re.escape(binding)}\.length\s*>\s*0\b",
                condition_code,
            ):
                continue
            protocol_matches = list(
                re.finditer(
                    rf"\b{re.escape(parsed_name)}\.protocol\s*===\s*(['\"])(.*?)\1",
                    condition,
                )
            )
            if len(protocol_matches) != len(
                re.findall(
                    rf"\b{re.escape(parsed_name)}\.protocol\s*===",
                    condition_code,
                )
            ):
                continue
            protocol_values = {
                match.group(2)
                for match in protocol_matches
            }
            if protocol_values != {"http:", "https:"}:
                continue
            domain_assignment = re.search(
                rf"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*"
                rf"{re.escape(parsed_name)}\.hostname\s*;",
                block_code,
            )
            if domain_assignment is None:
                continue
            domain_name = domain_assignment.group(1)
            some_call = re.search(
                rf"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*"
                rf"{re.escape(binding)}\.some\(\s*"
                rf"\(([A-Za-z_$][\w$]*)\)\s*=>\s*\{{([\s\S]*?)\}}\s*\)\s*;",
                block_code,
            )
            if some_call is None:
                continue
            result_name, allowed_name = some_call.group(1), some_call.group(2)
            callback = block[some_call.start(3) : some_call.end(3)]
            exact_match = re.search(
                rf"\breturn\s+{re.escape(domain_name)}\s*===\s*{re.escape(allowed_name)}\s*\|\|\s*"
                rf"{re.escape(domain_name)}\.endsWith\(\s*`\.\$\{{{re.escape(allowed_name)}\}}`\s*\)\s*;",
                callback,
            )
            if exact_match is None:
                continue
            rejected = next(
                (
                    rejected_block
                    for rejected_condition, rejected_block in typescript_if_blocks(block)
                    if re.fullmatch(
                        rf"\s*!\s*{re.escape(result_name)}\s*",
                        rejected_condition,
                    )
                    and re.match(r"\s*throw\b", typescript_code_mask(rejected_block))
                ),
                None,
            )
            if rejected is not None:
                matches.append((binding, environment_name))
    return matches[0] if len(matches) == 1 else None


def typescript_network_origin_helpers(
    relative: str, text: str, lines: list[str]
) -> dict[str, TypeScriptNetworkOriginHelper]:
    """Summarize same-file URL validators with an optional configured hostname policy."""
    domain_bindings = typescript_optional_domain_bindings(text)
    if not domain_bindings:
        return {}
    definitions = typescript_function_definitions(text)
    name_counts = Counter(name for name, _, _, _ in definitions)
    helpers = {}
    for name, line, parameters, body in definitions:
        if name_counts[name] != 1 or len(parameters) != 1:
            continue
        parameter = parameters[0]
        if parameter.property_name is not None:
            continue
        parsed_assignment = re.search(
            rf"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*new\s+URL\s*\(\s*"
            rf"{re.escape(parameter.local_name)}\s*\)\s*;",
            typescript_code_mask(body),
        )
        if parsed_assignment is None:
            continue
        parsed_name = parsed_assignment.group(1)
        scheme_sets = [
            schemes
            for condition, block in typescript_if_blocks(body)
            if re.match(r"\s*throw\b", typescript_code_mask(block))
            and (schemes := typescript_rejected_scheme_set(condition, parsed_name)) is not None
        ]
        hostname_policy = typescript_configured_hostname_policy(
            body, parsed_name, domain_bindings
        )
        if len(scheme_sets) != 1 or hostname_policy is None:
            continue
        _, environment_name = hostname_policy
        helpers[name] = TypeScriptNetworkOriginHelper(
            name,
            Evidence(relative, line, excerpt(lines, line)),
            scheme_sets[0],
            environment_name,
            "exact-or-subdomain",
        )
    return helpers


def typescript_network_origin_assignment(
    line: str,
    helpers: dict[str, TypeScriptNetworkOriginHelper],
    dynamic_names: set[str],
) -> tuple[str, TypeScriptNetworkOriginHelper] | None:
    code = typescript_code_mask(line)
    for local_name, helper in helpers.items():
        assignment = re.search(
            rf"\b(?:const|let)\s+([A-Za-z_$][\w$]*)"
            rf"(?:\s*:[^=]+)?\s*=\s*{re.escape(local_name)}\s*\(([^;]*)\)\s*;",
            code,
        )
        if assignment is None:
            continue
        argument = line[assignment.start(2) : assignment.end(2)].split(",", 1)[0]
        if typescript_expression_names(argument) & dynamic_names:
            return assignment.group(1), helper
    return None


def typescript_update_guarded_network_names(
    line: str,
    guarded_names: dict[str, TypeScriptNetworkOriginHelper],
) -> None:
    """Propagate direct aliases and invalidate transformed or rebound validated URLs."""
    code = typescript_code_mask(line)
    assignment = re.search(
        r"(?:\b(?:const|let)\s+|(?<![\w$]))([A-Za-z_$][\w$]*)"
        r"(?:\s*:[^=]+)?\s*=(?!=|>)",
        code,
    )
    if assignment is None:
        return
    target = assignment.group(1)
    value = code[assignment.end() :].strip().removesuffix(";").strip()
    source = guarded_names.get(value)
    if source is not None:
        guarded_names[target] = source
    else:
        guarded_names.pop(target, None)


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
    approval_bypass_function_summaries: dict[str, tuple[str, ...]],
) -> None:
    """Add one structure-backed TypeScript tool, its capabilities, and literal approval control."""
    line = line_at(text, call_offset)
    evidence = Evidence(relative, line, excerpt(lines, line))
    literal_options = typescript_code_mask(call_body).lstrip().startswith("{")
    approval_expression = typescript_object_property_expression(call_body, "needsApproval")
    approval_handler_expression = typescript_object_property_expression(call_body, "onApproval")
    handler_code = typescript_code_mask(approval_handler_expression or "").strip()
    handler_functions = {
        name
        for name in approval_bypass_function_summaries
        if re.fullmatch(re.escape(name), handler_code)
        or re.search(rf"\b{re.escape(name)}\s*\(", handler_code)
    }
    approval_bypass_environment_names = sorted(
        {
            environment_name
            for name in handler_functions
            for environment_name in approval_bypass_function_summaries.get(name, ())
        }
    )
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
        **(
            {
                "approval_bypass_environment_names": approval_bypass_environment_names,
                "approval_bypass_resolution": "same-file-transitive-callback",
            }
            if approval_bypass_environment_names
            else {}
        ),
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
    if approval_bypass_environment_names:
        ir.add_relationship(
            Relationship(
                "tool",
                tool_name,
                "configured-by",
                "control-setting",
                "auto-approval",
                evidence,
                {
                    "environment_names": approval_bypass_environment_names,
                    "resolution": "same-file-transitive-callback",
                },
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
    approval_bypass_function_summaries = (
        typescript_approval_bypass_function_summaries(text)
        if "onApproval" in text
        and set(openai_imports.values()) & TS_OPENAI_APPROVAL_BUILTINS
        else {}
    )
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
                approval_bypass_function_summaries=approval_bypass_function_summaries,
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
                    approval_bypass_function_summaries=approval_bypass_function_summaries,
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


def typescript_named_import_reaches_path(
    root: Path,
    caller_path: Path,
    caller_text: str,
    local_name: str,
    original_name: str,
    target_path: str,
    selected_paths: set[str],
) -> bool:
    """Prove a named import reaches one selected file directly or through one star barrel."""
    if target_path not in selected_paths:
        return False
    imported = resolve_typescript_imports(root, caller_path, caller_text).get(local_name)
    if imported == (target_path, original_name):
        return True
    if imported is None or imported[1] != original_name or imported[0] not in selected_paths:
        return False
    barrel_path = root / imported[0]
    try:
        barrel_text = barrel_path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return False
    matches = []
    barrel_code = typescript_code_mask(barrel_text)
    for match in re.finditer(r"\bexport\s*\*\s*from", barrel_code):
        specifier_match = re.match(
            r"[ \t]*(['\"])(\.{1,2}/[^'\"]+)\1",
            barrel_text[match.end() :],
        )
        if specifier_match is None:
            continue
        specifier = specifier_match.group(2)
        synthetic_import = f"import {{ {original_name} }} from '{specifier}'"
        resolved = resolve_typescript_imports(root, barrel_path, synthetic_import).get(original_name)
        if resolved == (target_path, original_name):
            matches.append(resolved)
    return len(matches) == 1


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


def add_typescript_network_origin_control(
    ir: RepositoryIR,
    capability_evidence: Evidence,
    helper: TypeScriptNetworkOriginHelper,
) -> None:
    attributes = {
        "scope": source_scope(helper.evidence.path),
        "policy_effect": "validates-initial-http-origin",
        "frontend": "typescript",
        "helper": helper.name,
        "schemes": list(helper.schemes),
        "scheme_scope": "allowlisted",
        "hostname_scope": "configured-optional",
        "hostname_default": "open",
        "hostname_match": helper.hostname_match,
        "environment_name": helper.environment_name,
        "redirect_scope": "unresolved",
        "dns_scope": "unresolved",
    }
    ir.add_component(
        Component("control", "network-origin-policy", helper.evidence, attributes)
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "network",
            "governed-by",
            "control",
            "network-origin-policy",
            capability_evidence,
            {
                "control_path": helper.evidence.path,
                "control_line": helper.evidence.line,
                **attributes,
            },
        )
    )


def scan_typescript(ir: RepositoryIR, root: Path, path: Path, text: str) -> None:
    relative = path.relative_to(root).as_posix()
    lines = text.splitlines()
    typescript_mcp_package_launchers(ir, relative, text, lines)
    masked_lines = typescript_code_mask(text).splitlines()
    line_depths: dict[int, tuple[int, int]] = {}
    brace_depth = 0
    for line_number, masked_line in enumerate(masked_lines, start=1):
        start_depth = brace_depth
        brace_depth += masked_line.count("{") - masked_line.count("}")
        line_depths[line_number] = (start_depth, brace_depth)
    imported_symbols = resolve_typescript_imports(root, path, text)
    tool_by_line, tool_input_names = typescript_graph(ir, relative, text, lines, imported_symbols)
    dynamic_names_by_tool = {tool_id: set(names) for tool_id, names in tool_input_names.items()}
    guarded_path_names_by_tool: dict[str, dict[str, TypeScriptPathBoundaryHelper]] = defaultdict(
        dict
    )
    guarded_network_names_by_tool: dict[
        str, dict[str, TypeScriptNetworkOriginHelper]
    ] = defaultdict(dict)
    network_callback_depth_by_tool: dict[str, int] = {}
    literal_bindings = typescript_literal_string_bindings(text)
    axios_bindings = typescript_axios_default_bindings(text)
    axios_instances = typescript_axios_instances(text, axios_bindings)
    network_calls = typescript_network_calls(text, axios_bindings, axios_instances)
    if tool_by_line and network_calls:
        network_helper_summaries = typescript_network_helper_summaries(
            text, literal_bindings, axios_bindings
        )
        network_helper_calls = typescript_helper_calls(text, network_helper_summaries)
        network_origin_helpers = typescript_network_origin_helpers(relative, text, lines)
        multiline_destructuring_assignments = typescript_multiline_destructuring_assignments(text)
    else:
        network_helper_calls = {}
        network_origin_helpers = {}
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
    for provider_call in typescript_ai_sdk_provider_calls(text):
        line_number = line_at(text, provider_call.offset)
        ev = Evidence(relative, line_number, excerpt(lines, line_number))
        attributes = {
            "call": provider_call.call,
            "call_kind": provider_call.call_kind,
            "module": provider_call.module,
            "imported_symbol": provider_call.imported_symbol,
            "resolution": "exact-typescript-provider-import",
        }
        if provider_call.model_method is not None:
            attributes["model_method"] = provider_call.model_method
        if provider_call.configured_by is not None:
            attributes["configured_by"] = provider_call.configured_by
        ir.add_component(
            Component("provider", provider_call.provider, ev, attributes)
        )
        if provider_call.model is not None:
            ir.add_component(
                Component(
                    "model",
                    provider_call.model,
                    ev,
                    {
                        "provider": provider_call.provider,
                        "configured_on": provider_call.call,
                        "model_method": provider_call.model_method,
                        "module": provider_call.module,
                        "resolution": "exact-typescript-provider-import",
                    },
                )
            )
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
        guarded_network_names: dict[str, TypeScriptNetworkOriginHelper] = {}
        if tool := tool_by_line.get(line_number):
            dynamic_names = dynamic_names_by_tool.setdefault(tool[1], set())
            guarded_path_names = guarded_path_names_by_tool.setdefault(tool[1], {})
            guarded_network_names = guarded_network_names_by_tool.setdefault(tool[1], {})
            typescript_apply_destructuring_assignments(
                multiline_destructuring_assignments.get(line_number, []), dynamic_names
            )
            typescript_update_dynamic_names(line, dynamic_names, literal_bindings)
            callback_opening = re.search(r"=>\s*\{", code_line)
            if (
                callback_opening is not None
                and typescript_expression_names(code_line[: callback_opening.start()])
                & dynamic_names
            ):
                network_callback_depth_by_tool.setdefault(
                    tool[1], line_depths[line_number][1]
                )
            typescript_update_guarded_path_names(line, guarded_path_names)
            typescript_update_guarded_network_names(line, guarded_network_names)
            if boundary_assignment := typescript_path_boundary_assignment(
                line, path_boundary_helpers, dynamic_names
            ):
                guarded_path_names[boundary_assignment[0]] = boundary_assignment[1]
            if (
                line_depths[line_number][0]
                == network_callback_depth_by_tool.get(tool[1])
                and (
                    origin_assignment := typescript_network_origin_assignment(
                        line, network_origin_helpers, dynamic_names
                    )
                )
            ):
                guarded_network_names[origin_assignment[0]] = origin_assignment[1]
        for match in TS_IMPORT.finditer(line):
            component_from_import(ir, match.group(1), ev, "typescript")
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
        for network_call in network_calls.get(line_number, []):
            api = network_call.api
            url_expression = network_call.url_expression
            origin_policies = {
                guarded_network_names[name]
                for name in typescript_expression_names(url_expression)
                if name in guarded_network_names
            }
            origin_policy = next(iter(origin_policies)) if len(origin_policies) == 1 else None
            dynamic_origin = typescript_http_origin_is_dynamic(
                url_expression, dynamic_names, literal_bindings
            )
            if (
                network_call.absolute_url_override == "disabled"
                and network_call.base_url_scope != "absent"
            ):
                dynamic_origin = False
            add_typescript_capability(
                ir,
                relative,
                line_number,
                ev,
                tool_by_line,
                "network",
                {
                    "api": api,
                    "dynamic_origin": dynamic_origin,
                    **(
                        {
                            "summary": network_call.summary,
                            "receiver": network_call.receiver,
                            "base_url_scope": network_call.base_url_scope,
                            "absolute_url_override": network_call.absolute_url_override,
                        }
                        if network_call.summary is not None
                        else {}
                    ),
                    **(
                        {
                            "network_origin_policy": True,
                            "scheme_scope": "allowlisted",
                            "hostname_scope": "configured-optional",
                        }
                        if origin_policy is not None
                        else {}
                    ),
                },
            )
            if origin_policy is not None:
                add_typescript_network_origin_control(ir, ev, origin_policy)
        if line_number in tool_by_line:
            for summary, arguments in network_helper_calls.get(line_number, []):
                dynamic_origin = False
                origin_policies: set[TypeScriptNetworkOriginHelper] = set()
                for parameter in summary.parameters:
                    if parameter.local_name not in summary.controlled_names:
                        continue
                    argument = typescript_helper_argument_expression(arguments, parameter)
                    if argument and typescript_http_origin_is_dynamic(
                        argument, dynamic_names, literal_bindings
                    ):
                        dynamic_origin = True
                    if argument:
                        origin_policies.update(
                            guarded_network_names[name]
                            for name in typescript_expression_names(argument)
                            if name in guarded_network_names
                        )
                origin_policy = (
                    next(iter(origin_policies)) if len(origin_policies) == 1 else None
                )
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
                        **(
                            {
                                "network_origin_policy": True,
                                "scheme_scope": "allowlisted",
                                "hostname_scope": "configured-optional",
                            }
                            if origin_policy is not None
                            else {}
                        ),
                    },
                )
                if origin_policy is not None:
                    add_typescript_network_origin_control(ir, ev, origin_policy)
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
        attributes = {
            "transport": "unknown",
            "frontend": "json",
            "scope": source_scope(relative),
        }
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
            if isinstance(command, str) and all(
                isinstance(argument, str) for argument in args
            ):
                package = mcp_package_reference(command, list(args))
                if package is not None:
                    attributes.update(
                        {
                            "package_manager": command,
                            "constructor": "mcpServers",
                            "analysis": "json-mcp-config",
                            **package,
                        }
                    )
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


HOST_CREDENTIAL_PATHS = (
    (re.compile(r"(?:^|/)\.ssh(?:/|$)"), "ssh"),
    (re.compile(r"(?:^|/)\.aws(?:/|$)"), "aws"),
    (re.compile(r"(?:^|/)\.kube(?:/|$)"), "kubernetes"),
    (re.compile(r"(?:^|/)\.config/gcloud(?:/|$)"), "gcp"),
    (re.compile(r"(?:^|/)\.docker/config\.json$"), "docker-registry"),
    (re.compile(r"(?:^|/)\.npmrc$"), "npm"),
    (re.compile(r"(?:^|/)\.pypirc$"), "pypi"),
    (re.compile(r"(?:^|/)\.netrc$"), "netrc"),
    (re.compile(r"(?:^|/)\.git-credentials$"), "git"),
)


def compose_host_credential_mount(stripped: str) -> dict[str, object] | None:
    """Return exact short-syntax host credential bind-mount evidence."""
    if not stripped.startswith("-"):
        return None
    payload = stripped[1:].strip().split(" #", 1)[0].strip()
    if len(payload) >= 2 and payload[0] == payload[-1] and payload[0] in {'"', "'"}:
        payload = payload[1:-1]
    parts = payload.split(":")
    if len(parts) < 2:
        return None
    source, target, *options = parts
    if not target.startswith("/") or not source.startswith(
        ("/", "./", "../", "~", "$HOME/", "${HOME}/")
    ):
        return None
    credential_kind = next(
        (kind for pattern, kind in HOST_CREDENTIAL_PATHS if pattern.search(source)),
        None,
    )
    if credential_kind is None:
        return None
    option_names = {
        option
        for value in options
        for option in value.lower().split(",")
    }
    return {
        "host_path": source,
        "container_path": target,
        "credential_kind": credential_kind,
        "read_only": "ro" in option_names,
    }


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
        elif credential_mount := compose_host_credential_mount(stripped):
            boundary = "host-credential-mount"
            attributes.update(credential_mount)
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
        module_parts.extend(
            parts[index + 1 :]
            for index, part in enumerate(parts)
            if part in {"src", "python"}
        )
        for candidate_parts in module_parts:
            if candidate_parts:
                module = ".".join(candidate_parts)
                candidates.setdefault(module, set()).add(relative.as_posix())
    return {
        module: next(iter(locations))
        for module, locations in candidates.items()
        if len(locations) == 1
    }


def build_python_decorated_tool_exports(
    root: Path,
    paths: list[Path],
) -> dict[tuple[str, str], str]:
    """Index exact importable Python functions recognized as decorated tools."""
    exports: dict[tuple[str, str], list[ast.FunctionDef | ast.AsyncFunctionDef]] = defaultdict(list)
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
            tree = ast.parse(
                path.read_text(encoding="utf-8-sig", errors="ignore"),
                filename=path.relative_to(root).as_posix(),
            )
        except (OSError, SyntaxError):
            continue
        relative = path.relative_to(root).as_posix()

        def collect(
            statements: list[ast.stmt],
            class_stack: tuple[str, ...] = (),
            source_path: str = relative,
        ) -> None:
            for statement in statements:
                if isinstance(statement, ast.ClassDef):
                    collect(statement.body, (*class_stack, statement.name))
                    continue
                if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                decorators = {
                    dotted_name(decorator.func)
                    if isinstance(decorator, ast.Call)
                    else dotted_name(decorator)
                    for decorator in statement.decorator_list
                }
                if decorators & TOOL_DECORATORS or any(
                    name.endswith(".tool") for name in decorators
                ):
                    qualified_name = ".".join([*class_stack, statement.name])
                    exports[(source_path, qualified_name)].append(statement)

        collect(tree.body)
    return {
        key: source_symbol("py", key[0], "tool", key[1])
        for key, definitions in exports.items()
        if len(definitions) == 1
    }


def build_python_literal_imported_tool_references(
    root: Path,
    paths: list[Path],
    module_paths: dict[str, str],
) -> tuple[
    dict[str, tuple[PythonImportedToolReference, ...]],
    dict[tuple[str, str], tuple[PythonImportedToolReference, ...]],
]:
    """Index immutable names imported directly into literal Python Agent tool lists."""
    parsed: dict[str, ast.Module] = {}
    callable_exports: dict[tuple[str, str], list[ast.FunctionDef | ast.AsyncFunctionDef]] = (
        defaultdict(list)
    )
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
            relative = path.relative_to(root).as_posix()
            tree = ast.parse(
                path.read_text(encoding="utf-8-sig", errors="ignore"),
                filename=relative,
            )
        except (OSError, SyntaxError):
            continue
        parsed[relative] = tree
        for statement in tree.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = {
                dotted_name(decorator.func)
                if isinstance(decorator, ast.Call)
                else dotted_name(decorator)
                for decorator in statement.decorator_list
            }
            if decorators & TOOL_DECORATORS or any(
                name.endswith(".tool") for name in decorators
            ):
                continue
            callable_exports[(relative, statement.name)].append(statement)
    unique_callable_exports = {
        key for key, definitions in callable_exports.items() if len(definitions) == 1
    }

    references_by_importer: dict[str, list[PythonImportedToolReference]] = defaultdict(list)
    references_by_export: dict[
        tuple[str, str], list[PythonImportedToolReference]
    ] = defaultdict(list)
    for relative, tree in parsed.items():
        nodes = list(ast.walk(tree))
        parent_by_id = {
            id(child): parent for parent in nodes for child in ast.iter_child_nodes(parent)
        }
        imports: dict[str, list[tuple[ast.ImportFrom, ast.alias]]] = defaultdict(list)
        import_counts: Counter[str] = Counter()
        for statement in tree.body:
            if not isinstance(statement, (ast.Import, ast.ImportFrom)):
                continue
            for alias in statement.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name.split(".", 1)[0]
                import_counts[local_name] += 1
                if isinstance(statement, ast.ImportFrom):
                    imports[local_name].append((statement, alias))

        module_mutations: set[str] = set()

        def collect_module_mutations(candidate: ast.AST, mutations: set[str]) -> None:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                mutations.add(candidate.name)
                return
            if isinstance(candidate, (ast.Import, ast.ImportFrom, ast.Lambda)):
                return
            if isinstance(candidate, ast.Name) and isinstance(
                candidate.ctx, (ast.Store, ast.Del)
            ):
                mutations.add(candidate.id)
            for child in ast.iter_child_nodes(candidate):
                collect_module_mutations(child, mutations)

        for statement in tree.body:
            if not isinstance(statement, (ast.Import, ast.ImportFrom)):
                collect_module_mutations(statement, module_mutations)
        module_mutations.update(
            name
            for candidate in nodes
            if isinstance(candidate, ast.Global)
            for name in candidate.names
        )

        for call in (
            candidate
            for candidate in nodes
            if isinstance(candidate, ast.Call)
            and dotted_name(candidate.func).rsplit(".", 1)[-1] in AGENT_CALLS
        ):
            for keyword in call.keywords:
                if keyword.arg != "tools" or not isinstance(
                    keyword.value, (ast.List, ast.Tuple)
                ):
                    continue
                for value in keyword.value.elts:
                    if not isinstance(value, ast.Name):
                        continue
                    name = value.id
                    candidates = imports.get(name, [])
                    if (
                        len(candidates) != 1
                        or import_counts[name] != 1
                        or name in module_mutations
                    ):
                        continue
                    shadowed = False
                    parent = parent_by_id.get(id(call))
                    while parent is not None:
                        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                            name in python_function_local_bindings(parent)
                        ):
                            shadowed = True
                            break
                        if isinstance(parent, ast.ClassDef):
                            class_bound_names = {
                                child.id
                                for statement in parent.body
                                for child in ast.walk(statement)
                                if isinstance(child, ast.Name)
                                and isinstance(child.ctx, (ast.Store, ast.Del))
                            }
                            if name in class_bound_names:
                                shadowed = True
                                break
                        parent = parent_by_id.get(id(parent))
                    if shadowed:
                        continue
                    import_node, alias = candidates[0]
                    if import_node.lineno >= call.lineno:
                        continue
                    resolution = resolve_python_import(
                        root,
                        relative,
                        import_node,
                        alias.name,
                        module_paths,
                    )
                    if resolution is None and import_node.level:
                        continue
                    export_key = (
                        (resolution.path, alias.name) if resolution is not None else None
                    )
                    target_path = (
                        resolution.path
                        if export_key is not None and export_key in unique_callable_exports
                        else None
                    )
                    reference = PythonImportedToolReference(
                        importer_path=relative,
                        local_name=name,
                        original_name=alias.name,
                        module=import_node.module or "",
                        import_line=import_node.lineno,
                        agent_line=call.lineno,
                        agent_col=call.col_offset,
                        import_resolution=(resolution.basis if resolution else None),
                        target_path=target_path,
                    )
                    references_by_importer[relative].append(reference)
                    if target_path is not None:
                        references_by_export[(target_path, alias.name)].append(reference)

    return (
        {
            path: tuple(
                sorted(
                    references,
                    key=lambda item: (
                        item.import_line,
                        item.agent_line,
                        item.agent_col,
                        item.local_name,
                    ),
                )
            )
            for path, references in references_by_importer.items()
        },
        {
            key: tuple(
                sorted(
                    references,
                    key=lambda item: (
                        item.importer_path,
                        item.agent_line,
                        item.agent_col,
                    ),
                )
            )
            for key, references in references_by_export.items()
        },
    )


def build_python_mcp_server_subclass_exports(
    root: Path,
    paths: list[Path],
) -> dict[tuple[str, str], PythonMCPServerSubclassTarget]:
    """Index immutable project classes implementing an exact SDK MCPServer contract."""
    exports: dict[
        tuple[str, str], list[PythonMCPServerSubclassTarget]
    ] = defaultdict(list)
    exact_bases = {
        ("agents.mcp", "MCPServer"),
        ("agents.mcp.server", "MCPServer"),
        ("pydantic_ai.mcp", "MCPServer"),
    }
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
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            if "MCPServer" not in text or "call_tool" not in text or "list_tools" not in text:
                continue
            tree = ast.parse(text, filename=path.relative_to(root).as_posix())
        except (OSError, SyntaxError):
            continue
        binding_counts: Counter[str] = Counter()
        for statement in tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                binding_counts[statement.name] += 1
            elif isinstance(statement, (ast.Import, ast.ImportFrom)):
                binding_counts.update(
                    alias.asname or alias.name.split(".", 1)[0]
                    for alias in statement.names
                    if alias.name != "*"
                )
            else:
                binding_counts.update(
                    candidate.id
                    for candidate in ast.walk(statement)
                    if isinstance(candidate, ast.Name)
                    and isinstance(candidate.ctx, (ast.Store, ast.Del))
                )
        base_bindings = {
            alias.asname or alias.name: (statement.module or "", alias.name)
            for statement in tree.body
            if isinstance(statement, ast.ImportFrom)
            and statement.level == 0
            for alias in statement.names
            if (statement.module or "", alias.name) in exact_bases
            and binding_counts[alias.asname or alias.name] == 1
        }
        relative = path.relative_to(root).as_posix()
        for class_node in (
            statement for statement in tree.body if isinstance(statement, ast.ClassDef)
        ):
            if (
                binding_counts[class_node.name] != 1
                or class_node.decorator_list
                or class_node.keywords
                or len(class_node.bases) != 1
                or not isinstance(class_node.bases[0], ast.Name)
                or class_node.bases[0].id not in base_bindings
            ):
                continue
            method_counts = Counter(
                statement.name
                for statement in class_node.body
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            if method_counts["list_tools"] != 1 or method_counts["call_tool"] != 1:
                continue
            base_module, base_name = base_bindings[class_node.bases[0].id]
            exports[(relative, class_node.name)].append(
                PythonMCPServerSubclassTarget(
                    relative,
                    class_node.name,
                    class_node.lineno,
                    base_module,
                    base_name,
                )
            )
    return {
        key: targets[0]
        for key, targets in exports.items()
        if len(targets) == 1
    }


def build_python_agent_factory_class_exports(
    root: Path,
    paths: list[Path],
) -> dict[tuple[str, str], PythonAgentFactoryClassTarget]:
    """Index exact imported classes whose methods directly return one agent.

    The summary intentionally excludes decorated/inherited classes, async or
    indirect returns, local constructor shadowing, and rebound class or method
    names. Call-site resolution applies additional same-block dominance checks.
    """
    exports: dict[
        tuple[str, str], list[PythonAgentFactoryClassTarget]
    ] = defaultdict(list)
    framework_modules = tuple(
        prefix
        for prefixes in IMPORT_SIGNATURES["framework"].values()
        for prefix in prefixes
        if not prefix.startswith("@")
    )

    def module_binding_counts(tree: ast.Module) -> Counter[str]:
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
            if isinstance(candidate, ast.ExceptHandler) and candidate.name:
                counts[candidate.name] += 1
            if isinstance(candidate, ast.Name) and isinstance(
                candidate.ctx, (ast.Store, ast.Del)
            ):
                counts[candidate.id] += 1
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        for statement in tree.body:
            collect(statement)
        return counts

    def class_binding_counts(node: ast.ClassDef) -> Counter[str]:
        counts: Counter[str] = Counter()
        for statement in node.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                counts[statement.name] += 1
                continue
            if isinstance(statement, (ast.Import, ast.ImportFrom)):
                counts.update(
                    alias.asname or alias.name.split(".", 1)[0]
                    for alias in statement.names
                    if alias.name != "*"
                )
                continue
            for candidate in ast.walk(statement):
                if isinstance(candidate, ast.Name) and isinstance(
                    candidate.ctx, (ast.Store, ast.Del)
                ):
                    counts[candidate.id] += 1
        return counts

    def method_instance_attribute_rebound(
        class_node: ast.ClassDef,
        method_name: str,
    ) -> bool:
        for method in class_node.body:
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
                if any(
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                    and target.attr == method_name
                    for target in targets
                ):
                    return True
                if (
                    isinstance(candidate, ast.Call)
                    and dotted_name(candidate.func) in {"setattr", "delattr"}
                    and len(candidate.args) >= 2
                    and isinstance(candidate.args[0], ast.Name)
                    and candidate.args[0].id == "self"
                    and isinstance(candidate.args[1], ast.Constant)
                    and candidate.args[1].value == method_name
                ):
                    return True
        return False

    def class_attribute_rebound(tree: ast.Module, class_name: str) -> bool:
        def target_matches(target: ast.AST) -> bool:
            return (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == class_name
            )

        def statement_rebinds(candidate: ast.AST) -> bool:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return False
            targets: tuple[ast.AST, ...] = ()
            if isinstance(candidate, ast.Assign):
                targets = tuple(candidate.targets)
            elif isinstance(candidate, (ast.AnnAssign, ast.AugAssign)):
                targets = (candidate.target,)
            elif isinstance(candidate, ast.Delete):
                targets = tuple(candidate.targets)
            if any(target_matches(target) for target in targets):
                return True
            if (
                isinstance(candidate, ast.Call)
                and dotted_name(candidate.func) in {"setattr", "delattr"}
                and candidate.args
                and isinstance(candidate.args[0], ast.Name)
                and candidate.args[0].id == class_name
            ):
                return True
            return any(statement_rebinds(child) for child in ast.iter_child_nodes(candidate))

        return any(statement_rebinds(statement) for statement in tree.body)

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
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            if "return" not in text or not any(
                f"{constructor}(" in text for constructor in AGENT_CALLS
            ):
                continue
            tree = ast.parse(text, filename=path.relative_to(root).as_posix())
        except (OSError, SyntaxError):
            continue
        relative = path.relative_to(root).as_posix()
        binding_counts = module_binding_counts(tree)
        agent_constructors = {
            alias.name
            for statement in tree.body
            if isinstance(statement, ast.ImportFrom)
            and statement.level == 0
            and statement.module is not None
            and any(
                statement.module == prefix
                or statement.module.startswith(f"{prefix}.")
                for prefix in framework_modules
            )
            for alias in statement.names
            if alias.asname is None
            and alias.name in AGENT_CALLS
            and binding_counts[alias.name] == 1
        }
        if not agent_constructors:
            continue
        for class_node in (
            statement for statement in tree.body if isinstance(statement, ast.ClassDef)
        ):
            if (
                binding_counts[class_node.name] != 1
                or class_node.decorator_list
                or class_node.bases
                or class_node.keywords
                or class_attribute_rebound(tree, class_node.name)
            ):
                continue
            class_counts = class_binding_counts(class_node)
            if class_counts["__getattr__"] or class_counts["__getattribute__"]:
                continue
            methods: dict[str, str] = {}
            for method in class_node.body:
                if not isinstance(method, ast.FunctionDef):
                    continue
                positional = (*method.args.posonlyargs, *method.args.args)
                if (
                    class_counts[method.name] != 1
                    or method.decorator_list
                    or not positional
                    or positional[0].arg != "self"
                    or method.name in {"__getattr__", "__getattribute__"}
                    or method_instance_attribute_rebound(class_node, method.name)
                ):
                    continue
                returns = [
                    candidate
                    for candidate in ast.walk(method)
                    if isinstance(candidate, ast.Return)
                ]
                if (
                    len(returns) != 1
                    or returns[0] not in method.body
                    or not isinstance(returns[0].value, ast.Call)
                    or not isinstance(returns[0].value.func, ast.Name)
                    or returns[0].value.func.id not in agent_constructors
                    or returns[0].value.func.id in python_function_local_bindings(method)
                ):
                    continue
                call = returns[0].value
                agent_name = call.func.id
                for keyword in call.keywords:
                    if (
                        keyword.arg == "name"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is not None
                    ):
                        agent_name = str(keyword.value.value)
                methods[method.name] = source_symbol(
                    "py", relative, "agent", f"{agent_name}@{call.lineno}"
                )
            if methods:
                exports[(relative, class_node.name)].append(
                    PythonAgentFactoryClassTarget(
                        relative,
                        class_node.name,
                        methods,
                    )
                )
    return {
        key: targets[0]
        for key, targets in exports.items()
        if len(targets) == 1
    }


def build_python_secure_network_helper_summaries(
    root: Path,
    paths: list[Path],
    module_paths: dict[str, str],
) -> dict[tuple[str, str], PythonNetworkHelperSummary]:
    """Index source-proven helpers that validate origins, redirects, peers, and proxies."""
    parsed_files: dict[str, tuple[str, ast.Module]] = {}
    selected_files = {path.relative_to(root).as_posix() for path in paths}

    def parsed_source(relative: str) -> tuple[str, ast.Module] | None:
        if relative not in selected_files:
            return None
        if relative in parsed_files:
            return parsed_files[relative]
        try:
            text = (root / relative).read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text, filename=relative)
        except (OSError, SyntaxError):
            return None
        parsed_files[relative] = (text, tree)
        return text, tree

    def unique_function(
        tree: ast.Module, name: str
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        matches = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ]
        return matches[0] if len(matches) == 1 else None

    def module_nonimport_rebound(tree: ast.Module, name: str) -> bool:
        for statement in tree.body:
            if (
                isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
                and statement.name == name
            ):
                continue
            if isinstance(statement, ast.ClassDef) and statement.name == name:
                return True
            if isinstance(statement, (ast.Import, ast.ImportFrom)):
                continue
            targets: list[ast.AST] = []
            if isinstance(statement, ast.Assign):
                targets = list(statement.targets)
            elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
                targets = [statement.target]
            elif isinstance(statement, ast.Delete):
                targets = list(statement.targets)
            if any(name in python_assigned_names(target) for target in targets):
                return True
        return False

    def module_value_rebound(tree: ast.Module, name: str) -> bool:
        return module_nonimport_rebound(tree, name) or any(
            (alias.asname or alias.name.split(".", 1)[0]) == name
            for statement in tree.body
            if isinstance(statement, (ast.Import, ast.ImportFrom))
            for alias in statement.names
        )

    def lexical_nodes(node: ast.AST) -> list[ast.AST]:
        result: list[ast.AST] = []

        def collect(candidate: ast.AST) -> None:
            if candidate is not node and isinstance(
                candidate,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),
            ):
                return
            result.append(candidate)
            for child in ast.iter_child_nodes(candidate):
                collect(child)

        collect(node)
        return result

    def resolved_import(
        relative: str,
        tree: ast.Module,
        local_name: str,
    ) -> tuple[str, str] | None:
        matches: list[tuple[str, str]] = []
        for statement in tree.body:
            if not isinstance(statement, ast.ImportFrom):
                continue
            for alias in statement.names:
                if (alias.asname or alias.name) != local_name:
                    continue
                target = resolve_python_import_path(
                    root, relative, statement, alias.name, module_paths
                )
                if target is not None:
                    matches.append((target, alias.name))
        if module_nonimport_rebound(tree, local_name):
            return None
        return matches[0] if len(matches) == 1 else None

    def static_environment_names(tree: ast.Module) -> tuple[str, str] | None:
        values: dict[str, list[str]] = defaultdict(list)
        mutation_counts: Counter[str] = Counter()
        for statement in tree.body:
            mutation_targets: list[ast.AST] = []
            if isinstance(statement, ast.Assign):
                mutation_targets = list(statement.targets)
            elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
                mutation_targets = [statement.target]
            elif isinstance(statement, ast.Delete):
                mutation_targets = list(statement.targets)
            mutation_counts.update(
                name
                for target in mutation_targets
                for name in python_assigned_names(target)
            )
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            value = statement.value
            if (
                len(targets) == 1
                and isinstance(targets[0], ast.Name)
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                values[targets[0].id].append(value.value)
        bypass_values = values.get("_UNSAFE_PATHS_ENV", [])
        force_values = values.get("_FORCE_SAFE_PATHS_ENV", [])
        escape = unique_function(tree, "_is_escape_hatch_enabled")
        flag = unique_function(tree, "_env_flag_enabled")
        if (
            len(bypass_values) != 1
            or len(force_values) != 1
            or escape is None
            or flag is None
            or mutation_counts["_UNSAFE_PATHS_ENV"] != 1
            or mutation_counts["_FORCE_SAFE_PATHS_ENV"] != 1
        ):
            return None
        force_guard = any(
            isinstance(candidate, ast.If)
            and isinstance(candidate.test, ast.Call)
            and dotted_name(candidate.test.func).rsplit(".", 1)[-1]
            == "_env_flag_enabled"
            and len(candidate.test.args) == 1
            and isinstance(candidate.test.args[0], ast.Name)
            and candidate.test.args[0].id == "_FORCE_SAFE_PATHS_ENV"
            and any(
                isinstance(statement, ast.Return)
                and isinstance(statement.value, ast.Constant)
                and statement.value.value is False
                for statement in candidate.body
            )
            for candidate in lexical_nodes(escape)
        )
        bypass_return = any(
            isinstance(candidate, ast.Return)
            and isinstance(candidate.value, ast.Call)
            and dotted_name(candidate.value.func).rsplit(".", 1)[-1]
            == "_env_flag_enabled"
            and len(candidate.value.args) == 1
            and isinstance(candidate.value.args[0], ast.Name)
            and candidate.value.args[0].id == "_UNSAFE_PATHS_ENV"
            for candidate in escape.body
        )
        flag_returns = [
            candidate
            for candidate in flag.body
            if isinstance(candidate, ast.Return) and candidate.value is not None
        ]
        flag_expression = flag_returns[0].value if len(flag_returns) == 1 else None
        flag_default_off = (
            isinstance(flag_expression, ast.Compare)
            and len(flag_expression.ops) == 1
            and isinstance(flag_expression.ops[0], ast.In)
            and len(flag_expression.comparators) == 1
            and isinstance(flag_expression.comparators[0], (ast.Tuple, ast.List, ast.Set))
            and "" not in {
                element.value
                for element in flag_expression.comparators[0].elts
                if isinstance(element, ast.Constant)
                and isinstance(element.value, str)
            }
            and any(
                isinstance(candidate, ast.Call)
                and isinstance(candidate.func, ast.Attribute)
                and candidate.func.attr == "get"
                and len(candidate.args) > 1
                and isinstance(candidate.args[1], ast.Constant)
                and candidate.args[1].value == ""
                for candidate in ast.walk(flag_expression.left)
            )
        )
        if not (force_guard and bypass_return and flag_default_off):
            return None
        return bypass_values[0], force_values[0]

    def validate_url_policy(
        relative: str,
        function_name: str,
    ) -> tuple[str, str] | None:
        parsed = parsed_source(relative)
        if parsed is None:
            return None
        _, tree = parsed
        function = unique_function(tree, function_name)
        parser_bindings = {
            alias.asname or alias.name
            for statement in tree.body
            if isinstance(statement, ast.ImportFrom)
            and statement.module == "urllib.parse"
            for alias in statement.names
            if alias.name in {"urlparse", "urlsplit"}
        }
        socket_imported = any(
            isinstance(statement, ast.Import)
            and any(
                alias.name == "socket" and (alias.asname or alias.name) == "socket"
                for alias in statement.names
            )
            for statement in tree.body
        )
        blocked_ip = unique_function(tree, "is_blocked_ip")
        if (
            function is None
            or module_value_rebound(tree, function_name)
            or len(parser_bindings) != 1
            or any(module_nonimport_rebound(tree, name) for name in parser_bindings)
            or not socket_imported
            or module_nonimport_rebound(tree, "socket")
            or blocked_ip is None
            or module_value_rebound(tree, "is_blocked_ip")
        ):
            return None
        blocked_nodes = lexical_nodes(blocked_ip)
        blocked_calls = {
            dotted_name(candidate.func)
            for candidate in blocked_nodes
            if isinstance(candidate, ast.Call)
        }
        blocked_returns = [
            candidate
            for candidate in blocked_nodes
            if isinstance(candidate, ast.Return) and candidate.value is not None
        ]
        if "ipaddress.ip_address" not in blocked_calls or not any(
            any(
                (isinstance(child, ast.Call) and dotted_name(child.func) == "any")
                or (isinstance(child, ast.Attribute) and child.attr == "is_private")
                for child in ast.walk(candidate.value)
            )
            for candidate in blocked_returns
        ):
            return None
        positional = (*function.args.posonlyargs, *function.args.args)
        if not positional:
            return None
        url_name = positional[0].arg
        nodes = lexical_nodes(function)
        parsed_names = {
            target.id
            for assignment in nodes
            if isinstance(assignment, ast.Assign)
            and len(assignment.targets) == 1
            and isinstance((target := assignment.targets[0]), ast.Name)
            and isinstance(assignment.value, ast.Call)
            and dotted_name(assignment.value.func) in parser_bindings
            and len(assignment.value.args) == 1
            and isinstance(assignment.value.args[0], ast.Name)
            and assignment.value.args[0].id == url_name
        }
        if len(parsed_names) != 1:
            return None
        parsed_name = next(iter(parsed_names))
        scheme_guard = any(
            isinstance(candidate, ast.If)
            and isinstance(candidate.test, ast.Compare)
            and isinstance(candidate.test.left, ast.Attribute)
            and isinstance(candidate.test.left.value, ast.Name)
            and candidate.test.left.value.id == parsed_name
            and candidate.test.left.attr == "scheme"
            and len(candidate.test.ops) == 1
            and isinstance(candidate.test.ops[0], ast.NotIn)
            and len(candidate.test.comparators) == 1
            and isinstance(candidate.test.comparators[0], (ast.Tuple, ast.List, ast.Set))
            and len(candidate.test.comparators[0].elts) == 2
            and {
                element.value
                for element in candidate.test.comparators[0].elts
                if isinstance(element, ast.Constant)
                and isinstance(element.value, str)
            }
            == {"http", "https"}
            and python_block_always_terminates(candidate.body)
            for candidate in nodes
        )
        call_names = {
            dotted_name(candidate.func).rsplit(".", 1)[-1]
            for candidate in nodes
            if isinstance(candidate, ast.Call)
        }
        blocked_guard = any(
            isinstance(candidate, ast.If)
            and any(
                isinstance(child, ast.Call)
                and dotted_name(child.func).rsplit(".", 1)[-1] == "is_blocked_ip"
                for child in ast.walk(candidate.test)
            )
            and python_block_always_terminates(candidate.body)
            for candidate in nodes
        )
        if not (
            scheme_guard
            and blocked_guard
            and {"getaddrinfo", "_is_escape_hatch_enabled"} <= call_names
        ):
            return None
        return static_environment_names(tree)

    def validated_transport(relative: str, class_name: str) -> bool:
        parsed = parsed_source(relative)
        if parsed is None:
            return False
        _, tree = parsed
        class_groups: dict[str, list[ast.ClassDef]] = defaultdict(list)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_groups[node.name].append(node)
        classes = {
            name: nodes[0] for name, nodes in class_groups.items() if len(nodes) == 1
        }
        adapter = classes.get(class_name)
        if adapter is None:
            return False
        def method(node: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
            matches = [
                candidate
                for candidate in node.body
                if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef))
                and candidate.name == name
            ]
            return matches[0] if len(matches) == 1 else None

        proxy_method = next(
            (
                node
                for node in adapter.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "proxy_manager_for"
            ),
            None,
        )
        adapter_init = method(adapter, "init_poolmanager")
        connection = unique_function(tree, "create_validated_connection")
        open_socket = unique_function(tree, "_open_validated_socket")
        if (
            proxy_method is None
            or adapter_init is None
            or connection is None
            or open_socket is None
        ):
            return False
        proxy_nodes = lexical_nodes(proxy_method)
        connection_nodes = lexical_nodes(connection)
        adapter_pool_names = {
            dotted_name(node.func).rsplit(".", 1)[-1]
            for node in lexical_nodes(adapter_init)
            if isinstance(node, ast.Call)
        }
        pool_manager = classes.get("_SafePoolManager")
        pool_init = method(pool_manager, "__init__") if pool_manager is not None else None
        if "_SafePoolManager" not in adapter_pool_names or pool_init is None:
            return False
        pool_mapping_assignments = [
            node
            for node in lexical_nodes(pool_init)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Attribute)
                and target.attr == "pool_classes_by_scheme"
                for target in node.targets
            )
            and isinstance(node.value, ast.Name)
        ]
        if len(pool_mapping_assignments) != 1:
            return False
        mapping_name = pool_mapping_assignments[0].value.id
        pool_classes: dict[str, str] = {}
        mapping_assignments = [
            statement
            for statement in tree.body
            if (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id == mapping_name
                and isinstance(statement.value, ast.Dict)
            )
        ]
        if len(mapping_assignments) != 1:
            return False
        for key, value in zip(
            mapping_assignments[0].value.keys,
            mapping_assignments[0].value.values,
            strict=True,
        ):
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and isinstance(value, ast.Name)
            ):
                pool_classes[key.value] = value.id
        if set(pool_classes) != {"http", "https"}:
            return False
        connection_classes: set[str] = set()
        for pool_class_name in pool_classes.values():
            pool_class = classes.get(pool_class_name)
            if pool_class is None:
                return False
            connection_assignments = [
                statement
                for statement in pool_class.body
                if isinstance(statement, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "ConnectionCls"
                    for target in statement.targets
                )
                and isinstance(statement.value, ast.Name)
            ]
            if len(connection_assignments) != 1:
                return False
            connection_classes.add(connection_assignments[0].value.id)
        if len(connection_classes) != 2:
            return False
        for connection_class_name in connection_classes:
            connection_class = classes.get(connection_class_name)
            new_connection = (
                method(connection_class, "_new_conn")
                if connection_class is not None
                else None
            )
            if new_connection is None or not any(
                isinstance(node, ast.Call)
                and dotted_name(node.func).rsplit(".", 1)[-1]
                == "_open_validated_socket"
                for node in lexical_nodes(new_connection)
            ):
                return False
        open_calls = {
            dotted_name(node.func).rsplit(".", 1)[-1]
            for node in lexical_nodes(open_socket)
            if isinstance(node, ast.Call)
        }
        connection_calls = {
            dotted_name(node.func).rsplit(".", 1)[-1]
            for node in connection_nodes
            if isinstance(node, ast.Call)
        }
        return (
            any(isinstance(node, ast.Raise) for node in proxy_nodes)
            and "_is_escape_hatch_enabled"
            in {
                dotted_name(node.func).rsplit(".", 1)[-1]
                for node in proxy_nodes
                if isinstance(node, ast.Call)
            }
            and "create_validated_connection" in open_calls
            and {"getaddrinfo", "is_blocked_ip", "_assert_safe_peer"}
            <= connection_calls
        )

    summaries: dict[tuple[str, str], PythonNetworkHelperSummary] = {}
    for path in paths:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix.lower() != ".py"
            or set(path.relative_to(root).parts) & SKIP_DIRECTORIES
        ):
            continue
        relative = path.relative_to(root).as_posix()
        parsed = parsed_source(relative)
        if parsed is None:
            continue
        text, tree = parsed
        if not all(
            marker in text
            for marker in (
                "validate_url",
                "allow_redirects",
                "_reject_proxies",
                "_raw_get",
            )
        ):
            continue
        raw_get = unique_function(tree, "_raw_get")
        create_session = unique_function(tree, "create_safe_session")
        reject_proxies = unique_function(tree, "_reject_proxies")
        if (
            raw_get is None
            or create_session is None
            or reject_proxies is None
            or any(
                module_value_rebound(tree, name)
                for name in ("_raw_get", "create_safe_session", "_reject_proxies")
            )
        ):
            continue
        raw_nodes = lexical_nodes(raw_get)
        session_nodes = lexical_nodes(create_session)
        reject_proxy_nodes = lexical_nodes(reject_proxies)
        raw_session_names = {
            target.id
            for assignment in raw_nodes
            if isinstance(assignment, ast.Assign)
            and len(assignment.targets) == 1
            and isinstance((target := assignment.targets[0]), ast.Name)
            and isinstance(assignment.value, ast.Call)
            and dotted_name(assignment.value.func).rsplit(".", 1)[-1]
            == "create_safe_session"
        }
        if len(raw_session_names) != 1:
            continue
        raw_session_name = next(iter(raw_session_names))
        raw_session_mutations = sum(
            raw_session_name in python_assigned_names(target)
            for node in raw_nodes
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
        )
        raw_network_lines = tuple(
            sorted(
                node.lineno
                for node in raw_nodes
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in raw_session_names
            )
        )
        session_names = {
            target.id
            for assignment in session_nodes
            if isinstance(assignment, ast.Assign)
            and len(assignment.targets) == 1
            and isinstance((target := assignment.targets[0]), ast.Name)
            and isinstance(assignment.value, ast.Call)
            and dotted_name(assignment.value.func).rsplit(".", 1)[-1]
            in {"Session", "_SafeSession"}
        }
        adapter_names = {
            target.id
            for assignment in session_nodes
            if isinstance(assignment, ast.Assign)
            and len(assignment.targets) == 1
            and isinstance((target := assignment.targets[0]), ast.Name)
            and isinstance(assignment.value, ast.Call)
            and dotted_name(assignment.value.func).rsplit(".", 1)[-1]
            == "SSRFProtectedAdapter"
        }
        session_mounts = {
            argument.value
            for node in session_nodes
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "mount"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in session_names
            and node.args
            and isinstance((argument := node.args[0]), ast.Constant)
            and isinstance(argument.value, str)
            and len(node.args) > 1
            and isinstance(node.args[1], ast.Name)
            and node.args[1].id in adapter_names
        }
        trust_env_assignments = [
            node
            for node in session_nodes
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Attribute) and target.attr == "trust_env"
                and isinstance(target.value, ast.Name)
                and target.value.id in session_names
                for target in node.targets
            )
        ]
        trust_env_disabled = len(trust_env_assignments) == 1 and (
            isinstance(trust_env_assignments[0].value, ast.Constant)
            and trust_env_assignments[0].value.value is False
        )
        proxy_assignments = [
            node
            for node in session_nodes
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Attribute) and target.attr == "proxies"
                and isinstance(target.value, ast.Name)
                and target.value.id in session_names
                for target in node.targets
            )
        ]
        proxies_disabled = len(proxy_assignments) == 1 and (
            isinstance(proxy_assignments[0].value, ast.Dict)
            and not proxy_assignments[0].value.keys
        )
        rejects_caller_proxies = (
            any(isinstance(node, ast.Raise) for node in reject_proxy_nodes)
            and any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "pop"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "proxies"
                for node in reject_proxy_nodes
            )
            and any(
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value == "proxies"
                    for target in node.targets
                )
                and isinstance(node.value, ast.Dict)
                and not node.value.keys
                for node in reject_proxy_nodes
            )
        )
        if not (
            len(raw_network_lines) == 1
            and raw_session_mutations == 1
            and len(session_names) == 1
            and len(adapter_names) == 1
            and any(
                isinstance(node, ast.Call)
                and dotted_name(node.func).rsplit(".", 1)[-1] == "create_safe_session"
                for node in raw_nodes
            )
            and trust_env_disabled
            and proxies_disabled
            and rejects_caller_proxies
            and {"http://", "https://"} <= session_mounts
            and any(
                isinstance(node, ast.Return)
                and isinstance(node.value, ast.Name)
                and node.value.id in session_names
                for node in session_nodes
            )
        ):
            continue
        validator_import = resolved_import(relative, tree, "validate_url")
        adapter_import = resolved_import(relative, tree, "SSRFProtectedAdapter")
        if validator_import is None or adapter_import is None:
            continue
        environment_names = validate_url_policy(*validator_import)
        if environment_names is None or not validated_transport(*adapter_import):
            continue
        for function in tree.body:
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if module_value_rebound(tree, function.name):
                continue
            positional_args = (*function.args.posonlyargs, *function.args.args)
            if not positional_args:
                continue
            url_name = positional_args[0].arg
            nodes = lexical_nodes(function)
            initial_bindings = {
                target.id
                for assignment in nodes
                if isinstance(assignment, ast.Assign)
                and len(assignment.targets) == 1
                and isinstance((target := assignment.targets[0]), ast.Name)
                and isinstance(assignment.value, ast.Call)
                and dotted_name(assignment.value.func).rsplit(".", 1)[-1]
                == "validate_url"
                and len(assignment.value.args) == 1
                and isinstance(assignment.value.args[0], ast.Name)
                and assignment.value.args[0].id == url_name
            }
            if len(initial_bindings) != 1:
                continue
            validated_name = next(iter(initial_bindings))
            calls = [node for node in nodes if isinstance(node, ast.Call)]
            request_bindings = {
                target.id
                for assignment in nodes
                if isinstance(assignment, ast.Assign)
                and len(assignment.targets) == 1
                and isinstance((target := assignment.targets[0]), ast.Name)
                and isinstance(assignment.value, ast.Dict)
                and any(
                    isinstance(key, ast.Constant)
                    and key.value == "allow_redirects"
                    and isinstance(value, ast.Constant)
                    and value.value is False
                    for key, value in zip(
                        assignment.value.keys,
                        assignment.value.values,
                        strict=True,
                    )
                )
            }
            rejecting_proxy_calls = [
                call
                for call in calls
                if dotted_name(call.func).rsplit(".", 1)[-1] == "_reject_proxies"
            ]
            loop_proofs: list[tuple[int, int]] = []
            for loop in (candidate for candidate in nodes if isinstance(candidate, ast.While)):
                if not isinstance(loop.test, ast.Constant) or loop.test.value is not True:
                    continue
                loop_nodes = lexical_nodes(loop)
                loop_calls = [
                    candidate for candidate in loop_nodes if isinstance(candidate, ast.Call)
                ]
                fetches = [
                    call
                    for call in loop_calls
                    if dotted_name(call.func).rsplit(".", 1)[-1] == "_raw_get"
                    and call.args
                    and isinstance(call.args[0], ast.Name)
                    and call.args[0].id == validated_name
                    and any(
                        keyword.arg is None
                        and isinstance(keyword.value, ast.Name)
                        and keyword.value.id in request_bindings
                        for keyword in call.keywords
                    )
                ]
                redirect_bindings = {
                    target.id: assignment.lineno
                    for assignment in loop_nodes
                    if isinstance(assignment, ast.Assign)
                    and len(assignment.targets) == 1
                    and isinstance((target := assignment.targets[0]), ast.Name)
                    and isinstance(assignment.value, ast.Call)
                    and dotted_name(assignment.value.func).rsplit(".", 1)[-1]
                    == "validate_url"
                    and len(assignment.value.args) == 1
                    and isinstance(assignment.value.args[0], ast.Call)
                    and dotted_name(assignment.value.args[0].func).rsplit(".", 1)[-1]
                    == "urljoin"
                }
                updates = [
                    assignment
                    for assignment in loop_nodes
                    if isinstance(assignment, ast.Assign)
                    and len(assignment.targets) == 1
                    and isinstance(assignment.targets[0], ast.Name)
                    and assignment.targets[0].id == validated_name
                    and isinstance(assignment.value, ast.Name)
                    and assignment.value.id in redirect_bindings
                    and redirect_bindings[assignment.value.id] < assignment.lineno
                ]
                if len(fetches) == 1 and len(redirect_bindings) == 1 and len(updates) == 1:
                    loop_proofs.append((fetches[0].lineno, updates[0].lineno))
            validated_assignments = [
                assignment
                for assignment in nodes
                if isinstance(assignment, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                and validated_name
                in python_assigned_names(
                    assignment.targets[0]
                    if isinstance(assignment, ast.Assign)
                    else assignment.target
                )
            ]
            if (
                len(request_bindings) != 1
                or len(rejecting_proxy_calls) != 1
                or len(loop_proofs) != 1
                or len(validated_assignments) != 2
                or rejecting_proxy_calls[0].lineno >= loop_proofs[0][0]
            ):
                continue
            bypass_environment, force_safe_environment = environment_names
            summaries[(relative, function.name)] = PythonNetworkHelperSummary(
                relative,
                function.name,
                tuple(argument.arg for argument in positional_args),
                tuple(argument.arg for argument in function.args.kwonlyargs),
                (url_name,),
                function.lineno,
                raw_network_lines,
                PythonSecureNetworkPolicy(
                    Evidence(relative, function.lineno, excerpt(text.splitlines(), function.lineno)),
                    ("http", "https"),
                    "each-hop-validated",
                    "connection-pinned",
                    "disabled",
                    "enabled",
                    "configured-opt-out",
                    bypass_environment=bypass_environment,
                    force_safe_environment=force_safe_environment,
                ),
            )
    return summaries


def build_python_proxy_conditional_secure_network_helper_summaries(
    root: Path,
    paths: list[Path],
) -> dict[tuple[str, str], PythonNetworkHelperSummary]:
    """Index URL guards that pin direct sockets but defer DNS to configured proxies."""
    summaries: dict[tuple[str, str], PythonNetworkHelperSummary] = {}
    required_markers = (
        "assert_safe_fetch_target",
        "_PinnedAddressAdapter",
        "_assert_pinned_peer",
        "_proxy_applies",
        "_pinned_request",
        "allow_redirects",
    )

    def unique_function(
        tree: ast.Module, name: str
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        matches = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ]
        return matches[0] if len(matches) == 1 else None

    def unique_method(
        node: ast.ClassDef, name: str
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        matches = [
            child
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and child.name == name
        ]
        return matches[0] if len(matches) == 1 else None

    def short_call_name(node: ast.Call) -> str:
        return dotted_name(node.func).rsplit(".", 1)[-1]

    def calls(node: ast.AST) -> list[ast.Call]:
        return [child for child in ast.walk(node) if isinstance(child, ast.Call)]

    def direct_return_call(
        function: ast.FunctionDef | ast.AsyncFunctionDef, name: str
    ) -> ast.Call | None:
        matches = [
            statement.value
            for statement in function.body
            if isinstance(statement, ast.Return)
            and isinstance(statement.value, ast.Call)
            and short_call_name(statement.value) == name
        ]
        return matches[0] if len(matches) == 1 else None

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
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            if not all(marker in text for marker in required_markers):
                continue
            tree = ast.parse(text, filename=path.relative_to(root).as_posix())
        except (OSError, SyntaxError):
            continue
        relative = path.relative_to(root).as_posix()
        lines = text.splitlines()
        functions = {
            name: unique_function(tree, name)
            for name in (
                "is_blocked_ip",
                "assert_safe_fetch_target",
                "_assert_pinned_peer",
                "_proxy_applies",
                "_pinned_request",
                "safe_get",
                "safe_request",
            )
        }
        if any(function is None for function in functions.values()):
            continue
        rebound_names = {
            name
            for statement in tree.body
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for target in (
                statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            )
            for name in python_assigned_names(target)
        }
        if rebound_names & functions.keys():
            continue

        blocked_ip = functions["is_blocked_ip"]
        validator = functions["assert_safe_fetch_target"]
        peer_guard = functions["_assert_pinned_peer"]
        proxy_guard = functions["_proxy_applies"]
        pinned_request = functions["_pinned_request"]
        safe_get = functions["safe_get"]
        safe_request = functions["safe_request"]
        assert all(
            function is not None
            for function in (
                blocked_ip,
                validator,
                peer_guard,
                proxy_guard,
                pinned_request,
                safe_get,
                safe_request,
            )
        )

        blocked_returns = [
            node
            for node in ast.walk(blocked_ip)
            if isinstance(node, ast.Return) and node.value is not None
        ]
        blocked_policy = (
            any(dotted_name(call.func) == "ipaddress.ip_address" for call in calls(blocked_ip))
            and any(
                isinstance(child, ast.UnaryOp)
                and isinstance(child.op, ast.Not)
                and isinstance(child.operand, ast.Attribute)
                and child.operand.attr == "is_global"
                for node in blocked_returns
                for child in ast.walk(node.value)
            )
        )
        validator_args = (*validator.args.posonlyargs, *validator.args.args)
        if not validator_args:
            continue
        validator_url = validator_args[0].arg
        validator_calls = calls(validator)
        parser_names = {
            alias.asname or alias.name
            for statement in tree.body
            if isinstance(statement, ast.ImportFrom)
            and statement.module == "urllib.parse"
            for alias in statement.names
            if alias.name in {"urlparse", "urlsplit"}
        }
        canonical_url_names = {
            target.id
            for node in ast.walk(validator)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and any(
                dotted_name(call.func) == "requests.Request"
                and any(
                    keyword.arg == "url"
                    and isinstance(keyword.value, ast.Name)
                    and keyword.value.id == validator_url
                    for keyword in call.keywords
                )
                for call in calls(node.value)
            )
        }
        parser_input_names = {validator_url, *canonical_url_names}
        parsed_names = {
            target.id
            for node in ast.walk(validator)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and isinstance(node.value, ast.Call)
            and dotted_name(node.value.func) in parser_names
            and len(node.value.args) == 1
            and isinstance(node.value.args[0], ast.Name)
            and node.value.args[0].id in parser_input_names
        }
        scheme_guard = any(
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Attribute)
            and isinstance(node.left.value, ast.Name)
            and node.left.value.id in parsed_names
            and node.left.attr == "scheme"
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.NotIn)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], (ast.Set, ast.Tuple, ast.List))
            and {
                child.value
                for child in node.comparators[0].elts
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            }
            == {"http", "https"}
            for node in ast.walk(validator)
        )
        blocked_guard = any(
            isinstance(node, ast.If)
            and any(short_call_name(call) == "is_blocked_ip" for call in calls(node.test))
            and python_block_always_terminates(node.body)
            for node in ast.walk(validator)
        )
        returned_addresses = {
            node.value.id
            for node in validator.body
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name)
        }
        resolution_flows_to_return = False
        if len(returned_addresses) == 1:
            returned_name = next(iter(returned_addresses))
            direct_resolution = any(
                (
                    isinstance(node, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == returned_name
                        for target in node.targets
                    )
                    or isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)
                    and node.target.id == returned_name
                )
                and node.value is not None
                and any(
                    dotted_name(call.func) == "socket.getaddrinfo"
                    for call in calls(node.value)
                )
                for node in ast.walk(validator)
                if isinstance(node, (ast.Assign, ast.AnnAssign))
            )
            loop_resolution = any(
                any(
                    dotted_name(call.func) == "socket.getaddrinfo"
                    for call in calls(loop.iter)
                )
                and any(
                    isinstance(call.func, ast.Attribute)
                    and call.func.attr == "append"
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == returned_name
                    for call in calls(loop)
                )
                for loop in ast.walk(validator)
                if isinstance(loop, (ast.For, ast.AsyncFor))
            )
            resolution_flows_to_return = direct_resolution or loop_resolution
        validator_policy = (
            blocked_policy
            and len(parser_names) == 1
            and not parser_names & rebound_names
            and len(parsed_names) == 1
            and scheme_guard
            and blocked_guard
            and any(dotted_name(call.func) == "socket.getaddrinfo" for call in validator_calls)
            and any(short_call_name(call) == "is_blocked_ip" for call in validator_calls)
            and len(returned_addresses) == 1
            and resolution_flows_to_return
        )

        adapters = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "_PinnedAddressAdapter"
        ]
        adapter_method = unique_method(adapters[0], "get_connection_with_tls_context") if len(adapters) == 1 else None
        adapter_policy = False
        if adapter_method is not None:
            adapter_calls = calls(adapter_method)
            dns_values = {
                node.value.id
                for node in ast.walk(adapter_method)
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Attribute) and target.attr == "_dns_host"
                    for target in node.targets
                )
                and isinstance(node.value, ast.Name)
            }
            adapter_policy = (
                {"address", "hostname"} <= dns_values
                and any(short_call_name(call) == "_assert_pinned_peer" for call in adapter_calls)
                and any(
                    isinstance(call.func, ast.Name) and call.func.id == "open_socket"
                    for call in adapter_calls
                )
            )
        peer_policy = (
            any(short_call_name(call) == "getpeername" for call in calls(peer_guard))
            and sum(
                dotted_name(call.func) == "ipaddress.ip_address" for call in calls(peer_guard)
            )
            >= 2
            and any(short_call_name(call) == "close" for call in calls(peer_guard))
            and any(isinstance(node, ast.Raise) for node in ast.walk(peer_guard))
        )
        proxy_policy = (
            any(short_call_name(call) == "get_environ_proxies" for call in calls(proxy_guard))
            and any(short_call_name(call) == "select_proxy" for call in calls(proxy_guard))
            and any(
                isinstance(handler, ast.ExceptHandler)
                and any(
                    isinstance(statement, ast.Return)
                    and isinstance(statement.value, ast.Constant)
                    and statement.value.value is True
                    for statement in handler.body
                )
                for handler in ast.walk(proxy_guard)
            )
        )

        pinned_args = (*pinned_request.args.posonlyargs, *pinned_request.args.args)
        if len(pinned_args) < 2:
            continue
        method_name, url_name = pinned_args[0].arg, pinned_args[1].arg
        addresses = {
            target.id
            for node in pinned_request.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and isinstance(node.value, ast.Call)
            and short_call_name(node.value) == "assert_safe_fetch_target"
            and len(node.value.args) == 1
            and isinstance(node.value.args[0], ast.Name)
            and node.value.args[0].id == url_name
        }
        sessions = {
            target.id
            for node in pinned_request.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and isinstance(node.value, ast.Call)
            and short_call_name(node.value) == "Session"
        }
        proxy_branches = [
            node
            for node in pinned_request.body
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.UnaryOp)
            and isinstance(node.test.op, ast.Not)
            and isinstance(node.test.operand, ast.Call)
            and short_call_name(node.test.operand) == "_proxy_applies"
            and len(node.test.operand.args) == 2
            and isinstance(node.test.operand.args[0], ast.Name)
            and node.test.operand.args[0].id == url_name
            and isinstance(node.test.operand.args[1], ast.Call)
            and isinstance(node.test.operand.args[1].func, ast.Attribute)
            and node.test.operand.args[1].func.attr == "get"
            and isinstance(node.test.operand.args[1].func.value, ast.Name)
            and pinned_request.args.kwarg is not None
            and node.test.operand.args[1].func.value.id
            == pinned_request.args.kwarg.arg
            and node.test.operand.args[1].args
            and isinstance(node.test.operand.args[1].args[0], ast.Constant)
            and node.test.operand.args[1].args[0].value == "proxies"
        ]
        mounts: set[str] = set()
        branch_adapter_names: set[str] = set()
        if len(proxy_branches) == 1 and len(addresses) == 1 and len(sessions) == 1:
            address_name = next(iter(addresses))
            session_name = next(iter(sessions))
            branch_adapter_names = {
                target.id
                for node in proxy_branches[0].body
                if isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance((target := node.targets[0]), ast.Name)
                and isinstance(node.value, ast.Call)
                and short_call_name(node.value) == "_PinnedAddressAdapter"
                and len(node.value.args) == 1
                and isinstance(node.value.args[0], ast.Name)
                and node.value.args[0].id == address_name
            }
            mounts = {
                call.args[0].value
                for call in calls(proxy_branches[0])
                if isinstance(call.func, ast.Attribute)
                and call.func.attr == "mount"
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == session_name
                and len(call.args) > 1
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
                and isinstance(call.args[1], ast.Name)
                and call.args[1].id in branch_adapter_names
            }
        request_calls = [
            call
            for call in calls(pinned_request)
            if isinstance(call.func, ast.Attribute)
            and call.func.attr == "request"
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id in sessions
            and len(call.args) >= 2
            and isinstance(call.args[0], ast.Name)
            and call.args[0].id == method_name
            and isinstance(call.args[1], ast.Name)
            and call.args[1].id == url_name
            and any(
                keyword.arg == "allow_redirects"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is False
                for keyword in call.keywords
            )
        ]
        transport_policy = (
            validator_policy
            and adapter_policy
            and peer_policy
            and proxy_policy
            and len(addresses) == 1
            and len(sessions) == 1
            and len(proxy_branches) == 1
            and len(branch_adapter_names) == 1
            and {"http://", "https://"} <= mounts
            and len(request_calls) == 1
        )
        if not transport_policy:
            continue

        get_args = (*safe_get.args.posonlyargs, *safe_get.args.args)
        get_call = direct_return_call(safe_get, "_pinned_request")
        get_proven = (
            bool(get_args)
            and get_call is not None
            and len(get_call.args) >= 2
            and isinstance(get_call.args[0], ast.Constant)
            and get_call.args[0].value == "GET"
            and isinstance(get_call.args[1], ast.Name)
            and get_call.args[1].id == get_args[0].arg
        )

        request_args = (*safe_request.args.posonlyargs, *safe_request.args.args)
        current_names = {
            target.id
            for node in safe_request.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and isinstance(node.value, ast.Name)
            and len(request_args) >= 2
            and node.value.id == request_args[1].arg
        }
        redirect_loops = [node for node in safe_request.body if isinstance(node, ast.For)]
        redirect_proven = False
        if len(redirect_loops) == 1 and len(current_names) == 1 and len(request_args) >= 2:
            current_name = next(iter(current_names))
            loop = redirect_loops[0]
            redirect_limit_names = {
                argument.arg for argument in safe_request.args.kwonlyargs
            }
            bounded_loop = (
                isinstance(loop.iter, ast.Call)
                and isinstance(loop.iter.func, ast.Name)
                and loop.iter.func.id == "range"
                and len(loop.iter.args) == 1
                and isinstance(loop.iter.args[0], ast.BinOp)
                and isinstance(loop.iter.args[0].op, ast.Add)
                and isinstance(loop.iter.args[0].left, ast.Name)
                and loop.iter.args[0].left.id in redirect_limit_names
                and isinstance(loop.iter.args[0].right, ast.Constant)
                and loop.iter.args[0].right.value == 1
            )
            loop_calls = calls(loop)
            pinned_calls = [
                call
                for call in loop_calls
                if short_call_name(call) == "_pinned_request"
                and len(call.args) >= 2
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == request_args[0].arg
                and isinstance(call.args[1], ast.Name)
                and call.args[1].id == current_name
            ]
            redirect_updates = [
                node
                for node in ast.walk(loop)
                if isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == current_name
                and isinstance(node.value, ast.Call)
                and short_call_name(node.value) == "urljoin"
                and node.value.args
                and isinstance(node.value.args[0], ast.Name)
                and node.value.args[0].id == current_name
            ]
            redirect_proven = (
                bounded_loop
                and len(pinned_calls) == 1
                and len(redirect_updates) == 1
                and any(isinstance(node, ast.Return) for node in ast.walk(loop))
                and any(isinstance(node, ast.Raise) for node in safe_request.body)
            )

        shared_policy = {
            "dns_scope": "connection-pinned-unless-proxied",
            "proxy_scope": "environment-or-caller-dependent",
            "enforcement_default": "enabled",
            "escape_hatch": "none",
            "policy_effect": "restricts-http-origin-and-conditionally-pins-peer",
        }
        if get_proven:
            summaries[(relative, safe_get.name)] = PythonNetworkHelperSummary(
                relative,
                safe_get.name,
                tuple(argument.arg for argument in get_args),
                tuple(argument.arg for argument in safe_get.args.kwonlyargs),
                (get_args[0].arg,),
                safe_get.lineno,
                (request_calls[0].lineno,),
                PythonSecureNetworkPolicy(
                    Evidence(relative, safe_get.lineno, excerpt(lines, safe_get.lineno)),
                    ("http", "https"),
                    "disabled",
                    **shared_policy,
                ),
            )
        if redirect_proven:
            summaries[(relative, safe_request.name)] = PythonNetworkHelperSummary(
                relative,
                safe_request.name,
                tuple(argument.arg for argument in request_args),
                tuple(argument.arg for argument in safe_request.args.kwonlyargs),
                (request_args[1].arg,),
                safe_request.lineno,
                (request_calls[0].lineno,),
                PythonSecureNetworkPolicy(
                    Evidence(
                        relative,
                        safe_request.lineno,
                        excerpt(lines, safe_request.lineno),
                    ),
                    ("http", "https"),
                    "each-hop-validated",
                    **shared_policy,
                ),
            )
    return summaries


def build_python_configurable_pinned_network_helper_summaries(
    root: Path,
    paths: list[Path],
    module_paths: dict[str, str],
) -> dict[tuple[str, str], PythonNetworkHelperSummary]:
    """Index default-on connector guards whose disabled state is an explicit no-op."""
    selected = {path.relative_to(root).as_posix(): path for path in paths if path.is_file()}
    parsed: dict[str, tuple[str, ast.Module]] = {}

    def parse(relative: str) -> tuple[str, ast.Module] | None:
        if relative not in selected:
            return None
        if relative in parsed:
            return parsed[relative]
        try:
            text = selected[relative].read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text, filename=relative)
        except (OSError, SyntaxError):
            return None
        parsed[relative] = (text, tree)
        return parsed[relative]

    def unique_function(
        tree: ast.Module, name: str
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        matches = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ]
        return matches[0] if len(matches) == 1 else None

    def short_name(call: ast.Call) -> str:
        return dotted_name(call.func).rsplit(".", 1)[-1]

    def calls(node: ast.AST) -> list[ast.Call]:
        return [child for child in ast.walk(node) if isinstance(child, ast.Call)]

    def call_names(node: ast.AST) -> set[str]:
        return {short_name(call) for call in calls(node)}

    def string_constants(node: ast.AST) -> set[str]:
        return {
            child.value
            for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        }

    def has_empty_ip_return(node: ast.AST) -> bool:
        return any(
            isinstance(child, ast.Return)
            and isinstance(child.value, ast.Tuple)
            and len(child.value.elts) == 2
            and isinstance(child.value.elts[1], ast.List)
            and not child.value.elts[1].elts
            for child in ast.walk(node)
        )

    def imported_path(relative: str, tree: ast.Module, local_name: str) -> str | None:
        matches = []
        for statement in tree.body:
            if not isinstance(statement, ast.ImportFrom):
                continue
            for alias in statement.names:
                if (alias.asname or alias.name) != local_name:
                    continue
                target = resolve_python_import_path(
                    root, relative, statement, alias.name, module_paths
                )
                if target is not None:
                    matches.append(target)
        return matches[0] if len(matches) == 1 else None

    settings_defaults = False
    for relative in selected:
        if not relative.endswith("/settings/groups/security.py"):
            continue
        source = parse(relative)
        if source is None:
            continue
        _, settings_tree = source
        defaults = {
            node.target.id
            for node in ast.walk(settings_tree)
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, ast.Constant)
            and node.value.value is True
        }
        settings_defaults = {
            "ssrf_protection_enabled",
            "connector_ssrf_validation_enabled",
            "connector_ssrf_allow_loopback",
        } <= defaults
        if settings_defaults:
            break
    if not settings_defaults:
        return {}

    summaries: dict[tuple[str, str], PythonNetworkHelperSummary] = {}
    for relative in sorted(selected):
        source = parse(relative)
        if source is None:
            continue
        text, tree = source
        if not all(
            marker in text
            for marker in (
                "validate_and_resolve_connector_url",
                "_async_client_for_url",
                "_sync_client_for_url",
                "ssrf_safe_httpx_get",
            )
        ):
            continue
        protection_path = imported_path(
            relative, tree, "validate_and_resolve_connector_url"
        )
        async_transport_path = imported_path(relative, tree, "SSRFProtectedTransport")
        sync_transport_path = imported_path(relative, tree, "SSRFProtectedSyncTransport")
        if (
            protection_path is None
            or async_transport_path is None
            or sync_transport_path is None
            or async_transport_path != sync_transport_path
        ):
            continue
        protection_source = parse(protection_path)
        transport_source = parse(async_transport_path)
        if protection_source is None or transport_source is None:
            continue
        _, protection_tree = protection_source
        _, transport_tree = transport_source

        global_gate = unique_function(protection_tree, "is_ssrf_protection_enabled")
        connector_gate = unique_function(
            protection_tree, "is_connector_ssrf_validation_enabled"
        )
        loopback_gate = unique_function(
            protection_tree, "is_connector_loopback_allowed"
        )
        loopback_exemption = unique_function(
            protection_tree, "_connector_url_has_loopback_exemption"
        )
        allowed_hosts = unique_function(protection_tree, "get_allowed_hosts")
        host_allowed = unique_function(protection_tree, "is_host_allowed")
        connector_validator = unique_function(
            protection_tree, "validate_and_resolve_connector_url"
        )
        core_validator = unique_function(protection_tree, "validate_and_resolve_url")
        if None in {
            global_gate,
            connector_gate,
            loopback_gate,
            loopback_exemption,
            allowed_hosts,
            host_allowed,
            connector_validator,
            core_validator,
        }:
            continue
        assert global_gate is not None
        assert connector_gate is not None
        assert loopback_gate is not None
        assert loopback_exemption is not None
        assert allowed_hosts is not None
        assert host_allowed is not None
        assert connector_validator is not None
        assert core_validator is not None
        gate_policy = (
            "LANGFLOW_SSRF_PROTECTION_ENABLED" in string_constants(global_gate)
            and "getenv" in call_names(global_gate)
            and "get_settings_service" in call_names(global_gate)
            and "LANGFLOW_CONNECTOR_SSRF_VALIDATION_ENABLED"
            in string_constants(connector_gate)
            and "getenv" in call_names(connector_gate)
            and "get_settings_service" in call_names(connector_gate)
        )
        loopback_policy = (
            "LANGFLOW_CONNECTOR_SSRF_ALLOW_LOOPBACK" in string_constants(loopback_gate)
            and "getenv" in call_names(loopback_gate)
            and "get_settings_service" in call_names(loopback_gate)
            and {
                "is_ssrf_protection_enabled",
                "_validate_raw_url_authority",
                "urlparse",
                "is_connector_loopback_allowed",
                "_is_loopback_host",
            }
            <= call_names(loopback_exemption)
            and any(isinstance(node, ast.Raise) for node in ast.walk(loopback_exemption))
        )
        allowlist_policy = (
            "LANGFLOW_SSRF_ALLOWED_HOSTS" in string_constants(allowed_hosts)
            and "getenv" in call_names(allowed_hosts)
            and "get_settings_service" in call_names(allowed_hosts)
            and "get_allowed_hosts" in call_names(host_allowed)
        )
        connector_policy = {
            "is_connector_ssrf_validation_enabled",
            "_connector_url_has_loopback_exemption",
            "validate_and_resolve_url",
        } <= call_names(connector_validator) and has_empty_ip_return(connector_validator)
        core_names = call_names(core_validator)
        core_policy = (
            {
                "is_ssrf_protection_enabled",
                "urlparse",
                "_validate_url_scheme",
                "_validate_hostname_exists",
                "is_host_allowed",
                "resolve_hostname",
                "is_ip_blocked",
            }
            <= core_names
            and has_empty_ip_return(core_validator)
            and any(isinstance(node, ast.Raise) for node in ast.walk(core_validator))
            and any(
                isinstance(node, ast.Return)
                and isinstance(node.value, ast.Tuple)
                and any(
                    isinstance(child, ast.Name) and child.id == "resolved_ips"
                    for child in node.value.elts
                )
                for node in ast.walk(core_validator)
            )
        )

        classes = {
            node.name: node for node in transport_tree.body if isinstance(node, ast.ClassDef)
        }
        backend_policy = True
        for class_name in ("DNSPinningNetworkBackend", "DNSPinningSyncNetworkBackend"):
            backend = classes.get(class_name)
            if backend is None or not any(
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "connect_tcp"
                and any(
                    keyword.arg == "host"
                    and isinstance(keyword.value, ast.Name)
                    and keyword.value.id == "pinned_ip"
                    for keyword in call.keywords
                )
                for call in calls(backend)
            ):
                backend_policy = False
        transport_policy = backend_policy
        for class_name in ("SSRFProtectedTransport", "SSRFProtectedSyncTransport"):
            transport = classes.get(class_name)
            if transport is None:
                transport_policy = False
                continue
            transport_calls = calls(transport)
            transport_policy = transport_policy and (
                any(short_name(call) in {"ConnectionPool", "AsyncConnectionPool"} for call in transport_calls)
                and any(
                    keyword.arg == "network_backend"
                    and isinstance(keyword.value, ast.Name)
                    and keyword.value.id == "network_backend"
                    for call in transport_calls
                    for keyword in call.keywords
                )
                and any(
                    isinstance(node, ast.Raise)
                    and isinstance(node.exc, ast.Call)
                    and short_name(node.exc) == "NotImplementedError"
                    for node in ast.walk(transport)
                )
            )
        creators_proven = all(
            (creator := unique_function(transport_tree, name)) is not None
            and expected in call_names(creator)
            and transport_name in call_names(creator)
            for name, expected, transport_name in (
                ("create_ssrf_protected_client", "AsyncClient", "SSRFProtectedTransport"),
                ("create_ssrf_protected_sync_client", "Client", "SSRFProtectedSyncTransport"),
            )
        )
        async_factory = unique_function(tree, "_async_client_for_url")
        sync_factory = unique_function(tree, "_sync_client_for_url")
        factories_proven = all(
            factory is not None
            and "is_ssrf_protection_enabled" in call_names(factory)
            and protected in call_names(factory)
            and fallback in call_names(factory)
            for factory, protected, fallback in (
                (async_factory, "create_ssrf_protected_client", "AsyncClient"),
                (sync_factory, "create_ssrf_protected_sync_client", "Client"),
            )
        )
        if not (
            gate_policy
            and loopback_policy
            and allowlist_policy
            and connector_policy
            and core_policy
            and transport_policy
            and creators_proven
            and factories_proven
        ):
            continue

        helper_specs = {
            "ssrf_safe_async_get": ("get", "disabled"),
            "ssrf_safe_async_post": ("post", "disabled"),
            "ssrf_safe_httpx_get": (
                "get",
                "disabled-default-each-hop-validated-when-enabled",
            ),
            "ssrf_safe_httpx_post": ("post", "disabled"),
        }
        for name, (method, redirect_scope) in helper_specs.items():
            function = unique_function(tree, name)
            if function is None:
                continue
            positional = (*function.args.posonlyargs, *function.args.args)
            if not positional or "validate_and_resolve_connector_url" not in call_names(function):
                continue
            network_calls = [
                call
                for call in calls(function)
                if isinstance(call.func, ast.Attribute)
                and call.func.attr == method
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "client"
            ]
            if len(network_calls) != 1:
                continue
            if name == "ssrf_safe_httpx_get":
                bounded = any(
                    isinstance(loop, ast.For)
                    and isinstance(loop.iter, ast.Call)
                    and short_name(loop.iter) == "range"
                    and any(short_name(call) == "urljoin" for call in calls(loop))
                    for loop in function.body
                )
                redirects_disabled = any(
                    keyword.arg == "follow_redirects"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False
                    for keyword in network_calls[0].keywords
                )
                if not (bounded and redirects_disabled):
                    continue
            elif "_raise_if_following_redirects" not in call_names(function):
                continue
            policy = PythonSecureNetworkPolicy(
                Evidence(relative, function.lineno, excerpt(text.splitlines(), function.lineno)),
                ("http", "https"),
                redirect_scope,
                "connection-pinned-when-enforced",
                "disabled-when-enforced",
                "enabled",
                "configured-opt-out",
                policy_effect="restricts-http-origin-and-pins-peer-when-enforced",
                initial_origin_scope=(
                    "public-addresses-with-configured-allowlist-and-loopback-exemption"
                ),
                bypass_environments=(
                    "LANGFLOW_SSRF_PROTECTION_ENABLED",
                    "LANGFLOW_CONNECTOR_SSRF_VALIDATION_ENABLED",
                ),
            )
            summaries[(relative, name)] = PythonNetworkHelperSummary(
                relative,
                name,
                tuple(argument.arg for argument in positional),
                tuple(argument.arg for argument in function.args.kwonlyargs),
                (positional[0].arg,),
                function.lineno,
                (network_calls[0].lineno,),
                policy,
            )
    return summaries


def build_python_network_helper_summaries(
    root: Path,
    paths: list[Path],
) -> dict[tuple[str, str], PythonNetworkHelperSummary]:
    """Index unique top-level functions whose parameters directly control HTTP origins."""
    summaries: dict[tuple[str, str], PythonNetworkHelperSummary] = {}
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
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        if not any(name in text for name in ("requests", "httpx", "aiohttp")):
            continue
        relative = path.relative_to(root).as_posix()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(text, filename=relative)
        except SyntaxError:
            continue
        function_counts = Counter(
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        module_clients = {
            alias.asname or alias.name.split(".", 1)[0]
            for node in tree.body
            if isinstance(node, ast.Import)
            for alias in node.names
            if alias.name in {"requests", "httpx", "aiohttp"}
        }
        imported_methods = {
            alias.asname or alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module in {"requests", "httpx", "aiohttp"}
            for alias in node.names
            if alias.name.lower() in {"get", "post", "put", "patch", "delete", "request"}
        }
        mutated_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        } | {
            target.id
            for statement in tree.body
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for target in (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            if isinstance(target, ast.Name)
        } | {
            target.id
            for statement in tree.body
            if isinstance(statement, ast.Delete)
            for target in statement.targets
            if isinstance(target, ast.Name)
        }
        module_clients -= mutated_names
        imported_methods -= mutated_names
        if not module_clients and not imported_methods:
            continue
        assignment_counts = Counter(
            target.id
            for statement in tree.body
            if isinstance(statement, (ast.Assign, ast.AnnAssign))
            for target in (
                statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            )
            if isinstance(target, ast.Name)
        )
        static_prefixes: dict[str, str] = {}
        for statement in tree.body:
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                continue
            name = targets[0].id
            if assignment_counts[name] != 1:
                continue
            if prefix := python_static_url_prefix(statement.value, static_prefixes):
                static_prefixes[name] = prefix

        parent_by_id = {
            id(child): parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }

        def enclosing_function(
            candidate: ast.AST,
            parents: dict[int, ast.AST] = parent_by_id,
        ) -> ast.AST | None:
            parent = parents.get(id(candidate))
            while parent is not None:
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    return parent
                parent = parents.get(id(parent))
            return None

        for function in tree.body:
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if function_counts[function.name] != 1:
                continue
            positional = tuple(
                argument.arg for argument in (*function.args.posonlyargs, *function.args.args)
            )
            keyword_only = tuple(argument.arg for argument in function.args.kwonlyargs)
            parameters = set(positional) | set(keyword_only)
            local_bindings = python_function_local_bindings(function)
            function_clients = module_clients - local_bindings
            function_methods = imported_methods - local_bindings
            controlled: set[str] = set()
            network_lines: list[int] = []
            for call in ast.walk(function):
                if not isinstance(call, ast.Call) or enclosing_function(call) is not function:
                    continue
                call_name = dotted_name(call.func)
                root_name = call_name.split(".", 1)[0]
                short_name = call_name.rsplit(".", 1)[-1].lower()
                if short_name not in {"get", "post", "put", "patch", "delete", "request"}:
                    continue
                if not (
                    root_name in function_clients
                    or (isinstance(call.func, ast.Name) and call.func.id in function_methods)
                ):
                    continue
                url_expression: ast.AST | None = None
                if short_name == "request":
                    if len(call.args) > 1:
                        url_expression = call.args[1]
                elif call.args:
                    url_expression = call.args[0]
                for keyword in call.keywords:
                    if keyword.arg == "url":
                        url_expression = keyword.value
                if url_expression is None:
                    continue
                network_lines.append(call.lineno)
                for parameter in parameters:
                    if python_http_origin_is_dynamic(
                        url_expression,
                        {parameter},
                        static_prefixes,
                    ):
                        controlled.add(parameter)
            if network_lines:
                summaries[(relative, function.name)] = PythonNetworkHelperSummary(
                    relative,
                    function.name,
                    positional,
                    keyword_only,
                    tuple(sorted(controlled)),
                    function.lineno,
                    tuple(sorted(network_lines)),
                )
    return summaries


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

    def returned_nested_function(
        container: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        returns = [statement for statement in container.body if isinstance(statement, ast.Return)]
        if len(returns) != 1 or returns[0] is not container.body[-1]:
            return None
        returned = returns[0].value
        if not isinstance(returned, ast.Name):
            return None
        matches = [
            statement
            for statement in container.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            and statement.name == returned.id
        ]
        return matches[0] if len(matches) == 1 else None

    def wrapper_forwarded_parameter(
        path: str,
        container: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str | None:
        if container.decorator_list or any(
            isinstance(candidate, (ast.Yield, ast.YieldFrom))
            for candidate in ast.walk(container)
        ):
            return None
        wrapper = returned_nested_function(container)
        if wrapper is None or wrapper.args.vararg is None or wrapper.args.kwarg is None:
            return None
        tree = parsed[path][0]
        direct_imports = [
            statement
            for statement in tree.body
            if isinstance(statement, (ast.Import, ast.ImportFrom))
        ]
        functools_modules = {
            alias.asname or alias.name.split(".", 1)[0]
            for statement in direct_imports
            if isinstance(statement, ast.Import)
            for alias in statement.names
            if alias.name == "functools"
            and binding_counts[path][alias.asname or alias.name] == 1
        }
        wraps_names = {
            alias.asname or alias.name
            for statement in direct_imports
            if isinstance(statement, ast.ImportFrom)
            and statement.module == "functools"
            for alias in statement.names
            if alias.name == "wraps"
            and binding_counts[path][alias.asname or alias.name] == 1
        }
        positional = [*container.args.posonlyargs, *container.args.args]
        candidates = []
        for parameter in positional:
            expected_decorators = {
                f"{module}.wraps" for module in functools_modules
            } | wraps_names
            if not (
                len(wrapper.decorator_list) == 1
                and isinstance(wrapper.decorator_list[0], ast.Call)
                and dotted_name(wrapper.decorator_list[0].func) in expected_decorators
                and len(wrapper.decorator_list[0].args) == 1
                and not wrapper.decorator_list[0].keywords
                and isinstance(wrapper.decorator_list[0].args[0], ast.Name)
                and wrapper.decorator_list[0].args[0].id == parameter.arg
            ):
                continue
            if any(
                isinstance(candidate, ast.Name)
                and candidate.id == parameter.arg
                and isinstance(candidate.ctx, (ast.Store, ast.Del))
                for statement in container.body
                for candidate in ast.walk(statement)
            ):
                continue
            forwarded = False
            for statement in wrapper.body:
                if isinstance(statement, ast.Raise):
                    break
                value: ast.AST | None = None
                if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Return)):
                    value = statement.value
                if isinstance(value, ast.Await):
                    value = value.value
                if not isinstance(value, ast.Call):
                    if isinstance(statement, ast.Return):
                        break
                    continue
                if (
                    isinstance(value.func, ast.Name)
                    and value.func.id == parameter.arg
                    and len(value.args) == 1
                    and isinstance(value.args[0], ast.Starred)
                    and isinstance(value.args[0].value, ast.Name)
                    and value.args[0].value.id == wrapper.args.vararg.arg
                    and len(value.keywords) == 1
                    and value.keywords[0].arg is None
                    and isinstance(value.keywords[0].value, ast.Name)
                    and value.keywords[0].value.id == wrapper.args.kwarg.arg
                ):
                    forwarded = True
                    break
                if isinstance(statement, ast.Return):
                    break
            if forwarded:
                candidates.append(parameter.arg)
        return candidates[0] if len(candidates) == 1 else None

    transparent_wrappers: dict[tuple[str, str], int] = {}
    for key, definition in definitions.items():
        path, _ = key
        if wrapper_forwarded_parameter(path, definition) is not None:
            transparent_wrappers[key] = 1
            continue
        decorator = returned_nested_function(definition)
        if decorator and wrapper_forwarded_parameter(path, decorator) is not None:
            transparent_wrappers[key] = 2

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
            if len(outer.args) != 1 or outer.keywords:
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

            def resolve_name(
                name: str,
                imported_bindings: dict[
                    str, list[tuple[str, str, int]]
                ] = imported_targets,
                current_path: str = path,
                before_line: int = statement.lineno,
            ) -> tuple[tuple[str, str], str] | None:
                imported = imported_bindings.get(name, [])
                if len(imported) == 1 and imported[0][2] < before_line:
                    return (
                        (imported[0][0], imported[0][1]),
                        "relative-import-single-definition",
                    )
                if (
                    (current_path, name) in definitions
                    and definitions[(current_path, name)].lineno < before_line
                ):
                    return (current_path, name), "same-module-single-definition"
                return None

            def resolve_registered_target(
                expression: ast.AST,
                depth: int = 0,
            ) -> tuple[tuple[str, str], str, tuple[str, ...]] | None:
                if depth > 4:
                    return None
                if isinstance(expression, ast.Name):
                    resolved = resolve_name(expression.id)
                    return (*resolved, ()) if resolved else None
                if not isinstance(expression, ast.Call) or expression.keywords:
                    return None
                wrapper_name: str | None = None
                expected_depth = 0
                if isinstance(expression.func, ast.Name):
                    wrapper_name = expression.func.id
                    expected_depth = 1
                elif (
                    isinstance(expression.func, ast.Call)
                    and isinstance(expression.func.func, ast.Name)
                ):
                    wrapper_name = expression.func.func.id
                    expected_depth = 2
                if wrapper_name is None or len(expression.args) != 1:
                    return None
                resolved_wrapper = resolve_name(wrapper_name)
                if resolved_wrapper is None:
                    return None
                wrapper_key = resolved_wrapper[0]
                if transparent_wrappers.get(wrapper_key) != expected_depth:
                    return None
                resolved_target = resolve_registered_target(
                    expression.args[0], depth + 1
                )
                if resolved_target is None:
                    return None
                target, resolution, wrappers = resolved_target
                return target, resolution, (wrapper_name, *wrappers)

            resolved_target = resolve_registered_target(outer.args[0])
            if resolved_target is None:
                continue
            target, resolution, wrappers = resolved_target
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
                    wrappers,
                )
            )

    return {
        target: registrations[0]
        for target, registrations in proposals.items()
        if len(registrations) == 1
    }


def propagate_python_class_network_helpers(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
    module_paths: dict[str, str],
) -> None:
    """Propagate dynamic network behavior through exact registered-class calls."""
    parsed: dict[str, tuple[ast.Module, list[str]]] = {}
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
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(text, filename=relative)
        except SyntaxError:
            continue
        parsed[relative] = (tree, text.splitlines())

    class_nodes: dict[tuple[str, str, int], ast.ClassDef] = {}
    method_nodes: dict[tuple[str, str, str], ast.FunctionDef | ast.AsyncFunctionDef] = {}
    module_imports: dict[str, dict[str, tuple[str, str]]] = {}
    module_prefixes: dict[str, dict[str, str]] = {}
    for relative, (tree, _) in parsed.items():
        mutations = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        } | {
            target.id
            for statement in tree.body
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for target in (
                statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            )
            if isinstance(target, ast.Name)
        } | {
            target.id
            for statement in tree.body
            if isinstance(statement, ast.Delete)
            for target in statement.targets
            if isinstance(target, ast.Name)
        }
        imports: dict[str, tuple[str, str]] = {}
        for statement in tree.body:
            if not isinstance(statement, ast.ImportFrom):
                continue
            for alias in statement.names:
                local_name = alias.asname or alias.name
                if local_name in mutations:
                    continue
                if target_path := resolve_python_import_path(
                    root,
                    relative,
                    statement,
                    alias.name,
                    module_paths,
                ):
                    imports[local_name] = (target_path, alias.name)
        module_imports[relative] = imports
        assignment_counts = Counter(
            target.id
            for statement in tree.body
            if isinstance(statement, (ast.Assign, ast.AnnAssign))
            for target in (
                statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            )
            if isinstance(target, ast.Name)
        )
        prefixes: dict[str, str] = {}
        for statement in tree.body:
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                continue
            name = targets[0].id
            if assignment_counts[name] == 1 and (
                prefix := python_static_url_prefix(statement.value, prefixes)
            ):
                prefixes[name] = prefix
        module_prefixes[relative] = prefixes
        class_counts = Counter(
            node.name for node in tree.body if isinstance(node, ast.ClassDef)
        )
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if class_counts[node.name] != 1:
                continue
            class_nodes[(relative, node.name, node.lineno)] = node
            for statement in node.body:
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_nodes[(relative, node.name, statement.name)] = statement

    def call_states(
        method: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> dict[int, set[str]]:
        states: dict[int, set[str]] = {}
        initial = {
            argument.arg
            for argument in (
                *method.args.posonlyargs,
                *method.args.args,
                *method.args.kwonlyargs,
            )
            if argument.arg not in {"self", "cls"}
        }
        if method.args.vararg:
            initial.add(method.args.vararg.arg)
        if method.args.kwarg:
            initial.add(method.args.kwarg.arg)

        class CallRecorder(ast.NodeVisitor):
            def __init__(self, dynamic: set[str]) -> None:
                self.dynamic = dynamic

            def visit_Call(self, node: ast.Call) -> None:
                states[id(node)] = set(self.dynamic)
                self.generic_visit(node)

            def visit_Lambda(self, node: ast.Lambda) -> None:
                return

        def target_names(target: ast.AST) -> set[str]:
            return {
                candidate.id
                for candidate in ast.walk(target)
                if isinstance(candidate, ast.Name) and isinstance(candidate.ctx, ast.Store)
            }

        def record(expression: ast.AST | None, dynamic: set[str]) -> None:
            if expression is not None:
                CallRecorder(dynamic).visit(expression)

        def update_target(target: ast.AST, value: ast.AST | None, dynamic: set[str]) -> None:
            names = target_names(target)
            if python_expression_names(value) & dynamic:
                dynamic.update(names)
            else:
                dynamic.difference_update(names)

        def analyze_block(statements: list[ast.stmt], dynamic: set[str]) -> set[str]:
            for statement in statements:
                if isinstance(statement, ast.Assign):
                    record(statement.value, dynamic)
                    for target in statement.targets:
                        update_target(target, statement.value, dynamic)
                elif isinstance(statement, ast.AnnAssign):
                    record(statement.value, dynamic)
                    update_target(statement.target, statement.value, dynamic)
                elif isinstance(statement, ast.AugAssign):
                    record(statement.value, dynamic)
                    if python_expression_names(statement.value) & dynamic:
                        dynamic.update(target_names(statement.target))
                elif isinstance(statement, (ast.For, ast.AsyncFor)):
                    record(statement.iter, dynamic)
                    loop_state = set(dynamic)
                    update_target(statement.target, statement.iter, loop_state)
                    analyze_block(statement.body, loop_state)
                    else_state = analyze_block(statement.orelse, set(dynamic))
                    dynamic.update(loop_state | else_state)
                elif isinstance(statement, ast.If):
                    record(statement.test, dynamic)
                    body_state = analyze_block(statement.body, set(dynamic))
                    else_state = analyze_block(statement.orelse, set(dynamic))
                    dynamic.clear()
                    dynamic.update(body_state | else_state)
                elif isinstance(statement, (ast.With, ast.AsyncWith)):
                    for item in statement.items:
                        record(item.context_expr, dynamic)
                    analyze_block(statement.body, dynamic)
                elif isinstance(statement, ast.Try):
                    branches = [analyze_block(statement.body, set(dynamic))]
                    branches.extend(
                        analyze_block(handler.body, set(dynamic)) for handler in statement.handlers
                    )
                    branches.append(analyze_block(statement.orelse, set(dynamic)))
                    merged = set().union(*branches)
                    analyze_block(statement.finalbody, merged)
                    dynamic.clear()
                    dynamic.update(merged)
                elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    dynamic.discard(statement.name)
                else:
                    for child in ast.iter_child_nodes(statement):
                        if isinstance(child, ast.expr):
                            record(child, dynamic)
            return dynamic

        analyze_block(method.body, set(initial))
        return states

    def class_bindings(
        class_node: ast.ClassDef,
        imports: dict[str, tuple[str, str]],
    ) -> dict[str, tuple[str, str]]:
        assignments: dict[str, list[tuple[str, ast.AST | None]]] = defaultdict(list)
        parents = {
            id(child): parent
            for parent in ast.walk(class_node)
            for child in ast.iter_child_nodes(parent)
        }

        def enclosing_function(candidate: ast.AST) -> ast.AST | None:
            parent = parents.get(id(candidate))
            while parent is not None:
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    return parent
                parent = parents.get(id(parent))
            return None

        for method in class_node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for candidate in ast.walk(method):
                if enclosing_function(candidate) is not method:
                    continue
                targets: list[ast.AST] = []
                value: ast.AST | None = None
                if isinstance(candidate, ast.Assign):
                    targets.extend(candidate.targets)
                    value = candidate.value
                elif isinstance(candidate, (ast.AnnAssign, ast.AugAssign)):
                    targets.append(candidate.target)
                    value = candidate.value
                elif isinstance(candidate, ast.Delete):
                    targets.extend(candidate.targets)
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
        resolved: dict[str, tuple[str, str]] = {}
        for attribute, observations in assignments.items():
            if len(observations) != 1 or observations[0][0] != "__init__":
                continue
            value = observations[0][1]
            if not (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id in imports
            ):
                continue
            init_methods = [
                method
                for method in class_node.body
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                and method.name == "__init__"
            ]
            if len(init_methods) != 1 or value.func.id in python_function_local_bindings(
                init_methods[0]
            ):
                continue
            resolved[attribute] = imports[value.func.id]
        return resolved

    seen_calls: set[tuple[str, int, str]] = set()
    for _ in range(4):
        dynamic_network_components = [
            component
            for component in ir.components
            if component.kind == "capability"
            and component.name == "network"
            and component.attributes.get("dynamic_origin")
        ]
        dynamic_network_locations = {
            (component.evidence.path, component.evidence.line)
            for component in dynamic_network_components
        }
        dynamic_network_by_location: dict[tuple[str, int], list[Component]] = defaultdict(list)
        for component in dynamic_network_components:
            dynamic_network_by_location[
                (component.evidence.path, component.evidence.line)
            ].append(component)
        summaries: dict[tuple[str, str, str], PythonClassNetworkSummary] = {}
        for tool in ir.components:
            entrypoints = tool.attributes.get("entrypoints")
            class_name = tool.attributes.get("class_name")
            if not (
                tool.kind == "tool"
                and tool.attributes.get("registration_target") == "class"
                and isinstance(class_name, str)
                and isinstance(entrypoints, list)
                and len(entrypoints) == 1
                and tool.symbol_id
            ):
                continue
            method_name = entrypoints[0]
            method = method_nodes.get((tool.evidence.path, class_name, method_name))
            if method is None:
                continue
            parameters = [
                argument.arg
                for argument in (*method.args.posonlyargs, *method.args.args)
                if argument.arg not in {"self", "cls"}
            ]
            if not parameters:
                continue
            parameter = parameters[0]
            network_lines = tuple(
                sorted(
                    edge.evidence.line
                    for edge in ir.relationships
                    if edge.source_id == tool.symbol_id
                    and edge.target_kind == "capability"
                    and edge.target_name == "network"
                    and (edge.evidence.path, edge.evidence.line)
                    in dynamic_network_locations
                )
            )
            if network_lines:
                direct_keys = {
                    candidate.slice.value
                    for candidate in ast.walk(method)
                    if isinstance(candidate, ast.Subscript)
                    and isinstance(candidate.value, ast.Name)
                    and candidate.value.id == parameter
                    and isinstance(candidate.slice, ast.Constant)
                    and isinstance(candidate.slice.value, str)
                } | {
                    candidate.args[0].value
                    for candidate in ast.walk(method)
                    if isinstance(candidate, ast.Call)
                    and isinstance(candidate.func, ast.Attribute)
                    and candidate.func.attr == "get"
                    and isinstance(candidate.func.value, ast.Name)
                    and candidate.func.value.id == parameter
                    and candidate.args
                    and isinstance(candidate.args[0], ast.Constant)
                    and isinstance(candidate.args[0].value, str)
                }
                propagated_keys = {
                    component.attributes["callee_parameter_key"]
                    for line in network_lines
                    for component in dynamic_network_by_location.get(
                        (tool.evidence.path, line), []
                    )
                    if isinstance(component.attributes.get("callee_parameter_key"), str)
                }
                parameter_key = (
                    next(iter(direct_keys))
                    if len(direct_keys) == 1
                    else next(iter(propagated_keys))
                    if not direct_keys and len(propagated_keys) == 1
                    else None
                )
                summaries[(tool.evidence.path, class_name, method_name)] = (
                    PythonClassNetworkSummary(
                        tool.evidence.path,
                        class_name,
                        method_name,
                        parameter,
                        parameter_key,
                        method.lineno,
                        network_lines,
                    )
                )
        added = 0
        for tool in list(ir.components):
            entrypoints = tool.attributes.get("entrypoints")
            class_name = tool.attributes.get("class_name")
            if not (
                tool.kind == "tool"
                and tool.attributes.get("registration_target") == "class"
                and isinstance(class_name, str)
                and isinstance(entrypoints, list)
                and len(entrypoints) == 1
                and tool.symbol_id
            ):
                continue
            relative = tool.evidence.path
            class_node = class_nodes.get((relative, class_name, tool.evidence.line))
            method = method_nodes.get((relative, class_name, entrypoints[0]))
            if class_node is None or method is None:
                continue
            imports = module_imports.get(relative, {})
            bindings = class_bindings(class_node, imports)
            local_bindings = python_function_local_bindings(method)
            method_call_states = call_states(method)
            for candidate in ast.walk(method):
                if not isinstance(candidate, ast.Call) or id(candidate) not in method_call_states:
                    continue
                if not isinstance(candidate.func, ast.Attribute):
                    continue
                callee_identity: tuple[str, str] | None = None
                receiver = candidate.func.value
                if (
                    isinstance(receiver, ast.Call)
                    and isinstance(receiver.func, ast.Name)
                    and receiver.func.id not in local_bindings
                ):
                    callee_identity = imports.get(receiver.func.id)
                elif (
                    isinstance(receiver, ast.Attribute)
                    and isinstance(receiver.value, ast.Name)
                    and receiver.value.id == "self"
                ):
                    callee_identity = bindings.get(receiver.attr)
                if callee_identity is None:
                    continue
                summary = summaries.get((*callee_identity, candidate.func.attr))
                if summary is None:
                    continue
                call_key = (relative, candidate.lineno, tool.symbol_id)
                if call_key in seen_calls:
                    continue
                argument = next(
                    (
                        keyword.value
                        for keyword in candidate.keywords
                        if keyword.arg == summary.parameter
                    ),
                    candidate.args[0] if candidate.args else None,
                )
                origin_argument = argument
                if isinstance(argument, ast.Dict):
                    origin_argument = None
                    if summary.parameter_key is not None:
                        origin_argument = next(
                            (
                                value
                                for key, value in zip(argument.keys, argument.values)
                                if isinstance(key, ast.Constant)
                                and key.value == summary.parameter_key
                            ),
                            None,
                        )
                dynamic_origin = python_http_origin_is_dynamic(
                    origin_argument,
                    method_call_states.get(id(candidate), set()),
                    module_prefixes.get(relative, {}),
                )
                evidence = Evidence(
                    relative,
                    candidate.lineno,
                    excerpt(parsed[relative][1], candidate.lineno),
                )
                attributes = {
                    "scope": source_scope(relative),
                    "api": f"{summary.class_name}.{summary.method}",
                    "dynamic_origin": dynamic_origin,
                    "summary": "imported-class-method",
                    "callee_path": summary.path,
                    "callee_class": summary.class_name,
                    "callee_method": summary.method,
                    "callee_parameter_key": summary.parameter_key,
                    "callee_line": summary.line,
                    "callee_network_lines": list(summary.network_lines),
                }
                ir.add_component(Component("capability", "network", evidence, attributes))
                ir.add_relationship(
                    Relationship(
                        "tool",
                        tool.name,
                        "uses",
                        "capability",
                        "network",
                        evidence,
                        source_id=tool.symbol_id,
                    )
                )
                seen_calls.add(call_key)
                added += 1
        if not added:
            break


def add_typescript_configurable_ssrf_composition(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve a default-off SSRF bridge from composition root to an Axios-backed tool."""
    sources: dict[str, tuple[str, str]] = {}
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        sources[relative] = (text, typescript_code_mask(text))

    def unique_source(*markers: str) -> tuple[str, str, str] | None:
        matches = [
            (relative, text, code)
            for relative, (text, code) in sources.items()
            if all(marker in code for marker in markers)
        ]
        return matches[0] if len(matches) == 1 else None

    config = unique_source("class SsrfProtectionConfig", "enabled: boolean =")
    service = unique_source(
        "class SsrfProtectionService",
        "createSecureLookup()",
        "lookupAndValidate(",
        "validateIp(",
        "allowedIps.check(",
        "blockedIps.check(",
        "dnsResolver.lookup(",
    )
    passthrough = unique_source(
        "function createPassthroughSsrfGuard(",
        "validateUrl: async () => createResultOk(undefined)",
        "createSecureLookup: () => dns.lookup",
    )
    composition = unique_source(
        "const webFetchSsrfGuard = this.ssrfConfig.enabled",
        "this.ssrfProtectionService",
        "createPassthroughSsrfGuard()",
        "new AiWorkflowBuilderService(",
    )
    discovery = unique_source(
        "config.ssrf ?? createPassthroughSsrfGuard()",
        "createWebFetchTool(discoverySecurityFactory, ssrf)",
        "createWebFetchTool(plannerSecurityFactory, ssrf)",
    )
    tool_source = unique_source(
        "function createWebFetchTool(",
        "webFetchSchema.parse(input)",
        "ssrf.validateUrl(url)",
        "fetchUrl(url, ssrf)",
        "fetchUrl(fetchResult.finalUrl, ssrf)",
        "requestDomainApproval(",
    )
    sink_source = unique_source(
        "function fetchUrl(",
        "ssrf.validateUrl(url)",
        "lookup: ssrf.createSecureLookup()",
        "ssrf.validateRedirectSync(opts.href)",
        "maxRedirects: WEB_FETCH_MAX_REDIRECTS",
        "axios.get<Readable>(url, config)",
    )
    if None in {
        config,
        service,
        passthrough,
        composition,
        discovery,
        tool_source,
        sink_source,
    }:
        return
    assert config is not None
    assert service is not None
    assert passthrough is not None
    assert composition is not None
    assert discovery is not None
    assert tool_source is not None
    assert sink_source is not None

    config_path, config_text, config_code = config
    service_path, _, _ = service
    passthrough_path, _, _ = passthrough
    composition_path, composition_text, composition_code = composition
    discovery_path, _, _ = discovery
    tool_path, tool_text, tool_code = tool_source
    sink_path, sink_text, sink_code = sink_source
    if not (
        "blockedIpRanges: string[] = [...SSRF_DEFAULT_BLOCKED_IP_RANGES]" in config_code
        and "allowedIpRanges:" in config_code
        and "allowedHostnames:" in config_code
        and re.search(
            r"webFetchSsrfGuard\s*=\s*this\.ssrfConfig\.enabled\s*"
            r"\?\s*this\.ssrfProtectionService\s*:\s*createPassthroughSsrfGuard\(\)",
            composition_code,
        )
        and re.search(
            r"new\s+AiWorkflowBuilderService\([\s\S]{0,2500}webFetchSsrfGuard",
            composition_code,
        )
        and sum(code.count("private readonly ssrf?: SsrfGuard") for _, code in sources.values())
        >= 1
        and sum(code.count("ssrf: this.ssrf") for _, code in sources.values()) >= 2
    ):
        return

    tool_call = re.search(r"\bfetchUrl\s*\(\s*url\s*,\s*ssrf\s*\)", tool_code)
    sink_call = re.search(r"\baxios\.get\s*<Readable>\s*\(\s*url\s*,\s*config\s*\)", sink_code)
    control_match = re.search(r"\bconst\s+webFetchSsrfGuard\b", composition_code)
    config_match = re.search(r"\benabled\s*:\s*boolean\s*=\s*(true|false)\b", config_code)
    tool_definition = re.search(r"\bfunction\s+createWebFetchTool\b", tool_code)
    if None in {tool_call, sink_call, control_match, config_match, tool_definition}:
        return
    assert tool_call is not None
    assert sink_call is not None
    assert control_match is not None
    assert config_match is not None
    assert tool_definition is not None

    call_line = line_at(tool_text, tool_call.start())
    sink_line = line_at(sink_text, sink_call.start())
    control_line = line_at(composition_text, control_match.start())
    config_line = line_at(config_text, config_match.start())
    tool_line = line_at(tool_text, tool_definition.start())
    enabled_default = config_match.group(1) == "true"
    call_evidence = Evidence(tool_path, call_line, excerpt(tool_text.splitlines(), call_line))
    control_evidence = Evidence(
        composition_path,
        control_line,
        excerpt(composition_text.splitlines(), control_line),
    )
    tool_id = f"ts:{tool_path}#tool:web_fetch"
    attributes = {
        "scope": source_scope(tool_path),
        "policy_effect": "validates-url-and-resolved-host-when-enforced",
        "frontend": "typescript",
        "analysis": "typescript-configurable-ssrf-composition",
        "initial_origin_scope": "configured-address-policy-when-enforced",
        "redirect_scope": "bounded-each-hop-hooks-when-enforced",
        "dns_scope": "secure-lookup-configured-when-enforced",
        "proxy_scope": "unresolved",
        "enforcement_default": "enabled" if enabled_default else "disabled",
        "escape_hatch": "configured-opt-out" if enabled_default else "default-disabled",
        "enforcement_mode": "configured-opt-out" if enabled_default else "configured-opt-in",
        "enable_environment": "N8N_SSRF_PROTECTION_ENABLED",
        "config_path": config_path,
        "config_line": config_line,
        "service_path": service_path,
        "passthrough_path": passthrough_path,
        "discovery_path": discovery_path,
        "helper_path": sink_path,
        "helper_line": sink_line,
        "approval_scope": "domain-hitl-independent",
    }
    ir.add_component(
        Component(
            "tool",
            "web_fetch",
            Evidence(tool_path, tool_line, excerpt(tool_text.splitlines(), tool_line)),
            {"constructor": "tool", "domain_approval": "conditional-independent"},
            tool_id,
        )
    )
    ir.add_component(
        Component(
            "capability",
            "network",
            call_evidence,
            {
                "scope": source_scope(tool_path),
                "api": "axios.get",
                "dynamic_origin": True,
                "summary": "configured-ssrf-composition",
                "helper_path": sink_path,
                "helper_line": sink_line,
            },
        )
    )
    ir.add_component(Component("control", "network-ssrf-policy", control_evidence, attributes))
    ir.add_relationship(
        Relationship(
            "tool",
            "web_fetch",
            "uses",
            "capability",
            "network",
            call_evidence,
            source_id=tool_id,
        )
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "network",
            "governed-by",
            "control",
            "network-ssrf-policy",
            call_evidence,
            {"control_path": composition_path, "control_line": control_line, **attributes},
        )
    )


def add_typescript_flowise_secure_request_composition(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve Flowise's request-object URL flow into its pinned Axios transport."""
    sources: dict[str, tuple[str, str]] = {}
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        sources[relative] = (text, typescript_code_mask(text))

    def unique_source(*markers: str) -> tuple[str, str, str] | None:
        matches = [
            (relative, text, code)
            for relative, (text, code) in sources.items()
            if all(marker in code for marker in markers)
        ]
        return matches[0] if len(matches) == 1 else None

    helper = unique_source(
        "function getHttpDenyList()",
        "export async function secureAxiosRequest(",
        "resolveAndValidate(currentUrl)",
        "createPinnedAgent(target",
        "axios(currentConfig)",
        "function createPinnedAgent(",
    )
    caller = unique_source(
        "class HTTP_Agentflow implements INode",
        "async run(nodeData: INodeData",
        "nodeData.inputs?.url",
        "const requestConfig: AxiosRequestConfig =",
        "secureAxiosRequest(requestConfig)",
        "module.exports = { nodeClass: HTTP_Agentflow }",
    )
    if helper is None or caller is None:
        return
    helper_path, helper_text, helper_code = helper
    caller_path, caller_text, caller_code = caller
    if not typescript_named_import_reaches_path(
        root,
        root / caller_path,
        caller_text,
        "secureAxiosRequest",
        "secureAxiosRequest",
        helper_path,
        set(sources),
    ):
        return
    required_helper_text = (
        "process.env.HTTP_SECURITY_CHECK !== 'false'",
        "return [...new Set([...DEFAULT_DENY_LIST, ...customList])]",
        "'10.0.0.0/8'",
        "'127.0.0.0/8'",
        "'169.254.169.254'",
        "'::1'",
        "maxRedirects: 0",
        "const records = await dns.lookup(hostname, { all: true })",
        "const chosen = records.find((r) => r.family === 4) ?? records[0]",
        "lookup: (_host, _opts, cb) =>",
        "cb(null, target.ip, target.family)",
        "currentUrl = new URL(location, currentUrl).toString()",
        "ipv6Addr.isIPv4MappedAddress()",
        "parsedIp = ipv6Addr.toIPv4Address()",
    )
    if not all(marker in helper_text for marker in required_helper_text):
        return
    if not (
        re.search(
            r"(?:export\s+)?function\s+isDeniedIP\s*\([\s\S]{0,6000}"
            r"ipaddr\.parse\s*\(\s*ip\s*\)[\s\S]{0,6000}"
            r"isIPv4MappedAddress\s*\(\s*\)[\s\S]{0,1000}"
            r"toIPv4Address\s*\(\s*\)[\s\S]{0,6000}"
            r"ipaddr\.parseCIDR\s*\([\s\S]{0,2500}"
            r"\.match\s*\([\s\S]{0,1200}Access to this host is denied by policy",
            helper_text,
        )
        and re.search(
            r"if\s*\(\s*ipaddr\.isValid\s*\(\s*hostname\s*\)\s*\)\s*\{"
            r"[\s\S]{0,500}isDeniedIP\s*\(\s*hostname\s*,",
            helper_code,
        )
        and re.search(
            r"dns\.lookup\s*\(\s*hostname\s*,\s*\{\s*all\s*:\s*true\s*\}\s*\)"
            r"[\s\S]{0,700}for\s*\([^)]*\s+of\s+records\s*\)\s*\{"
            r"[\s\S]{0,300}isDeniedIP\s*\([^,]+\.address\s*,",
            helper_code,
        )
        and re.search(
            r"while\s*\(\s*redirects\s*<=\s*maxRedirects\s*\)[\s\S]{0,1800}"
            r"resolveAndValidate\s*\(\s*currentUrl\s*\)[\s\S]{0,1200}"
            r"axios\s*\(\s*currentConfig\s*\)",
            helper_code,
        )
        and "httpAgent: undefined" in helper_code
        and "httpsAgent: undefined" in helper_code
        and "target.protocol ===" in helper_code
        and "httpAgent: agent" in helper_code
        and "httpsAgent: agent" in helper_code
    ):
        return

    input_match = re.search(
        r"const\s+url\s*=\s*nodeData\.inputs\?\.url\s+as\s+string\b",
        caller_code,
    )
    final_url_match = re.search(
        r"const\s+finalUrl\s*=\s*queryString\s*\?\s*"
        r"`\$\{url\}[\s\S]{0,180}\$\{queryString\}`\s*:\s*url\b",
        caller_text,
    )
    config_match = re.search(
        r"const\s+requestConfig\s*:\s*AxiosRequestConfig\s*=\s*\{",
        caller_code,
    )
    call_match = re.search(r"\bsecureAxiosRequest\s*\(\s*requestConfig\s*\)", caller_code)
    helper_match = re.search(r"\bexport\s+async\s+function\s+secureAxiosRequest\b", helper_code)
    class_match = re.search(r"\bclass\s+HTTP_Agentflow\b", caller_code)
    if None in {
        input_match,
        final_url_match,
        config_match,
        call_match,
        helper_match,
        class_match,
    }:
        return
    assert input_match is not None
    assert final_url_match is not None
    assert config_match is not None
    assert call_match is not None
    assert helper_match is not None
    assert class_match is not None
    config_opening = caller_code.find("{", config_match.start(), config_match.end())
    config_end = typescript_balanced_end(caller_code, config_opening, "{", "}")
    if config_end is None or call_match.start() <= config_end:
        return
    config_source = caller_text[config_opening:config_end]
    post_config_code = caller_code[config_end : call_match.start()]
    if (
        typescript_object_property_expression(config_source, "url") != "finalUrl"
        or any(
            typescript_object_property_expression(config_source, name) is not None
            for name in ("adapter", "httpAgent", "httpsAgent", "proxy", "socketPath", "transport")
        )
        or "..." in typescript_code_mask(config_source)
        or re.search(
            r"\brequestConfig\s*\.\s*"
            r"(?:adapter|httpAgent|httpsAgent|proxy|socketPath|transport)\s*=",
            post_config_code,
        )
        or re.search(r"\bObject\.assign\s*\(\s*requestConfig\b", post_config_code)
    ):
        return
    if not (
        re.search(r"name\s*:\s*['\"]url['\"][\s\S]{0,160}acceptVariable\s*:\s*true", caller_text)
        and re.search(r"this\.name\s*=\s*['\"]httpAgentflow['\"]", caller_text)
    ):
        return

    call_line = line_at(caller_text, call_match.start())
    helper_line = line_at(helper_text, helper_match.start())
    class_line = line_at(caller_text, class_match.start())
    evidence = Evidence(caller_path, call_line, excerpt(caller_text.splitlines(), call_line))
    helper_evidence = Evidence(
        helper_path,
        helper_line,
        excerpt(helper_text.splitlines(), helper_line),
    )
    tool_id = f"ts:{caller_path}#tool:httpAgentflow"
    attributes = {
        "scope": source_scope(caller_path),
        "policy_effect": "validates-and-pins-addresses-unless-proxied",
        "frontend": "typescript",
        "analysis": "typescript-flowise-secure-request-composition",
        "initial_origin_scope": "default-address-denylist-when-enforced",
        "redirect_scope": "each-hop-validated",
        "dns_scope": "connection-pinned-unless-proxied",
        "proxy_scope": "environment-dependent",
        "transport_scope": "fixed-caller-config",
        "enforcement_default": "enabled",
        "escape_hatch": "configured-opt-out",
        "enforcement_mode": "configured-opt-out",
        "disable_environment": "HTTP_SECURITY_CHECK",
        "denylist_environment": "HTTP_DENY_LIST",
        "ipv4_mapped_ipv6": "normalized",
        "helper_path": helper_path,
        "helper_line": helper_line,
    }
    ir.add_component(
        Component(
            "tool",
            "httpAgentflow",
            Evidence(caller_path, class_line, excerpt(caller_text.splitlines(), class_line)),
            {
                "constructor": "flowise-node",
                "framework": "flowise",
                "entrypoint": "HTTP_Agentflow.run",
                "url_input": "nodeData.inputs.url",
            },
            tool_id,
        )
    )
    ir.add_component(
        Component(
            "capability",
            "network",
            evidence,
            {
                "scope": source_scope(caller_path),
                "api": "secureAxiosRequest",
                "dynamic_origin": True,
                "summary": "imported-request-object-helper",
                "request_url_property": "url",
                "helper_path": helper_path,
                "helper_line": helper_line,
            },
        )
    )
    ir.add_component(Component("control", "network-ssrf-policy", helper_evidence, attributes))
    ir.add_relationship(
        Relationship(
            "tool",
            "httpAgentflow",
            "uses",
            "capability",
            "network",
            evidence,
            source_id=tool_id,
        )
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "network",
            "governed-by",
            "control",
            "network-ssrf-policy",
            evidence,
            attributes,
        )
    )


def add_typescript_flowise_secure_fetch_composition(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve a Flowise LangChain tool through its pinned node-fetch transport."""
    sources: dict[str, tuple[str, str]] = {}
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        sources[relative] = (text, typescript_code_mask(text))

    def unique_source(*markers: str) -> tuple[str, str, str] | None:
        matches = [
            (relative, text, code)
            for relative, (text, code) in sources.items()
            if all(marker in code for marker in markers)
        ]
        return matches[0] if len(matches) == 1 else None

    helper = unique_source(
        "function getHttpDenyList()",
        "export async function secureFetch(",
        "resolveAndValidate(currentUrl)",
        "createPinnedAgent(resolved",
        "fetch(currentUrl,",
        "function createPinnedAgent(",
    )
    caller = unique_source(
        "class WebScraperRecursiveTool extends Tool",
        "async scrapeSingleUrl(url: string)",
        "secureFetch(url,",
        "async scrapeRecursive(url: string, currentDepth: number)",
        "this.scrapeSingleUrl(url)",
        "async _call(initialInput: string)",
        "this.scrapeRecursive(initialInput, 1)",
    )
    if helper is None or caller is None:
        return
    helper_path, helper_text, helper_code = helper
    caller_path, caller_text, caller_code = caller
    if not typescript_named_import_reaches_path(
        root,
        root / caller_path,
        caller_text,
        "secureFetch",
        "secureFetch",
        helper_path,
        set(sources),
    ):
        return

    required_helper_text = (
        "process.env.HTTP_SECURITY_CHECK !== 'false'",
        "return [...new Set([...DEFAULT_DENY_LIST, ...customList])]",
        "'10.0.0.0/8'",
        "'127.0.0.0/8'",
        "'169.254.169.254'",
        "'::1'",
        "const records = await dns.lookup(hostname, { all: true })",
        "const chosen = records.find((r) => r.family === 4) ?? records[0]",
        "lookup: (_host, _opts, cb) =>",
        "cb(null, target.ip, target.family)",
        "currentUrl = new URL(location, currentUrl).toString()",
        "ipv6Addr.isIPv4MappedAddress()",
        "parsedIp = ipv6Addr.toIPv4Address()",
        "let currentInit = { ...init, redirect: 'manual' as const }",
    )
    if not all(marker in helper_text for marker in required_helper_text):
        return
    if not (
        re.search(
            r"(?:export\s+)?function\s+isDeniedIP\s*\([\s\S]{0,6000}"
            r"ipaddr\.parse\s*\(\s*ip\s*\)[\s\S]{0,6000}"
            r"isIPv4MappedAddress\s*\(\s*\)[\s\S]{0,1000}"
            r"toIPv4Address\s*\(\s*\)[\s\S]{0,6000}"
            r"ipaddr\.parseCIDR\s*\([\s\S]{0,2500}"
            r"\.match\s*\([\s\S]{0,1200}Access to this host is denied by policy",
            helper_text,
        )
        and re.search(
            r"if\s*\(\s*ipaddr\.isValid\s*\(\s*hostname\s*\)\s*\)\s*\{"
            r"[\s\S]{0,500}isDeniedIP\s*\(\s*hostname\s*,",
            helper_code,
        )
        and re.search(
            r"dns\.lookup\s*\(\s*hostname\s*,\s*\{\s*all\s*:\s*true\s*\}\s*\)"
            r"[\s\S]{0,700}for\s*\([^)]*\s+of\s+records\s*\)\s*\{"
            r"[\s\S]{0,300}isDeniedIP\s*\([^,]+\.address\s*,",
            helper_code,
        )
        and re.search(
            r"while\s*\(\s*redirectCount\s*<=\s*maxRedirects\s*\)"
            r"[\s\S]{0,1200}resolveAndValidate\s*\(\s*currentUrl\s*\)"
            r"[\s\S]{0,800}fetch\s*\(\s*currentUrl\s*,\s*\{"
            r"[\s\S]{0,300}agent\s*:\s*\(\s*\)\s*=>\s*agent",
            helper_code,
        )
        and re.search(
            r"fetch\s*\(\s*currentUrl\s*,\s*\{\s*\.\.\.currentInit\s*,"
            r"\s*agent\s*:\s*\(\s*\)\s*=>\s*agent\s*\}\s*\)",
            helper_code,
        )
    ):
        return

    class_match = re.search(r"\bclass\s+WebScraperRecursiveTool\s+extends\s+Tool\b", caller_code)
    call_match = re.search(r"\bsecureFetch\s*\(\s*url\s*,", caller_code)
    helper_match = re.search(r"\bexport\s+async\s+function\s+secureFetch\b", helper_code)
    if class_match is None or call_match is None or helper_match is None:
        return
    if not (
        re.search(r"\bname\s*=\s*['\"]web_scraper_tool['\"]", caller_text)
        and re.search(
            r"(?:private\s+)?async\s+scrapeSingleUrl\s*\(\s*url\s*:\s*string\s*\)"
            r"[\s\S]{0,800}secureFetch\s*\(\s*url\s*,",
            caller_code,
        )
        and re.search(
            r"(?:private\s+)?async\s+scrapeRecursive\s*\(\s*url\s*:\s*string\s*,"
            r"[\s\S]{0,2200}this\.scrapeSingleUrl\s*\(\s*url\s*\)",
            caller_code,
        )
        and re.search(
            r"async\s+_call\s*\(\s*initialInput\s*:\s*string\s*\)"
            r"[\s\S]{0,3500}this\.scrapeRecursive\s*\(\s*initialInput\s*,\s*1\s*\)",
            caller_code,
        )
    ):
        return

    call_line = line_at(caller_text, call_match.start())
    helper_line = line_at(helper_text, helper_match.start())
    class_line = line_at(caller_text, class_match.start())
    evidence = Evidence(caller_path, call_line, excerpt(caller_text.splitlines(), call_line))
    helper_evidence = Evidence(
        helper_path,
        helper_line,
        excerpt(helper_text.splitlines(), helper_line),
    )
    tool_id = f"ts:{caller_path}#tool:web_scraper_tool"
    attributes = {
        "scope": source_scope(caller_path),
        "policy_effect": "validates-and-pins-addresses",
        "frontend": "typescript",
        "analysis": "typescript-flowise-secure-fetch-composition",
        "initial_origin_scope": "default-address-denylist-when-enforced",
        "redirect_scope": "each-hop-validated",
        "dns_scope": "connection-pinned",
        "proxy_scope": "pinned-agent",
        "transport_scope": "caller-agent-overridden",
        "enforcement_default": "enabled",
        "escape_hatch": "configured-opt-out",
        "enforcement_mode": "configured-opt-out",
        "disable_environment": "HTTP_SECURITY_CHECK",
        "denylist_environment": "HTTP_DENY_LIST",
        "ipv4_mapped_ipv6": "normalized",
        "helper_path": helper_path,
        "helper_line": helper_line,
    }
    ir.add_component(
        Component(
            "tool",
            "web_scraper_tool",
            Evidence(caller_path, class_line, excerpt(caller_text.splitlines(), class_line)),
            {
                "constructor": "langchain-tool",
                "framework": "langchain",
                "entrypoint": "WebScraperRecursiveTool._call",
                "url_input": "initialInput",
            },
            tool_id,
        )
    )
    ir.add_component(
        Component(
            "capability",
            "network",
            evidence,
            {
                "scope": source_scope(caller_path),
                "api": "secureFetch",
                "dynamic_origin": True,
                "summary": "same-class-imported-fetch-helper",
                "helper_path": helper_path,
                "helper_line": helper_line,
            },
        )
    )
    ir.add_component(Component("control", "network-ssrf-policy", helper_evidence, attributes))
    ir.add_relationship(
        Relationship(
            "tool",
            "web_scraper_tool",
            "uses",
            "capability",
            "network",
            evidence,
            source_id=tool_id,
        )
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "network",
            "governed-by",
            "control",
            "network-ssrf-policy",
            evidence,
            attributes,
        )
    )


def add_typescript_google_adk_load_web_page_composition(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve Google ADK's FunctionTool through its preflight-only fetch policy."""
    sources: dict[str, tuple[str, str]] = {}
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        sources[relative] = (text, typescript_code_mask(text))

    def unique_source(*markers: str) -> tuple[str, str, str] | None:
        matches = [
            (relative, text, code)
            for relative, (text, code) in sources.items()
            if all(marker in code for marker in markers)
        ]
        return matches[0] if len(matches) == 1 else None

    caller = unique_source(
        "export async function loadWebPage(",
        "export const LOAD_WEB_PAGE = new FunctionTool(",
        "execute: ({url}) => loadWebPage(url)",
        "await validateResolvedAddresses(normalizeHost(parsed.hostname))",
        "const response = await fetch(url,",
    )
    tool_class = unique_source("export class FunctionTool<", "extends BaseTool")
    if caller is None or tool_class is None:
        return
    caller_path, caller_text, caller_code = caller
    tool_class_path, _, _ = tool_class
    if not typescript_named_import_reaches_path(
        root,
        root / caller_path,
        caller_text,
        "FunctionTool",
        "FunctionTool",
        tool_class_path,
        set(sources),
    ):
        return

    required_text = (
        "const ALLOWED_SCHEMES = new Set(['http:', 'https:'])",
        "'0.0.0.0/8'",
        "'10.0.0.0/8'",
        "'127.0.0.0/8'",
        "'169.254.0.0/16'",
        "'192.168.0.0/16'",
        "'::1/128'",
        "'fc00::/7'",
        "'fe80::/10'",
        "value >> 32n === 0xffffn",
        "const records = await lookup(hostname, {all: true})",
        "addresses.some(isBlockedAddress)",
        "redirect: 'manual'",
        "name: 'load_web_page'",
    )
    if not all(marker in caller_text for marker in required_text):
        return
    if not (
        re.search(
            r"function\s+assertUrlAllowed\s*\(\s*url\s*:\s*string\s*\)"
            r"[\s\S]{0,1200}new\s+URL\s*\(\s*url\s*\)"
            r"[\s\S]{0,800}ALLOWED_SCHEMES\.has\s*\(\s*parsed\.protocol\s*\)"
            r"[\s\S]{0,800}isBlockedHostname\s*\(\s*parsed\.hostname\s*\)",
            caller_code,
        )
        and re.search(
            r"function\s+isBlockedIpv6\s*\([^)]*\)\s*:[^{]+\{"
            r"[\s\S]{0,1000}value\s*>>\s*32n\s*===\s*0xffffn"
            r"[\s\S]{0,700}isBlockedIpv4\s*\(",
            caller_code,
        )
        and re.search(
            r"lookup\s*\(\s*hostname\s*,\s*\{\s*all\s*:\s*true\s*\}\s*\)"
            r"[\s\S]{0,800}new\s+Set\s*\(\s*records\.map\s*\(",
            caller_code,
        )
        and re.search(
            r"async\s+function\s+validateResolvedAddresses\s*\(\s*hostname\s*:\s*string\s*\)"
            r"[\s\S]{0,500}resolveHostAddresses\s*\(\s*hostname\s*\)"
            r"[\s\S]{0,400}addresses\.some\s*\(\s*isBlockedAddress\s*\)",
            caller_code,
        )
        and re.search(
            r"export\s+async\s+function\s+loadWebPage\s*\(\s*url\s*:\s*string"
            r"[\s\S]{0,800}assertUrlAllowed\s*\(\s*url\s*\)"
            r"[\s\S]{0,500}validateResolvedAddresses\s*\(\s*normalizeHost\s*\(\s*parsed\.hostname\s*\)\s*\)"
            r"[\s\S]{0,500}fetch\s*\(\s*url\s*,\s*\{",
            caller_code,
        )
        and re.search(
            r"new\s+FunctionTool\s*\(\s*\{[\s\S]{0,1200}parameters\s*:\s*z\.object\s*\(\s*\{"
            r"[\s\S]{0,300}url\s*:\s*z\.string\s*\(\)"
            r"[\s\S]{0,500}execute\s*:\s*\(\s*\{\s*url\s*\}\s*\)\s*=>\s*loadWebPage\s*\(\s*url\s*\)",
            caller_code,
        )
    ):
        return

    call_match = re.search(
        r"execute\s*:\s*\(\s*\{\s*url\s*\}\s*\)\s*=>\s*"
        r"loadWebPage\s*\(\s*url\s*\)",
        caller_code,
    )
    tool_match = re.search(r"\bLOAD_WEB_PAGE\s*=\s*new\s+FunctionTool\b", caller_code)
    helper_match = re.search(r"\bexport\s+async\s+function\s+loadWebPage\b", caller_code)
    if call_match is None or tool_match is None or helper_match is None:
        return
    call_line = line_at(caller_text, call_match.start())
    tool_line = line_at(caller_text, tool_match.start())
    helper_line = line_at(caller_text, helper_match.start())
    evidence = Evidence(caller_path, call_line, excerpt(caller_text.splitlines(), call_line))
    control_evidence = Evidence(
        caller_path,
        helper_line,
        excerpt(caller_text.splitlines(), helper_line),
    )
    tool_id = f"ts:{caller_path}#tool:load_web_page"
    attributes = {
        "scope": source_scope(caller_path),
        "policy_effect": "validates-public-addresses-preflight",
        "frontend": "typescript",
        "analysis": "typescript-google-adk-load-web-page-composition",
        "initial_origin_scope": "public-addresses-preflight",
        "redirect_scope": "disabled",
        "dns_scope": "preflight-only-rebinding-residual",
        "proxy_scope": "unresolved",
        "transport_scope": "global-fetch-unpinned",
        "enforcement_default": "enabled",
        "escape_hatch": "none",
        "enforcement_mode": "always-on",
        "ipv4_mapped_ipv6": "normalized",
        "helper_path": caller_path,
        "helper_line": helper_line,
    }
    ir.add_component(
        Component(
            "tool",
            "load_web_page",
            Evidence(caller_path, tool_line, excerpt(caller_text.splitlines(), tool_line)),
            {
                "constructor": "google-adk-function-tool",
                "framework": "google-adk",
                "entrypoint": "loadWebPage",
                "url_input": "url",
            },
            tool_id,
        )
    )
    ir.add_component(
        Component(
            "capability",
            "network",
            evidence,
            {
                "scope": source_scope(caller_path),
                "api": "loadWebPage",
                "dynamic_origin": True,
                "summary": "google-adk-function-tool-helper",
                "helper_path": caller_path,
                "helper_line": helper_line,
            },
        )
    )
    ir.add_component(Component("control", "network-ssrf-policy", control_evidence, attributes))
    ir.add_relationship(
        Relationship(
            "tool",
            "load_web_page",
            "uses",
            "capability",
            "network",
            evidence,
            source_id=tool_id,
        )
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "network",
            "governed-by",
            "control",
            "network-ssrf-policy",
            evidence,
            attributes,
        )
    )


def add_typescript_activepieces_safe_http_composition(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve Activepieces' MCP request through its imported filtering Axios instance."""
    sources: dict[str, tuple[str, str]] = {}
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        sources[relative] = (text, typescript_code_mask(text))

    def unique_source(*markers: str) -> tuple[str, str, str] | None:
        matches = [
            (relative, text, code)
            for relative, (text, code) in sources.items()
            if all(marker in code for marker in markers)
        ]
        return matches[0] if len(matches) == 1 else None

    safe_source = unique_source(
        "function buildAgents(",
        "new RequestFilteringHttpAgent(",
        "new RequestFilteringHttpsAgent(",
        "function createAxios(",
        "axios.create(",
        "export const safeHttp =",
    )
    transport_source = unique_source(
        "function createSafeMcpFetch(",
        "safeHttp.axios.request<",
        "function createSafeMcpTransport(",
        "new SSEClientTransport(",
        "new StreamableHTTPClientTransport(",
    )
    entry_source = unique_source(
        "validateAgentMcpTool(",
        "mcpTransport.createTransport(",
        "serverUrl: tool.serverUrl",
        "client.connect(transport)",
    )
    if safe_source is None or transport_source is None or entry_source is None:
        return
    safe_path, safe_text, safe_code = safe_source
    transport_path, transport_text, transport_code = transport_source
    entry_path, entry_text, entry_code = entry_source

    manifest_matches: list[tuple[int, str]] = []
    safe_source_path = Path(safe_path)
    for path in paths:
        if path.name != "package.json" or not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        dependencies = {
            **value.get("dependencies", {}),
            **value.get("devDependencies", {}),
        }
        relative_manifest = path.relative_to(root)
        if (
            dependencies.get("request-filtering-agent") == "3.2.0"
            and relative_manifest.parent in safe_source_path.parents
        ):
            manifest_matches.append(
                (len(relative_manifest.parent.parts), relative_manifest.as_posix())
            )
    if not manifest_matches:
        return
    deepest_manifest = max(depth for depth, _ in manifest_matches)
    deepest_manifests = [
        path for depth, path in manifest_matches if depth == deepest_manifest
    ]
    if len(deepest_manifests) != 1:
        return
    manifest_path = deepest_manifests[0]

    axios_bindings = typescript_axios_default_bindings(safe_text)
    filtering_imports = typescript_named_import_bindings(
        safe_text, "request-filtering-agent"
    )
    if not (
        axios_bindings == {"axios"}
        and filtering_imports.get("RequestFilteringHttpAgent")
        == "RequestFilteringHttpAgent"
        and filtering_imports.get("RequestFilteringHttpsAgent")
        == "RequestFilteringHttpsAgent"
        and typescript_named_import_reaches_path(
            root,
            root / transport_path,
            transport_text,
            "safeHttp",
            "safeHttp",
            safe_path,
            set(sources),
        )
    ):
        return

    required_safe_text = (
        "process.env['AP_SSRF_ALLOW_LIST']",
        "return raw.split(',').map((s) => s.trim()).filter(Boolean)",
        "allowPrivateIPAddress: false",
        "allowLoopbackIPAddress: false",
        "allowMetaIPAddress: false",
        "allowIPAddressList: allowList",
        "httpAgent: new RequestFilteringHttpAgent(filteringOptions)",
        "httpsAgent: new RequestFilteringHttpsAgent({ ...filteringOptions, ...httpsAgentOptions })",
        "const { httpAgent, httpsAgent } = buildAgents(",
        "allowList: parseAllowListFromEnv()",
        "return attachSsrfErrorInterceptor(axios.create({",
        "...config",
        "httpAgent",
        "httpsAgent",
        "lazyDefaultAxios ??= createAxios()",
    )
    if not all(marker in safe_text for marker in required_safe_text):
        return
    if not (
        re.search(
            r"const\s+filteringOptions\s*=\s*\{"
            r"[\s\S]{0,500}allowPrivateIPAddress\s*:\s*false"
            r"[\s\S]{0,500}allowLoopbackIPAddress\s*:\s*false"
            r"[\s\S]{0,500}allowMetaIPAddress\s*:\s*false"
            r"[\s\S]{0,500}allowIPAddressList\s*:\s*allowList"
            r"[\s\S]{0,300}\}",
            safe_code,
        )
        and re.search(
            r"return\s+\{\s*httpAgent\s*:\s*new\s+RequestFilteringHttpAgent"
            r"\s*\(\s*filteringOptions\s*\)\s*,\s*httpsAgent\s*:\s*new\s+"
            r"RequestFilteringHttpsAgent\s*\(\s*\{\s*\.\.\.filteringOptions\s*,"
            r"\s*\.\.\.httpsAgentOptions\s*\}\s*\)",
            safe_code,
        )
        and re.search(
            r"axios\.create\s*\(\s*\{\s*\.\.\.config\s*,\s*httpAgent\s*,"
            r"\s*httpsAgent\s*,?\s*\}\s*\)",
            safe_code,
        )
        and not re.search(
            r"(?:allowPrivateIPAddress|allowMetaIPAddress)\s*:\s*true",
            safe_code,
        )
    ):
        return

    request_match = re.search(
        r"safeHttp\.axios\.request(?:\s*<[^;{}]+>)?\s*\(\s*\{",
        transport_code,
    )
    create_fetch_match = re.search(r"\bfunction\s+createSafeMcpFetch\b", transport_code)
    create_transport_match = re.search(
        r"\bfunction\s+createSafeMcpTransport\b", transport_code
    )
    control_match = re.search(r"\bfunction\s+createAxios\b", safe_code)
    entry_match = re.search(r"\bvalidateAgentMcpTool\s*\(", entry_code)
    if None in {
        request_match,
        create_fetch_match,
        create_transport_match,
        control_match,
        entry_match,
    }:
        return
    assert request_match is not None
    assert create_fetch_match is not None
    assert create_transport_match is not None
    assert control_match is not None
    assert entry_match is not None
    request_opening = transport_code.find("{", request_match.start(), request_match.end())
    request_end = typescript_balanced_end(transport_code, request_opening, "{", "}")
    if request_end is None:
        return
    request_object = transport_text[request_opening:request_end]
    request_url = typescript_object_property_expression(request_object, "url")
    request_has_url_shorthand = any(
        typescript_code_mask(item).strip() == "url"
        for item, _ in typescript_object_items(request_object)
    )
    if (
        request_url not in {None, "url"}
        or (request_url is None and not request_has_url_shorthand)
        or "httpAgent" in typescript_code_mask(request_object)
        or "httpsAgent" in typescript_code_mask(request_object)
        or "proxy" in typescript_code_mask(request_object)
        or not re.search(
            r"const\s+url\s*=\s*input\s+instanceof\s+URL\s*\?"
            r"[\s\S]{0,300}typeof\s+input\s*===\s*['\"]string['\"]"
            r"[\s\S]{0,200}input\.url",
            transport_text,
        )
        or not re.search(
            r"const\s+fetch\s*=\s*createSafeMcpFetch\s*\("
            r"[\s\S]{0,500}new\s+SSEClientTransport\s*\(\s*url\s*,"
            r"[\s\S]{0,300}\bfetch\b"
            r"[\s\S]{0,500}new\s+StreamableHTTPClientTransport\s*\(\s*url\s*,"
            r"[\s\S]{0,300}\bfetch\b",
            transport_code,
        )
        or not re.search(
            r"mcpTransport\.createTransport\s*\(\s*\{"
            r"[\s\S]{0,500}serverUrl\s*:\s*tool\.serverUrl",
            entry_code,
        )
    ):
        return

    request_line = line_at(transport_text, request_match.start())
    control_line = line_at(safe_text, control_match.start())
    entry_line = line_at(entry_text, entry_match.start())
    transport_line = line_at(transport_text, create_transport_match.start())
    evidence = Evidence(
        transport_path,
        request_line,
        excerpt(transport_text.splitlines(), request_line),
    )
    control_evidence = Evidence(
        safe_path,
        control_line,
        excerpt(safe_text.splitlines(), control_line),
    )
    attributes = {
        "scope": source_scope(transport_path),
        "policy_effect": "filters-connected-addresses-unless-proxied",
        "frontend": "typescript",
        "analysis": "typescript-imported-filtering-axios-instance",
        "initial_origin_scope": "http-https-with-connected-address-filter",
        "redirect_scope": "each-direct-connection-filtered",
        "dns_scope": "connection-time-filtered-unless-proxied",
        "proxy_scope": "environment-dependent",
        "transport_scope": "imported-axios-client-instance",
        "enforcement_default": "enabled",
        "escape_hatch": "configured-address-allowlist",
        "enforcement_mode": "always-on-with-configured-exceptions",
        "allowlist_environment": "AP_SSRF_ALLOW_LIST",
        "allowlist_scope": "ip-or-cidr",
        "filter_library": "request-filtering-agent",
        "filter_library_version": "3.2.0",
        "manifest_path": manifest_path,
        "helper_path": safe_path,
        "helper_line": control_line,
        "transport_path": transport_path,
        "transport_line": transport_line,
        "entry_path": entry_path,
        "entry_line": entry_line,
    }
    ir.add_component(
        Component(
            "capability",
            "network",
            evidence,
            {
                "scope": source_scope(transport_path),
                "api": "safeHttp.axios.request",
                "dynamic_origin": False,
                "origin_authority": "configured-mcp-server",
                "summary": "imported-axios-client-instance",
                "request_url_property": "url",
                "helper_path": safe_path,
                "helper_line": control_line,
            },
        )
    )
    ir.add_component(
        Component(
            "protocol",
            "MCP",
            Evidence(
                entry_path,
                entry_line,
                excerpt(entry_text.splitlines(), entry_line),
            ),
            {"transport": "http-or-sse", "endpoint_authority": "configuration"},
        )
    )
    ir.add_component(Component("control", "network-ssrf-policy", control_evidence, attributes))
    ir.add_relationship(
        Relationship(
            "protocol",
            "MCP",
            "uses",
            "capability",
            "network",
            evidence,
        )
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "network",
            "governed-by",
            "control",
            "network-ssrf-policy",
            evidence,
            attributes,
        )
    )


def add_typescript_composio_ssrf_safe_fetch_composition(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve Composio's conditional-runtime SSRF-safe fetch composition."""
    sources: dict[str, tuple[str, str]] = {}
    manifests: dict[str, dict[str, object]] = {}
    for path in paths:
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if path.name == "package.json":
            try:
                manifests[relative] = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
        elif path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx"}:
            try:
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
            except OSError:
                continue
            sources[relative] = (text, typescript_code_mask(text))

    def unique_source(*markers: str) -> tuple[str, str, str] | None:
        matches = [
            (relative, text, code)
            for relative, (text, code) in sources.items()
            if all(marker in code for marker in markers)
        ]
        return matches[0] if len(matches) == 1 else None

    node_source = unique_source(
        "export const assertSafeFetchTarget = async",
        "export const ssrfSafeFetch = async",
        "const envProxyApplies =",
        "hasCustomGlobalDispatcher()",
        "createPinnedDispatcher(addresses)",
    )
    edge_source = unique_source(
        "export const ssrfSafeFetch = async",
        "throw new ComposioBlockedInternalUrlError(",
        "export const ssrfSafeFetchWhereSupported = async",
        "fetch(rawUrl, init)",
    )
    dispatcher_source = unique_source(
        "export const createPinnedDispatcher = async",
        "const loadUndici =",
        "new Agent({",
        "export const hasCustomGlobalDispatcher =",
    )
    mount_source = unique_source(
        "export class ToolRouterSessionFilesMount",
        "ssrfSafeFetch(input)",
        "ssrfSafeFetchWhereSupported(",
        "upload_url: string",
    )
    remote_source = unique_source(
        "export class RemoteFile",
        "ssrfSafeFetchWhereSupported(this.downloadUrl)",
        "async buffer()",
        "async blob()",
    )
    if None in {
        node_source,
        edge_source,
        dispatcher_source,
        mount_source,
        remote_source,
    }:
        return
    assert node_source is not None
    assert edge_source is not None
    assert dispatcher_source is not None
    assert mount_source is not None
    assert remote_source is not None
    node_path, node_text, node_code = node_source
    edge_path, _edge_text, edge_code = edge_source
    dispatcher_path, dispatcher_text, dispatcher_code = dispatcher_source
    mount_path, mount_text, _mount_code = mount_source
    remote_path, remote_text, _remote_code = remote_source

    package_matches: list[tuple[int, str, dict[str, object]]] = []
    node_source_path = Path(node_path)
    for manifest_path, manifest in manifests.items():
        relative_manifest = Path(manifest_path)
        imports = manifest.get("imports", {})
        guard_import = imports.get("#ssrf_guard", {}) if isinstance(imports, dict) else {}
        dependencies = manifest.get("dependencies", {})
        if not isinstance(guard_import, dict) or not isinstance(dependencies, dict):
            continue
        if (
            guard_import.get("workerd") == "./dist/utils/ssrfGuard.workerd.mjs"
            and guard_import.get("edge-light") == "./dist/utils/ssrfGuard.workerd.mjs"
            and guard_import.get("node") == "./dist/utils/ssrfGuard.node.mjs"
            and guard_import.get("default") == "./dist/utils/ssrfGuard.node.mjs"
            and dependencies.get("undici") == "^7.29.0"
            and relative_manifest.parent in node_source_path.parents
        ):
            package_matches.append(
                (len(relative_manifest.parent.parts), manifest_path, manifest)
            )
    if not package_matches:
        return
    deepest = max(depth for depth, _, _ in package_matches)
    selected_manifests = [
        (path, manifest)
        for depth, path, manifest in package_matches
        if depth == deepest
    ]
    if len(selected_manifests) != 1:
        return
    manifest_path, _ = selected_manifests[0]

    mount_imports = typescript_named_import_bindings(mount_text, "#ssrf_guard")
    remote_imports = typescript_named_import_bindings(remote_text, "#ssrf_guard")
    if not (
        mount_imports.get("ssrfSafeFetch") == "ssrfSafeFetch"
        and mount_imports.get("ssrfSafeFetchWhereSupported")
        == "ssrfSafeFetchWhereSupported"
        and remote_imports.get("ssrfSafeFetchWhereSupported")
        == "ssrfSafeFetchWhereSupported"
    ):
        return

    node_checks = (
        all(
            marker in node_text
            for marker in (
                "['10.0.0.0', 8]",
                "['127.0.0.0', 8]",
                "['169.254.0.0', 16]",
                "['172.16.0.0', 12]",
                "['192.168.0.0', 16]",
                "h[5] === 0xffff",
                "h[0] === 0x0064 && h[1] === 0xff9b",
                "(h[0] & 0xfe00) === 0xfc00",
                "(h[0] & 0xffc0) === 0xfe80",
                "(h[0] & 0xff00) === 0xff00",
                "process.env.NODE_USE_ENV_PROXY",
                "process.env.NO_PROXY ?? process.env.no_proxy",
                "'HTTPS_PROXY' : 'HTTP_PROXY'",
            )
        ),
        re.search(
            r"export\s+const\s+isBlockedIp\s*=[\s\S]{0,300}"
            r"family\s*===\s*4[\s\S]{0,150}isBlockedIpv4Long"
            r"[\s\S]{0,200}family\s*===\s*6[\s\S]{0,150}isBlockedIpv6",
            node_code,
        ),
        re.search(
            r"lookup\s*\(\s*host\s*,\s*\{\s*all\s*:\s*true\s*,"
            r"\s*verbatim\s*:\s*true\s*\}\s*\)",
            node_code,
        ),
        re.search(
            r"for\s*\(\s*const\s*\{\s*address\s*\}\s*of\s*resolved\s*\)"
            r"\s*\{[\s\S]{0,200}if\s*\(\s*isBlockedIp\s*\(\s*address\s*\)",
            node_code,
        ),
        re.search(
            r"url\.protocol\s*!==\s*['\"]http:['\"]\s*&&\s*"
            r"url\.protocol\s*!==\s*['\"]https:['\"]",
            node_text,
        ),
        re.search(
            r"for\s*\(\s*let\s+hop\s*=\s*0\s*;\s*hop\s*<=\s*maxRedirects",
            node_code,
        ),
        re.search(
            r"callerDispatcher\s*!==\s*undefined\s*\|\|[\s\S]{0,200}"
            r"envProxyApplies\s*\([\s\S]{0,100}\)\s*\|\|[\s\S]{0,100}"
            r"hasCustomGlobalDispatcher\s*\(\s*\)",
            node_code,
        ),
        re.search(
            r"respectConfiguredRoute\s*\?\s*undefined\s*:\s*await\s+"
            r"createPinnedDispatcher\s*\(\s*addresses\s*\)",
            node_code,
        ),
        re.search(
            r"\{\s*\.\.\.init\s*,\s*redirect\s*:\s*['\"]manual['\"]\s*,"
            r"\s*dispatcher\s*\}",
            node_text,
        ),
        re.search(
            r"currentUrl\s*=\s*new\s+URL\s*\(\s*response\.headers\.get"
            r"\s*\(\s*['\"]location['\"]\s*\)!?\s*,\s*currentUrl\s*\)"
            r"\.toString\s*\(\s*\)",
            node_text,
        ),
    )
    dispatcher_checks = (
        "import type { Agent } from 'undici'" in dispatcher_text,
        "import('undici')" in dispatcher_text,
        "Symbol.for('undici.globalDispatcher.1')" in dispatcher_text,
        "Symbol.for('undici.globalDispatcher.2')" in dispatcher_text,
        bool(
            re.search(
                r"return\s+new\s+Agent\s*\(\s*\{[\s\S]{0,1200}"
                r"connect\s*:\s*\{[\s\S]{0,500}lookup\s*:\s*"
                r"\([^)]*callback[^)]*\)\s*=>[\s\S]{0,900}addresses\.map",
                dispatcher_code,
            )
        ),
        "dispatcher.constructor?.name !== 'Agent'" in dispatcher_text,
    )
    edge_checks = (
        bool(
            re.search(
                r"export\s+const\s+ssrfSafeFetch\s*=\s*async[\s\S]{0,300}"
                r"throw\s+new\s+ComposioBlockedInternalUrlError",
                edge_code,
            )
        ),
        bool(
            re.search(
                r"export\s+const\s+ssrfSafeFetchWhereSupported\s*=\s*async"
                r"[\s\S]{0,300}=>\s*fetch\s*\(\s*rawUrl\s*,\s*init\s*\)",
                edge_code,
            )
        ),
    )
    if not all((*node_checks, *dispatcher_checks, *edge_checks)):
        return

    call_specs: list[tuple[str, str, re.Pattern[str], bool, str]] = [
        (
            mount_path,
            mount_text,
            re.compile(r"(?<![\w$.])ssrfSafeFetch\s*\(\s*input\s*\)"),
            True,
            "caller-supplied-url",
        ),
        (
            mount_path,
            mount_text,
            re.compile(
                r"(?<![\w$.])ssrfSafeFetchWhereSupported\s*\(\s*"
                r"\(\s*uploadURLData\s+as\s+\{\s*upload_url\s*:\s*string\s*\}\s*\)"
                r"\.upload_url\s*,"
            ),
            False,
            "remote-api-response",
        ),
        (
            remote_path,
            remote_text,
            re.compile(
                r"(?<![\w$.])ssrfSafeFetchWhereSupported\s*\(\s*this\.downloadUrl\s*\)"
            ),
            False,
            "remote-api-response",
        ),
    ]
    calls: list[tuple[str, str, re.Match[str], bool, str, str]] = []
    for call_path, call_text, pattern, dynamic_origin, authority in call_specs:
        matches = list(pattern.finditer(typescript_code_mask(call_text)))
        expected = 2 if call_path == remote_path else 1
        if len(matches) != expected:
            return
        helper = (
            "ssrfSafeFetch"
            if "WhereSupported" not in pattern.pattern
            else "ssrfSafeFetchWhereSupported"
        )
        calls.extend(
            (call_path, call_text, match, dynamic_origin, authority, helper)
            for match in matches
        )

    control_match = re.search(r"export\s+const\s+ssrfSafeFetch\s*=", node_code)
    if control_match is None:
        return
    control_line = line_at(node_text, control_match.start())
    control_evidence = Evidence(
        node_path,
        control_line,
        excerpt(node_text.splitlines(), control_line),
    )
    for call_path, call_text, match, dynamic_origin, authority, helper in calls:
        line = line_at(call_text, match.start())
        evidence = Evidence(call_path, line, excerpt(call_text.splitlines(), line))
        edge_runtime = "fail-closed" if helper == "ssrfSafeFetch" else "unguarded-fetch"
        attributes = {
            "scope": source_scope(call_path),
            "policy_effect": "filters-public-addresses-with-configured-route-residual",
            "frontend": "typescript",
            "analysis": "typescript-imported-undici-ssrf-safe-fetch",
            "initial_origin_scope": "http-https-public-resolution",
            "redirect_scope": "each-hop-validated",
            "dns_scope": "connection-pinned-unless-configured-route",
            "proxy_scope": "caller-global-or-environment-dependent",
            "transport_scope": "undici-pinned-dispatcher-unless-configured-route",
            "enforcement_default": (
                "enabled" if helper == "ssrfSafeFetch" else "runtime-conditional"
            ),
            "enforcement_mode": (
                "node-filtered-edge-fail-closed"
                if helper == "ssrfSafeFetch"
                else "node-filtered-edge-unenforced"
            ),
            "escape_hatch": "none",
            "configured_route_residual": True,
            "edge_runtime_scope": edge_runtime,
            "ipv4_mapped_ipv6": "normalized",
            "filter_library": "undici",
            "filter_library_version": "^7.29.0",
            "manifest_path": manifest_path,
            "helper_path": node_path,
            "helper_line": control_line,
            "dispatcher_path": dispatcher_path,
            "edge_helper_path": edge_path,
            "call_helper": helper,
        }
        ir.add_component(
            Component(
                "capability",
                "network",
                evidence,
                {
                    "scope": source_scope(call_path),
                    "api": helper,
                    "dynamic_origin": dynamic_origin,
                    "origin_authority": authority,
                    "summary": "imported-undici-ssrf-safe-fetch",
                    "runtime_scope": (
                        "node-filtered-edge-fail-closed"
                        if helper == "ssrfSafeFetch"
                        else "node-filtered-edge-unenforced"
                    ),
                    "helper_path": node_path,
                    "helper_line": control_line,
                },
            )
        )
        ir.add_component(
            Component("control", "network-ssrf-policy", control_evidence, attributes)
        )
        ir.add_relationship(
            Relationship(
                "capability",
                "network",
                "governed-by",
                "control",
                "network-ssrf-policy",
                evidence,
                attributes,
            )
        )


def add_typescript_composio_cli_file_upload_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve Composio CLI tool arguments into its raw URL-file fetch."""
    sources: list[tuple[str, str, str]] = []
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        sources.append(
            (path.relative_to(root).as_posix(), text, typescript_code_mask(text))
        )

    upload_matches = [
        item
        for item in sources
        if all(
            marker in item[2]
            for marker in (
                "const readFileFromUrl = async",
                "const response = await fetch(url)",
                "const readUploadSource = async",
                "return readFileFromUrl(path, file)",
                "const uploadFile = async",
                "readUploadSource(params.fs, params.path, params.file)",
                "const hydrateFileUploads = async",
                "schema?.file_uploadable === true",
                "export const uploadToolInputFiles = async",
                "hydrateFileUploads(params.arguments_, params.inputSchema",
            )
        )
    ]
    executor_matches = [
        item
        for item in sources
        if all(
            marker in item[2]
            for marker in (
                "export interface ToolsExecutor",
                "export const ToolsExecutor =",
                "execute: (slug, params) =>",
                "uploadToolInputFiles({",
                "arguments_: params.arguments",
                "inputSchema: definition.schema",
            )
        )
    ]
    if len(upload_matches) != 1 or len(executor_matches) != 1:
        return
    upload_path, upload_text, upload_code = upload_matches[0]
    executor_path, executor_text, executor_code = executor_matches[0]
    if (
        "ssrfSafeFetch" in upload_code
        or not re.search(
            r"if\s*\(\s*typeof\s+file\s*===\s*['\"]string['\"]\s*&&\s*"
            r"/\^https\?:\\/\\//i\.test\s*\(\s*file\s*\)\s*\)\s*\{"
            r"\s*return\s+readFileFromUrl\s*\(\s*path\s*,\s*file\s*\)",
            upload_text,
        )
        or not re.search(
            r"return\s+uploadFile\s*\(\s*\{[\s\S]{0,300}file\s*:\s*value"
            r"[\s\S]{0,300}\}\s*\)",
            upload_code,
        )
        or not re.search(
            r"import\s*\{[^}]*\buploadToolInputFiles\b[^}]*\}\s*from\s*"
            r"['\"]src/services/tool-file-uploads['\"]",
            executor_text,
        )
        or not re.search(
            r"uploadToolInputFiles\s*\(\s*\{[\s\S]{0,300}"
            r"arguments_\s*:\s*params\.arguments[\s\S]{0,200}"
            r"inputSchema\s*:\s*definition\.schema",
            executor_code,
        )
    ):
        return
    fetch_matches = list(
        re.finditer(r"(?<![\w$.])fetch\s*\(\s*url\s*\)", upload_code)
    )
    execute_match = re.search(r"\bexecute\s*:\s*\(\s*slug\s*,\s*params\s*\)\s*=>", executor_code)
    upload_entry_match = re.search(
        r"export\s+const\s+uploadToolInputFiles\s*=", upload_code
    )
    if len(fetch_matches) != 1 or execute_match is None or upload_entry_match is None:
        return
    fetch_match = fetch_matches[0]
    fetch_line = line_at(upload_text, fetch_match.start())
    execute_line = line_at(executor_text, execute_match.start())
    upload_entry_line = line_at(upload_text, upload_entry_match.start())
    evidence = Evidence(
        upload_path,
        fetch_line,
        excerpt(upload_text.splitlines(), fetch_line),
    )
    tool_name = "Composio ToolsExecutor.execute"
    ir.add_component(
        Component(
            "tool",
            tool_name,
            Evidence(
                executor_path,
                execute_line,
                excerpt(executor_text.splitlines(), execute_line),
            ),
            {
                "scope": source_scope(executor_path),
                "entrypoint": "execute",
                "argument_source": "tool-execution-arguments",
                "file_upload_gate": "schema-file-uploadable",
                "analysis": "typescript-composio-cli-file-upload-flow",
            },
            source_symbol("ts", executor_path, "tool", "ToolsExecutor.execute"),
        )
    )
    capability_attributes = {
        "scope": source_scope(upload_path),
        "api": "fetch",
        "dynamic_origin": True,
        "origin_authority": "tool-execution-arguments",
        "summary": "composio-cli-schema-file-upload",
        "analysis": "typescript-composio-cli-file-upload-flow",
        "transport_scope": "raw-global-fetch",
        "destination_policy": "absent-on-proven-path",
        "redirect_scope": "global-fetch-default",
        "dns_scope": "global-fetch-default",
        "proxy_scope": "runtime-default",
        "executor_path": executor_path,
        "executor_line": execute_line,
        "upload_entry_line": upload_entry_line,
    }
    ir.components = [
        item
        for item in ir.components
        if not (
            item.kind == "capability"
            and item.name == "network"
            and item.evidence.path == upload_path
            and item.evidence.line == fetch_line
        )
    ]
    ir.add_component(
        Component("capability", "network", evidence, capability_attributes)
    )
    ir.add_relationship(
        Relationship(
            "tool",
            tool_name,
            "uses",
            "capability",
            "network",
            evidence,
            {"analysis": "typescript-composio-cli-file-upload-flow"},
            source_symbol("ts", executor_path, "tool", "ToolsExecutor.execute"),
        )
    )


def add_typescript_google_adk_openapi_rest_tool_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve ADK OpenAPI tools while keeping model input off the request origin."""
    sources: list[tuple[str, str, str]] = []
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        sources.append(
            (path.relative_to(root).as_posix(), text, typescript_code_mask(text))
        )

    def unique_source(*markers: str) -> tuple[str, str, str] | None:
        matches = [item for item in sources if all(marker in item[2] for marker in markers)]
        return matches[0] if len(matches) == 1 else None

    rest_source = unique_source(
        "export class RestApiTool extends BaseTool",
        "const args = request.args",
        "prepareRequestParams(",
        "this.endpoint",
        "const url = applyCredential(",
        "globalThis.fetch(url",
        "function encodePathParamValue(",
        "return encodeURIComponent(value)",
        "export function prepareRequestParams(",
        "Object.entries(args)",
        "if (location ===",
        "pathParams[originalName] = encodePathParamValue(",
        "endpoint.path.replace(",
        "Object.hasOwn(pathParams, name) ? pathParams[name] : placeholder",
        "let url =",
        "export function createRestApiTool(",
        "return new RestApiTool(",
    )
    parser_source = unique_source(
        "export interface OperationEndpoint",
        "function resolveServerUrl(",
        "return server.url.replace(",
        "variable?.default || variable?.enum?.[0]",
        "export class OpenApiSpecParser",
        "const baseUrl = server ? resolveServerUrl(server) :",
        "endpoint: {baseUrl, path, method}",
    )
    toolset_source = unique_source(
        "export class OpenAPIToolset extends BaseToolset",
        "const parser = new OpenApiSpecParser(",
        "const parsedOperations = parser.parse(spec)",
        "const tool = createRestApiTool(",
        "endpoint: op.endpoint",
        "this.tools.push(tool)",
        "return this.tools",
    )
    auth_source = unique_source(
        "export function applyCredential(",
        "if (!credential",
        "return url",
        "url +=",
    )
    if None in {rest_source, parser_source, toolset_source, auth_source}:
        return
    assert rest_source is not None
    assert parser_source is not None
    assert toolset_source is not None
    assert auth_source is not None
    rest_path, rest_text, rest_code = rest_source
    parser_path, parser_text, parser_code = parser_source
    toolset_path, toolset_text, toolset_code = toolset_source
    auth_path, auth_text, auth_code = auth_source
    if (
        not re.search(
            r"import\s*\{[^}]*\bOperationEndpoint\b[^}]*\}\s*from\s*"
            r"['\"]\./openapi_spec_parser/openapi_spec_parser\.js['\"]",
            rest_text,
        )
        and not re.search(
            r"import\s*\{[^}]*\bOperationEndpoint\b[^}]*\}\s*from\s*"
            r"['\"]\./openapi_spec_parser\.js['\"]",
            rest_text,
        )
    ):
        return
    if (
        not re.search(
            r"import\s*\{[^}]*\bapplyCredential\b[^}]*\}\s*from\s*"
            r"['\"]\./auth/auth_helpers\.js['\"]",
            rest_text,
        )
        and not re.search(
            r"import\s*\{[^}]*\bapplyCredential\b[^}]*\}\s*from\s*"
            r"['\"]\./auth_helpers\.js['\"]",
            rest_text,
        )
    ):
        return
    if not (
        re.search(
            r"import\s*\{[^}]*\bOpenApiSpecParser\b[^}]*\}\s*from\s*"
            r"['\"]\./openapi_spec_parser/openapi_spec_parser\.js['\"]",
            toolset_text,
        )
        and re.search(
            r"import\s*\{[^}]*\bcreateRestApiTool\b[^}]*\bRestApiTool\b[^}]*\}\s*"
            r"from\s*['\"]\./rest_api_tool\.js['\"]",
            toolset_text,
        )
    ) and not (
        re.search(
            r"import\s*\{[^}]*\bOpenApiSpecParser\b[^}]*\}\s*from\s*"
            r"['\"]\./openapi_spec_parser\.js['\"]",
            toolset_text,
        )
        and re.search(
            r"import\s*\{[^}]*\bcreateRestApiTool\b[^}]*\bRestApiTool\b[^}]*\}\s*"
            r"from\s*['\"]\./rest_api_tool\.js['\"]",
            toolset_text,
        )
    ):
        return
    if (
        re.search(r"\burl\s*=(?!=)", auth_code)
        or "return credential" in auth_code
        or not re.search(
            r"url\s*\+=\s*`\$\{separator\}[^`]*\$\{encodeURIComponent\(credential\.apiKey\)\}`",
            auth_text,
        )
        or not re.search(
            r"let\s+url\s*=\s*`\$\{endpoint\.baseUrl\}\$\{resolvedPath\}`",
            rest_text,
        )
        or not re.search(
            r"if\s*\(\s*location\s*===\s*['\"]path['\"]\s*\)\s*\{\s*"
            r"pathParams\[originalName\]\s*=\s*encodePathParamValue\s*\(",
            rest_text,
        )
        or not re.search(
            r"if\s*\(\s*value\s*===\s*['\"]\.['\"]\s*\|\|\s*"
            r"value\s*===\s*['\"]\.\.['\"]\s*\)",
            rest_text,
        )
    ):
        return
    fetch_matches = list(
        re.finditer(r"\bglobalThis\.fetch\s*\(\s*url\b", rest_code)
    )
    run_match = re.search(
        r"(?:override\s+)?async\s+runAsync\s*\(\s*request\b", rest_code
    )
    encode_match = re.search(r"function\s+encodePathParamValue\s*\(", rest_code)
    parser_match = re.search(r"function\s+resolveServerUrl\s*\(", parser_code)
    toolset_match = re.search(r"export\s+class\s+OpenAPIToolset\b", toolset_code)
    if (
        len(fetch_matches) != 1
        or run_match is None
        or encode_match is None
        or parser_match is None
        or toolset_match is None
    ):
        return
    fetch_match = fetch_matches[0]
    fetch_line = line_at(rest_text, fetch_match.start())
    run_line = line_at(rest_text, run_match.start())
    encode_line = line_at(rest_text, encode_match.start())
    parser_line = line_at(parser_text, parser_match.start())
    toolset_line = line_at(toolset_text, toolset_match.start())
    capability_evidence = Evidence(
        rest_path,
        fetch_line,
        excerpt(rest_text.splitlines(), fetch_line),
    )
    control_evidence = Evidence(
        rest_path,
        encode_line,
        excerpt(rest_text.splitlines(), encode_line),
    )
    tool_name = "Google ADK RestApiTool.runAsync"
    tool_id = source_symbol("ts", rest_path, "tool", "RestApiTool.runAsync")
    analysis = "typescript-google-adk-openapi-rest-tool"
    ir.add_component(
        Component(
            "tool",
            tool_name,
            Evidence(rest_path, run_line, excerpt(rest_text.splitlines(), run_line)),
            {
                "scope": source_scope(rest_path),
                "entrypoint": "runAsync",
                "factory": "OpenAPIToolset",
                "toolset_path": toolset_path,
                "toolset_line": toolset_line,
                "analysis": analysis,
            },
            tool_id,
        )
    )
    ir.add_component(
        Component(
            "capability",
            "network",
            capability_evidence,
            {
                "scope": source_scope(rest_path),
                "api": "globalThis.fetch",
                "dynamic_origin": False,
                "configured_origin": True,
                "origin_authority": "openapi-server-configuration",
                "model_controlled_fields": ["path", "query", "header", "body"],
                "summary": "google-adk-openapi-rest-tool",
                "analysis": analysis,
                "transport_scope": "raw-global-fetch",
                "destination_policy": "configured-origin-unrestricted",
                "redirect_scope": "global-fetch-default",
                "dns_scope": "global-fetch-default",
                "proxy_scope": "runtime-default",
            },
        )
    )
    control_attributes = {
        "scope": source_scope(rest_path),
        "frontend": "typescript",
        "analysis": analysis,
        "policy_effect": "keeps-model-input-off-http-origin",
        "origin_authority": "openapi-server-configuration",
        "server_url_scope": "first-openapi-server",
        "server_variable_scope": "declared-default-or-enum",
        "model_path_scope": "segment-encoded",
        "dot_segment_policy": "rejected",
        "credential_url_scope": "query-only",
        "hostname_scope": "configured-open",
        "enforcement_default": "enabled",
        "escape_hatch": "none-on-proven-path",
        "parser_path": parser_path,
        "parser_line": parser_line,
        "auth_path": auth_path,
    }
    ir.add_component(
        Component("control", "network-origin-policy", control_evidence, control_attributes)
    )
    ir.add_relationship(
        Relationship(
            "tool",
            tool_name,
            "uses",
            "capability",
            "network",
            capability_evidence,
            {"analysis": analysis},
            tool_id,
        )
    )
    ir.add_relationship(
        Relationship(
            "capability",
            "network",
            "governed-by",
            "control",
            "network-origin-policy",
            capability_evidence,
            {"control_path": rest_path, "control_line": encode_line, **control_attributes},
        )
    )


def add_python_openai_agents_mcp_approval_default_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve the OpenAI Agents Python MCP approval default into an agent binding."""
    sources: list[tuple[str, str, ast.Module]] = []
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        sources.append((path.relative_to(root).as_posix(), text, tree))

    server_matches = [
        item
        for item in sources
        if all(
            marker in item[1]
            for marker in (
                "class MCPServer(",
                "self._needs_approval_policy = self._normalize_needs_approval(",
                "def _normalize_needs_approval(",
                "if require_approval is None:",
                "return False",
                "policy.get(tool.name, False)",
                "class MCPServerStdio(",
                "require_approval=require_approval",
            )
        )
        and len(re.findall(r"require_approval\s*:[^=\n]+?=\s*None", item[1])) >= 2
        or all(
            marker in item[1]
            for marker in (
                "class MCPServer:",
                "self._needs_approval_policy = self._normalize_needs_approval(",
                "def _normalize_needs_approval(",
                "if require_approval is None:",
                "return False",
                "policy.get(tool.name, False)",
                "class MCPServerStdio(MCPServer):",
                "require_approval=None",
                "require_approval=require_approval",
            )
        )
    ]
    util_matches = [
        item
        for item in sources
        if all(
            marker in item[1]
            for marker in (
                "server._get_needs_approval_for_tool(tool, agent)",
                "_build_wrapped_function_tool(",
                "needs_approval=needs_approval",
            )
        )
    ]
    if len(server_matches) != 1 or len(util_matches) != 1:
        return
    server_path, server_text, _server_tree = server_matches[0]
    util_path, util_text, _util_tree = util_matches[0]
    if not re.search(
        r"if\s+require_approval\s+is\s+None\s*:\s*return\s+False",
        server_text,
    ) or not re.search(
        r"needs_approval\s*(?::[^=]+)?=\s*server\._get_needs_approval_for_tool\s*\(\s*tool\s*,\s*agent\s*\)"
        r"[\s\S]{0,1800}?_build_wrapped_function_tool\s*\([\s\S]{0,1200}?"
        r"needs_approval\s*=\s*needs_approval",
        util_text,
    ):
        return

    candidates: list[
        tuple[str, str, ast.AsyncWith, ast.Call, str, str, ast.Call, str, str]
    ] = []
    for app_path, app_text, tree in sources:
        imported_stdio = False
        imported_agent = False
        for statement in tree.body:
            if not isinstance(statement, ast.ImportFrom):
                continue
            if statement.module == "agents.mcp":
                imported_stdio = any(
                    alias.name == "MCPServerStdio" and alias.asname is None
                    for alias in statement.names
                )
            if statement.module == "agents.sandbox":
                imported_agent = any(
                    alias.name == "SandboxAgent" and alias.asname is None
                    for alias in statement.names
                )
        if not (imported_stdio and imported_agent):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncWith) or len(node.items) != 1:
                continue
            item = node.items[0]
            if (
                not isinstance(item.context_expr, ast.Call)
                or dotted_name(item.context_expr.func) != "MCPServerStdio"
                or not isinstance(item.optional_vars, ast.Name)
            ):
                continue
            server_call = item.context_expr
            if any(keyword.arg == "require_approval" for keyword in server_call.keywords):
                continue
            server_binding = item.optional_vars.id
            server_name = "MCPServerStdio"
            for keyword in server_call.keywords:
                if (
                    keyword.arg == "name"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    server_name = keyword.value.value
            for child in node.body:
                if (
                    not isinstance(child, ast.Assign)
                    or len(child.targets) != 1
                    or not isinstance(child.targets[0], ast.Name)
                    or not isinstance(child.value, ast.Call)
                    or dotted_name(child.value.func) != "SandboxAgent"
                ):
                    continue
                agent_call = child.value
                mcp_keyword = next(
                    (
                        keyword
                        for keyword in agent_call.keywords
                        if keyword.arg == "mcp_servers"
                        and isinstance(keyword.value, ast.List)
                        and len(keyword.value.elts) == 1
                        and isinstance(keyword.value.elts[0], ast.Name)
                        and keyword.value.elts[0].id == server_binding
                    ),
                    None,
                )
                if mcp_keyword is None:
                    continue
                agent_binding = child.targets[0].id
                agent_name = agent_binding
                for keyword in agent_call.keywords:
                    if (
                        keyword.arg == "name"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        agent_name = keyword.value.value
                candidates.append(
                    (
                        app_path,
                        app_text,
                        node,
                        server_call,
                        server_name,
                        server_binding,
                        agent_call,
                        agent_name,
                        agent_binding,
                    )
                )
    if len(candidates) != 1:
        return
    (
        app_path,
        app_text,
        _with_node,
        server_call,
        server_name,
        server_binding,
        agent_call,
        agent_name,
        agent_binding,
    ) = candidates[0]
    server_line = server_call.lineno
    agent_line = agent_call.lineno
    server_evidence = Evidence(
        app_path,
        server_line,
        excerpt(app_text.splitlines(), server_line),
    )
    agent_evidence = Evidence(
        app_path,
        agent_line,
        excerpt(app_text.splitlines(), agent_line),
    )
    analysis = "python-openai-agents-mcp-approval-default"
    agent_id = source_symbol("py", app_path, "agent", agent_binding)
    server_id = source_symbol("py", app_path, "mcp-server", server_binding)
    agent_attributes = {
        "framework": "OpenAI Agents SDK",
        "constructor": "SandboxAgent",
        "scope": source_scope(app_path),
        "analysis": analysis,
    }
    server_attributes = {
        "transport": "stdio",
        "approval_policy": "disabled-default",
        "approval_source": "sdk-default",
        "scope": source_scope(app_path),
        "analysis": analysis,
    }
    for component in ir.components:
        if component.symbol_id == agent_id:
            component.attributes.update(agent_attributes)
        elif component.symbol_id == server_id:
            component.attributes.update(server_attributes)
    ir.add_component(
        Component(
            "agent",
            agent_name,
            agent_evidence,
            agent_attributes,
            agent_id,
        )
    )
    ir.add_component(
        Component(
            "mcp-server",
            server_name,
            server_evidence,
            server_attributes,
            server_id,
        )
    )
    setting_attributes = {
        "enabled": False,
        "approval_policy": "disabled-default",
        "approval_source": "sdk-default",
        "policy_scope": "all-discovered-mcp-tools",
        "missing_tool_mapping_default": "disabled",
        "server_path": server_path,
        "util_path": util_path,
        "analysis": analysis,
        "scope": source_scope(app_path),
    }
    ir.add_component(
        Component("control-setting", "mcp-tool-approval", server_evidence, setting_attributes)
    )
    ir.add_relationship(
        Relationship(
            "agent",
            agent_name,
            "uses",
            "mcp-server",
            server_name,
            agent_evidence,
            {"analysis": analysis, "approval_policy": "disabled-default"},
            agent_id,
            server_id,
        )
    )
    for relationship in ir.relationships:
        if (
            relationship.source_id == agent_id
            and relationship.target_id == server_id
            and relationship.source_kind == "agent"
            and relationship.target_kind == "mcp-server"
        ):
            relationship.attributes.update(
                {"analysis": analysis, "approval_policy": "disabled-default"}
            )
    ir.add_relationship(
        Relationship(
            "mcp-server",
            server_name,
            "configured-by",
            "control-setting",
            "mcp-tool-approval",
            server_evidence,
            setting_attributes,
        )
    )


TS_OPENAI_MCP_READ_ONLY_FILESYSTEM_TOOLS = frozenset(
    {
        "directory_tree",
        "get_file_info",
        "list_allowed_directories",
        "list_directory",
        "list_directory_with_sizes",
        "read_file",
        "read_media_file",
        "read_multiple_files",
        "read_text_file",
        "search_files",
    }
)


def typescript_literal_or_template_text(expression: str) -> str | None:
    """Return a string/template body while retaining template substitutions as text."""
    expression = expression.strip()
    match = re.fullmatch(r"(['\"])(.*?)\1", expression, re.DOTALL)
    if match is not None:
        return match.group(2)
    match = re.fullmatch(r"`(.*)`", expression, re.DOTALL)
    return match.group(1) if match is not None else None


def typescript_openai_mcp_filesystem_package(
    text: str,
    options: str,
    server_offset: int,
) -> str | None:
    """Resolve the exact local filesystem MCP package from one stdio options object."""
    full_command = typescript_literal_object_property_expression(options, "fullCommand")
    if full_command is not None:
        command_text = typescript_literal_or_template_text(full_command)
        if command_text is not None:
            interpolation = command_text.find("${")
            literal_prefix = command_text if interpolation < 0 else command_text[:interpolation]
            if re.search(r"(?:^|\s)mcp-server-filesystem(?:\s|$)", literal_prefix):
                return "@modelcontextprotocol/server-filesystem"

    command = typescript_literal_object_property_expression(options, "command")
    arguments_expression = typescript_literal_object_property_expression(options, "args")
    if command is None or command.strip() != "process.execPath" or arguments_expression is None:
        return None
    arguments_code = typescript_code_mask(arguments_expression)
    opening = len(arguments_code) - len(arguments_code.lstrip())
    if opening >= len(arguments_code) or arguments_code[opening] != "[":
        return None
    end = typescript_balanced_end(arguments_code, opening, "[", "]")
    if end is None or arguments_code[end:].strip() not in {"", "as const"}:
        return None
    arguments = typescript_call_arguments(arguments_expression[opening + 1 : end - 1])
    if not arguments:
        return None
    require_match = re.fullmatch(
        r"([A-Za-z_$][\w$]*)\.resolve\s*\(\s*(['\"])"
        r"@modelcontextprotocol/server-filesystem/dist/index\.js\2\s*\)",
        arguments[0][0].strip(),
        re.DOTALL,
    )
    if require_match is None:
        return None
    require_name = require_match.group(1)
    node_imports = typescript_named_import_bindings(text, "node:module")
    create_require_names = {
        name
        for name, original in node_imports.items()
        if original == "createRequire" and not typescript_import_binding_is_shadowed(text, name)
    }
    if not create_require_names:
        return None
    require_assignments = [
        match
        for match in re.finditer(
            rf"\bconst\s+{re.escape(require_name)}\s*=\s*"
            r"([A-Za-z_$][\w$]*)\s*\(\s*import\.meta\.url\s*\)",
            typescript_code_mask(text),
        )
        if match.group(1) in create_require_names and match.start() < server_offset
    ]
    if len(require_assignments) != 1:
        return None
    if re.search(
        rf"(?<![\w$.]){re.escape(require_name)}\s*=(?!=)",
        typescript_code_mask(text)[require_assignments[0].end() : server_offset],
    ):
        return None
    return "@modelcontextprotocol/server-filesystem"


def typescript_openai_mcp_read_only_filter(
    text: str,
    options: str,
) -> tuple[bool, list[str]]:
    """Prove a static MCP filter exposes only known read-only filesystem tools."""
    expression = typescript_literal_object_property_expression(options, "toolFilter")
    if expression is None:
        return False, []
    call = typescript_call_parts(expression)
    if call is None:
        return False, []
    factory, body, _ = call
    imports = typescript_named_import_bindings(text, "@openai/agents")
    if (
        imports.get(factory) != "createMCPToolStaticFilter"
        or typescript_import_binding_is_shadowed(text, factory)
    ):
        return False, []
    call_arguments = typescript_call_arguments(body)
    if not call_arguments:
        return False, []
    allowed_expression = typescript_literal_object_property_expression(
        call_arguments[0][0], "allowed"
    )
    if allowed_expression is None:
        return False, []
    allowed = typescript_literal_string_arguments(allowed_expression)
    if not allowed or any(name is None for name in allowed):
        return False, []
    allowed_names = [name for name in allowed if name is not None]
    return (
        bool(allowed_names)
        and set(allowed_names) <= TS_OPENAI_MCP_READ_ONLY_FILESYSTEM_TOOLS,
        allowed_names,
    )


def add_typescript_openai_agents_mcp_approval_default_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve writable local MCP tools through the OpenAI Agents JS approval default."""
    selected: dict[str, tuple[str, list[str]]] = {}
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        selected[path.relative_to(root).as_posix()] = (text, text.splitlines())

    source_paths = {
        "agent": "packages/agents-core/src/agent.ts",
        "mcp": "packages/agents-core/src/mcp.ts",
        "tool": "packages/agents-core/src/tool.ts",
    }
    if not all(path in selected for path in source_paths.values()):
        return
    agent_source = selected[source_paths["agent"]][0]
    mcp_source = selected[source_paths["mcp"]][0]
    tool_source = selected[source_paths["tool"]][0]
    if not all(
        marker in agent_source
        for marker in (
            "this.mcpServers = config.mcpServers ?? [];",
            "return getAllMcpTools({",
            "mcpServers: this.mcpServers,",
            "return [...mcpTools, ...enabledTools];",
        )
    ):
        return
    mcp_conversion_offset = mcp_source.find("export function mcpToFunctionTool")
    if mcp_conversion_offset < 0:
        return
    mcp_conversion = mcp_source[mcp_conversion_offset:]
    if (
        not mcp_conversion
        or mcp_conversion.count("return tool({") < 2
        or "needsApproval" in mcp_conversion
        or "mcpTools.map((mcpTool, index) =>" not in mcp_source
        or "mcpToFunctionTool(mcpTool, server" not in mcp_source
    ):
        return
    if not re.search(
        r"const\s+needsApproval[\s\S]{0,300}?typeof\s+options\.needsApproval\s*===\s*"
        r"['\"]boolean['\"][\s\S]{0,100}?options\.needsApproval[\s\S]{0,100}?:\s*false",
        tool_source,
    ):
        return

    analysis = "typescript-openai-agents-mcp-approval-default"
    for relative, (text, lines) in selected.items():
        if relative in source_paths.values() or "MCPServerStdio" not in text:
            continue
        imports = typescript_named_import_bindings(text, "@openai/agents")
        server_constructors = {
            name
            for name, original in imports.items()
            if original == "MCPServerStdio"
            and not typescript_import_binding_is_shadowed(text, name)
        }
        agent_constructors = {
            name
            for name, original in imports.items()
            if original == "Agent" and not typescript_import_binding_is_shadowed(text, name)
        }
        if not server_constructors or not agent_constructors:
            continue
        code = typescript_code_mask(text)
        declaration_counts = Counter(
            re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\b", code)
        )
        servers: dict[str, tuple[str, str, Evidence, bool, list[str]]] = {}
        for constructor in server_constructors:
            pattern = re.compile(
                rf"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*new\s+{re.escape(constructor)}\s*\("
            )
            for match in pattern.finditer(code):
                binding = match.group(1)
                if declaration_counts[binding] != 1:
                    continue
                opening = code.find("(", match.start(), match.end())
                end = typescript_balanced_end(code, opening, "(", ")")
                if end is None or re.search(
                    rf"(?<![\w$.]){re.escape(binding)}\s*=(?!=)", code[end:]
                ):
                    continue
                call_arguments = typescript_call_arguments(
                    text[opening + 1 : end - 1], opening + 1
                )
                if not call_arguments:
                    continue
                options, _ = call_arguments[0]
                package = typescript_openai_mcp_filesystem_package(
                    text, options, match.start()
                )
                if package is None:
                    continue
                line = line_at(text, match.start())
                evidence = Evidence(relative, line, excerpt(lines, line))
                display_name = (
                    typescript_literal_object_string_property(options, "name") or binding
                )
                filter_proven, allowed_tools = typescript_openai_mcp_read_only_filter(
                    text, options
                )
                server_id = source_symbol("ts", relative, "mcp-server", binding)
                servers[binding] = (
                    display_name,
                    server_id,
                    evidence,
                    filter_proven,
                    allowed_tools,
                )
                server_attributes = {
                    "transport": "stdio",
                    "constructor": "MCPServerStdio",
                    "framework": "OpenAI Agents SDK",
                    "package": package,
                    "capability": "filesystem",
                    "approval_policy": "disabled-default",
                    "approval_source": "sdk-function-tool-default",
                    "tool_filter": "read-only-static" if filter_proven else "absent-or-unresolved",
                    "scope": source_scope(relative),
                    "analysis": analysis,
                }
                ir.add_component(
                    Component(
                        "mcp-server",
                        display_name,
                        evidence,
                        server_attributes,
                        server_id,
                    )
                )
                capability_attributes = {
                    "write_access": not filter_proven,
                    "package": package,
                    "approval_policy": "disabled-default",
                    "tool_filter": server_attributes["tool_filter"],
                    "scope": source_scope(relative),
                    "analysis": analysis,
                }
                ir.add_component(
                    Component("capability", "filesystem", evidence, capability_attributes)
                )
                ir.add_relationship(
                    Relationship(
                        "mcp-server",
                        display_name,
                        "uses",
                        "capability",
                        "filesystem",
                        evidence,
                        capability_attributes,
                        source_id=server_id,
                    )
                )
                setting_attributes = {
                    "enabled": False,
                    "approval_policy": "disabled-default",
                    "approval_source": "sdk-function-tool-default",
                    "policy_scope": "all-converted-local-mcp-tools",
                    "agent_source_path": source_paths["agent"],
                    "mcp_source_path": source_paths["mcp"],
                    "tool_source_path": source_paths["tool"],
                    "scope": source_scope(relative),
                    "analysis": analysis,
                }
                ir.add_component(
                    Component(
                        "control-setting",
                        "mcp-tool-approval",
                        evidence,
                        setting_attributes,
                    )
                )
                ir.add_relationship(
                    Relationship(
                        "mcp-server",
                        display_name,
                        "configured-by",
                        "control-setting",
                        "mcp-tool-approval",
                        evidence,
                        setting_attributes,
                        source_id=server_id,
                    )
                )
                if filter_proven:
                    control_attributes = {
                        "policy_effect": "blocks-filesystem-mutation",
                        "allowed_tools": allowed_tools,
                        "scope": source_scope(relative),
                        "analysis": analysis,
                    }
                    ir.add_component(
                        Component("control", "mcp-tool-filter", evidence, control_attributes)
                    )
                    ir.add_relationship(
                        Relationship(
                            "capability",
                            "filesystem",
                            "governed-by",
                            "control",
                            "mcp-tool-filter",
                            evidence,
                            control_attributes,
                        )
                    )

        if not servers:
            continue
        for constructor in agent_constructors:
            pattern = re.compile(
                rf"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*new\s+{re.escape(constructor)}\s*\("
            )
            for match in pattern.finditer(code):
                agent_binding = match.group(1)
                opening = code.find("(", match.start(), match.end())
                end = typescript_balanced_end(code, opening, "(", ")")
                if end is None:
                    continue
                call_arguments = typescript_call_arguments(
                    text[opening + 1 : end - 1], opening + 1
                )
                if not call_arguments:
                    continue
                options, _ = call_arguments[0]
                servers_expression = typescript_literal_object_property_expression(
                    options, "mcpServers"
                )
                server_bindings = (
                    typescript_literal_identifier_arguments(servers_expression)
                    if servers_expression is not None
                    else None
                )
                if server_bindings is None:
                    continue
                agent_line = line_at(text, match.start())
                agent_evidence = Evidence(
                    relative, agent_line, excerpt(lines, agent_line)
                )
                agent_name = (
                    typescript_literal_object_string_property(options, "name")
                    or agent_binding
                )
                agent_id = source_symbol("ts", relative, "agent", agent_binding)
                ir.add_component(
                    Component(
                        "agent",
                        agent_name,
                        agent_evidence,
                        {
                            "constructor": "Agent",
                            "framework": "OpenAI Agents SDK",
                            "scope": source_scope(relative),
                            "analysis": analysis,
                        },
                        agent_id,
                    )
                )
                for server_binding in server_bindings:
                    if server_binding is None or server_binding not in servers:
                        continue
                    server_name, server_id, _evidence, filter_proven, _allowed = servers[
                        server_binding
                    ]
                    ir.add_relationship(
                        Relationship(
                            "agent",
                            agent_name,
                            "uses",
                            "mcp-server",
                            server_name,
                            agent_evidence,
                            {
                                "approval_policy": "disabled-default",
                                "write_access": not filter_proven,
                                "analysis": analysis,
                            },
                            source_id=agent_id,
                            target_id=server_id,
                        )
                    )


AGNO_MCP_FILESYSTEM_MUTATING_TOOLS = frozenset(
    {"create_directory", "edit_file", "move_file", "write_file"}
)
AGNO_MCP_FILESYSTEM_READ_ONLY_TOOLS = frozenset(
    {
        "directory_tree",
        "get_file_info",
        "list_allowed_directories",
        "list_directory",
        "list_directory_with_sizes",
        "read_file",
        "read_media_file",
        "read_multiple_files",
        "read_text_file",
        "search_files",
    }
)


def python_exact_import_name(
    tree: ast.Module,
    module: str,
    exported: str,
) -> str | None:
    """Return one immutable module-level binding for an exact Python import."""
    matches = [
        alias.asname or alias.name
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom) and statement.module == module
        for alias in statement.names
        if alias.name == exported
    ]
    if len(matches) != 1:
        return None
    binding = matches[0]
    if any(
        isinstance(node, ast.Name)
        and isinstance(node.ctx, (ast.Store, ast.Del))
        and node.id == binding
        for node in ast.walk(tree)
    ) or any(
        isinstance(node, ast.arg) and node.arg == binding for node in ast.walk(tree)
    ):
        return None
    return binding


def python_exact_module_scope_import_name(
    tree: ast.Module,
    module: str,
    exported: str,
) -> str | None:
    """Return one immutable module binding, including imports inside try/with guards."""

    def import_guard_statements(statements: list[ast.stmt]) -> list[ast.stmt]:
        guarded: list[ast.stmt] = []
        for statement in statements:
            guarded.append(statement)
            if isinstance(statement, (ast.With, ast.AsyncWith)):
                guarded.extend(import_guard_statements(statement.body))
            elif isinstance(statement, (ast.Try, ast.TryStar)):
                guarded.extend(import_guard_statements(statement.body))
                guarded.extend(import_guard_statements(statement.orelse))
                guarded.extend(import_guard_statements(statement.finalbody))
                for handler in statement.handlers:
                    guarded.extend(import_guard_statements(handler.body))
        return guarded

    matches = [
        alias.asname or alias.name
        for statement in import_guard_statements(tree.body)
        if isinstance(statement, ast.ImportFrom) and statement.module == module
        for alias in statement.names
        if alias.name == exported
    ]
    if len(matches) != 1:
        return None
    binding = matches[0]
    if any(
        isinstance(node, ast.Name)
        and isinstance(node.ctx, (ast.Store, ast.Del))
        and node.id == binding
        for node in ast.walk(tree)
    ) or any(
        isinstance(node, ast.arg) and node.arg == binding for node in ast.walk(tree)
    ):
        return None
    return binding


def python_exact_module_import_name(tree: ast.Module, module: str) -> str | None:
    """Return one immutable module binding for an exact Python import."""
    matches = [
        alias.asname or alias.name
        for statement in tree.body
        if isinstance(statement, ast.Import)
        for alias in statement.names
        if alias.name == module and (alias.asname is not None or "." not in alias.name)
    ]
    if len(matches) != 1:
        return None
    binding = matches[0]
    if any(
        isinstance(node, ast.Name)
        and isinstance(node.ctx, (ast.Store, ast.Del))
        and node.id == binding
        for node in ast.walk(tree)
    ) or any(
        isinstance(node, ast.arg) and node.arg == binding for node in ast.walk(tree)
    ):
        return None
    return binding


def python_scope_nodes(body: list[ast.stmt]) -> list[ast.AST]:
    """Walk one lexical Python body without descending into nested definitions."""
    nodes: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        nodes.append(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        for child in ast.iter_child_nodes(node):
            visit(child)

    for statement in body:
        visit(statement)
    return nodes


def python_literal_string_list(node: ast.AST | None) -> list[str] | None:
    """Return a list/tuple only when every element is a literal string."""
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values = [
        item.value
        for item in node.elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    ]
    return values if len(values) == len(node.elts) else None


def python_call_keyword(call: ast.Call, name: str) -> ast.AST | None:
    """Return one unambiguous named keyword value from a Python call."""
    values = [keyword.value for keyword in call.keywords if keyword.arg == name]
    return values[0] if len(values) == 1 else None


def python_agno_filesystem_command(expression: ast.AST | None) -> str | None:
    """Recognize an Agno full command for the official filesystem MCP package."""
    if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
        try:
            arguments = shlex.split(expression.value)
        except ValueError:
            return None
        package = mcp_package_reference(arguments[0], arguments[1:]) if arguments else None
        if package and package.get("package") == "@modelcontextprotocol/server-filesystem":
            return expression.value
        return None
    if not isinstance(expression, ast.JoinedStr):
        return None
    structural = "".join(
        value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else " <root> "
        for value in expression.values
    )
    if re.search(
        r"^\s*npx\s+(?:-y|--yes)\s+@modelcontextprotocol/server-filesystem(?:\s|$)",
        structural,
    ):
        return ast.unparse(expression)
    return None


def add_python_agno_mcp_confirmation_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve Agno filesystem MCP exposure through its per-tool confirmation default."""
    selected: dict[str, tuple[str, list[str], ast.Module]] = {}
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        selected[path.relative_to(root).as_posix()] = (text, text.splitlines(), tree)

    sdk_path = "libs/agno/agno/tools/mcp/mcp.py"
    if sdk_path not in selected:
        return
    sdk_source = selected[sdk_path][0]
    if not all(
        marker in sdk_source
        for marker in (
            'requires_confirmation_tools = kwargs.pop("requires_confirmation_tools", None)',
            "self.requires_confirmation_tools = requires_confirmation_tools or []",
            "if self.include_tools is None or tool.name in self.include_tools:",
            "requires_confirmation=tool_name in self.requires_confirmation_tools",
            "self.functions[f.name] = f",
        )
    ):
        return

    analysis = "python-agno-mcp-confirmation-default"
    for relative, (text, lines, tree) in selected.items():
        if relative == sdk_path or "server-filesystem" not in text:
            continue
        agent_constructor = python_exact_import_name(tree, "agno.agent", "Agent")
        mcp_constructor = python_exact_import_name(tree, "agno.tools.mcp", "MCPTools")
        if agent_constructor is None or mcp_constructor is None:
            continue
        stdio_parameters = python_exact_import_name(tree, "mcp", "StdioServerParameters")
        client_session = python_exact_import_name(tree, "mcp", "ClientSession")
        stdio_client_name = python_exact_import_name(
            tree, "mcp.client.stdio", "stdio_client"
        )

        scopes: list[tuple[str, list[ast.stmt]]] = [("module", tree.body)]
        scopes.extend(
            (statement.name, statement.body)
            for statement in tree.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for _scope_name, body in scopes:
            nodes = python_scope_nodes(body)
            store_counts = Counter(
                node.id
                for node in nodes
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
            )

            server_parameters: list[tuple[str, ast.Call]] = []
            if stdio_parameters is not None:
                for node in nodes:
                    if (
                        isinstance(node, ast.Assign)
                        and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id == stdio_parameters
                    ):
                        command = python_call_keyword(node.value, "command")
                        arguments = literal_string_arguments(
                            python_call_keyword(node.value, "args")
                        )
                        package = (
                            mcp_package_reference(command.value, arguments)
                            if isinstance(command, ast.Constant)
                            and isinstance(command.value, str)
                            and arguments is not None
                            else None
                        )
                        if (
                            package
                            and package.get("package")
                            == "@modelcontextprotocol/server-filesystem"
                            and store_counts[node.targets[0].id] == 1
                        ):
                            server_parameters.append((node.targets[0].id, node.value))

            session_ranges: dict[str, list[tuple[int, int]]] = defaultdict(list)
            if client_session is not None and stdio_client_name is not None:
                stdio_parameter_names = {name for name, _call in server_parameters}
                for stdio_with in nodes:
                    if not isinstance(stdio_with, ast.AsyncWith):
                        continue
                    for stdio_item in stdio_with.items:
                        stdio_call = stdio_item.context_expr
                        channels = stdio_item.optional_vars
                        if not (
                            isinstance(stdio_call, ast.Call)
                            and isinstance(stdio_call.func, ast.Name)
                            and stdio_call.func.id == stdio_client_name
                            and len(stdio_call.args) == 1
                            and isinstance(stdio_call.args[0], ast.Name)
                            and stdio_call.args[0].id in stdio_parameter_names
                            and isinstance(channels, (ast.Tuple, ast.List))
                            and len(channels.elts) == 2
                            and all(isinstance(item, ast.Name) for item in channels.elts)
                        ):
                            continue
                        channel_names = [
                            item.id for item in channels.elts if isinstance(item, ast.Name)
                        ]
                        for session_with in python_scope_nodes(stdio_with.body):
                            if not isinstance(session_with, ast.AsyncWith):
                                continue
                            for session_item in session_with.items:
                                session_call = session_item.context_expr
                                session_target = session_item.optional_vars
                                if not (
                                    isinstance(session_call, ast.Call)
                                    and isinstance(session_call.func, ast.Name)
                                    and session_call.func.id == client_session
                                    and len(session_call.args) == 2
                                    and [
                                        argument.id
                                        for argument in session_call.args
                                        if isinstance(argument, ast.Name)
                                    ]
                                    == channel_names
                                    and isinstance(session_target, ast.Name)
                                    and store_counts[session_target.id] == 1
                                ):
                                    continue
                                session_ranges[session_target.id].append(
                                    (
                                        session_with.lineno,
                                        getattr(
                                            session_with,
                                            "end_lineno",
                                            session_with.lineno,
                                        ),
                                    )
                                )

            mcp_candidates: list[tuple[str, ast.Call, ast.Call]] = []
            for node in nodes:
                binding: str | None = None
                call: ast.Call | None = None
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Call)
                ):
                    binding = node.targets[0].id
                    call = node.value
                elif isinstance(node, ast.AsyncWith):
                    for item in node.items:
                        if isinstance(item.optional_vars, ast.Name) and isinstance(
                            item.context_expr, ast.Call
                        ):
                            binding = item.optional_vars.id
                            call = item.context_expr
                            if (
                                isinstance(call.func, ast.Name)
                                and call.func.id == mcp_constructor
                            ):
                                break
                            binding = None
                            call = None
                if (
                    binding is None
                    or call is None
                    or not isinstance(call.func, ast.Name)
                    or call.func.id != mcp_constructor
                    or store_counts[binding] != 1
                ):
                    continue
                command_expression = (
                    call.args[0]
                    if call.args
                    else python_call_keyword(call, "command")
                )
                direct_command = python_agno_filesystem_command(command_expression)
                session_expression = python_call_keyword(call, "session")
                session_proven = (
                    isinstance(session_expression, ast.Name)
                    and any(
                        start <= call.lineno <= end
                        for start, end in session_ranges.get(session_expression.id, [])
                    )
                    and len(server_parameters) == 1
                )
                if direct_command is not None or session_proven:
                    evidence_call = call if direct_command is not None else server_parameters[0][1]
                    mcp_candidates.append((binding, call, evidence_call))

            for mcp_binding, mcp_call, evidence_call in mcp_candidates:
                include_expression = python_call_keyword(mcp_call, "include_tools")
                include_tools = (
                    python_literal_string_list(include_expression)
                    if include_expression is not None
                    else None
                )
                filter_proven = bool(include_tools) and set(include_tools or []) <= (
                    AGNO_MCP_FILESYSTEM_READ_ONLY_TOOLS
                )
                available_mutations = (
                    set()
                    if filter_proven
                    else set(AGNO_MCP_FILESYSTEM_MUTATING_TOOLS)
                    if include_tools is None
                    else set(include_tools) & set(AGNO_MCP_FILESYSTEM_MUTATING_TOOLS)
                )
                confirmation_expression = python_call_keyword(
                    mcp_call, "requires_confirmation_tools"
                )
                confirmation_tools = (
                    python_literal_string_list(confirmation_expression)
                    if confirmation_expression is not None
                    else None
                )
                if confirmation_expression is None:
                    approval_policy = "disabled-default"
                    setting_enabled: bool | None = False
                    protected_mutations: set[str] = set()
                elif confirmation_tools is None:
                    approval_policy = "unresolved-explicit"
                    setting_enabled = None
                    protected_mutations = set()
                else:
                    protected_mutations = available_mutations & set(confirmation_tools)
                    if not confirmation_tools:
                        approval_policy = "disabled-explicit"
                        setting_enabled = False
                    elif available_mutations <= protected_mutations:
                        approval_policy = "enabled-static-mutations"
                        setting_enabled = True
                    else:
                        approval_policy = "partial-static"
                        setting_enabled = True
                unprotected_mutations = sorted(available_mutations - protected_mutations)

                agent_calls: list[tuple[str, ast.Call]] = []
                for node in nodes:
                    if not (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == agent_constructor
                        and node.lineno >= mcp_call.lineno
                    ):
                        continue
                    tools_expression = python_call_keyword(node, "tools")
                    if not isinstance(tools_expression, (ast.List, ast.Tuple)) or not any(
                        isinstance(item, ast.Name) and item.id == mcp_binding
                        for item in tools_expression.elts
                    ):
                        continue
                    binding = f"Agent@{node.lineno}"
                    for assignment in nodes:
                        if (
                            isinstance(assignment, ast.Assign)
                            and assignment.value is node
                            and len(assignment.targets) == 1
                            and isinstance(assignment.targets[0], ast.Name)
                            and store_counts[assignment.targets[0].id] == 1
                        ):
                            binding = assignment.targets[0].id
                    agent_calls.append((binding, node))
                if not agent_calls:
                    continue

                server_line = evidence_call.lineno
                server_evidence = Evidence(
                    relative, server_line, excerpt(lines, server_line)
                )
                server_name = f"Agno filesystem@{server_line}"
                server_id = source_symbol("py", relative, "mcp-server", mcp_binding)
                server_attributes = {
                    "transport": "stdio",
                    "framework": "Agno",
                    "constructor": "MCPTools",
                    "package": "@modelcontextprotocol/server-filesystem",
                    "capability": "filesystem",
                    "tool_filter": "read-only-static" if filter_proven else "absent-or-unresolved",
                    "approval_policy": approval_policy,
                    "approval_source": "agno-requires-confirmation-tools",
                    "scope": source_scope(relative),
                    "analysis": analysis,
                }
                ir.add_component(
                    Component(
                        "mcp-server",
                        server_name,
                        server_evidence,
                        server_attributes,
                        server_id,
                    )
                )
                capability_attributes = {
                    "write_access": bool(available_mutations),
                    "package": "@modelcontextprotocol/server-filesystem",
                    "tool_filter": server_attributes["tool_filter"],
                    "approval_policy": approval_policy,
                    "unprotected_mutations": unprotected_mutations,
                    "scope": source_scope(relative),
                    "analysis": analysis,
                }
                ir.add_component(
                    Component("capability", "filesystem", server_evidence, capability_attributes)
                )
                ir.add_relationship(
                    Relationship(
                        "mcp-server",
                        server_name,
                        "uses",
                        "capability",
                        "filesystem",
                        server_evidence,
                        capability_attributes,
                        source_id=server_id,
                    )
                )
                setting_attributes = {
                    "enabled": setting_enabled,
                    "approval_policy": approval_policy,
                    "approval_source": "agno-requires-confirmation-tools",
                    "protected_mutations": sorted(protected_mutations),
                    "unprotected_mutations": unprotected_mutations,
                    "sdk_source_path": sdk_path,
                    "scope": source_scope(relative),
                    "analysis": analysis,
                }
                ir.add_component(
                    Component(
                        "control-setting",
                        "mcp-tool-confirmation",
                        server_evidence,
                        setting_attributes,
                    )
                )
                ir.add_relationship(
                    Relationship(
                        "mcp-server",
                        server_name,
                        "configured-by",
                        "control-setting",
                        "mcp-tool-confirmation",
                        server_evidence,
                        setting_attributes,
                        source_id=server_id,
                    )
                )
                if filter_proven:
                    control_attributes = {
                        "policy_effect": "blocks-filesystem-mutation",
                        "allowed_tools": include_tools,
                        "scope": source_scope(relative),
                        "analysis": analysis,
                    }
                    ir.add_component(
                        Component("control", "mcp-tool-filter", server_evidence, control_attributes)
                    )
                    ir.add_relationship(
                        Relationship(
                            "capability",
                            "filesystem",
                            "governed-by",
                            "control",
                            "mcp-tool-filter",
                            server_evidence,
                            control_attributes,
                        )
                    )
                elif available_mutations and not unprotected_mutations:
                    control_attributes = {
                        "policy_effect": "requires-confirmation-for-filesystem-mutation",
                        "protected_mutations": sorted(protected_mutations),
                        "scope": source_scope(relative),
                        "analysis": analysis,
                    }
                    ir.add_component(
                        Component("control", "human-approval", server_evidence, control_attributes)
                    )
                    ir.add_relationship(
                        Relationship(
                            "capability",
                            "filesystem",
                            "governed-by",
                            "control",
                            "human-approval",
                            server_evidence,
                            control_attributes,
                        )
                    )

                for agent_binding, agent_call in agent_calls:
                    agent_name_expression = python_call_keyword(agent_call, "name")
                    agent_name = (
                        agent_name_expression.value
                        if isinstance(agent_name_expression, ast.Constant)
                        and isinstance(agent_name_expression.value, str)
                        else agent_binding
                    )
                    agent_evidence = Evidence(
                        relative,
                        agent_call.lineno,
                        excerpt(lines, agent_call.lineno),
                    )
                    agent_id = source_symbol("py", relative, "agent", agent_binding)
                    ir.add_component(
                        Component(
                            "agent",
                            agent_name,
                            agent_evidence,
                            {
                                "constructor": "Agent",
                                "framework": "Agno",
                                "scope": source_scope(relative),
                                "analysis": analysis,
                            },
                            agent_id,
                        )
                    )
                    ir.add_relationship(
                        Relationship(
                            "agent",
                            agent_name,
                            "uses",
                            "mcp-server",
                            server_name,
                            agent_evidence,
                            {
                                "approval_policy": approval_policy,
                                "write_access": bool(available_mutations),
                                "analysis": analysis,
                            },
                            source_id=agent_id,
                            target_id=server_id,
                        )
                    )


SEMANTIC_KERNEL_MCP_PLUGIN_CONSTRUCTORS = {
    "MCPStdioPlugin": "stdio",
    "MCPSsePlugin": "sse",
    "MCPStreamableHttpPlugin": "streamable-http",
    "MCPWebsocketPlugin": "websocket",
}


def add_python_semantic_kernel_mcp_sampling_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve MCP server-originated model sampling through Semantic Kernel policy."""
    selected: dict[str, tuple[str, list[str], ast.Module]] = {}
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        selected[path.relative_to(root).as_posix()] = (text, text.splitlines(), tree)

    sdk_path = "python/semantic_kernel/connectors/mcp.py"
    if sdk_path not in selected:
        return
    sdk_source = selected[sdk_path][0]
    if not all(
        marker in sdk_source
        for marker in (
            "sampling_auto_approve: bool = False",
            "sampling_auto_approve=sampling_auto_approve,",
            "sampling_callback=self.sampling_callback",
            "if self.sampling_consent_callback is None:",
            "if not self.sampling_auto_approve:",
            "elif not await self._is_sampling_approved(params):",
            "chat_history = ChatHistory(system_message=params.systemPrompt)",
            "completion_settings.max_completion_tokens = params.maxTokens",
            "result = await service.get_chat_message_content(",
            "return types.CreateMessageResult(",
        )
    ):
        return

    analysis = "python-semantic-kernel-mcp-sampling-approval"
    for relative, (text, lines, tree) in selected.items():
        if relative == sdk_path or "MCP" not in text or "Plugin" not in text:
            continue
        agent_constructor = python_exact_import_name(
            tree, "semantic_kernel.agents", "ChatCompletionAgent"
        )
        if agent_constructor is None:
            continue
        plugin_bindings = {
            binding: (exported, transport)
            for exported, transport in SEMANTIC_KERNEL_MCP_PLUGIN_CONSTRUCTORS.items()
            if (
                binding := python_exact_import_name(
                    tree, "semantic_kernel.connectors.mcp", exported
                )
            )
            is not None
        }
        if not plugin_bindings:
            continue

        scopes: list[list[ast.stmt]] = [tree.body]
        scopes.extend(
            statement.body
            for statement in tree.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for body in scopes:
            nodes = python_scope_nodes(body)
            store_counts = Counter(
                node.id
                for node in nodes
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
            )
            for context in nodes:
                if not isinstance(context, ast.AsyncWith):
                    continue
                context_nodes = python_scope_nodes(context.body)
                for item in context.items:
                    plugin_call = item.context_expr
                    plugin_target = item.optional_vars
                    if not (
                        isinstance(plugin_call, ast.Call)
                        and isinstance(plugin_call.func, ast.Name)
                        and plugin_call.func.id in plugin_bindings
                        and isinstance(plugin_target, ast.Name)
                        and store_counts[plugin_target.id] == 1
                    ):
                        continue
                    agent_calls = [
                        node
                        for node in context_nodes
                        if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == agent_constructor
                        and isinstance(
                            plugins_expression := python_call_keyword(node, "plugins"),
                            (ast.List, ast.Tuple),
                        )
                        and any(
                            isinstance(plugin, ast.Name)
                            and plugin.id == plugin_target.id
                            for plugin in plugins_expression.elts
                        )
                    ]
                    if not agent_calls:
                        continue

                    callback_expression = python_call_keyword(
                        plugin_call, "sampling_consent_callback"
                    )
                    callback_configured = callback_expression is not None and not (
                        isinstance(callback_expression, ast.Constant)
                        and callback_expression.value is None
                    )
                    auto_expression = python_call_keyword(
                        plugin_call, "sampling_auto_approve"
                    )
                    if callback_configured:
                        approval_policy = "callback-controlled"
                        auto_approved: bool | None = None
                        policy_expression = callback_expression
                    elif auto_expression is None:
                        approval_policy = "denied-default"
                        auto_approved = False
                        policy_expression = plugin_call
                    elif (
                        isinstance(auto_expression, ast.Constant)
                        and auto_expression.value is True
                    ):
                        approval_policy = "auto-approved-explicit"
                        auto_approved = True
                        policy_expression = auto_expression
                    elif (
                        isinstance(auto_expression, ast.Constant)
                        and auto_expression.value is False
                    ):
                        approval_policy = "denied-explicit"
                        auto_approved = False
                        policy_expression = auto_expression
                    else:
                        approval_policy = "unresolved-explicit"
                        auto_approved = None
                        policy_expression = auto_expression

                    ir.components = [
                        component
                        for component in ir.components
                        if not (
                            component.kind == "control-setting"
                            and component.name == "auto-approval"
                            and component.evidence.path == relative
                            and component.evidence.line == plugin_call.lineno
                        )
                    ]

                    exported, transport = plugin_bindings[plugin_call.func.id]
                    server_name_expression = python_call_keyword(plugin_call, "name")
                    server_name = (
                        server_name_expression.value
                        if isinstance(server_name_expression, ast.Constant)
                        and isinstance(server_name_expression.value, str)
                        else f"Semantic Kernel MCP@{plugin_call.lineno}"
                    )
                    server_evidence = Evidence(
                        relative,
                        plugin_call.lineno,
                        excerpt(lines, plugin_call.lineno),
                    )
                    policy_evidence = Evidence(
                        relative,
                        policy_expression.lineno,
                        excerpt(lines, policy_expression.lineno),
                    )
                    server_id = source_symbol(
                        "py", relative, "mcp-server", plugin_target.id
                    )
                    server_attributes = {
                        "framework": "Semantic Kernel",
                        "constructor": exported,
                        "transport": transport,
                        "sampling": "client-callback-enabled",
                        "approval_policy": approval_policy,
                        "scope": source_scope(relative),
                        "analysis": analysis,
                    }
                    ir.add_component(
                        Component(
                            "mcp-server",
                            server_name,
                            server_evidence,
                            server_attributes,
                            server_id,
                        )
                    )
                    capability_attributes = {
                        "input_authority": "mcp-server",
                        "system_prompt_authority": "mcp-server",
                        "model_hint_authority": "mcp-server",
                        "sampling_parameters_authority": "mcp-server",
                        "response_destination": "mcp-server",
                        "approval_policy": approval_policy,
                        "auto_approved": auto_approved,
                        "consent_callback": (
                            "configured" if callback_configured else "absent"
                        ),
                        "configuration_call_line": plugin_call.lineno,
                        "sdk_source_path": sdk_path,
                        "scope": source_scope(relative),
                        "analysis": analysis,
                    }
                    ir.add_component(
                        Component(
                            "capability",
                            "model-sampling",
                            policy_evidence,
                            capability_attributes,
                        )
                    )
                    ir.add_relationship(
                        Relationship(
                            "mcp-server",
                            server_name,
                            "uses",
                            "capability",
                            "model-sampling",
                            policy_evidence,
                            capability_attributes,
                            source_id=server_id,
                        )
                    )
                    setting_attributes = {
                        "enabled": auto_approved,
                        "approval_policy": approval_policy,
                        "consent_callback": (
                            "configured" if callback_configured else "absent"
                        ),
                        "scope": source_scope(relative),
                        "analysis": analysis,
                    }
                    ir.add_component(
                        Component(
                            "control-setting",
                            "mcp-sampling-approval",
                            policy_evidence,
                            setting_attributes,
                        )
                    )
                    ir.add_relationship(
                        Relationship(
                            "mcp-server",
                            server_name,
                            "configured-by",
                            "control-setting",
                            "mcp-sampling-approval",
                            policy_evidence,
                            setting_attributes,
                            source_id=server_id,
                        )
                    )
                    if approval_policy in {"denied-default", "denied-explicit"}:
                        control_attributes = {
                            "policy_effect": "denies-model-sampling-without-consent",
                            "approval_policy": approval_policy,
                            "scope": source_scope(relative),
                            "analysis": analysis,
                        }
                        ir.add_component(
                            Component(
                                "control",
                                "mcp-sampling-consent",
                                policy_evidence,
                                control_attributes,
                            )
                        )
                        ir.add_relationship(
                            Relationship(
                                "capability",
                                "model-sampling",
                                "governed-by",
                                "control",
                                "mcp-sampling-consent",
                                policy_evidence,
                                control_attributes,
                            )
                        )

                    for agent_call in agent_calls:
                        agent_name_expression = python_call_keyword(agent_call, "name")
                        agent_name = (
                            agent_name_expression.value
                            if isinstance(agent_name_expression, ast.Constant)
                            and isinstance(agent_name_expression.value, str)
                            else f"ChatCompletionAgent@{agent_call.lineno}"
                        )
                        agent_binding = f"ChatCompletionAgent@{agent_call.lineno}"
                        for assignment in context_nodes:
                            if (
                                isinstance(assignment, ast.Assign)
                                and assignment.value is agent_call
                                and len(assignment.targets) == 1
                                and isinstance(assignment.targets[0], ast.Name)
                                and store_counts[assignment.targets[0].id] == 1
                            ):
                                agent_binding = assignment.targets[0].id
                        agent_evidence = Evidence(
                            relative,
                            agent_call.lineno,
                            excerpt(lines, agent_call.lineno),
                        )
                        agent_id = source_symbol(
                            "py", relative, "agent", agent_binding
                        )
                        ir.add_component(
                            Component(
                                "agent",
                                agent_name,
                                agent_evidence,
                                {
                                    "constructor": "ChatCompletionAgent",
                                    "framework": "Semantic Kernel",
                                    "scope": source_scope(relative),
                                    "analysis": analysis,
                                },
                                agent_id,
                            )
                        )
                        ir.add_relationship(
                            Relationship(
                                "agent",
                                agent_name,
                                "uses",
                                "mcp-server",
                                server_name,
                                agent_evidence,
                                {
                                    "approval_policy": approval_policy,
                                    "model_sampling": True,
                                    "analysis": analysis,
                                },
                                source_id=agent_id,
                                target_id=server_id,
                            )
                        )


def add_mcp_sampling_consent_observation(
    ir: RepositoryIR,
    *,
    relative: str,
    lines: list[str],
    line: int,
    frontend: str,
    analysis: str,
    approval_policy: str,
    response_created: bool,
    fulfilment_target: str,
    callback_line: int | None,
    consent_line: int | None = None,
    request_disclosure: str = "unresolved",
    token_budget_line: int | None = None,
    extra_attributes: dict[str, object] | None = None,
) -> None:
    """Emit one exact MCP client sampling handler and its mediation state."""
    evidence = Evidence(relative, line, excerpt(lines, line))
    symbol_frontend = {"python": "py", "typescript": "ts"}.get(frontend, frontend)
    protocol_id = source_symbol(
        symbol_frontend,
        relative,
        "protocol",
        f"mcp-sampling@{line}",
    )
    common_attributes: dict[str, object] = {
        "frontend": frontend,
        "input_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": approval_policy,
        "response_created": response_created,
        "fulfilment_target": fulfilment_target,
        "callback_definition_line": callback_line,
        "request_disclosure": request_disclosure,
        "scope": source_scope(relative),
        "analysis": analysis,
        **(extra_attributes or {}),
    }
    ir.add_component(
        Component(
            "protocol",
            "MCP",
            evidence,
            {
                "role": "client",
                "sampling_handler": "registered",
                **common_attributes,
            },
            protocol_id,
        )
    )
    ir.add_component(
        Component(
            "capability",
            "model-sampling",
            evidence,
            common_attributes,
        )
    )
    ir.add_relationship(
        Relationship(
            "protocol",
            "MCP",
            "uses",
            "capability",
            "model-sampling",
            evidence,
            common_attributes,
            source_id=protocol_id,
        )
    )
    setting_attributes = {
        "enabled": (
            True
            if response_created
            else False
            if approval_policy == "denied-handler"
            else None
        ),
        "approval_policy": approval_policy,
        "scope": source_scope(relative),
        "analysis": analysis,
        **(extra_attributes or {}),
    }
    ir.add_component(
        Component(
            "control-setting",
            "mcp-sampling-fulfilment",
            evidence,
            setting_attributes,
        )
    )
    ir.add_relationship(
        Relationship(
            "protocol",
            "MCP",
            "configured-by",
            "control-setting",
            "mcp-sampling-fulfilment",
            evidence,
            setting_attributes,
            source_id=protocol_id,
        )
    )
    if consent_line is not None:
        control_attributes = {
            "policy_effect": "requires-user-decision-before-model-sampling",
            "request_disclosure": request_disclosure,
            "control_line": consent_line,
            "scope": source_scope(relative),
            "analysis": analysis,
        }
        ir.add_component(
            Component(
                "control",
                "mcp-sampling-consent",
                Evidence(relative, consent_line, excerpt(lines, consent_line)),
                control_attributes,
            )
        )
        ir.add_relationship(
            Relationship(
                "capability",
                "model-sampling",
                "governed-by",
                "control",
                "mcp-sampling-consent",
                evidence,
                control_attributes,
            )
        )
    if token_budget_line is not None:
        budget_attributes = {
            "policy_effect": "caps-server-requested-sampling-tokens",
            "control_line": token_budget_line,
            "scope": source_scope(relative),
            "analysis": analysis,
        }
        ir.add_component(
            Component(
                "control",
                "mcp-sampling-token-budget",
                Evidence(
                    relative,
                    token_budget_line,
                    excerpt(lines, token_budget_line),
                ),
                budget_attributes,
            )
        )
        ir.add_relationship(
            Relationship(
                "capability",
                "model-sampling",
                "governed-by",
                "control",
                "mcp-sampling-token-budget",
                evidence,
                budget_attributes,
            )
        )


def python_mcp_sampling_result_kind(
    node: ast.AST | None,
    types_binding: str | None,
) -> str | None:
    """Classify an exact mcp.types sampling callback return expression."""
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == types_binding
    ):
        return None
    if node.func.attr in {"CreateMessageResult", "CreateMessageResultWithTools"}:
        return "response"
    if node.func.attr == "ErrorData":
        return "error"
    return None


def python_mcp_sampling_human_consent(
    function: ast.AsyncFunctionDef,
    types_binding: str | None,
    successful_lines: set[int],
) -> int | None:
    """Prove a fail-closed interactive decision before a successful response."""
    interactive_names: dict[str, int] = {}
    for node in python_scope_nodes(function.body):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else None
        if isinstance(node, ast.AnnAssign):
            target = node.target
        value = node.value
        if not (
            isinstance(target, ast.Name)
            and isinstance(value, (ast.Call, ast.Await))
        ):
            continue
        call = value.value if isinstance(value, ast.Await) else value
        if not isinstance(call, ast.Call):
            continue
        callee = call.func
        if (
            isinstance(callee, ast.Name)
            and callee.id == "input"
            or isinstance(callee, ast.Attribute)
            and callee.attr == "input"
        ):
            interactive_names[target.id] = node.lineno

    for statement in function.body:
        if not isinstance(statement, ast.If):
            continue
        test = statement.test
        if not (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id in interactive_names
            and len(test.ops) == 1
            and isinstance(test.ops[0], (ast.NotEq, ast.NotIn))
            and len(test.comparators) == 1
        ):
            continue
        accepted = test.comparators[0]
        literal_acceptance = (
            isinstance(accepted, ast.Constant)
            and accepted.value in {True, "y", "yes", "allow", "approve"}
            or isinstance(accepted, (ast.Set, ast.List, ast.Tuple))
            and bool(accepted.elts)
            and all(
                isinstance(item, ast.Constant)
                and item.value in {True, "y", "yes", "allow", "approve"}
                for item in accepted.elts
            )
        )
        if not literal_acceptance:
            continue
        rejected = any(
            isinstance(node, ast.Raise)
            or isinstance(node, ast.Return)
            and python_mcp_sampling_result_kind(node.value, types_binding) == "error"
            for node in python_scope_nodes(statement.body)
        )
        if rejected and any(
            line > (statement.end_lineno or statement.lineno)
            for line in successful_lines
        ):
            return interactive_names[test.left.id]
    return None


def add_python_mcp_sampling_callback_consent_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve direct Python MCP ClientSession sampling callbacks and consent."""
    analysis = "python-mcp-sampling-callback-consent"
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        if "sampling_callback" not in text or "ClientSession" not in text:
            continue
        client_session = python_exact_import_name(tree, "mcp", "ClientSession")
        if client_session is None:
            continue
        types_binding = python_exact_module_import_name(tree, "mcp.types")
        relative = path.relative_to(root).as_posix()
        lines = text.splitlines()
        scopes: list[list[ast.stmt]] = [tree.body]
        scopes.extend(
            statement.body
            for statement in tree.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for body in scopes:
            nodes = python_scope_nodes(body)
            callbacks = {
                node.name: node
                for node in nodes
                if isinstance(node, ast.AsyncFunctionDef)
            }
            for call in nodes:
                if not (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == client_session
                ):
                    continue
                callback_expression = python_call_keyword(call, "sampling_callback")
                if callback_expression is None:
                    continue
                callback = (
                    callbacks.get(callback_expression.id)
                    if isinstance(callback_expression, ast.Name)
                    else None
                )
                if callback is None or callback.lineno >= call.lineno:
                    add_mcp_sampling_consent_observation(
                        ir,
                        relative=relative,
                        lines=lines,
                        line=callback_expression.lineno,
                        frontend="python",
                        analysis=analysis,
                        approval_policy="unresolved-handler",
                        response_created=False,
                        fulfilment_target="unresolved",
                        callback_line=None,
                    )
                    continue
                return_kinds = [
                    (node.lineno, python_mcp_sampling_result_kind(node.value, types_binding))
                    for node in python_scope_nodes(callback.body)
                    if isinstance(node, ast.Return)
                ]
                successful_lines = {
                    line for line, kind in return_kinds if kind == "response"
                }
                error_lines = {line for line, kind in return_kinds if kind == "error"}
                consent_line = python_mcp_sampling_human_consent(
                    callback,
                    types_binding,
                    successful_lines,
                )
                if successful_lines and consent_line is not None:
                    approval_policy = "human-confirmed"
                elif successful_lines:
                    approval_policy = "automatic-fulfilment"
                elif error_lines:
                    approval_policy = "denied-handler"
                else:
                    approval_policy = "unresolved-handler"
                callback_nodes = python_scope_nodes(callback.body)
                if not successful_lines:
                    fulfilment_target = "denial" if error_lines else "unresolved"
                elif any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr
                    in {"generate", "create", "request", "get_chat_message_content"}
                    for node in callback_nodes
                ):
                    fulfilment_target = "model-provider"
                else:
                    fulfilment_target = "handler-response"
                add_mcp_sampling_consent_observation(
                    ir,
                    relative=relative,
                    lines=lines,
                    line=callback_expression.lineno,
                    frontend="python",
                    analysis=analysis,
                    approval_policy=approval_policy,
                    response_created=bool(successful_lines),
                    fulfilment_target=fulfilment_target,
                    callback_line=callback.lineno,
                    consent_line=consent_line,
                    request_disclosure=(
                        "interactive-decision"
                        if consent_line is not None
                        else "not-proven"
                    ),
                )


def add_python_pydantic_ai_mcp_sampling_model_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve PydanticAI's sampling_model shortcut into automatic MCP fulfilment."""
    analysis = "python-pydantic-ai-mcp-sampling-model"
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        if "MCPToolset" not in text or "sampling_model" not in text:
            continue
        toolset_binding = python_exact_module_scope_import_name(
            tree,
            "pydantic_ai.mcp",
            "MCPToolset",
        )
        if toolset_binding is None:
            continue
        relative = path.relative_to(root).as_posix()
        lines = text.splitlines()
        for call in ast.walk(tree):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == toolset_binding
                and not any(keyword.arg is None for keyword in call.keywords)
            ):
                continue
            sampling_model = python_call_keyword(call, "sampling_model")
            sampling_handler = python_call_keyword(call, "sampling_handler")
            if sampling_model is None or (
                isinstance(sampling_model, ast.Constant) and sampling_model.value is None
            ):
                continue
            if sampling_handler is not None and not (
                isinstance(sampling_handler, ast.Constant) and sampling_handler.value is None
            ):
                # The SDK rejects simultaneous model and handler configuration.
                continue
            add_mcp_sampling_consent_observation(
                ir,
                relative=relative,
                lines=lines,
                line=call.lineno,
                frontend="python",
                analysis=analysis,
                approval_policy="automatic-fulfilment",
                response_created=True,
                fulfilment_target="model-provider",
                callback_line=None,
                request_disclosure="not-proven",
                extra_attributes={
                    "adapter": "pydantic-ai-mcp-toolset",
                    "configuration": "sampling-model",
                    "handler_origin": "sdk-generated",
                    "protocol_compatibility": "sdk-session-dependent",
                },
            )


def typescript_sampling_response_offset(callback: str) -> int | None:
    """Return the first exact sampling-result object returned by an arrow callback."""
    code = typescript_code_mask(callback)
    arrow = code.find("=>")
    if arrow < 0:
        return None
    cursor = arrow + 2
    while cursor < len(code) and code[cursor].isspace():
        cursor += 1
    candidates: list[int] = []
    if cursor < len(code) and code[cursor] == "{":
        body_end = typescript_balanced_end(code, cursor, "{", "}")
        if body_end is None:
            return None
        body_code = code[cursor + 1 : body_end - 1]
        candidates.extend(
            cursor + 1 + match.end() - 1
            for match in re.finditer(r"\breturn\s*\{", body_code)
        )
    else:
        if cursor < len(code) and code[cursor] == "(":
            cursor += 1
            while cursor < len(code) and code[cursor].isspace():
                cursor += 1
        if cursor < len(code) and code[cursor] == "{":
            candidates.append(cursor)
    for opening in candidates:
        end = typescript_balanced_end(code, opening, "{", "}")
        if end is None:
            continue
        result = callback[opening:end]
        if all(
            typescript_object_property_expression(result, name) is not None
            for name in ("role", "content", "model")
        ):
            return opening
    return None


def typescript_sampling_consent_proof(
    callback: str,
    response_offset: int,
) -> tuple[int | None, str]:
    """Prove full-request disclosure and a fail-closed awaited user decision."""
    prefix = callback[:response_offset]
    code = typescript_code_mask(prefix)
    for match in re.finditer(
        r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*await\s+"
        r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\.confirm\s*\(",
        code,
    ):
        decision = match.group(1)
        rejection = re.search(
            rf"\bif\s*\(\s*!\s*{re.escape(decision)}\s*\)\s*\{{",
            code[match.end() :],
        )
        if rejection is None:
            continue
        opening = match.end() + rejection.end() - 1
        end = typescript_balanced_end(code, opening, "{", "}")
        if end is None or not re.search(r"\bthrow\b", code[opening + 1 : end - 1]):
            continue
        if re.search(r"\.(?:generate|create|request)\s*\(", code[:end]):
            continue
        disclosed = (
            "systemPrompt" in prefix
            and ".messages" in prefix
            and re.search(r"\.(?:attention|print|log)\s*\(", code[: match.start()])
            is not None
        )
        return match.start(), "full-request" if disclosed else "partial-or-unresolved"
    return None, "not-proven"


def typescript_sampling_token_budget_line(
    callback: str,
    response_offset: int,
) -> int | None:
    """Locate a token cap that is passed to the provider before sampling."""
    prefix = callback[:response_offset]
    code = typescript_code_mask(prefix)
    for match in re.finditer(
        r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*Math\.min\s*\("
        r"\s*[A-Za-z_$][\w$]*(?:\.params)?\.maxTokens\s*,\s*"
        r"(?:[A-Za-z_$][\w$]*|\d+)",
        code,
    ):
        binding = match.group(1)
        if re.search(rf"\bmaxTokens\s*:\s*{re.escape(binding)}\b", code[match.end() :]):
            return match.start()
    return None


def typescript_literal_object_body(expression: str) -> str | None:
    """Return the body of one complete literal TypeScript object expression."""
    code = typescript_code_mask(expression)
    opening = len(code) - len(code.lstrip())
    if opening >= len(code) or code[opening] != "{":
        return None
    end = typescript_balanced_end(code, opening, "{", "}")
    if end is None or code[end:].strip():
        return None
    return expression[opening + 1 : end - 1]


def typescript_mcp_client_capability_receivers(
    text: str,
    capability: str,
) -> dict[str, tuple[str, ...]]:
    """Resolve exact MCP Client receivers with one literal advertised capability."""
    imports = typescript_named_import_bindings(text, "@modelcontextprotocol/client")
    client_constructors = {
        local
        for local, exported in imports.items()
        if exported == "Client" and not typescript_import_binding_is_shadowed(text, local)
    }
    if not client_constructors:
        return {}
    code = typescript_code_mask(text)
    configured: dict[str, tuple[str, ...]] = {}
    for constructor in client_constructors:
        for match in re.finditer(
            rf"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*new\s+"
            rf"{re.escape(constructor)}\s*\(",
            code,
        ):
            opening = match.end() - 1
            end = typescript_balanced_end(code, opening, "(", ")")
            if end is None:
                continue
            arguments = typescript_call_arguments(text[opening + 1 : end - 1])
            if len(arguments) < 2:
                continue
            capabilities = typescript_object_property_expression(
                arguments[1][0],
                "capabilities",
            )
            capability_expression = (
                typescript_object_property_expression(capabilities, capability)
                if capabilities is not None
                else None
            )
            capability_body = (
                typescript_literal_object_body(capability_expression)
                if capability_expression is not None
                else None
            )
            if capability_body is None:
                continue
            if capability == "elicitation":
                modes = tuple(
                    mode
                    for mode in ("form", "url")
                    if typescript_object_property_expression(capability_expression, mode)
                    is not None
                )
                if not modes and not typescript_code_mask(capability_body).strip():
                    modes = ("form",)
                if not modes:
                    continue
            else:
                modes = (capability,)
            configured[match.group(1)] = modes

    receivers = dict(configured)
    for constructor in client_constructors:
        for match in re.finditer(
            rf"\b(?P<method>[A-Za-z_$][\w$]*)\s*\([^)]*\b"
            rf"(?P<parameter>[A-Za-z_$][\w$]*)\s*:\s*"
            rf"{re.escape(constructor)}\b[^)]*\)",
            code,
        ):
            method = match.group("method")
            parameter = match.group("parameter")
            callsite_modes = {
                modes
                for receiver, modes in configured.items()
                if re.search(
                    rf"\b(?:this|[A-Za-z_$][\w$]*)\.{re.escape(method)}"
                    rf"\s*\(\s*{re.escape(receiver)}\b",
                    code,
                )
            }
            if len(callsite_modes) == 1:
                receivers[parameter] = next(iter(callsite_modes))
    return receivers


def add_typescript_mcp_sampling_handler_consent_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve TypeScript MCP client sampling handlers and explicit consent gates."""
    analysis = "typescript-mcp-sampling-handler-consent"
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        if "sampling/createMessage" not in text or "setRequestHandler" not in text:
            continue
        code = typescript_code_mask(text)
        receivers = typescript_mcp_client_capability_receivers(text, "sampling")
        if not receivers:
            continue
        relative = path.relative_to(root).as_posix()
        lines = text.splitlines()
        receiver_pattern = "|".join(re.escape(receiver) for receiver in sorted(receivers))
        for match in re.finditer(
            rf"\b(?P<receiver>{receiver_pattern})\.setRequestHandler\s*\(",
            code,
        ):
            opening = match.end() - 1
            end = typescript_balanced_end(code, opening, "(", ")")
            if end is None:
                continue
            arguments = typescript_call_arguments(
                text[opening + 1 : end - 1],
                opening + 1,
            )
            if len(arguments) != 2 or re.fullmatch(
                r"(['\"])sampling/createMessage\1", arguments[0][0].strip()
            ) is None:
                continue
            callback, callback_offset = arguments[1]
            response_offset = typescript_sampling_response_offset(callback)
            if response_offset is None:
                approval_policy = "unresolved-handler"
                response_created = False
                consent_offset = None
                request_disclosure = "unresolved"
                budget_offset = None
                fulfilment_target = "unresolved"
            else:
                consent_offset, request_disclosure = typescript_sampling_consent_proof(
                    callback,
                    response_offset,
                )
                approval_policy = (
                    "human-confirmed"
                    if consent_offset is not None
                    else "automatic-fulfilment"
                )
                response_created = True
                budget_offset = typescript_sampling_token_budget_line(
                    callback,
                    response_offset,
                )
                callback_prefix_code = typescript_code_mask(callback[:response_offset])
                fulfilment_target = (
                    "model-provider"
                    if re.search(
                        r"\.(?:generate|create|request)\s*\(",
                        callback_prefix_code,
                    )
                    else "handler-response"
                )
                if fulfilment_target != "model-provider":
                    budget_offset = None
            line = line_at(text, match.start())
            callback_line = line_at(text, callback_offset)
            add_mcp_sampling_consent_observation(
                ir,
                relative=relative,
                lines=lines,
                line=line,
                frontend="typescript",
                analysis=analysis,
                approval_policy=approval_policy,
                response_created=response_created,
                fulfilment_target=fulfilment_target,
                callback_line=callback_line,
                consent_line=(
                    line_at(text, callback_offset + consent_offset)
                    if consent_offset is not None
                    else None
                ),
                request_disclosure=request_disclosure,
                token_budget_line=(
                    line_at(text, callback_offset + budget_offset)
                    if budget_offset is not None
                    else None
                ),
            )


def add_mcp_elicitation_consent_observation(
    ir: RepositoryIR,
    *,
    relative: str,
    lines: list[str],
    line: int,
    frontend: str,
    analysis: str,
    approval_policy: str,
    response_created: bool,
    acceptance_created: bool,
    elicitation_modes: tuple[str, ...],
    callback_line: int | None,
    consent_line: int | None = None,
    request_disclosure: str = "unresolved",
    url_disclosure: str = "not-proven",
    extra_attributes: dict[str, object] | None = None,
) -> None:
    """Emit one exact MCP client elicitation handler and its consent state."""
    evidence = Evidence(relative, line, excerpt(lines, line))
    symbol_frontend = {"python": "py", "typescript": "ts"}.get(frontend, frontend)
    protocol_id = source_symbol(
        symbol_frontend,
        relative,
        "protocol",
        f"mcp-elicitation@{line}",
    )
    common_attributes: dict[str, object] = {
        "frontend": frontend,
        "input_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": approval_policy,
        "response_created": response_created,
        "acceptance_created": acceptance_created,
        "elicitation_modes": elicitation_modes,
        "callback_definition_line": callback_line,
        "request_disclosure": request_disclosure,
        "url_disclosure": url_disclosure,
        "scope": source_scope(relative),
        "analysis": analysis,
        **(extra_attributes or {}),
    }
    ir.add_component(
        Component(
            "protocol",
            "MCP",
            evidence,
            {
                "role": "client",
                "elicitation_handler": "registered",
                **common_attributes,
            },
            protocol_id,
        )
    )
    ir.add_component(
        Component(
            "capability",
            "user-elicitation",
            evidence,
            common_attributes,
        )
    )
    ir.add_relationship(
        Relationship(
            "protocol",
            "MCP",
            "uses",
            "capability",
            "user-elicitation",
            evidence,
            common_attributes,
            source_id=protocol_id,
        )
    )
    setting_attributes = {
        "enabled": (
            True
            if acceptance_created
            else False
            if approval_policy == "declined-handler"
            else None
        ),
        "approval_policy": approval_policy,
        "elicitation_modes": elicitation_modes,
        "url_disclosure": url_disclosure,
        "scope": source_scope(relative),
        "analysis": analysis,
        **(extra_attributes or {}),
    }
    ir.add_component(
        Component(
            "control-setting",
            "mcp-elicitation-acceptance",
            evidence,
            setting_attributes,
        )
    )
    ir.add_relationship(
        Relationship(
            "protocol",
            "MCP",
            "configured-by",
            "control-setting",
            "mcp-elicitation-acceptance",
            evidence,
            setting_attributes,
            source_id=protocol_id,
        )
    )
    if consent_line is not None:
        control_attributes = {
            "policy_effect": "requires-user-decision-before-elicitation-acceptance",
            "request_disclosure": request_disclosure,
            "control_line": consent_line,
            "scope": source_scope(relative),
            "analysis": analysis,
        }
        ir.add_component(
            Component(
                "control",
                "mcp-elicitation-consent",
                Evidence(relative, consent_line, excerpt(lines, consent_line)),
                control_attributes,
            )
        )
        ir.add_relationship(
            Relationship(
                "capability",
                "user-elicitation",
                "governed-by",
                "control",
                "mcp-elicitation-consent",
                evidence,
                control_attributes,
            )
        )


def python_mcp_elicitation_result_action(
    node: ast.AST | None,
    types_binding: str | None,
    result_binding: str | None = None,
) -> str | None:
    """Return the literal action of one exact mcp.types elicitation result."""
    if not isinstance(node, ast.Call):
        return None
    constructor: str | None = None
    if (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == types_binding
    ):
        constructor = node.func.attr
    elif isinstance(node.func, ast.Name) and node.func.id == result_binding:
        constructor = "ElicitResult"
    if constructor == "ErrorData":
        return "error"
    if constructor != "ElicitResult":
        return None
    action = python_call_keyword(node, "action")
    if isinstance(action, ast.Constant) and action.value in {
        "accept",
        "decline",
        "cancel",
    }:
        return str(action.value)
    return None


def python_elicitation_input_name(node: ast.AST) -> str | None:
    """Return a direct input binding through exact string normalization calls."""
    current = node
    while (
        isinstance(current, ast.Call)
        and not current.args
        and not current.keywords
        and isinstance(current.func, ast.Attribute)
        and current.func.attr in {"casefold", "lower", "strip"}
    ):
        current = current.func.value
    return current.id if isinstance(current, ast.Name) else None


def python_elicitation_decision_test(
    test: ast.AST,
    interactive_names: set[str],
    *,
    positive: bool,
) -> bool:
    """Recognize a literal allow/deny comparison over direct user input."""
    if not (
        isinstance(test, ast.Compare)
        and python_elicitation_input_name(test.left) in interactive_names
        and len(test.ops) == 1
        and len(test.comparators) == 1
    ):
        return False
    operator = test.ops[0]
    if positive and not isinstance(operator, (ast.Eq, ast.In)):
        return False
    if not positive and not isinstance(operator, (ast.NotEq, ast.NotIn)):
        return False
    accepted = test.comparators[0]
    allowed_values = {True, "y", "yes", "accept", "approve", "submit", "ok"}
    if isinstance(accepted, ast.Constant):
        return accepted.value in allowed_values
    return (
        isinstance(accepted, (ast.Set, ast.List, ast.Tuple))
        and bool(accepted.elts)
        and all(
            isinstance(item, ast.Constant) and item.value in allowed_values
            for item in accepted.elts
        )
    )


def python_elicitation_rejection_test(
    test: ast.AST,
    interactive_names: set[str],
) -> str | None:
    """Return the user-input binding for a direct decline/cancel branch."""
    if (
        isinstance(test, ast.UnaryOp)
        and isinstance(test.op, ast.Not)
        and isinstance(test.operand, ast.Name)
        and test.operand.id in interactive_names
    ):
        return test.operand.id
    if not (
        isinstance(test, ast.Compare)
        and python_elicitation_input_name(test.left) in interactive_names
        and len(test.ops) == 1
        and isinstance(test.ops[0], (ast.Eq, ast.In))
        and len(test.comparators) == 1
    ):
        return None
    rejected = test.comparators[0]
    denied_values = {False, "n", "no", "decline", "cancel", "reject", "deny"}
    if isinstance(rejected, ast.Constant):
        binding = python_elicitation_input_name(test.left)
        return binding if rejected.value in denied_values else None
    if (
        isinstance(rejected, (ast.Set, ast.List, ast.Tuple))
        and bool(rejected.elts)
        and all(
            isinstance(item, ast.Constant) and item.value in denied_values
            for item in rejected.elts
        )
    ):
        return python_elicitation_input_name(test.left)
    return None


def python_mcp_elicitation_human_consent(
    function: ast.AsyncFunctionDef,
    types_binding: str | None,
    accept_returns: list[ast.Return],
    result_binding: str | None = None,
) -> int | None:
    """Prove every literal acceptance follows direct interactive input."""
    interactions: list[tuple[str, int]] = []
    nodes = python_scope_nodes(function.body)
    for node in nodes:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = (
            node.targets[0]
            if isinstance(node, ast.Assign) and len(node.targets) == 1
            else node.target
            if isinstance(node, ast.AnnAssign)
            else None
        )
        if not isinstance(target, ast.Name) or node.value is None:
            continue
        if any(
            isinstance(call, ast.Call)
            and (
                isinstance(call.func, ast.Name)
                and call.func.id == "input"
                or isinstance(call.func, ast.Attribute)
                and call.func.attr in {"ask", "confirm", "input", "question"}
            )
            for call in ast.walk(node.value)
        ):
            interactions.append((target.id, node.lineno))
    if not interactions or not accept_returns:
        return None

    interactive_names = {name for name, _ in interactions}
    controlled: set[int] = set()
    consent_lines: set[int] = set()
    for returned in accept_returns:
        for statement in nodes:
            if not isinstance(statement, ast.If):
                continue
            if python_elicitation_decision_test(
                statement.test,
                interactive_names,
                positive=True,
            ) and any(
                node is returned
                for child in statement.body
                for node in ast.walk(child)
            ):
                binding = (
                    python_elicitation_input_name(statement.test.left)
                    if isinstance(statement.test, ast.Compare)
                    else None
                )
                candidate_lines = [
                    line
                    for name, line in interactions
                    if name == binding and line <= statement.lineno
                ]
                if candidate_lines:
                    controlled.add(id(returned))
                    consent_lines.add(max(candidate_lines))
                    break
            if python_elicitation_decision_test(
                statement.test,
                interactive_names,
                positive=False,
            ):
                rejection_binding = (
                    python_elicitation_input_name(statement.test.left)
                    if isinstance(statement.test, ast.Compare)
                    else None
                )
            else:
                rejection_binding = python_elicitation_rejection_test(
                    statement.test,
                    interactive_names,
                )
            if rejection_binding is None or returned.lineno <= (
                statement.end_lineno or statement.lineno
            ):
                continue
            candidate_lines = [
                line
                for name, line in interactions
                if name == rejection_binding and line <= statement.lineno
            ]
            if not candidate_lines:
                continue
            rejection_actions = {
                python_mcp_elicitation_result_action(
                    node.value,
                    types_binding,
                    result_binding,
                )
                for child in statement.body
                for node in ast.walk(child)
                if isinstance(node, ast.Return)
            }
            latest_input = max(candidate_lines)
            if rejection_actions & {"decline", "cancel", "error"} and not any(
                name == rejection_binding and latest_input < line < returned.lineno
                for name, line in interactions
            ):
                controlled.add(id(returned))
                consent_lines.add(latest_input)
                break
    if len(controlled) != len(accept_returns):
        return None
    return min(consent_lines) if consent_lines else None


def python_elicitation_url_is_displayed(
    function: ast.AsyncFunctionDef,
    params_binding: str | None,
) -> bool:
    """Prove a full URL or the complete request params reach a direct user display."""
    if params_binding is None:
        return False

    def contains_url(expression: ast.AST) -> bool:
        if isinstance(expression, ast.Attribute):
            return (
                isinstance(expression.value, ast.Name)
                and expression.value.id == params_binding
                and expression.attr == "url"
            )
        if isinstance(expression, ast.Name):
            return expression.id == params_binding
        if isinstance(expression, ast.Call):
            return (
                isinstance(expression.func, ast.Name)
                and expression.func.id in {"repr", "str"}
                and any(contains_url(argument) for argument in expression.args)
            )
        if isinstance(expression, ast.IfExp):
            return contains_url(expression.body) or contains_url(expression.orelse)
        if isinstance(expression, ast.FormattedValue):
            return contains_url(expression.value)
        if isinstance(expression, ast.BinOp):
            return contains_url(expression.left) or contains_url(expression.right)
        if isinstance(expression, ast.JoinedStr):
            return any(contains_url(item) for item in expression.values)
        if isinstance(expression, (ast.List, ast.Set, ast.Tuple)):
            return any(contains_url(item) for item in expression.elts)
        if isinstance(expression, ast.Dict):
            return any(contains_url(item) for item in (*expression.keys, *expression.values) if item is not None)
        return False

    return any(
        isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id in {"input", "print"}
            or isinstance(node.func, ast.Attribute)
            and node.func.attr
            in {"ask", "attention", "confirm", "input", "print", "question", "show"}
        )
        and any(
            contains_url(argument)
            for argument in (*node.args, *(keyword.value for keyword in node.keywords))
        )
        for node in python_scope_nodes(function.body)
    )


def add_python_mcp_elicitation_callback_consent_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve direct Python MCP ClientSession elicitation callbacks and consent."""
    analysis = "python-mcp-elicitation-callback-consent"
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        if "elicitation_callback" not in text or "ClientSession" not in text:
            continue
        client_session = python_exact_import_name(tree, "mcp", "ClientSession")
        if client_session is None:
            continue
        types_binding = python_exact_module_import_name(tree, "mcp.types")
        relative = path.relative_to(root).as_posix()
        lines = text.splitlines()
        scopes: list[list[ast.stmt]] = [tree.body]
        scopes.extend(
            statement.body
            for statement in tree.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for body in scopes:
            nodes = python_scope_nodes(body)
            callbacks = {
                node.name: node
                for node in nodes
                if isinstance(node, ast.AsyncFunctionDef)
            }
            for call in nodes:
                if not (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == client_session
                ):
                    continue
                callback_expression = python_call_keyword(call, "elicitation_callback")
                if callback_expression is None:
                    continue
                callback = (
                    callbacks.get(callback_expression.id)
                    if isinstance(callback_expression, ast.Name)
                    else None
                )
                if callback is None or callback.lineno >= call.lineno:
                    add_mcp_elicitation_consent_observation(
                        ir,
                        relative=relative,
                        lines=lines,
                        line=callback_expression.lineno,
                        frontend="python",
                        analysis=analysis,
                        approval_policy="unresolved-handler",
                        response_created=False,
                        acceptance_created=False,
                        elicitation_modes=("form", "url"),
                        callback_line=None,
                    )
                    continue
                returned = [
                    node
                    for node in python_scope_nodes(callback.body)
                    if isinstance(node, ast.Return)
                ]
                actions = {
                    id(node): python_mcp_elicitation_result_action(
                        node.value,
                        types_binding,
                    )
                    for node in returned
                }
                accept_returns = [
                    node for node in returned if actions[id(node)] == "accept"
                ]
                response_created = any(action is not None for action in actions.values())
                consent_line = python_mcp_elicitation_human_consent(
                    callback,
                    types_binding,
                    accept_returns,
                )
                if accept_returns and consent_line is not None:
                    approval_policy = "human-confirmed"
                elif accept_returns:
                    approval_policy = "automatic-accept"
                elif set(actions.values()) & {"decline", "cancel", "error"}:
                    approval_policy = "declined-handler"
                else:
                    approval_policy = "unresolved-handler"
                callback_text = ast.get_source_segment(text, callback) or ""
                callback_parameters = [
                    argument.arg
                    for argument in (*callback.args.posonlyargs, *callback.args.args)
                ]
                has_message = ".message" in callback_text
                has_details = any(
                    marker in callback_text
                    for marker in (".requestedSchema", ".requested_schema", ".url")
                )
                add_mcp_elicitation_consent_observation(
                    ir,
                    relative=relative,
                    lines=lines,
                    line=callback_expression.lineno,
                    frontend="python",
                    analysis=analysis,
                    approval_policy=approval_policy,
                    response_created=response_created,
                    acceptance_created=bool(accept_returns),
                    elicitation_modes=("form", "url"),
                    callback_line=callback.lineno,
                    consent_line=consent_line,
                    request_disclosure=(
                        "message-and-request-details"
                        if consent_line is not None and has_message and has_details
                        else "interactive-decision"
                        if consent_line is not None
                        else "not-proven"
                    ),
                    url_disclosure=(
                        "full-url"
                        if python_elicitation_url_is_displayed(
                            callback,
                            callback_parameters[1]
                            if len(callback_parameters) >= 2
                            else None,
                        )
                        else "not-proven"
                    ),
                )


def python_fastmcp_elicitation_return_action(
    node: ast.AST | None,
    result_binding: str | None,
    response_type_binding: str | None,
) -> str:
    """Classify one FastMCP handler return through its implicit-accept adapter."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == result_binding
    ):
        return python_mcp_elicitation_result_action(
            node,
            None,
            result_binding,
        ) or "unresolved"
    if isinstance(node, (ast.Constant, ast.Dict, ast.List, ast.Set, ast.Tuple)):
        return "accept"
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == response_type_binding
    ):
        return "accept"
    return "unresolved"


def add_python_fastmcp_elicitation_handler_consent_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve FastMCP Client handlers, including its implicit acceptance adapter."""
    analysis = "python-fastmcp-elicitation-handler-consent"
    client_modules = ("fastmcp", "fastmcp.client", "fastmcp.client.client")
    result_modules = ("fastmcp", "fastmcp.client", "fastmcp.client.elicitation")
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        if "Client" not in text or "elicitation_handler" not in text:
            continue
        client_bindings = {
            binding
            for module in client_modules
            if (
                binding := python_exact_module_scope_import_name(
                    tree,
                    module,
                    "Client",
                )
            )
            is not None
        }
        if len(client_bindings) != 1:
            continue
        client_binding = next(iter(client_bindings))
        result_bindings = {
            binding
            for module in result_modules
            if (
                binding := python_exact_module_scope_import_name(
                    tree,
                    module,
                    "ElicitResult",
                )
            )
            is not None
        }
        result_binding = next(iter(result_bindings)) if len(result_bindings) == 1 else None
        relative = path.relative_to(root).as_posix()
        lines = text.splitlines()
        module_nodes = python_scope_nodes(tree.body)
        module_callbacks = {
            node.name: node
            for node in module_nodes
            if isinstance(node, ast.AsyncFunctionDef)
        }
        scopes: list[
            tuple[list[ast.AST], dict[str, ast.AsyncFunctionDef], set[str]]
        ] = [
            (module_nodes, module_callbacks, set())
        ]
        scopes.extend(
            (
                python_scope_nodes(function.body),
                {
                    **module_callbacks,
                    **{
                        node.name: node
                        for node in python_scope_nodes(function.body)
                        if isinstance(node, ast.AsyncFunctionDef)
                    },
                },
                {
                    argument.arg
                    for argument in (
                        *function.args.posonlyargs,
                        *function.args.args,
                        *function.args.kwonlyargs,
                    )
                }
                | ({function.args.vararg.arg} if function.args.vararg is not None else set())
                | ({function.args.kwarg.arg} if function.args.kwarg is not None else set()),
            )
            for function in module_nodes
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        seen_calls: set[int] = set()
        for nodes, callbacks, shadowed_parameters in scopes:
            for call in nodes:
                if not (
                    isinstance(call, ast.Call)
                    and id(call) not in seen_calls
                    and isinstance(call.func, ast.Name)
                    and call.func.id == client_binding
                    and not any(keyword.arg is None for keyword in call.keywords)
                ):
                    continue
                callback_expression = python_call_keyword(call, "elicitation_handler")
                if callback_expression is None or (
                    isinstance(callback_expression, ast.Constant)
                    and callback_expression.value is None
                ):
                    continue
                seen_calls.add(id(call))
                callback = (
                    callbacks.get(callback_expression.id)
                    if isinstance(callback_expression, ast.Name)
                    else None
                )
                callback_rebound = (
                    callback is not None
                    and isinstance(callback_expression, ast.Name)
                    and (
                        callback_expression.id in shadowed_parameters
                        and callback is module_callbacks.get(callback_expression.id)
                        or any(
                            isinstance(node, ast.Name)
                            and isinstance(node.ctx, (ast.Store, ast.Del))
                            and node.id == callback_expression.id
                            and callback.lineno < getattr(node, "lineno", 0) <= call.lineno
                            for node in (
                                [*nodes, *module_nodes]
                                if callback_expression.id in module_callbacks
                                else nodes
                            )
                        )
                    )
                )
                if callback is None or callback.lineno >= call.lineno or callback_rebound:
                    add_mcp_elicitation_consent_observation(
                        ir,
                        relative=relative,
                        lines=lines,
                        line=call.lineno,
                        frontend="python",
                        analysis=analysis,
                        approval_policy="unresolved-handler",
                        response_created=False,
                        acceptance_created=False,
                        elicitation_modes=("form", "url"),
                        callback_line=None,
                        extra_attributes={
                            "adapter": "fastmcp-client",
                            "acceptance_semantics": "non-result-return-implies-accept",
                        },
                    )
                    continue
                parameters = [
                    argument.arg
                    for argument in (*callback.args.posonlyargs, *callback.args.args)
                ]
                response_type_binding = parameters[1] if len(parameters) >= 2 else None
                if response_type_binding is not None and any(
                    isinstance(node, ast.Name)
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    and node.id == response_type_binding
                    for node in python_scope_nodes(callback.body)
                ):
                    response_type_binding = None
                returned = [
                    node
                    for node in python_scope_nodes(callback.body)
                    if isinstance(node, ast.Return)
                ]
                actions = {
                    id(node): python_fastmcp_elicitation_return_action(
                        node.value,
                        result_binding,
                        response_type_binding,
                    )
                    for node in returned
                }
                accept_returns = [
                    node for node in returned if actions[id(node)] == "accept"
                ]
                consent_line = python_mcp_elicitation_human_consent(
                    callback,
                    None,
                    accept_returns,
                    result_binding,
                )
                action_values = set(actions.values())
                if accept_returns and consent_line is None:
                    approval_policy = "automatic-accept"
                elif "unresolved" in action_values:
                    approval_policy = "unresolved-handler"
                elif accept_returns:
                    approval_policy = "human-confirmed"
                elif action_values and action_values <= {"decline", "cancel", "error"}:
                    approval_policy = "declined-handler"
                else:
                    approval_policy = "unresolved-handler"
                callback_nodes = python_scope_nodes(callback.body)

                def displayed(
                    name: str,
                    callback_nodes: list[ast.AST] = callback_nodes,
                ) -> bool:
                    return any(
                        isinstance(node, ast.Call)
                        and (
                            isinstance(node.func, ast.Name)
                            and node.func.id in {"input", "print"}
                            or isinstance(node.func, ast.Attribute)
                            and node.func.attr
                            in {"ask", "confirm", "input", "print", "question"}
                        )
                        and any(
                            isinstance(candidate, ast.Name) and candidate.id == name
                            for argument in (*node.args, *(item.value for item in node.keywords))
                            for candidate in ast.walk(argument)
                        )
                        for node in callback_nodes
                    )

                has_message = bool(parameters) and displayed(parameters[0])
                has_details = len(parameters) >= 3 and displayed(parameters[2])
                add_mcp_elicitation_consent_observation(
                    ir,
                    relative=relative,
                    lines=lines,
                    line=call.lineno,
                    frontend="python",
                    analysis=analysis,
                    approval_policy=approval_policy,
                    response_created=bool(action_values - {"unresolved"}),
                    acceptance_created=bool(accept_returns),
                    elicitation_modes=("form", "url"),
                    callback_line=callback.lineno,
                    consent_line=consent_line,
                    request_disclosure=(
                        "message-and-request-details"
                        if consent_line is not None and has_message and has_details
                        else "message-only"
                        if consent_line is not None and has_message
                        else "interactive-decision"
                        if consent_line is not None
                        else "not-proven"
                    ),
                    url_disclosure=(
                        "full-url"
                        if len(parameters) >= 3
                        and python_elicitation_url_is_displayed(callback, parameters[2])
                        else "not-proven"
                    ),
                    extra_attributes={
                        "adapter": "fastmcp-client",
                        "acceptance_semantics": "non-result-return-implies-accept",
                    },
                )


def typescript_elicitation_action_offsets(
    callback: str,
) -> list[tuple[int, str]]:
    """Return literal actions from object expressions returned by an arrow handler."""
    code = typescript_code_mask(callback)
    arrow = code.find("=>")
    if arrow < 0:
        return []
    body_start = arrow + 2
    while body_start < len(code) and code[body_start].isspace():
        body_start += 1
    block_body = body_start < len(code) and code[body_start] == "{"
    actions: list[tuple[int, str]] = []
    for match in re.finditer(
        r"\baction\s*:\s*(['\"])(accept|decline|cancel)\1",
        callback[arrow + 2 :],
    ):
        action_offset = arrow + 2 + match.start()
        depth = 0
        opening = None
        for offset in range(action_offset - 1, arrow, -1):
            if code[offset] == "}":
                depth += 1
            elif code[offset] == "{":
                if depth == 0:
                    opening = offset
                    break
                depth -= 1
        if opening is None:
            continue
        end = typescript_balanced_end(code, opening, "{", "}")
        if end is None:
            continue
        result = callback[opening:end]
        if typescript_literal_object_string_property(result, "action") != match.group(2):
            continue
        statement_start = max(code.rfind(";", arrow, opening), arrow) + 1
        prefix = code[statement_start:opening]
        if block_body and re.search(r"\breturn\b(?=[^{};]*$)", prefix) is None:
            continue
        actions.append((opening, match.group(2)))
    return sorted(set(actions))


def typescript_elicitation_interactions(
    callback: str,
) -> list[tuple[int, str, str]]:
    """Return direct awaited UI decision/input assignments in one handler."""
    code = typescript_code_mask(callback)
    interactions: list[tuple[int, str, str]] = []
    for match in re.finditer(
        r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*await\s+",
        code,
    ):
        binding = match.group(1)
        direct = re.match(
            r"[^;]{0,400}?\.(confirm|ask|input|question)\s*\(",
            code[match.end() :],
        )
        if direct is not None:
            interactions.append((match.start(), binding, direct.group(1)))
            continue
        promise_window = code[match.end() : match.end() + 1000]
        if re.match(r"new\s+Promise\b", promise_window) and re.search(
            r"\.(?:ask|input|question)\s*\(",
            promise_window,
        ):
            interactions.append((match.start(), binding, "question"))
    return interactions


def typescript_imported_elicitation_helper_consent(
    root: Path,
    path: Path,
    text: str,
    local_name: str,
) -> bool:
    """Prove one exact local helper collects input and can decline before acceptance."""
    if typescript_import_binding_is_shadowed(text, local_name):
        return False
    imported = resolve_typescript_imports(root, path, text).get(local_name)
    if imported is None:
        return False
    target_path, original_name = imported
    try:
        target_text = (root / target_path).read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )
    except OSError:
        return False
    definition = typescript_unique_function_definition(target_text, original_name)
    if definition is None:
        return False
    _, _, body = definition
    synthetic = f"async () => {{{body}}}"
    actions = {action for _, action in typescript_elicitation_action_offsets(synthetic)}
    return (
        "accept" in actions
        and bool(actions & {"decline", "cancel"})
        and bool(typescript_elicitation_interactions(synthetic))
    )


def typescript_elicitation_handler_consent(
    root: Path,
    path: Path,
    text: str,
    callback: str,
) -> tuple[str, bool, bool, int | None, str]:
    """Classify literal elicitation outcomes and direct user mediation."""
    actions = typescript_elicitation_action_offsets(callback)
    accept_offsets = [offset for offset, action in actions if action == "accept"]
    interactions = typescript_elicitation_interactions(callback)
    callback_code = typescript_code_mask(callback)
    controlled_accepts: set[int] = set()
    for accept_offset in accept_offsets:
        for interaction_offset, binding, kind in interactions:
            if interaction_offset >= accept_offset:
                continue
            between = callback_code[interaction_offset:accept_offset]
            binding_used = len(re.findall(rf"\b{re.escape(binding)}\b", between)) > 1
            if kind == "confirm" and not binding_used:
                continue
            controlled_accepts.add(accept_offset)
            break

    helper_offsets: list[int] = []
    unresolved_helper = False
    for match in re.finditer(
        r"\breturn\s+([A-Za-z_$][\w$]*)\s*\(",
        callback_code,
    ):
        helper = match.group(1)
        if typescript_imported_elicitation_helper_consent(
            root,
            path,
            text,
            helper,
        ):
            helper_offsets.append(match.start())
        else:
            unresolved_helper = True

    acceptance_created = bool(accept_offsets or helper_offsets)
    response_created = bool(actions or helper_offsets)
    consent_offsets = [
        offset
        for offset, _, _ in interactions
        if any(offset < accept for accept in controlled_accepts)
    ] + helper_offsets
    if accept_offsets and len(controlled_accepts) != len(accept_offsets):
        policy = "automatic-accept"
    elif unresolved_helper:
        policy = "unresolved-handler"
    elif acceptance_created:
        policy = "human-confirmed"
    elif actions and {action for _, action in actions} <= {"decline", "cancel"}:
        policy = "declined-handler"
    else:
        policy = "unresolved-handler"
    has_message = ".message" in callback
    has_details = ".requestedSchema" in callback or ".url" in callback
    disclosure = (
        "message-and-request-details"
        if policy == "human-confirmed" and has_message and has_details
        else "interactive-decision"
        if policy == "human-confirmed"
        else "not-proven"
    )
    return (
        policy,
        response_created,
        acceptance_created,
        min(consent_offsets) if consent_offsets else None,
        disclosure,
    )


def typescript_elicitation_url_is_displayed(callback: str) -> bool:
    """Prove request.params.url reaches a direct UI display or prompt call."""
    code = typescript_code_mask(callback)
    for match in re.finditer(
        r"\.(?:ask|attention|confirm|input|print|question|show)\s*\(",
        code,
    ):
        opening = match.end() - 1
        end = typescript_balanced_end(code, opening, "(", ")")
        if end is not None and re.search(
            r"\b(?:request\.)?params\.url\b",
            callback[opening:end],
        ):
            return True
    return False


def add_typescript_mcp_elicitation_handler_consent_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve TypeScript MCP client elicitation handlers and explicit consent gates."""
    analysis = "typescript-mcp-elicitation-handler-consent"
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        if "elicitation/create" not in text or "setRequestHandler" not in text:
            continue
        code = typescript_code_mask(text)
        receivers = typescript_mcp_client_capability_receivers(text, "elicitation")
        if not receivers:
            continue
        relative = path.relative_to(root).as_posix()
        lines = text.splitlines()
        receiver_pattern = "|".join(re.escape(receiver) for receiver in sorted(receivers))
        for match in re.finditer(
            rf"\b(?P<receiver>{receiver_pattern})\.setRequestHandler\s*\(",
            code,
        ):
            opening = match.end() - 1
            end = typescript_balanced_end(code, opening, "(", ")")
            if end is None:
                continue
            arguments = typescript_call_arguments(
                text[opening + 1 : end - 1],
                opening + 1,
            )
            if len(arguments) != 2 or re.fullmatch(
                r"(['\"])elicitation/create\1",
                arguments[0][0].strip(),
            ) is None:
                continue
            callback, callback_offset = arguments[1]
            if "=>" not in typescript_code_mask(callback):
                policy = "unresolved-handler"
                response_created = False
                acceptance_created = False
                consent_offset = None
                request_disclosure = "unresolved"
                callback_line = None
            else:
                (
                    policy,
                    response_created,
                    acceptance_created,
                    consent_offset,
                    request_disclosure,
                ) = typescript_elicitation_handler_consent(
                    root,
                    path,
                    text,
                    callback,
                )
                callback_line = line_at(text, callback_offset)
            line = line_at(text, match.start())
            add_mcp_elicitation_consent_observation(
                ir,
                relative=relative,
                lines=lines,
                line=line,
                frontend="typescript",
                analysis=analysis,
                approval_policy=policy,
                response_created=response_created,
                acceptance_created=acceptance_created,
                elicitation_modes=receivers[match.group("receiver")],
                callback_line=callback_line,
                consent_line=(
                    line_at(text, callback_offset + consent_offset)
                    if consent_offset is not None
                    else None
                ),
                request_disclosure=request_disclosure,
                url_disclosure=(
                    "full-url"
                    if "=>" in typescript_code_mask(callback)
                    and typescript_elicitation_url_is_displayed(callback)
                    else "not-proven"
                ),
            )


def add_python_google_adk_bigquery_audit_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve ADK Runner plugins into attributable BigQuery action-audit edges."""
    sources: list[tuple[str, str, ast.Module]] = []
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        sources.append((path.relative_to(root).as_posix(), text, tree))

    plugin_matches = [
        item
        for item in sources
        if all(
            marker in item[1]
            for marker in (
                "class BigQueryLoggerConfig:",
                "enabled: bool = True",
                "event_allowlist: list[str] | None = None",
                "event_denylist: list[str] | None = None",
                "class BigQueryAgentAnalyticsPlugin(BasePlugin):",
                "async def before_tool_callback(",
                '"TOOL_STARTING"',
                "async def after_tool_callback(",
                '"TOOL_COMPLETED"',
                "async def on_tool_error_callback(",
                '"TOOL_ERROR"',
                '"event_id": uuid.uuid4().hex',
                '"user_id": callback_context.user_id',
                '"session_id": callback_context.session.id',
                '"invocation_id": callback_context.invocation_id',
                '"agent":',
                '"tool":',
                "def get_drop_stats(",
                'self._dropped["retry_exhausted"]',
                "await self.write_client.append_rows(",
            )
        )
        and re.search(
            r"async\s+def\s+_log_event\s*\([\s\S]{0,700}?"
            r"if\s+not\s+self\.config\.enabled\s+or\s+self\._is_shutting_down\s*:\s*return",
            item[1],
        )
    ]
    runner_matches = [
        item
        for item in sources
        if all(
            marker in item[1]
            for marker in (
                "class Runner:",
                "plugins: Optional[List[BasePlugin]] = None",
                "self.plugin_manager = PluginManager(",
                "plugins=app.plugins",
            )
        )
    ]
    manager_matches = [
        item
        for item in sources
        if all(
            marker in item[1]
            for marker in (
                "class PluginManager:",
                "for plugin in self.plugins:",
                "run_before_tool_callback",
                '"before_tool_callback"',
                "run_after_tool_callback",
                '"after_tool_callback"',
                "run_on_tool_error_callback",
                '"on_tool_error_callback"',
            )
        )
    ]
    flow_matches = [
        item
        for item in sources
        if re.search(
            r"run_before_tool_callback\s*\([\s\S]{0,1800}?"
            r"__call_tool_async\s*\([\s\S]{0,1800}?"
            r"run_after_tool_callback\s*\(",
            item[1],
        )
        and "run_on_tool_error_callback(" in item[1]
    ]
    if not all(
        len(matches) == 1
        for matches in (plugin_matches, runner_matches, manager_matches, flow_matches)
    ):
        return

    plugin_path, plugin_text, _plugin_tree = plugin_matches[0]
    runner_path, _runner_text, _runner_tree = runner_matches[0]
    manager_path, _manager_text, _manager_tree = manager_matches[0]
    flow_path, _flow_text, _flow_tree = flow_matches[0]
    plugin_lines = plugin_text.splitlines()
    class_offset = plugin_text.find("class BigQueryAgentAnalyticsPlugin(BasePlugin):")
    storage_offset = plugin_text.find("await self.write_client.append_rows(")
    if class_offset < 0 or storage_offset < 0:
        return
    class_line = line_at(plugin_text, class_offset)
    storage_line = line_at(plugin_text, storage_offset)
    class_evidence = Evidence(plugin_path, class_line, excerpt(plugin_lines, class_line))
    storage_evidence = Evidence(plugin_path, storage_line, excerpt(plugin_lines, storage_line))
    analysis = "python-google-adk-bigquery-action-audit"
    audit_attributes: dict[str, object] = {
        "analysis": analysis,
        "framework": "google-adk",
        "sink": "bigquery-storage-write-api",
        "durability": "durable-remote-database",
        "delivery": "best-effort-with-drop-accounting",
        "event_types": ["TOOL_STARTING", "TOOL_COMPLETED", "TOOL_ERROR"],
        "attribution_fields": [
            "event_id",
            "agent",
            "user_id",
            "session_id",
            "invocation_id",
            "tool",
        ],
        "plugin_path": plugin_path,
        "runner_path": runner_path,
        "manager_path": manager_path,
        "flow_path": flow_path,
    }
    ir.add_component(
        Component(
            "control",
            "durable-action-audit",
            class_evidence,
            {
                **audit_attributes,
                "deployment_state": "framework-available",
                "scope": source_scope(plugin_path),
            },
        )
    )
    ir.add_component(
        Component(
            "capability",
            "audit-storage",
            storage_evidence,
            {
                "analysis": analysis,
                "api": "BigQueryWriteAsyncClient.append_rows",
                "sink": "bigquery-storage-write-api",
                "durability": "durable-remote-database",
                "scope": source_scope(plugin_path),
            },
        )
    )
    ir.add_relationship(
        Relationship(
            "control",
            "durable-action-audit",
            "exports-to",
            "capability",
            "audit-storage",
            storage_evidence,
            audit_attributes,
        )
    )

    wrapper_matches = [
        item
        for item in sources
        if all(
            marker in item[1]
            for marker in (
                "from google.adk.runners import InMemoryRunner as AfInMemoryRunner",
                "from google.adk.runners import Runner",
                "class InMemoryRunner:",
                "plugins: list[BasePlugin] = []",
                "self.runner = Runner(",
                "plugins=plugins",
            )
        )
    ]
    wrapper_available = len(wrapper_matches) == 1

    def imported_bindings(body: list[ast.stmt]) -> tuple[set[str], set[str], set[str]]:
        plugin_classes: set[str] = set()
        config_classes: set[str] = set()
        runner_constructors: set[str] = set()
        for statement in body:
            if isinstance(statement, ast.ImportFrom):
                if statement.module == "google.adk.plugins.bigquery_agent_analytics_plugin":
                    for alias in statement.names:
                        local = alias.asname or alias.name
                        if alias.name == "BigQueryAgentAnalyticsPlugin":
                            plugin_classes.add(local)
                        elif alias.name == "BigQueryLoggerConfig":
                            config_classes.add(local)
                elif statement.module == "google.adk.plugins":
                    for alias in statement.names:
                        if alias.name == "bigquery_agent_analytics_plugin":
                            module = alias.asname or alias.name
                            plugin_classes.add(f"{module}.BigQueryAgentAnalyticsPlugin")
                            config_classes.add(f"{module}.BigQueryLoggerConfig")
                elif statement.module == "google.adk.runners":
                    for alias in statement.names:
                        if alias.name in {"Runner", "InMemoryRunner"}:
                            runner_constructors.add(alias.asname or alias.name)
                elif wrapper_available and statement.level and any(
                    alias.name == "testing_utils" for alias in statement.names
                ):
                    for alias in statement.names:
                        if alias.name == "testing_utils":
                            runner_constructors.add(
                                f"{alias.asname or alias.name}.InMemoryRunner"
                            )
            elif isinstance(statement, ast.Import):
                for alias in statement.names:
                    if alias.name == "google.adk.plugins.bigquery_agent_analytics_plugin":
                        module = alias.asname or alias.name
                        plugin_classes.add(f"{module}.BigQueryAgentAnalyticsPlugin")
                        config_classes.add(f"{module}.BigQueryLoggerConfig")
                    elif alias.name == "google.adk.runners":
                        module = alias.asname or alias.name
                        runner_constructors.update(
                            {f"{module}.Runner", f"{module}.InMemoryRunner"}
                        )
        return plugin_classes, config_classes, runner_constructors

    def scope_binding_counts(
        body: list[ast.stmt], parameters: tuple[str, ...] = ()
    ) -> Counter[str]:
        counts: Counter[str] = Counter(parameters)

        def collect(node: ast.AST) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    counts[node.name] += 1
                return
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    counts[alias.asname or alias.name.split(".", 1)[0]] += 1
                return
            if isinstance(node, ast.ExceptHandler) and node.name:
                counts[node.name] += 1
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                counts[node.id] += 1
            for child in ast.iter_child_nodes(node):
                collect(child)

        for statement in body:
            collect(statement)
        return counts

    def assigned_calls(
        body: list[ast.stmt], parameters: tuple[str, ...] = ()
    ) -> dict[str, ast.Call]:
        counts = scope_binding_counts(body, parameters)
        result: dict[str, ast.Call] = {}
        for statement in body:
            target: ast.Name | None = None
            value: ast.AST | None = None
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
            if target is not None and counts[target.id] == 1 and isinstance(value, ast.Call):
                result[target.id] = value
        return result

    def configuration_state(
        expression: ast.AST,
        config_classes: set[str],
        configs: dict[str, ast.Call],
    ) -> str:
        if isinstance(expression, ast.Constant) and expression.value is None:
            return "enabled"
        if isinstance(expression, ast.Name):
            call = configs.get(expression.id)
            return configuration_state(call, config_classes, configs) if call else "unresolved"
        if not isinstance(expression, ast.Call) or dotted_name(expression.func) not in config_classes:
            return "unresolved"
        if any(keyword.arg is None for keyword in expression.keywords):
            return "unresolved"
        if any(
            keyword.arg in {"event_allowlist", "event_denylist"}
            for keyword in expression.keywords
        ):
            return "unresolved"
        enabled = next(
            (keyword.value for keyword in expression.keywords if keyword.arg == "enabled"),
            None,
        )
        if enabled is None:
            return "enabled"
        if isinstance(enabled, ast.Constant) and isinstance(enabled.value, bool):
            return "enabled" if enabled.value else "disabled-explicit"
        return "unresolved"

    def plugin_state(
        call: ast.Call,
        config_classes: set[str],
        configs: dict[str, ast.Call],
    ) -> str:
        if any(keyword.arg is None for keyword in call.keywords):
            return "unresolved"
        if any(
            keyword.arg in {"event_allowlist", "event_denylist"}
            for keyword in call.keywords
        ):
            return "unresolved"
        config = next((keyword.value for keyword in call.keywords if keyword.arg == "config"), None)
        state = (
            configuration_state(config, config_classes, configs)
            if config is not None
            else "enabled"
        )
        enabled = next(
            (keyword.value for keyword in call.keywords if keyword.arg == "enabled"),
            None,
        )
        if enabled is not None:
            if not isinstance(enabled, ast.Constant) or not isinstance(enabled.value, bool):
                return "unresolved"
            state = "enabled" if enabled.value else "disabled-explicit"
        return state

    for app_path, app_text, tree in sources:
        module_plugin_classes, module_config_classes, module_runner_constructors = (
            imported_bindings(tree.body)
        )
        if not module_plugin_classes:
            continue
        app_lines = app_text.splitlines()
        scopes: list[tuple[list[ast.stmt], tuple[str, ...]]] = [(tree.body, ())]
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            arguments = (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
            parameters = tuple(argument.arg for argument in arguments)
            if node.args.vararg is not None:
                parameters += (node.args.vararg.arg,)
            if node.args.kwarg is not None:
                parameters += (node.args.kwarg.arg,)
            scopes.append((node.body, parameters))
        for body, parameters in scopes:
            local_plugin_classes, local_config_classes, local_runner_constructors = (
                imported_bindings(body)
            )
            plugin_classes = module_plugin_classes | local_plugin_classes
            config_classes = module_config_classes | local_config_classes
            runner_constructors = module_runner_constructors | local_runner_constructors
            if not runner_constructors:
                continue
            calls = assigned_calls(body, parameters)
            configs = {
                name: call
                for name, call in calls.items()
                if dotted_name(call.func) in config_classes
            }
            plugins = {
                name: (call, plugin_state(call, config_classes, configs))
                for name, call in calls.items()
                if dotted_name(call.func) in plugin_classes
            }
            agents = {
                name: next(
                    (
                        component
                        for component in ir.components
                        if component.kind == "agent"
                        and component.evidence.path == app_path
                        and component.evidence.line == call.lineno
                    ),
                    None,
                )
                for name, call in calls.items()
                if dotted_name(call.func).rsplit(".", 1)[-1] in AGENT_CALLS
            }
            for runner_call in calls.values():
                if dotted_name(runner_call.func) not in runner_constructors:
                    continue
                agent_expression = next(
                    (
                        keyword.value
                        for keyword in runner_call.keywords
                        if keyword.arg in {"agent", "root_agent"}
                    ),
                    runner_call.args[0] if runner_call.args else None,
                )
                plugins_expression = next(
                    (
                        keyword.value
                        for keyword in runner_call.keywords
                        if keyword.arg == "plugins"
                    ),
                    None,
                )
                if not isinstance(agent_expression, ast.Name) or not isinstance(
                    plugins_expression, (ast.List, ast.Tuple)
                ):
                    continue
                agent = agents.get(agent_expression.id)
                if agent is None:
                    continue
                plugin_names = [
                    element.id for element in plugins_expression.elts if isinstance(element, ast.Name)
                ]
                if len(plugin_names) != len(plugins_expression.elts):
                    continue
                selected_plugins = [plugins[name] for name in plugin_names if name in plugins]
                if len(selected_plugins) != 1:
                    continue
                plugin_call, state = selected_plugins[0]
                runner_evidence = Evidence(
                    app_path,
                    runner_call.lineno,
                    excerpt(app_lines, runner_call.lineno),
                )
                plugin_evidence = Evidence(
                    app_path,
                    plugin_call.lineno,
                    excerpt(app_lines, plugin_call.lineno),
                )
                if state != "enabled":
                    setting_attributes = {
                        "analysis": analysis,
                        "enabled": False if state == "disabled-explicit" else "unresolved",
                        "state": state,
                        "scope": source_scope(app_path),
                        "plugin_path": plugin_path,
                    }
                    ir.add_component(
                        Component(
                            "control-setting",
                            "action-audit",
                            plugin_evidence,
                            setting_attributes,
                        )
                    )
                    ir.add_relationship(
                        Relationship(
                            "agent",
                            agent.name,
                            "configured-by",
                            "control-setting",
                            "action-audit",
                            runner_evidence,
                            setting_attributes,
                            source_id=agent.symbol_id,
                        )
                    )
                    continue

                deployed_attributes = {
                    **audit_attributes,
                    "deployment_state": "enabled",
                    "scope": source_scope(app_path),
                    "plugin_line": plugin_call.lineno,
                    "policy_effect": "records-attributable-tool-actions",
                }
                ir.add_component(
                    Component(
                        "control",
                        "durable-action-audit",
                        runner_evidence,
                        deployed_attributes,
                    )
                )
                ir.add_relationship(
                    Relationship(
                        "agent",
                        agent.name,
                        "governed-by",
                        "control",
                        "durable-action-audit",
                        runner_evidence,
                        deployed_attributes,
                        source_id=agent.symbol_id,
                    )
                )
                tool_edges = [
                    edge
                    for edge in ir.relationships
                    if edge.source_kind == "agent"
                    and edge.relation == "uses"
                    and edge.target_kind == "tool"
                    and (
                        (agent.symbol_id is not None and edge.source_id == agent.symbol_id)
                        or (
                            agent.symbol_id is None
                            and edge.source_name == agent.name
                            and edge.evidence.path == app_path
                            and edge.evidence.line == agent.evidence.line
                        )
                    )
                ]
                for tool_edge in tool_edges:
                    ir.add_relationship(
                        Relationship(
                            "tool",
                            tool_edge.target_name,
                            "governed-by",
                            "control",
                            "durable-action-audit",
                            runner_evidence,
                            deployed_attributes,
                            source_id=tool_edge.target_id,
                        )
                    )
                    capability_edges = [
                        edge
                        for edge in ir.relationships
                        if edge.source_kind == "tool"
                        and edge.relation == "uses"
                        and edge.target_kind == "capability"
                        and edge.target_name == "external-action"
                        and (
                            (
                                tool_edge.target_id is not None
                                and edge.source_id == tool_edge.target_id
                            )
                            or (
                                tool_edge.target_id is None
                                and edge.source_name == tool_edge.target_name
                                and edge.evidence.path
                                == tool_edge.attributes.get("target_path", app_path)
                            )
                        )
                    ]
                    for capability_edge in capability_edges:
                        ir.add_relationship(
                            Relationship(
                                "capability",
                                "external-action",
                                "governed-by",
                                "control",
                                "durable-action-audit",
                                capability_edge.evidence,
                                {
                                    **deployed_attributes,
                                    "control_path": app_path,
                                    "control_line": runner_call.lineno,
                                },
                            )
                        )


def add_python_skyvern_action_history_flow(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve Skyvern Task v3 actions into its committed SQL action history."""
    sources: dict[str, str] = {}
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            ast.parse(text, filename=relative)
        except (OSError, SyntaxError, ValueError):
            continue
        sources[relative] = text

    required_paths = {
        "loop": "skyvern/forge/taskv3/loop.py",
        "agent": "skyvern/forge/agent.py",
        "repository": "skyvern/forge/sdk/db/repositories/workflow_parameters.py",
        "model": "skyvern/forge/sdk/db/models.py",
    }
    if not all(path in sources for path in required_paths.values()):
        return
    loop_path = required_paths["loop"]
    agent_path = required_paths["agent"]
    repository_path = required_paths["repository"]
    model_path = required_paths["model"]
    loop_text = sources[loop_path]
    agent_text = sources[agent_path]
    repository_text = sources[repository_path]
    model_text = sources[model_path]

    loop_markers = (
        "async def run_agent_tool_loop(",
        "result = await spec.handler(args)",
        "if spec is not None and (spec.billable or spec.recordable):",
        "round_actions.append((tool_name, args, result.status == \"ok\"))",
        "if round_actions and on_action_round is not None:",
        "await on_action_round(round_actions)",
        'LOG.warning("taskv3 on_action_round callback failed"',
    )
    if not all(marker in loop_text for marker in loop_markers):
        return
    agent_markers = (
        "async def _on_action_round(",
        "for name, args, succeeded in round_actions:",
        "status=ActionStatus.completed if succeeded else ActionStatus.failed",
        "organization_id=task.organization_id",
        "workflow_run_id=task.workflow_run_id",
        "task_id=task.task_id",
        "step_id=step.step_id",
        "action_order=len(v3_persisted_actions)",
        "await app.DATABASE.workflow_params.create_action(action=action)",
        'LOG.warning("task_v3 failed to persist action row"',
        "outcome = await run_task_v3_agent_loop(",
        "on_action_round=_on_action_round",
    )
    if not all(marker in agent_text for marker in agent_markers):
        return
    repository_markers = (
        '@db_operation("create_action")',
        "async def create_action(self, action:",
        "raw_action_payload = action.model_dump()",
        "new_action = ActionModel(",
        "action_json=raw_action_payload",
        "session.add(new_action)",
        "await session.commit()",
        "await session.refresh(new_action)",
        "return hydrate_action(new_action)",
    )
    if not all(marker in repository_text for marker in repository_markers):
        return
    model_markers = (
        "class ActionModel(Base):",
        '__tablename__ = "actions"',
        "action_id = Column(String, primary_key=True",
        "action_type = Column(String, nullable=False)",
        "organization_id = Column(String, nullable=True)",
        "workflow_run_id = Column(String, nullable=True)",
        "task_id = Column(String, nullable=False",
        "step_id = Column(String, nullable=False)",
        "step_order = Column(Integer, nullable=False)",
        "action_order = Column(Integer, nullable=False)",
        "status = Column(String, nullable=False)",
        "action_json = Column(JSON, nullable=True)",
        "screenshot_artifact_id = Column(String, nullable=True)",
        "created_by = Column(String, nullable=True)",
    )
    if not all(marker in model_text for marker in model_markers):
        return

    handler_offset = loop_text.find("result = await spec.handler(args)")
    callback_offset = agent_text.find(
        "await app.DATABASE.workflow_params.create_action(action=action)"
    )
    agent_offset = agent_text.find("outcome = await run_task_v3_agent_loop(")
    create_action_offset = repository_text.find("async def create_action(self, action:")
    commit_offset = repository_text.find("await session.commit()", create_action_offset)
    if min(handler_offset, callback_offset, agent_offset, commit_offset) < 0:
        return
    loop_lines = loop_text.splitlines()
    agent_lines = agent_text.splitlines()
    repository_lines = repository_text.splitlines()
    handler_line = line_at(loop_text, handler_offset)
    callback_line = line_at(agent_text, callback_offset)
    agent_line = line_at(agent_text, agent_offset)
    commit_line = line_at(repository_text, commit_offset)
    handler_evidence = Evidence(
        loop_path, handler_line, excerpt(loop_lines, handler_line)
    )
    callback_evidence = Evidence(
        agent_path, callback_line, excerpt(agent_lines, callback_line)
    )
    agent_evidence = Evidence(agent_path, agent_line, excerpt(agent_lines, agent_line))
    storage_evidence = Evidence(
        repository_path,
        commit_line,
        excerpt(repository_lines, commit_line),
    )
    analysis = "python-skyvern-taskv3-action-history"
    agent_name = "Skyvern Task v3 agent loop"
    tool_name = "Task v3 recordable action dispatch"
    agent_id = source_symbol("py", agent_path, "agent", "skyvern-task-v3-loop")
    tool_id = source_symbol("py", loop_path, "tool", "recordable-action-dispatch")
    control_attributes: dict[str, object] = {
        "analysis": analysis,
        "framework": "skyvern-task-v3",
        "deployment_state": "enabled",
        "scope": source_scope(agent_path),
        "durability": "durable-relational-database",
        "delivery": "best-effort-post-action",
        "record_states": ["completed", "failed"],
        "attribution_fields": [
            "action_id",
            "organization_id",
            "workflow_run_id",
            "task_id",
            "step_id",
            "action_type",
            "status",
            "step_order",
            "action_order",
        ],
        "actor_attribution": "unresolved-created-by-nullable-and-unset",
        "failure_behavior": "persistence-errors-contained",
        "policy_effect": "records-executed-browser-actions",
        "loop_path": loop_path,
        "repository_path": repository_path,
        "model_path": model_path,
    }
    capability_attributes = {
        "analysis": analysis,
        "scope": source_scope(loop_path),
        "operation": "billable-or-recordable-browser-action",
        "dispatch": "post-model-tool-selection",
    }
    storage_attributes = {
        "analysis": analysis,
        "scope": source_scope(repository_path),
        "api": "SQLAlchemy AsyncSession.commit",
        "sink": "sqlalchemy-actions-table",
        "table": "actions",
        "durability": "durable-relational-database",
    }
    ir.add_component(
        Component("agent", agent_name, agent_evidence, {"framework": "Skyvern"}, agent_id)
    )
    ir.add_component(Component("tool", tool_name, handler_evidence, {}, tool_id))
    ir.add_component(
        Component("capability", "external-action", handler_evidence, capability_attributes)
    )
    ir.add_component(
        Component(
            "control",
            "durable-action-record",
            callback_evidence,
            control_attributes,
        )
    )
    ir.add_component(
        Component("capability", "audit-storage", storage_evidence, storage_attributes)
    )
    ir.add_relationship(
        Relationship(
            "agent",
            agent_name,
            "uses",
            "tool",
            tool_name,
            agent_evidence,
            {"analysis": analysis},
            source_id=agent_id,
            target_id=tool_id,
        )
    )
    ir.add_relationship(
        Relationship(
            "tool",
            tool_name,
            "uses",
            "capability",
            "external-action",
            handler_evidence,
            capability_attributes,
            source_id=tool_id,
        )
    )
    for source_kind, source_name, evidence, source_id in (
        ("agent", agent_name, agent_evidence, agent_id),
        ("tool", tool_name, callback_evidence, tool_id),
        ("capability", "external-action", handler_evidence, None),
    ):
        ir.add_relationship(
            Relationship(
                source_kind,
                source_name,
                "governed-by",
                "control",
                "durable-action-record",
                evidence,
                control_attributes,
                source_id=source_id,
            )
        )
    ir.add_relationship(
        Relationship(
            "control",
            "durable-action-record",
            "exports-to",
            "capability",
            "audit-storage",
            storage_evidence,
            {**control_attributes, **storage_attributes},
        )
    )


def add_typescript_a2a_card_endpoint_composition(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve remotely fetched A2A cards into SDK-selected downstream RPC origins."""
    sources: dict[str, tuple[str, str]] = {}
    for path in paths:
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"} or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        sources[relative] = (text, typescript_code_mask(text))

    def add_gap(
        relative: str,
        text: str,
        call_offset: int,
        class_match: re.Match[str],
        attributes: dict[str, object],
    ) -> None:
        call_line = line_at(text, call_offset)
        class_line = line_at(text, class_match.start())
        evidence = Evidence(relative, call_line, excerpt(text.splitlines(), call_line))
        protocol_id = f"ts:{relative}#protocol:a2a-card-client"
        capability_attributes = {
            "scope": source_scope(relative),
            "frontend": "typescript",
            "protocol": "a2a",
            "dynamic_origin": False,
            "origin_authority": "remote-agent-card",
            "remote_card_endpoint_scope": "unconstrained",
            **attributes,
        }
        ir.add_component(
            Component(
                "protocol",
                "A2A",
                Evidence(relative, class_line, excerpt(text.splitlines(), class_line)),
                {
                    "role": "client",
                    "card_source": capability_attributes["card_source_scope"],
                },
                protocol_id,
            )
        )
        ir.add_component(Component("capability", "a2a-rpc", evidence, capability_attributes))
        ir.add_relationship(
            Relationship(
                "protocol",
                "A2A",
                "uses",
                "capability",
                "a2a-rpc",
                evidence,
                capability_attributes,
                source_id=protocol_id,
            )
        )

    selected = set(sources)
    remote_agent_callers = [
        (relative, text, code)
        for relative, (text, code) in sources.items()
        if re.search(r"\bclass\s+(?:A2ARemoteAgent|RemoteA2AAgent)\b", code)
        and "this.card = await resolveAgentCard(this.a2aConfig.agentCard)" in code
        and "factory.createFromAgentCard(this.card)" in code
    ]
    resolver_sources = [
        (relative, text, code)
        for relative, (text, code) in sources.items()
        if "export async function resolveAgentCard(" in code
        and "new DefaultAgentCardResolver()" in code
        and "resolver.resolve(source)" in code
    ]
    if len(remote_agent_callers) == 1 and len(resolver_sources) == 1:
        caller_path, caller_text, caller_code = remote_agent_callers[0]
        resolver_path, resolver_text, resolver_code = resolver_sources[0]
        imports = typescript_named_import_bindings(caller_text, "@a2a-js/sdk/client")
        chain_match = re.search(
            r"this\.card\s*=\s*await\s+resolveAgentCard\s*\(\s*this\.a2aConfig\.agentCard\s*\)\s*;"
            r"\s*if\s*\(\s*!this\.client\s*\)\s*\{"
            r"[\s\S]{0,500}?this\.client\s*=\s*await\s+factory\.createFromAgentCard\s*\(\s*this\.card\s*\)",
            caller_code,
        )
        call_match = re.search(
            r"factory\.createFromAgentCard\s*\(\s*this\.card\s*\)", caller_code
        )
        class_match = re.search(
            r"\bclass\s+(?:A2ARemoteAgent|RemoteA2AAgent)\b", caller_code
        )
        resolver_proof = re.search(
            r"source\.startsWith\s*\(\s*['\"]http://['\"]\s*\)\s*\|\|\s*"
            r"source\.startsWith\s*\(\s*['\"]https://['\"]\s*\)"
            r"[\s\S]{0,300}?new\s+DefaultAgentCardResolver\s*\(\s*\)"
            r"[\s\S]{0,300}?resolver\.resolve\s*\(\s*source\s*\)",
            resolver_text,
        )
        if (
            chain_match is not None
            and call_match is not None
            and class_match is not None
            and resolver_proof is not None
            and imports.get("ClientFactory") == "ClientFactory"
            and typescript_named_import_reaches_path(
                root,
                root / caller_path,
                caller_text,
                "resolveAgentCard",
                "resolveAgentCard",
                resolver_path,
                selected,
            )
        ):
            resolver_offset = resolver_code.find("export async function resolveAgentCard(")
            add_gap(
                caller_path,
                caller_text,
                call_match.start(),
                class_match,
                {
                    "analysis": "typescript-adk-a2a-card-endpoint-composition",
                    "card_source_scope": "configuration-object-url-or-local-file",
                    "card_fetch_scope": "sdk-default-resolver",
                    "rpc_origin_scope": "remote-card-controlled",
                    "rpc_scheme_scope": "remote-card-controlled",
                    "advertised_interface_scope": "sdk-selected",
                    "redirect_scope": "sdk-default-unresolved",
                    "dns_scope": "sdk-default-unresolved",
                    "proxy_scope": "sdk-default-unresolved",
                    "transport_scope": "sdk-client-factory",
                    "endpoint_policy": "absent-on-proven-path",
                    "resolver_path": resolver_path,
                    "resolver_line": line_at(resolver_text, resolver_offset),
                },
            )

    manager_sources = [
        (relative, text, code)
        for relative, (text, code) in sources.items()
        if "class A2AClientManager" in code
        and "new DefaultAgentCardResolver({" in code
        and "factory.createFromAgentCard(agentCard)" in code
        and "dispatcher: this.a2aDispatcher" in code
    ]
    if len(manager_sources) == 1:
        relative, text, code = manager_sources[0]
        sdk_imports = typescript_named_import_bindings(text, "@a2a-js/sdk/client")
        undici_imports = typescript_named_import_bindings(text, "undici")
        remote_resolution = re.search(
            r"if\s*\(\s*options\.type\s*===\s*['\"]json['\"]\s*\)\s*\{"
            r"[\s\S]{0,500}?JSON\.parse\s*\(\s*options\.json\s*\)"
            r"[\s\S]{0,1500}?\}\s*else\s*\{"
            r"[\s\S]{0,300}?resolver\.resolve\s*\(\s*options\.url\s*,\s*['\"]['\"]\s*\)",
            text,
        )
        create_chain = re.search(
            r"const\s+agentCard\s*=\s*normalizeAgentCard\s*\(\s*rawCard\s*\)"
            r"[\s\S]{0,1800}?new\s+ClientFactory\s*\([^)]*\)"
            r"[\s\S]{0,300}?(?:const\s+client\s*=|return)\s*await\s+"
            r"factory\.createFromAgentCard\s*\(\s*agentCard\s*\)",
            code,
        )
        create_match = re.search(
            r"factory\.createFromAgentCard\s*\(\s*agentCard\s*\)", code
        )
        normalized_card = re.search(
            r"const\s+agentCard\s*=\s*normalizeAgentCard\s*\(\s*rawCard\s*\)", code
        )
        intervening_card_call = None
        if normalized_card is not None and create_match is not None:
            intervening_card_call = re.search(
                r"\b[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*\(\s*agentCard\s*[,)]",
                code[normalized_card.end() : create_match.start()],
            )
        class_match = re.search(r"\bclass\s+A2AClientManager\b", code)
        dispatcher_proof = re.search(
            r"new\s+ProxyAgent\s*\([\s\S]{0,400}?new\s+UndiciAgent\s*\("
            r"[\s\S]{0,500}?fetch\s*\(\s*input\s*,\s*\{\s*\.\.\.init\s*,\s*"
            r"dispatcher\s*:\s*this\.a2aDispatcher",
            code,
        )
        grpc_endpoint = re.search(
            r"agentCard\.additionalInterfaces\?\.find\s*\([\s\S]{0,250}?"
            r"transport\s*===\s*['\"]GRPC['\"][\s\S]{0,120}?\)\s*\?\.url"
            r"\s*\?\?\s*agentCard\.url",
            text,
        )
        if (
            remote_resolution is not None
            and create_chain is not None
            and create_match is not None
            and normalized_card is not None
            and intervening_card_call is None
            and class_match is not None
            and dispatcher_proof is not None
            and grpc_endpoint is not None
            and all(
                sdk_imports.get(name) == name
                for name in ("ClientFactory", "DefaultAgentCardResolver")
            )
            and undici_imports.get("ProxyAgent") == "ProxyAgent"
            and undici_imports.get("UndiciAgent") == "Agent"
        ):
            add_gap(
                relative,
                text,
                create_match.start(),
                class_match,
                {
                    "analysis": "typescript-gemini-a2a-card-endpoint-composition",
                    "card_source_scope": "configured-url-or-inline-json",
                    "card_fetch_scope": "unauthenticated-first-auth-retry",
                    "rpc_origin_scope": "remote-card-controlled",
                    "rpc_scheme_scope": "remote-card-controlled-grpc-allows-insecure",
                    "advertised_interface_scope": "sdk-selected",
                    "redirect_scope": "sdk-default-unresolved",
                    "dns_scope": "dispatcher-default-unpinned",
                    "proxy_scope": "configuration-dependent",
                    "transport_scope": "undici-agent-or-proxy",
                    "endpoint_policy": "absent-on-proven-path",
                },
            )


def add_python_adk_a2a_card_endpoint_policy(
    ir: RepositoryIR,
    root: Path,
    paths: list[Path],
) -> None:
    """Resolve ADK Python's all-interface HTTPS/loopback and same-origin card policy."""
    candidates: list[tuple[str, str]] = []
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        required = (
            "class RemoteA2aAgent",
            "async def _validate_agent_card(",
            "def _validate_card_rpc_targets(",
            "_compat.agent_card_rpc_urls(agent_card)",
            "self._a2a_client_factory.create(",
        )
        if all(marker in text for marker in required):
            candidates.append((relative, text))
    if len(candidates) != 1:
        return
    relative, text = candidates[0]
    try:
        ast.parse(text, filename=relative)
    except SyntaxError:
        return
    policy_proof = (
        re.search(
            r"async\s+def\s+_validate_agent_card\s*\([^)]*agent_card[^)]*\)\s*[^:]*:"
            r"[\s\S]{0,1000}?self\._validate_card_rpc_targets\s*\(\s*agent_card\s*\)",
            text,
        )
        and re.search(
            r"def\s+_validate_card_rpc_targets\s*\([^)]*agent_card[^)]*\)\s*[^:]*:"
            r"[\s\S]{0,1000}?source\.startswith\s*\(\s*\(\s*['\"]http://['\"]\s*,\s*['\"]https://['\"]\s*\)\s*\)"
            r"[\s\S]{0,1000}?for\s+card_url\s+in\s+_compat\.agent_card_rpc_urls\s*\(\s*agent_card\s*\)\s*:"
            r"[\s\S]{0,1000}?parsed_card\.scheme\.lower\s*\(\s*\)\s*!=\s*['\"]https['\"]"
            r"[\s\S]{0,500}?not\s+_is_loopback_host\s*\(\s*parsed_card\.hostname\s*\)"
            r"[\s\S]{0,1000}?card_origin\s*=\s*_url_origin\s*\(\s*card_url\s*\)"
            r"[\s\S]{0,500}?card_origin\s*!=\s*source_origin",
            text,
        )
    )
    if not policy_proof:
        return
    path_patterns = (
        re.compile(
            r"agent_card\s*=\s*await\s+self\._resolve_agent_card\s*\(\s*ctx\s*\)"
            r"[\s\S]{0,500}?await\s+self\._validate_agent_card\s*\(\s*agent_card\s*\)"
            r"[\s\S]{0,500}?client\s*=\s*self\._a2a_client_factory\.create\s*\(\s*agent_card\s*\)"
        ),
        re.compile(
            r"self\._agent_card\s*=\s*await\s+self\._resolve_agent_card\s*\(\s*ctx\s*\)"
            r"[\s\S]{0,600}?await\s+self\._validate_agent_card\s*\(\s*self\._agent_card\s*\)"
            r"[\s\S]{0,800}?self\._a2a_client\s*=\s*self\._a2a_client_factory\.create\s*\(\s*self\._agent_card\s*\)"
        ),
    )
    matches = [match for pattern in path_patterns if (match := pattern.search(text)) is not None]
    if not matches:
        return
    class_match = re.search(r"\bclass\s+RemoteA2aAgent\b", text)
    policy_match = re.search(r"\bdef\s+_validate_card_rpc_targets\b", text)
    if class_match is None or policy_match is None:
        return
    protocol_id = f"py:{relative}#protocol:a2a-card-client"
    class_line = line_at(text, class_match.start())
    policy_line = line_at(text, policy_match.start())
    control_attributes: dict[str, object] = {
        "scope": source_scope(relative),
        "frontend": "python",
        "analysis": "python-google-adk-a2a-card-endpoint-policy",
        "policy_effect": "binds-network-card-rpc-to-source-origin",
        "card_source_scope": "network-card-only",
        "rpc_origin_scope": "same-origin-with-card-source",
        "rpc_scheme_scope": "https-or-loopback-http",
        "advertised_interface_scope": "all-rpc-urls",
        "enforcement_default": "enabled",
        "escape_hatch": "none",
        "enforcement_mode": "always-on-for-network-cards",
        "redirect_scope": "httpx-default-unresolved",
        "dns_scope": "httpx-default-unresolved",
        "proxy_scope": "httpx-environment-dependent",
        "transport_scope": "httpx-sdk-client-factory",
        "control_path": relative,
        "control_line": policy_line,
    }
    ir.add_component(
        Component(
            "protocol",
            "A2A",
            Evidence(relative, class_line, excerpt(text.splitlines(), class_line)),
            {"role": "client", "card_source": "configuration-url-or-local-file"},
            protocol_id,
        )
    )
    ir.add_component(
        Component(
            "control",
            "a2a-card-rpc-origin-policy",
            Evidence(relative, policy_line, excerpt(text.splitlines(), policy_line)),
            control_attributes,
        )
    )
    for match in matches:
        create_offset = match.start() + match.group(0).rfind(
            "self._a2a_client_factory.create"
        )
        if create_offset < match.start():
            continue
        call_line = line_at(text, create_offset)
        evidence = Evidence(relative, call_line, excerpt(text.splitlines(), call_line))
        capability_attributes = {
            "scope": source_scope(relative),
            "frontend": "python",
            "protocol": "a2a",
            "dynamic_origin": False,
            "origin_authority": "remote-agent-card",
            "remote_card_endpoint_scope": "same-origin-constrained",
            "analysis": "python-google-adk-a2a-card-endpoint-policy",
        }
        ir.add_component(Component("capability", "a2a-rpc", evidence, capability_attributes))
        ir.add_relationship(
            Relationship(
                "protocol",
                "A2A",
                "uses",
                "capability",
                "a2a-rpc",
                evidence,
                capability_attributes,
                source_id=protocol_id,
            )
        )
        ir.add_relationship(
            Relationship(
                "capability",
                "a2a-rpc",
                "governed-by",
                "control",
                "a2a-card-rpc-origin-policy",
                evidence,
                control_attributes,
            )
        )


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
    decorated_tool_exports = build_python_decorated_tool_exports(root, registry_paths)
    (
        imported_tool_references,
        imported_tool_export_references,
    ) = build_python_literal_imported_tool_references(
        root,
        registry_paths,
        module_paths,
    )
    agent_factory_class_exports = build_python_agent_factory_class_exports(
        root,
        registry_paths,
    )
    mcp_server_subclass_exports = build_python_mcp_server_subclass_exports(
        root,
        registry_paths,
    )
    registry_class_exports = build_python_registry_class_exports(
        root,
        registry_paths,
        module_paths,
    )
    network_helper_summaries = build_python_network_helper_summaries(
        root,
        registry_paths,
    )
    network_helper_summaries.update(
        build_python_secure_network_helper_summaries(
            root,
            registry_paths,
            module_paths,
        )
    )
    network_helper_summaries.update(
        build_python_proxy_conditional_secure_network_helper_summaries(
            root,
            registry_paths,
        )
    )
    network_helper_summaries.update(
        build_python_configurable_pinned_network_helper_summaries(
            root,
            registry_paths,
            module_paths,
        )
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
                decorated_tool_exports,
                imported_tool_references,
                imported_tool_export_references,
                agent_factory_class_exports,
                mcp_server_subclass_exports,
                registry_class_exports,
                network_helper_summaries,
                registered_tool_functions,
            )
        else:
            scan_typescript(ir, root, path, text)
    add_typescript_configurable_ssrf_composition(ir, root, registry_paths)
    add_typescript_flowise_secure_request_composition(ir, root, registry_paths)
    add_typescript_flowise_secure_fetch_composition(ir, root, registry_paths)
    add_typescript_google_adk_load_web_page_composition(ir, root, registry_paths)
    add_typescript_activepieces_safe_http_composition(ir, root, registry_paths)
    add_typescript_composio_ssrf_safe_fetch_composition(ir, root, registry_paths)
    add_typescript_composio_cli_file_upload_flow(ir, root, registry_paths)
    add_typescript_google_adk_openapi_rest_tool_flow(ir, root, registry_paths)
    add_typescript_a2a_card_endpoint_composition(ir, root, registry_paths)
    add_typescript_openai_agents_mcp_approval_default_flow(ir, root, registry_paths)
    add_typescript_mcp_sampling_handler_consent_flow(ir, root, registry_paths)
    add_typescript_mcp_elicitation_handler_consent_flow(ir, root, registry_paths)
    add_python_agno_mcp_confirmation_flow(ir, root, registry_paths)
    add_python_mcp_sampling_callback_consent_flow(ir, root, registry_paths)
    add_python_pydantic_ai_mcp_sampling_model_flow(ir, root, registry_paths)
    add_python_mcp_elicitation_callback_consent_flow(ir, root, registry_paths)
    add_python_fastmcp_elicitation_handler_consent_flow(ir, root, registry_paths)
    add_python_semantic_kernel_mcp_sampling_flow(ir, root, registry_paths)
    add_python_adk_a2a_card_endpoint_policy(ir, root, registry_paths)
    add_python_openai_agents_mcp_approval_default_flow(ir, root, registry_paths)
    add_python_google_adk_bigquery_audit_flow(ir, root, registry_paths)
    add_python_skyvern_action_history_flow(ir, root, registry_paths)
    propagate_python_class_network_helpers(
        ir,
        root,
        registry_paths,
        module_paths,
    )
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
