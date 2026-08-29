from __future__ import annotations

import json
import shutil
import textwrap
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator

from agentverify.analysis import component_context
from agentverify.cli import main
from agentverify.policy import evaluate_policy, normalize_policy
from agentverify.report import render_bom, render_json, render_sarif, render_text
from agentverify.scanner import build_python_module_index, scan_repository

ROOT = Path(__file__).resolve().parents[1]


def test_python_module_index_includes_every_nested_source_root(tmp_path: Path) -> None:
    helper = tmp_path / "src/distribution/src/package/security/ssrf_http.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("VALUE = 1\n", encoding="utf-8")

    assert build_python_module_index(tmp_path, [helper])["package.security.ssrf_http"] == (
        "src/distribution/src/package/security/ssrf_http.py"
    )


def test_framework_and_provider_taxonomy_requires_exact_import_or_service_proof() -> None:
    ir = scan_repository(ROOT / "cases/framework_provider_taxonomy")
    inventory = {
        (
            item.evidence.path,
            item.evidence.line,
            item.kind,
            item.name,
            item.attributes.get("module"),
        )
        for item in ir.components
        if item.kind in {"framework", "provider"}
    }

    assert inventory >= {
        ("positive.py", 1, "framework", "Agno", "agno.agent"),
        ("positive.py", 2, "framework", "Google ADK", "google.adk"),
        ("positive.py", 3, "framework", "LlamaIndex", "llama_index.core"),
        ("positive.py", 4, "framework", "Semantic Kernel", "semantic_kernel"),
        ("positive.py", 5, "framework", "smolagents", "smolagents"),
        ("positive.py", 6, "provider", "Google", "google.genai"),
        ("positive.py", 7, "provider", "Google", "google.genai"),
        ("positive.py", 8, "provider", "AWS Bedrock", "langchain_aws"),
        ("positive.ts", 1, "framework", "Google ADK", "@google/adk"),
        (
            "positive.ts",
            2,
            "framework",
            "Semantic Kernel",
            "@microsoft/semantic-kernel",
        ),
        ("positive.ts", 3, "framework", "LlamaIndex", "@llamaindex/core"),
        ("positive.ts", 4, "framework", "Mastra", "@mastra/core/agent"),
        ("positive.ts", 5, "provider", "Google", "@google/genai"),
        ("positive.ts", 6, "provider", "Google", "@ai-sdk/google"),
        (
            "positive.ts",
            7,
            "provider",
            "AWS Bedrock",
            "@aws-sdk/client-bedrock-runtime",
        ),
        (
            "positive.py",
            16,
            "framework",
            "Microsoft Agent Framework",
            "agent_framework",
        ),
        ("positive.py", 17, "framework", "CAMEL", "camel.agents"),
        ("positive.py", 18, "framework", "Qwen-Agent", "qwen_agent.agents"),
        ("positive.py", 19, "framework", "Lagent", "lagent.agents"),
        ("positive.py", 20, "framework", "MetaGPT", "metagpt.roles"),
        ("positive.py", 21, "framework", "Marvin", "marvin.agents"),
        ("positive.py", 22, "framework", "AgentScope", "agentscope.agent"),
        ("positive.py", 24, "provider", "Mistral", "mistralai"),
        ("positive.py", 25, "provider", "Groq", "groq"),
        ("positive.py", 26, "provider", "Cohere", "cohere"),
        ("positive.py", 27, "provider", "Ollama", "ollama"),
        ("positive.ts", 11, "framework", "Vercel AI SDK", "ai"),
        ("positive.ts", 12, "framework", "Vercel AI SDK", "ai/internal"),
        ("provider_calls.ts", 1, "provider", "Mistral", "@ai-sdk/mistral"),
        ("provider_calls.ts", 2, "provider", "Groq", "@ai-sdk/groq"),
        ("provider_calls.ts", 3, "provider", "Cohere", "@ai-sdk/cohere"),
    }
    service = next(
        item
        for item in ir.components
        if item.kind == "provider"
        and item.name == "AWS Bedrock"
        and item.evidence.path == "positive.py"
        and item.evidence.line == 13
    )
    assert service.attributes == {
        "constructor": "boto3.client",
        "service": "bedrock-runtime",
    }
    assert any(
        item.kind == "model"
        and item.name == "gemini-2.5-pro"
        and item.attributes["provider"] == "Google"
        for item in ir.components
    )
    assert not any(
        item.kind in {"framework", "provider"} and item.evidence.path.startswith("negative.")
        for item in ir.components
    )
    provider_calls = {
        (
            item.evidence.path,
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("module"),
            item.attributes.get("imported_symbol"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.evidence.path == "provider_constructors.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
    }
    assert provider_calls == {
        ("provider_constructors.py", 9, "Mistral", "MistralClient", "mistralai", "Mistral"),
        ("provider_constructors.py", 10, "Groq", "AsyncGroq", "groq", "AsyncGroq"),
        ("provider_constructors.py", 11, "Cohere", "co.Client", "cohere", "Client"),
        ("provider_constructors.py", 12, "Ollama", "local_models.Client", "ollama", "Client"),
        (
            "provider_constructors.py",
            13,
            "Cohere",
            "ChatCohere",
            "langchain_cohere",
            "ChatCohere",
        ),
        (
            "provider_constructors.py",
            14,
            "Groq",
            "GroqChat",
            "langchain_groq",
            "ChatGroq",
        ),
    }
    attributed_models = {
        (item.evidence.path, item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model" and item.evidence.path.startswith("provider_constructors")
    }
    assert attributed_models == {
        ("provider_constructors.py", 13, "command-r-plus", "Cohere"),
        ("provider_constructors.py", 14, "llama-3.3-70b-versatile", "Groq"),
        ("provider_constructors.py", 16, "mistral-large-latest", "Mistral"),
        ("provider_constructors_rebound.py", 17, "mixtral-8x7b", "unresolved"),
    }
    assert not any(
        item.kind == "provider"
        and item.evidence.path == "provider_constructors_rebound.py"
        and item.evidence.line >= 12
        for item in ir.components
    )
    typescript_provider_calls = {
        (
            item.evidence.path,
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("call_kind"),
            item.attributes.get("configured_by"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
    }
    assert typescript_provider_calls == {
        (
            "provider_calls.ts",
            5,
            "Mistral",
            "hostedMistral",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_calls.ts",
            6,
            "Groq",
            "buildGroq",
            "ai-sdk-provider-factory",
            None,
        ),
        (
            "provider_calls.ts",
            7,
            "Groq",
            "configuredGroq",
            "ai-sdk-provider-model",
            "buildGroq",
        ),
        (
            "provider_calls.ts",
            8,
            "Cohere",
            "cohere.embedding",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_calls.ts",
            12,
            "Groq",
            "dynamicGroq",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_calls.ts",
            21,
            "OpenAI",
            "openai",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_calls.ts",
            22,
            "OpenAI",
            "openai.image",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_calls.ts",
            23,
            "Anthropic",
            "createAnthropic",
            "ai-sdk-provider-factory",
            None,
        ),
        (
            "provider_calls.ts",
            24,
            "Anthropic",
            "configuredAnthropic",
            "ai-sdk-provider-model",
            "createAnthropic",
        ),
        (
            "provider_calls.ts",
            25,
            "Google",
            "createGoogleGenerativeAI.textEmbeddingModel",
            "ai-sdk-provider-model",
            "createGoogleGenerativeAI",
        ),
        (
            "provider_calls.ts",
            28,
            "xAI",
            "xai",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_calls.ts",
            29,
            "Azure OpenAI",
            "createAzure",
            "ai-sdk-provider-factory",
            None,
        ),
        (
            "provider_calls.ts",
            34,
            "Azure OpenAI",
            "configuredAzure.embeddingModel",
            "ai-sdk-provider-model",
            "createAzure",
        ),
        (
            "provider_calls.ts",
            38,
            "OpenAI",
            "commonJSOpenAI",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_calls.ts",
            39,
            "Azure OpenAI",
            "commonJSCreateAzure.embeddingModel",
            "ai-sdk-provider-model",
            "commonJSCreateAzure",
        ),
        (
            "provider_ai_sdk_model_bindings.ts",
            5,
            "OpenAI",
            "openai",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_ai_sdk_model_bindings.ts",
            6,
            "OpenAI",
            "createOpenAI.embeddingModel",
            "ai-sdk-provider-model",
            "createOpenAI",
        ),
        (
            "provider_ai_sdk_model_bindings.ts",
            15,
            "OpenAI",
            "openai",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_ai_sdk_model_bindings.ts",
            16,
            "OpenAI",
            "createOpenAI.embeddingModel",
            "ai-sdk-provider-model",
            "createOpenAI",
        ),
        (
            "provider_ai_sdk_model_bindings.ts",
            17,
            "OpenAI",
            "openai",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_ai_sdk_model_bindings.ts",
            18,
            "OpenAI",
            "createOpenAI.embeddingModel",
            "ai-sdk-provider-model",
            "createOpenAI",
        ),
        (
            "provider_ai_sdk_model_bindings.ts",
            19,
            "OpenAI",
            "openai",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_ai_sdk_model_bindings.ts",
            20,
            "OpenAI",
            "createOpenAI.embeddingModel",
            "ai-sdk-provider-model",
            "createOpenAI",
        ),
        (
            "provider_ai_sdk_reexport_calls.ts",
            4,
            "OpenAI",
            "projectOpenAI",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_ai_sdk_reexport_calls.ts",
            5,
            "Google",
            "projectGoogleFactory.textEmbeddingModel",
            "ai-sdk-provider-model",
            "projectGoogleFactory",
        ),
        (
            "provider_ai_sdk_reexport_calls.ts",
            6,
            "OpenAI",
            "transitiveOpenAI",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_ai_sdk_reexport_calls.ts",
            7,
            "Azure OpenAI",
            "projectAzureFactory.embeddingModel",
            "ai-sdk-provider-model",
            "projectAzureFactory",
        ),
        (
            "provider_ai_sdk_star_reexport_calls.ts",
            3,
            "OpenAI",
            "openai",
            "ai-sdk-provider-model",
            None,
        ),
        (
            "provider_ai_sdk_star_reexport_calls.ts",
            4,
            "Azure OpenAI",
            "createAzure.embeddingModel",
            "ai-sdk-provider-model",
            "createAzure",
        ),
        *(
            (
                "provider_ai_sdk_model_bindings_unresolved.ts",
                line,
                "OpenAI",
                "openai",
                "ai-sdk-provider-model",
                None,
            )
            for line in (5, 9, 13, 18, 20, 31, 37, 42, 45, 53)
        ),
        (
            "provider_native_calls.ts",
            5,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_calls.ts",
            10,
            "OpenAI",
            "openAIClient.chat.completions.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_calls.ts",
            11,
            "OpenAI",
            "namedOpenAIClient.responses.create",
            "provider-sdk-model",
            "NamedOpenAI",
        ),
        (
            "provider_native_calls.ts",
            12,
            "Anthropic",
            "anthropicClient.messages.create",
            "provider-sdk-model",
            "Anthropic",
        ),
        (
            "provider_native_calls.ts",
            13,
            "Google",
            "googleClient.models.generateContent",
            "provider-sdk-model",
            "GeminiClient",
        ),
        (
            "provider_native_calls_commonjs.js",
            9,
            "OpenAI",
            "openaiClient.responses.create",
            "provider-sdk-model",
            "OpenAIClient",
        ),
        (
            "provider_native_calls_commonjs.js",
            10,
            "Anthropic",
            "anthropicClient.messages.create",
            "provider-sdk-model",
            "AnthropicClient",
        ),
        (
            "provider_native_calls_commonjs.js",
            11,
            "Google",
            "googleClient.models.generateContent",
            "provider-sdk-model",
            "GoogleGenAI",
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            5,
            "Google",
            "aliasedGoogleClient.models.generateContent",
            "provider-sdk-model",
            "GeminiAliasClient",
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            13,
            "OpenAI",
            "aliasedOpenAIClient.responses.create",
            "provider-sdk-model",
            "NamedOpenAICommonJS",
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            14,
            "Anthropic",
            "aliasedAnthropicClient.messages.create",
            "provider-sdk-model",
            "NamedAnthropicCommonJS",
        ),
        (
            "provider_native_calls_commonjs.js",
            5,
            "OpenAI",
            "OpenAIClient",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_model_calls_unresolved.ts",
            3,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_typed_parameter_calls.ts",
            4,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_typed_parameter_calls.ts",
            12,
            "OpenAI",
            "client.responses.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_typed_arrow_calls.ts",
            4,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_typed_arrow_calls.ts",
            12,
            "OpenAI",
            "client.responses.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        *(
            (
                "provider_native_typed_arrow_calls_unresolved.ts",
                line,
                "OpenAI",
                "OpenAI",
                "provider-sdk-constructor",
                None,
            )
            for line in (7, 13, 21, 26)
        ),
        (
            "provider_native_typed_parameter_calls_unresolved.ts",
            11,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_typed_parameter_calls_unresolved.ts",
            28,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_model_calls_unresolved.ts",
            7,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_model_calls_unresolved.ts",
            8,
            "OpenAI",
            "unknownClient.responses.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_class_fields.ts",
            8,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_fields.ts",
            11,
            "OpenAI",
            "this.client.responses.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_class_fields.ts",
            18,
            "Anthropic",
            "Anthropic",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_fields.ts",
            21,
            "Anthropic",
            "this.client.messages.create",
            "provider-sdk-model",
            "Anthropic",
        ),
        (
            "provider_native_class_fields.ts",
            28,
            "Google",
            "GoogleGenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_fields.ts",
            31,
            "Google",
            "this.client.models.generateContent",
            "provider-sdk-model",
            "GoogleGenAI",
        ),
        (
            "provider_native_class_fields.ts",
            36,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_fields.ts",
            38,
            "OpenAI",
            "this.client.chat.completions.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_class_fields_unresolved.ts",
            6,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_fields_unresolved.ts",
            16,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_fields_unresolved.ts",
            17,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_fields_unresolved.ts",
            37,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_fields_unresolved.ts",
            53,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_getter.ts",
            6,
            "Anthropic",
            "Anthropic",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_getter.ts",
            9,
            "Anthropic",
            "this.client.messages.create",
            "provider-sdk-model",
            "Anthropic",
        ),
        (
            "provider_native_class_getter.ts",
            20,
            "Anthropic",
            "Anthropic",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_getter.ts",
            24,
            "Anthropic",
            "this.anthropic.messages.create",
            "provider-sdk-model",
            "Anthropic",
        ),
        (
            "provider_native_class_getter_unresolved.ts",
            16,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_getter_unresolved.ts",
            29,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_getter_unresolved.ts",
            38,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_class_getter_unresolved.ts",
            48,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_model_bindings.ts",
            4,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_model_bindings.ts",
            5,
            "OpenAI",
            "client.responses.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_model_bindings.ts",
            11,
            "OpenAI",
            "client.responses.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_model_bindings.ts",
            12,
            "OpenAI",
            "client.responses.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_model_bindings.ts",
            13,
            "OpenAI",
            "client.responses.create",
            "provider-sdk-model",
            "OpenAI",
        ),
        (
            "provider_native_model_bindings_unresolved.ts",
            3,
            "OpenAI",
            "OpenAI",
            "provider-sdk-constructor",
            None,
        ),
        *(
            (
                "provider_native_model_bindings_unresolved.ts",
                line,
                "OpenAI",
                "client.responses.create",
                "provider-sdk-model",
                "OpenAI",
            )
            for line in (7, 9, 14, 18, 23, 29, 35, 40, 43, 50)
        ),
        (
            "provider_native_calls_commonjs.js",
            6,
            "Anthropic",
            "AnthropicClient",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_calls_commonjs.js",
            7,
            "Google",
            "GoogleGenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            3,
            "Google",
            "GeminiAliasClient",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            10,
            "OpenAI",
            "NamedOpenAICommonJS",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            11,
            "Anthropic",
            "NamedAnthropicCommonJS",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_calls.ts",
            6,
            "OpenAI",
            "NamedOpenAI",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_calls.ts",
            7,
            "Anthropic",
            "Anthropic",
            "provider-sdk-constructor",
            None,
        ),
        (
            "provider_native_calls.ts",
            8,
            "Google",
            "GeminiClient",
            "provider-sdk-constructor",
            None,
        ),
    }
    assert {
        (item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_calls.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
    } == {
        (5, "mistral-small-latest", "Mistral"),
        (7, "llama-3.3-70b-versatile", "Groq"),
        (8, "embed-english-v3.0", "Cohere"),
        (21, "gpt-5-mini", "OpenAI"),
        (22, "gpt-image-2", "OpenAI"),
        (24, "claude-sonnet-4-5", "Anthropic"),
        (25, "gemini-embedding-001", "Google"),
        (28, "grok-4", "xAI"),
        (34, "text-embedding-3-small-azure", "Azure OpenAI"),
        (38, "gpt-5-commonjs", "OpenAI"),
        (39, "text-embedding-3-small-azure-commonjs", "Azure OpenAI"),
    }
    assert {
        (
            item.evidence.line,
            item.name,
            item.attributes["provider"],
            item.attributes.get("model_method"),
            item.attributes.get("model_resolution_basis"),
        )
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_ai_sdk_model_bindings.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
    } == {
        (5, "gpt-5-mini", "OpenAI", "language", "immutable-module-literal-binding"),
        (
            6,
            "text-embedding-3-small",
            "OpenAI",
            "embedding",
            "immutable-module-literal-binding",
        ),
        (15, "gpt-5-mini-object", "OpenAI", "language", "immutable-module-literal-binding"),
        (
            16,
            "text-embedding-3-large",
            "OpenAI",
            "embedding",
            "immutable-module-literal-binding",
        ),
        (17, "gpt-5-mini-bracket", "OpenAI", "language", "immutable-module-literal-binding"),
        (
            18,
            "text-embedding-3-bracket",
            "OpenAI",
            "embedding",
            "immutable-module-literal-binding",
        ),
        (19, "gpt-5-mini-quoted-key", "OpenAI", "language", "immutable-module-literal-binding"),
        (
            20,
            "text-embedding-3-quoted-key",
            "OpenAI",
            "embedding",
            "immutable-module-literal-binding",
        ),
    }
    assert {
        (
            item.evidence.line,
            item.name,
            item.attributes["provider"],
            item.attributes.get("model_method"),
            item.attributes.get("model_resolution_basis"),
        )
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_ai_sdk_model_bindings_unresolved.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
    } == {
        (9, "gpt-composed", "OpenAI", "language", "immutable-module-literal-binding"),
    }
    assert not any(
        item.kind == "model"
        and item.evidence.path == "provider_ai_sdk_model_bindings_unresolved.ts"
        and item.evidence.line != 9
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert {
        (
            item.evidence.line,
            item.name,
            item.attributes["provider"],
            item.attributes.get("model_method"),
            item.attributes.get("module"),
        )
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_ai_sdk_reexport_calls.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
    } == {
        (4, "gpt-5-reexport", "OpenAI", "language", "@ai-sdk/openai"),
        (5, "gemini-embedding-reexport", "Google", "embedding", "@ai-sdk/google"),
        (6, "gpt-5-transitive-reexport", "OpenAI", "language", "@ai-sdk/openai"),
        (
            7,
            "text-embedding-3-small-azure-reexport",
            "Azure OpenAI",
            "embedding",
            "@ai-sdk/azure",
        ),
    }
    assert {
        (
            item.evidence.line,
            item.name,
            item.attributes["provider"],
            item.attributes.get("model_method"),
            item.attributes.get("module"),
        )
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_ai_sdk_star_reexport_calls.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
    } == {
        (3, "gpt-5-star-reexport", "OpenAI", "language", "@ai-sdk/openai"),
        (
            4,
            "text-embedding-3-small-azure-star-reexport",
            "Azure OpenAI",
            "embedding",
            "@ai-sdk/azure",
        ),
    }
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_ai_sdk_reexport_calls_unresolved.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_ai_sdk_star_reexport_calls_unresolved.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert {
        (item.evidence.path, item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path
        in {
            "provider_native_calls.ts",
            "provider_native_calls_commonjs.js",
            "provider_native_calls_commonjs_alias.js",
            "provider_native_class_getter.ts",
        }
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
    } == {
        (
            "provider_native_class_getter.ts",
            24,
            "claude-sonnet-4-6-local",
            "Anthropic",
        ),
        ("provider_native_calls.ts", 10, "gpt-5-mini", "OpenAI"),
        ("provider_native_calls.ts", 11, "gpt-5.4", "OpenAI"),
        ("provider_native_calls.ts", 12, "claude-sonnet-4-6", "Anthropic"),
        ("provider_native_calls.ts", 13, "gemini-2.5-flash", "Google"),
        ("provider_native_calls_commonjs.js", 9, "gpt-5-mini", "OpenAI"),
        (
            "provider_native_calls_commonjs.js",
            10,
            "claude-sonnet-4-6",
            "Anthropic",
        ),
        (
            "provider_native_calls_commonjs.js",
            11,
            "gemini-2.5-flash",
            "Google",
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            5,
            "gemini-2.5-pro",
            "Google",
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            13,
            "gpt-5.6-mini",
            "OpenAI",
        ),
        (
            "provider_native_calls_commonjs_alias.js",
            14,
            "claude-sonnet-4-6",
            "Anthropic",
        ),
    }
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_native_typed_parameter_calls.ts"
        and item.evidence.line == 12
        and item.name == "gpt-5.4"
        and item.attributes.get("provider") == "OpenAI"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_native_class_fields.ts"
        and item.evidence.line == 31
        and item.name == "gemini-2.5-flash"
        and item.attributes.get("provider") == "Google"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_native_model_bindings.ts"
        and item.evidence.line == 5
        and item.name == "gpt-5.4"
        and item.attributes.get("provider") == "OpenAI"
        and item.attributes.get("model_resolution_basis") == "immutable-module-literal-binding"
        for item in ir.components
    )
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_native_model_bindings.ts"
        and item.evidence.line == 11
        and item.name == "gpt-5.4-object"
        and item.attributes.get("provider") == "OpenAI"
        and item.attributes.get("model_resolution_basis") == "immutable-module-literal-binding"
        for item in ir.components
    )
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_native_model_bindings.ts"
        and item.evidence.line == 12
        and item.name == "gpt-5.4-bracket"
        and item.attributes.get("provider") == "OpenAI"
        and item.attributes.get("model_resolution_basis") == "immutable-module-literal-binding"
        for item in ir.components
    )
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_native_model_bindings.ts"
        and item.evidence.line == 13
        and item.name == "gpt-5.4-quoted-key"
        and item.attributes.get("provider") == "OpenAI"
        and item.attributes.get("model_resolution_basis") == "immutable-module-literal-binding"
        for item in ir.components
    )
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_native_model_bindings_unresolved.ts"
        and item.evidence.line == 14
        and item.name == "gpt-composed"
        and item.attributes.get("provider") == "OpenAI"
        and item.attributes.get("model_resolution_basis") == "immutable-module-literal-binding"
        for item in ir.components
    )
    assert not any(
        item.kind == "provider"
        and item.evidence.path == "provider_calls_rebound.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_native_typed_parameter_calls_unresolved.ts"
        and (
            item.attributes.get("call_kind") == "provider-sdk-model"
            or (
                item.kind == "model"
                and item.attributes.get("resolution") == "exact-typescript-provider-import"
            )
        )
        for item in ir.components
    )
    assert not any(
        item.kind == "provider"
        and item.evidence.path == "provider_native_import_shadowed.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert not any(
        item.kind == "provider"
        and item.evidence.path == "provider_native_calls_commonjs_scoped.js"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_native_type_only_unresolved.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert {
        (
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("resolution_basis"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.evidence.path == "provider_native_model_calls_unresolved.ts"
        and item.attributes.get("call_kind") == "provider-sdk-model"
    } == {
        (
            8,
            "OpenAI",
            "unknownClient.responses.create",
            "immutable-constructor-binding",
        )
    }
    assert not any(
        item.kind == "model"
        and item.evidence.path == "provider_native_model_calls_unresolved.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_native_class_fields_unresolved.ts"
        and (
            item.attributes.get("call_kind") == "provider-sdk-model"
            or (
                item.kind == "model"
                and item.attributes.get("resolution") == "exact-typescript-provider-import"
            )
        )
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_native_class_getter_unresolved.ts"
        and (
            item.attributes.get("call_kind") == "provider-sdk-model"
            or (
                item.kind == "model"
                and item.attributes.get("resolution") == "exact-typescript-provider-import"
            )
        )
        for item in ir.components
    )
    assert not any(
        item.kind == "model"
        and item.evidence.path == "provider_native_model_bindings_unresolved.ts"
        and item.evidence.line != 14
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_calls_custom_endpoints.ts"
        and item.attributes.get("resolution") == "exact-typescript-provider-import"
        for item in ir.components
    )
    framework_wrapper_calls = {
        (
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("module"),
            item.attributes.get("imported_symbol"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.evidence.path == "provider_framework_wrappers.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
    }
    assert framework_wrapper_calls == {
        (13, "Ollama", "agent_models.OllamaChatModel", "agentscope.model", "OllamaChatModel"),
        (14, "Groq", "GroqProvider", "pydantic_ai.providers.groq", "GroqProvider"),
        (
            15,
            "Mistral",
            "MistralProvider",
            "pydantic_ai.providers.mistral",
            "MistralProvider",
        ),
        (
            16,
            "Cohere",
            "CohereProvider",
            "pydantic_ai.providers.cohere",
            "CohereProvider",
        ),
        (
            17,
            "Ollama",
            "OllamaProvider",
            "pydantic_ai.providers.ollama",
            "OllamaProvider",
        ),
        (18, "Groq", "PydanticGroqModel", "pydantic_ai.models.groq", "GroqModel"),
        (
            19,
            "Mistral",
            "MistralModel",
            "pydantic_ai.models.mistral",
            "MistralModel",
        ),
        (20, "Cohere", "CohereModel", "pydantic_ai.models.cohere", "CohereModel"),
        (21, "Ollama", "OllamaModel", "pydantic_ai.models.ollama", "OllamaModel"),
        (
            22,
            "Cohere",
            "CohereEmbeddingModel",
            "pydantic_ai.embeddings.cohere",
            "CohereEmbeddingModel",
        ),
        (
            23,
            "Anthropic",
            "agent_models.AnthropicChatModel",
            "agentscope.model",
            "AnthropicChatModel",
        ),
        (
            24,
            "Google",
            "agent_models.GeminiChatModel",
            "agentscope.model",
            "GeminiChatModel",
        ),
        (
            25,
            "OpenAI",
            "agent_models.OpenAIChatModel",
            "agentscope.model",
            "OpenAIChatModel",
        ),
        (
            26,
            "OpenAI",
            "agent_models.OpenAIResponseModel",
            "agentscope.model",
            "OpenAIResponseModel",
        ),
        (
            27,
            "Alibaba DashScope",
            "agent_models.DashScopeChatModel",
            "agentscope.model",
            "DashScopeChatModel",
        ),
        (
            28,
            "DeepSeek",
            "agent_models.DeepSeekChatModel",
            "agentscope.model",
            "DeepSeekChatModel",
        ),
        (
            29,
            "Moonshot AI",
            "agent_models.MoonshotChatModel",
            "agentscope.model",
            "MoonshotChatModel",
        ),
        (
            30,
            "xAI",
            "agent_models.XAIChatModel",
            "agentscope.model",
            "XAIChatModel",
        ),
        (
            46,
            "Anthropic",
            "AnthropicProvider",
            "pydantic_ai.providers.anthropic",
            "AnthropicProvider",
        ),
        (47, "Anthropic", "AnthropicModel", "pydantic_ai.models.anthropic", "AnthropicModel"),
        (48, "Google", "GoogleProvider", "pydantic_ai.providers.google", "GoogleProvider"),
        (
            49,
            "Google",
            "GoogleCloudProvider",
            "pydantic_ai.providers.google_cloud",
            "GoogleCloudProvider",
        ),
        (50, "Google", "GoogleModel", "pydantic_ai.models.google", "GoogleModel"),
        (
            51,
            "Google",
            "GoogleEmbeddingModel",
            "pydantic_ai.embeddings.google",
            "GoogleEmbeddingModel",
        ),
        (
            52,
            "AWS Bedrock",
            "BedrockProvider",
            "pydantic_ai.providers.bedrock",
            "BedrockProvider",
        ),
        (
            53,
            "AWS Bedrock",
            "BedrockConverseModel",
            "pydantic_ai.models.bedrock",
            "BedrockConverseModel",
        ),
        (
            54,
            "AWS Bedrock",
            "BedrockEmbeddingModel",
            "pydantic_ai.embeddings.bedrock",
            "BedrockEmbeddingModel",
        ),
        (55, "xAI", "XaiProvider", "pydantic_ai.providers.xai", "XaiProvider"),
        (56, "xAI", "XaiModel", "pydantic_ai.models.xai", "XaiModel"),
        (
            57,
            "DeepSeek",
            "DeepSeekProvider",
            "pydantic_ai.providers.deepseek",
            "DeepSeekProvider",
        ),
    }
    assert {
        (item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_framework_wrappers.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
    } == {
        (13, "qwen3:14b", "Ollama"),
        (18, "llama-3.3-70b-versatile", "Groq"),
        (19, "mistral-large-latest", "Mistral"),
        (20, "command-r-plus", "Cohere"),
        (21, "qwen3:14b", "Ollama"),
        (22, "embed-v4.0", "Cohere"),
        (23, "claude-opus-4-5", "Anthropic"),
        (24, "gemini-2.5-flash", "Google"),
        (25, "gpt-4.1", "OpenAI"),
        (26, "gpt-4.1", "OpenAI"),
        (27, "qwen-plus", "Alibaba DashScope"),
        (28, "deepseek-chat", "DeepSeek"),
        (29, "kimi-k2.5", "Moonshot AI"),
        (30, "grok-3", "xAI"),
        (47, "claude-sonnet-4-5", "Anthropic"),
        (50, "gemini-2.5-flash", "Google"),
        (51, "gemini-embedding-001", "Google"),
        (53, "amazon.nova-lite-v1:0", "AWS Bedrock"),
        (54, "amazon.titan-embed-text-v2:0", "AWS Bedrock"),
        (56, "grok-4.3", "xAI"),
    }
    assert not any(
        item.kind == "provider"
        and item.evidence.path == "provider_framework_wrappers_rebound.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    local_reexport_providers = {
        (
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("module"),
            item.attributes.get("imported_symbol"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.evidence.path == "provider_local_reexports.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
    }
    assert local_reexport_providers == {
        (
            9,
            "Anthropic",
            "ProjectAnthropicProvider",
            "pydantic_ai.providers.anthropic",
            "AnthropicProvider",
        ),
        (
            10,
            "Anthropic",
            "ProjectAnthropicModel",
            "pydantic_ai.models.anthropic",
            "AnthropicModel",
        ),
        (
            11,
            "OpenAI",
            "ProjectOpenAIChatModel",
            "agentscope.model",
            "OpenAIChatModel",
        ),
    }
    assert {
        (item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_local_reexports.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
    } == {
        (10, "claude-sonnet-4-5", "Anthropic"),
        (11, "gpt-4.1", "OpenAI"),
    }
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_local_reexports.py"
        and item.evidence.line == 12
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    assert any(
        item.kind == "provider"
        and item.evidence.path == "provider_transitive_reexports.py"
        and item.evidence.line == 6
        and item.name == "OpenAI"
        and item.attributes.get("call") == "TransitiveOpenAIChatModel"
        and item.attributes.get("module") == "agentscope.model"
        and item.attributes.get("imported_symbol") == "OpenAIChatModel"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_transitive_reexports.py"
        and item.evidence.line == 6
        and item.name == "gpt-4.1-mini"
        and item.attributes.get("provider") == "OpenAI"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_transitive_reexports.py"
        and item.evidence.line == 7
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    assert any(
        item.kind == "provider"
        and item.evidence.path == "provider_star_reexports.py"
        and item.evidence.line == 3
        and item.name == "OpenAI"
        and item.attributes.get("call") == "TransitiveOpenAIChatModel"
        and item.attributes.get("module") == "agentscope.model"
        and item.attributes.get("imported_symbol") == "OpenAIChatModel"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    assert any(
        item.kind == "model"
        and item.evidence.path == "provider_star_reexports.py"
        and item.evidence.line == 3
        and item.name == "gpt-4.1-nano"
        and item.attributes.get("provider") == "OpenAI"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_star_reexports.py"
        and item.evidence.line == 4
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    factory_providers = {
        (
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("module"),
            item.attributes.get("imported_symbol"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.evidence.path == "provider_factory_calls.py"
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
    }
    assert factory_providers == {
        (
            10,
            "OpenAI",
            "make_openai_model",
            "agentscope.model",
            "OpenAIChatModel",
        ),
        (
            11,
            "Anthropic",
            "make_anthropic_model",
            "pydantic_ai.models.anthropic",
            "AnthropicModel",
        ),
        (
            12,
            "OpenAI",
            "make_static_openai_model",
            "agentscope.model",
            "OpenAIChatModel",
        ),
    }
    assert {
        (item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_factory_calls.py"
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
    } == {
        (10, "gpt-4.1", "OpenAI"),
        (11, "claude-sonnet-4-5", "Anthropic"),
        (12, "gpt-4.1-mini", "OpenAI"),
    }
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_factory_calls.py"
        and item.evidence.line in {13, 14}
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
        for item in ir.components
    )
    star_factory_providers = {
        (
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("module"),
            item.attributes.get("imported_symbol"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.evidence.path == "provider_factory_star_calls.py"
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
    }
    assert star_factory_providers == {
        (
            3,
            "OpenAI",
            "make_openai_model",
            "agentscope.model",
            "OpenAIChatModel",
        ),
        (
            4,
            "OpenAI",
            "make_static_openai_model",
            "agentscope.model",
            "OpenAIChatModel",
        ),
    }
    assert {
        (item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_factory_star_calls.py"
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
    } == {
        (3, "gpt-4.1-star", "OpenAI"),
        (4, "gpt-4.1-mini", "OpenAI"),
    }
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_factory_star_calls.py"
        and item.evidence.line in {5, 6, 7}
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
        for item in ir.components
    )
    reexport_factory_providers = {
        (
            item.evidence.path,
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("module"),
            item.attributes.get("imported_symbol"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.evidence.path
        in {
            "provider_factory_reexport_calls.py",
            "provider_factory_reexport_star_calls.py",
        }
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
    }
    assert reexport_factory_providers == {
        (
            "provider_factory_reexport_calls.py",
            8,
            "OpenAI",
            "ReexportedOpenAIFactory",
            "agentscope.model",
            "OpenAIChatModel",
        ),
        (
            "provider_factory_reexport_calls.py",
            9,
            "Anthropic",
            "ReexportedAnthropicFactory",
            "pydantic_ai.models.anthropic",
            "AnthropicModel",
        ),
        (
            "provider_factory_reexport_calls.py",
            10,
            "OpenAI",
            "ReexportedStaticOpenAIFactory",
            "agentscope.model",
            "OpenAIChatModel",
        ),
        (
            "provider_factory_reexport_star_calls.py",
            3,
            "OpenAI",
            "ReexportedOpenAIFactory",
            "agentscope.model",
            "OpenAIChatModel",
        ),
        (
            "provider_factory_reexport_star_calls.py",
            4,
            "OpenAI",
            "ReexportedStaticOpenAIFactory",
            "agentscope.model",
            "OpenAIChatModel",
        ),
    }
    assert {
        (item.evidence.path, item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path
        in {
            "provider_factory_reexport_calls.py",
            "provider_factory_reexport_star_calls.py",
        }
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
    } == {
        ("provider_factory_reexport_calls.py", 8, "gpt-4.1-reexport", "OpenAI"),
        (
            "provider_factory_reexport_calls.py",
            9,
            "claude-sonnet-4-5-reexport",
            "Anthropic",
        ),
        ("provider_factory_reexport_calls.py", 10, "gpt-4.1-mini", "OpenAI"),
        ("provider_factory_reexport_star_calls.py", 3, "gpt-4.1-star-reexport", "OpenAI"),
        ("provider_factory_reexport_star_calls.py", 4, "gpt-4.1-mini", "OpenAI"),
    }
    assert not any(
        item.kind in {"provider", "model"}
        and (
            (
                item.evidence.path == "provider_factory_reexport_calls.py"
                and item.evidence.line == 11
            )
            or (
                item.evidence.path == "provider_factory_reexport_star_calls.py"
                and item.evidence.line in {5, 6}
            )
        )
        and item.attributes.get("resolution") == "exact-provider-wrapper-factory"
        for item in ir.components
    )
    framework_agent_aliases = {
        (
            item.evidence.path,
            item.evidence.line,
            item.name,
            item.attributes.get("constructor"),
            item.attributes.get("constructor_module"),
            item.attributes.get("imported_symbol"),
            item.attributes.get("constructor_resolution"),
        )
        for item in ir.components
        if item.kind == "agent"
        and item.evidence.path
        in {
            "framework_agent_alias_calls.py",
            "framework_agent_module_calls.py",
            "framework_agent_reexport_calls.py",
            "framework_agent_star_import_calls.py",
            "framework_agent_star_import_google.py",
            "framework_agent_star_import_openai.py",
        }
    }
    assert framework_agent_aliases == {
        (
            "framework_agent_alias_calls.py",
            6,
            "react-facade",
            "ReActAgent",
            "agentscope.agent",
            "ReActAgent",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_alias_calls.py",
            7,
            "camel-facade",
            "CamelChatAgent",
            "camel.agents",
            "ChatAgent",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_alias_calls.py",
            8,
            "marvin-facade",
            "MarvinAgent",
            "marvin.agents",
            "Agent",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_alias_calls.py",
            13,
            "openai-facade",
            "OpenAIAgent",
            "agents",
            "Agent",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_alias_calls.py",
            18,
            "google-adk-facade",
            "GoogleADKAgent",
            "google.adk.agents",
            "Agent",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_alias_calls.py",
            23,
            "semantic-kernel-facade",
            "SemanticKernelAgent",
            "semantic_kernel.agents",
            "ChatCompletionAgent",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_alias_calls.py",
            30,
            "qwen-facade",
            "QwenAssistant",
            "qwen_agent.agents",
            "Assistant",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_alias_calls.py",
            31,
            "lagent-facade",
            "LagentAgent",
            "lagent.agents",
            "AgentForInternLM",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_alias_calls.py",
            32,
            "metagpt-facade",
            "MetaGPTRole",
            "metagpt.roles",
            "Role",
            "exact-framework-agent-import",
        ),
        (
            "framework_agent_module_calls.py",
            12,
            "module-react",
            "agentscope_agents.ReActAgent",
            "agentscope.agent",
            "ReActAgent",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_module_calls.py",
            13,
            "module-openai",
            "openai_agents.Agent",
            "agents",
            "Agent",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_module_calls.py",
            14,
            "module-google-adk",
            "adk_agents.Agent",
            "google.adk.agents",
            "Agent",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_module_calls.py",
            15,
            "module-semantic-kernel",
            "sk_agents.ChatCompletionAgent",
            "semantic_kernel.agents",
            "ChatCompletionAgent",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_module_calls.py",
            16,
            "module-camel",
            "camel_agents.ChatAgent",
            "camel.agents",
            "ChatAgent",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_module_calls.py",
            17,
            "module-marvin",
            "marvin_agents.Agent",
            "marvin.agents",
            "Agent",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_module_calls.py",
            18,
            "module-qwen",
            "qwen_agent.agents.Assistant",
            "qwen_agent.agents",
            "Assistant",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_module_calls.py",
            19,
            "module-lagent",
            "lagent.agents.AgentForInternLM",
            "lagent.agents",
            "AgentForInternLM",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_module_calls.py",
            20,
            "module-metagpt",
            "metagpt_roles.Role",
            "metagpt.roles",
            "Role",
            "exact-framework-agent-module-import",
        ),
        (
            "framework_agent_star_import_calls.py",
            10,
            "star-react",
            "ReActAgent",
            "agentscope.agent",
            "ReActAgent",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_star_import_calls.py",
            11,
            "star-semantic-kernel",
            "ChatCompletionAgent",
            "semantic_kernel.agents",
            "ChatCompletionAgent",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_star_import_calls.py",
            12,
            "star-camel",
            "ChatAgent",
            "camel.agents",
            "ChatAgent",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_star_import_calls.py",
            13,
            "star-marvin",
            "Agent",
            "marvin.agents",
            "Agent",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_star_import_calls.py",
            14,
            "star-qwen",
            "Assistant",
            "qwen_agent.agents",
            "Assistant",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_star_import_calls.py",
            15,
            "star-lagent",
            "AgentForInternLM",
            "lagent.agents",
            "AgentForInternLM",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_star_import_calls.py",
            16,
            "star-metagpt",
            "Role",
            "metagpt.roles",
            "Role",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_star_import_openai.py",
            4,
            "star-openai",
            "Agent",
            "agents",
            "Agent",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_star_import_google.py",
            4,
            "star-google-adk",
            "Agent",
            "google.adk.agents",
            "Agent",
            "exact-framework-agent-star-import",
        ),
        (
            "framework_agent_reexport_calls.py",
            6,
            "reexport-react",
            "ImportedReActAgent",
            "agentscope.agent",
            "ReActAgent",
            "exact-framework-agent-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            7,
            "reexport-camel",
            "ProjectChatAgent",
            "camel.agents",
            "ChatAgent",
            "exact-framework-agent-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            8,
            "star-marvin",
            "ProjectMarvinAgent",
            "marvin.agents",
            "Agent",
            "exact-framework-agent-star-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            14,
            "reexport-openai",
            "ProjectOpenAIAgent",
            "agents",
            "Agent",
            "exact-framework-agent-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            15,
            "star-openai",
            "ProjectStarOpenAIAgent",
            "agents",
            "Agent",
            "exact-framework-agent-star-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            20,
            "reexport-google-adk",
            "ProjectGoogleADKAgent",
            "google.adk.agents",
            "Agent",
            "exact-framework-agent-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            21,
            "star-google-adk",
            "ProjectStarGoogleADKAgent",
            "google.adk.agents",
            "Agent",
            "exact-framework-agent-star-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            26,
            "reexport-semantic-kernel",
            "ProjectSemanticKernelAgent",
            "semantic_kernel.agents",
            "ChatCompletionAgent",
            "exact-framework-agent-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            27,
            "star-semantic-kernel",
            "ProjectStarSemanticKernelAgent",
            "semantic_kernel.agents",
            "ChatCompletionAgent",
            "exact-framework-agent-star-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            34,
            "reexport-qwen",
            "ProjectQwenAssistant",
            "qwen_agent.agents",
            "Assistant",
            "exact-framework-agent-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            35,
            "reexport-lagent",
            "ProjectLagentAgent",
            "lagent.agents",
            "AgentForInternLM",
            "exact-framework-agent-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            36,
            "reexport-metagpt",
            "ProjectMetaGPTRole",
            "metagpt.roles",
            "Role",
            "exact-framework-agent-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            37,
            "star-qwen",
            "ProjectStarQwenAssistant",
            "qwen_agent.agents",
            "Assistant",
            "exact-framework-agent-star-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            38,
            "star-lagent",
            "ProjectStarLagentAgent",
            "lagent.agents",
            "AgentForInternLM",
            "exact-framework-agent-star-reexport",
        ),
        (
            "framework_agent_reexport_calls.py",
            39,
            "star-metagpt",
            "ProjectStarMetaGPTRole",
            "metagpt.roles",
            "Role",
            "exact-framework-agent-star-reexport",
        ),
    }
    assert not any(
        item.kind == "agent"
        and (
            item.evidence.path == "framework_agent_alias_rebound.py"
            or (
                item.evidence.path == "framework_agent_reexport_calls.py"
                and item.evidence.line == 9
            )
        )
        for item in ir.components
    )
    assert not any(
        item.kind == "agent"
        and item.evidence.path
        in {
            "framework_agent_module_rebound.py",
            "framework_agent_module_rebound_camel_marvin.py",
        }
        and item.attributes.get("constructor_resolution") == "exact-framework-agent-module-import"
        for item in ir.components
    )
    assert not any(
        item.kind == "agent"
        and item.evidence.path
        in {
            "framework_agent_star_import_near.py",
            "framework_agent_star_import_rebound.py",
            "framework_agent_star_import_rebound_camel_marvin.py",
        }
        and item.attributes.get("constructor_resolution") == "exact-framework-agent-star-import"
        for item in ir.components
    )
    local_factory_agents = {
        (
            item.evidence.line,
            item.name,
            item.attributes.get("constructor"),
            item.attributes.get("constructor_module"),
            item.attributes.get("imported_symbol"),
            item.attributes.get("constructor_resolution"),
        )
        for item in ir.components
        if item.kind == "agent" and item.evidence.path == "framework_agent_local_factory_calls.py"
    }
    assert local_factory_agents == {
        (
            9,
            "factory-react",
            "ReActAgent",
            "agentscope.agent",
            "ReActAgent",
            "exact-framework-agent-import",
        ),
        (
            12,
            "factory-openai",
            "OpenAIAgent",
            "agents",
            "Agent",
            "exact-framework-agent-import",
        ),
        (
            15,
            "factory-google-adk",
            "adk_agents.Agent",
            "google.adk.agents",
            "Agent",
            "exact-framework-agent-module-import",
        ),
        (
            20,
            "Crew",
            "Crew",
            "crewai",
            "Crew",
            "exact-framework-agent-import",
        ),
    }
    local_factory_edges = {
        (edge.target_name, edge.target_id, edge.attributes.get("target_identity"))
        for edge in ir.relationships
        if edge.evidence.path == "framework_agent_local_factory_calls.py"
        and edge.evidence.line == 20
        and edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_kind == "agent"
    }
    assert local_factory_edges == {
        (
            "react",
            "py:framework_agent_local_factory_calls.py#agent:factory-react@9",
            "same-block-function-factory-return",
        ),
        (
            "worker",
            "py:framework_agent_local_factory_calls.py#agent:factory-openai@12",
            "same-block-function-factory-return",
        ),
        (
            "google",
            "py:framework_agent_local_factory_calls.py#agent:factory-google-adk@15",
            "same-block-function-factory-return",
        ),
    }
    assert {
        (edge.evidence.line, edge.target_id, tuple(sorted(edge.attributes.items())))
        for edge in ir.relationships
        if edge.evidence.path == "framework_agent_local_factory_negative.py"
        and edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_kind == "agent"
    } == {
        (12, None, ()),
        (21, None, ()),
        (30, None, ()),
    }


def test_python_dify_shell_layer_requires_default_off_runtime_composition() -> None:
    ir = scan_repository(ROOT / "cases/python_dify_agent_shell_layer")

    assert any(
        item.kind == "framework"
        and item.name == "Dify Agent"
        and item.evidence.path == "app.py"
        and item.attributes["module"] == "dify_agent.layers.runtime"
        for item in ir.components
    )
    assert not any(
        item.kind == "framework"
        and item.name == "Dify Agent"
        and item.evidence.path == "near_name.py"
        for item in ir.components
    )
    composition = [
        item
        for item in ir.components
        if item.attributes.get("analysis") == "python-dify-agent-shell-layer"
    ]
    assert [
        (item.kind, item.name, item.evidence.path, item.evidence.line) for item in composition
    ] == [
        ("control", "sandbox-runtime", "app.py", 25),
        ("capability", "shell-execution", "app.py", 33),
        ("tool", "dify.shell", "app.py", 33),
    ]
    shell = next(item for item in composition if item.kind == "tool")
    assert shell.attributes == {
        "scope": "production",
        "frontend": "python",
        "framework": "Dify Agent",
        "analysis": "python-dify-agent-shell-layer",
        "composition_method": "build",
        "conditional": True,
        "enabled_default": False,
        "enable_sources": [
            "run_input.include_shell",
            "run_input.config_layer_config",
        ],
        "constructor": "DifyShellLayerConfig",
        "registration": "conditional-run-layer",
    }
    assert [
        (
            edge.source_kind,
            edge.source_name,
            edge.relation,
            edge.target_kind,
            edge.target_name,
            edge.evidence.line,
        )
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "python-dify-agent-shell-layer"
    ] == [
        (
            "capability",
            "shell-execution",
            "governed-by",
            "control",
            "sandbox-runtime",
            33,
        ),
        ("tool", "dify.shell", "uses", "capability", "shell-execution", 33),
    ]
    assert not ir.findings


def test_python_autogen_provider_wrappers_require_exact_unrebound_imports() -> None:
    ir = scan_repository(ROOT / "cases/python_autogen_provider_wrappers")

    assert any(
        item.kind == "framework"
        and item.name == "AutoGen"
        and item.evidence.path == "positive.py"
        and item.attributes["module"] == "autogen_agentchat.agents"
        for item in ir.components
    )
    assert not any(
        item.kind == "framework" and item.name == "AutoGen" and item.evidence.path == "near_name.py"
        for item in ir.components
    )
    provider_calls = {
        (
            item.name,
            item.evidence.path,
            item.evidence.line,
            item.attributes.get("module"),
            item.attributes.get("call_kind"),
        )
        for item in ir.components
        if item.kind == "provider"
    }
    assert provider_calls == {
        (
            "OpenAI",
            "positive.py",
            8,
            "autogen_ext.models.openai",
            "wrapper-constructor",
        ),
        (
            "Azure OpenAI",
            "positive.py",
            9,
            "autogen_ext.models.openai",
            "wrapper-constructor",
        ),
        (
            "Anthropic",
            "positive.py",
            13,
            "autogen_ext.models.anthropic",
            "wrapper-constructor",
        ),
    }
    assert {
        (item.name, item.attributes.get("provider"))
        for item in ir.components
        if item.kind == "model"
    } == {
        ("gpt-4o-mini", "OpenAI"),
        ("gpt-4o", "Azure OpenAI"),
        ("claude-3-5-sonnet-latest", "Anthropic"),
    }
    assert any(
        item.kind == "agent"
        and item.name == "AssistantAgent"
        and item.evidence.path == "positive.py"
        for item in ir.components
    )
    assert not ir.findings


def test_agno_provider_wrappers_require_exact_unrebound_imports() -> None:
    ir = scan_repository(ROOT / "cases/framework_provider_taxonomy")

    assert {
        (
            item.evidence.line,
            item.name,
            item.attributes.get("call"),
            item.attributes.get("module"),
            item.attributes.get("imported_symbol"),
        )
        for item in ir.components
        if item.kind == "provider"
        and item.evidence.path == "provider_agno_wrappers.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
    } == {
        (10, "OpenAI", "OpenAIChat", "agno.models.openai", "OpenAIChat"),
        (11, "OpenAI", "OpenAIResponses", "agno.models.openai", "OpenAIResponses"),
        (12, "OpenAI", "DirectOpenAIChat", "agno.models.openai.chat", "OpenAIChat"),
        (13, "Google", "Gemini", "agno.models.google", "Gemini"),
        (14, "Google", "DirectGemini", "agno.models.google.gemini", "Gemini"),
        (15, "Anthropic", "Claude", "agno.models.anthropic", "Claude"),
        (16, "Azure OpenAI", "AzureOpenAI", "agno.models.azure", "AzureOpenAI"),
        (17, "Groq", "Groq", "agno.models.groq", "Groq"),
    }
    assert {
        (item.evidence.line, item.name, item.attributes["provider"])
        for item in ir.components
        if item.kind == "model"
        and item.evidence.path == "provider_agno_wrappers.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
    } == {
        (10, "gpt-5-mini", "OpenAI"),
        (11, "gpt-5-mini", "OpenAI"),
        (12, "gpt-5-mini", "OpenAI"),
        (13, "gemini-2.5-flash", "Google"),
        (14, "gemini-2.5-flash", "Google"),
        (15, "claude-sonnet-4-5", "Anthropic"),
        (16, "gpt-5-mini", "Azure OpenAI"),
        (17, "openai/gpt-oss-120b", "Groq"),
    }
    assert not any(
        item.kind == "provider"
        and item.evidence.path == "provider_agno_wrappers_rebound.py"
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )
    assert not any(
        item.kind in {"provider", "model"}
        and item.evidence.path == "provider_agno_wrappers.py"
        and item.evidence.line in {18, 19}
        and item.attributes.get("resolution") == "exact-provider-sdk-import"
        for item in ir.components
    )


def test_scan_repository_suppresses_third_party_python_syntax_warnings(
    tmp_path: Path, capsys
) -> None:
    (tmp_path / "agent.py").write_text('PATTERN = "\\F"\n', encoding="utf-8")

    ir = scan_repository(tmp_path)

    assert ir.files_scanned == 1
    assert capsys.readouterr().err == ""


def test_python_agent_inventory_and_dynamic_shell_finding() -> None:
    ir = scan_repository(ROOT / "cases/python_dangerous")

    assert {(item.kind, item.name) for item in ir.components} >= {
        ("framework", "OpenAI Agents SDK"),
        ("provider", "OpenAI"),
        ("agent", "operator"),
        ("model", "gpt-5"),
        ("tool", "run_task"),
        ("capability", "shell-execution"),
    }
    assert [finding.rule_id for finding in ir.findings] == ["AV-EXEC001"]
    assert ir.findings[0].confidence == "high"
    assert ir.findings[0].ir_path == (
        "agent:operator",
        "tool:run_task",
        "capability:shell-execution",
    )
    assert ir.findings[0].analysis["approval_coverage"] == "unresolved"
    assert {
        (item.source_kind, item.source_name, item.relation, item.target_kind, item.target_name)
        for item in ir.relationships
    } >= {
        ("agent", "operator", "uses", "tool", "run_task"),
        ("tool", "run_task", "uses", "capability", "shell-execution"),
    }


def test_fixed_argv_is_inventory_not_finding() -> None:
    ir = scan_repository(ROOT / "examples/safe_agent")

    assert any(item.name == "shell-execution" for item in ir.components)
    assert not ir.findings


def test_approval_control_governs_privileged_tool() -> None:
    ir = scan_repository(ROOT / "cases/python_approved")

    relationships = {
        (item.source_kind, item.source_name, item.relation, item.target_kind, item.target_name)
        for item in ir.relationships
    }
    assert ("agent", "deployer", "uses", "tool", "deploy") in relationships
    assert ("tool", "deploy", "uses", "capability", "shell-execution") in relationships
    assert ("tool", "deploy", "governed-by", "control", "human-approval") in relationships
    assert ir.findings[0].analysis["approval_coverage"] == "present"
    assert ir.findings[0].analysis["governing_controls"] == ["human-approval"]


def test_typescript_literal_approval_governs_only_its_tool() -> None:
    ir = scan_repository(ROOT / "cases/typescript_approved")

    tools = {
        component.name: component.attributes
        for component in ir.components
        if component.kind == "tool"
    }
    assert tools["approvedCommand"] == {
        "constructor": "tool",
        "needs_approval": True,
        "approval_policy": "enabled",
        "approval_handler": "none",
        "approval_decision": "always",
    }
    assert tools["conditionalCommand"] == {
        "constructor": "tool",
        "needs_approval": False,
        "approval_policy": "callback-controlled",
        "approval_handler": "needsApproval-callback",
        "approval_decision": "dynamic-callback",
        "approval_predicate": "field-prefix-literal",
        "approval_predicate_field": "command",
        "approval_predicate_values": ["git status"],
    }
    assert tools["disabledApproval"] == {
        "constructor": "tool",
        "needs_approval": False,
    }

    shell_findings = [finding for finding in ir.findings if finding.rule_id == "AV-EXEC001"]
    coverage = {
        finding.analysis["tool"]: finding.analysis["approval_coverage"]
        for finding in shell_findings
    }
    assert coverage == {
        "approvedCommand": "present",
        "conditionalCommand": "unresolved",
        "disabledApproval": "unresolved",
    }
    assert all(finding.ir_path[0] == "agent:operator" for finding in shell_findings)
    assert {
        (item.source_name, item.relation, item.target_name)
        for item in ir.relationships
        if item.source_kind == "tool" and item.target_kind == "control"
    } == {("approvedCommand", "governed-by", "human-approval")}


def test_python_enabled_auto_approval_is_review_candidate() -> None:
    ir = scan_repository(ROOT / "cases/python_auto_approval")

    assert [finding.rule_id for finding in ir.findings] == ["AV-APPROVAL001"]
    assert ir.findings[0].result_kind == "review"


def test_approval_callback_bypass_is_resolved_to_reachable_privileged_tools() -> None:
    ir = scan_repository(ROOT / "cases/approval_callback_bypass")

    findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL003"]
    assert [
        (finding.evidence.path, finding.evidence.line, finding.analysis["tool"])
        for finding in findings
    ] == [
        ("approval.py", 33, "ShellTool@33"),
        ("approval.ts", 27, "shellTool@27"),
        ("approval.ts", 32, "applyPatchTool@32"),
    ]
    assert {
        tuple(finding.analysis["approval_bypass_environment_names"]) for finding in findings
    } == {("SHELL_AUTO_APPROVE",), ("APPLY_PATCH_AUTO_APPROVE",)}
    assert all(finding.result_kind == "finding" for finding in findings)
    assert all(finding.analysis["direct_agents"] == ["operator"] for finding in findings)

    bypass_tools = {
        component.name: component.attributes["approval_bypass_environment_names"]
        for component in ir.components
        if component.kind == "tool"
        and component.attributes.get("approval_bypass_environment_names")
    }
    assert bypass_tools == {
        "ShellTool@33": ["SHELL_AUTO_APPROVE"],
        "ShellTool@43": ["SHELL_AUTO_APPROVE"],
        "shellTool@27": ["SHELL_AUTO_APPROVE"],
        "applyPatchTool@32": ["APPLY_PATCH_AUTO_APPROVE"],
        "shellTool@37": ["SHELL_AUTO_APPROVE"],
    }
    configured_edges = [
        edge
        for edge in ir.relationships
        if edge.relation == "configured-by"
        and edge.target_kind == "control-setting"
        and edge.target_name == "auto-approval"
    ]
    assert len(configured_edges) == 5
    assert {edge.attributes["resolution"] for edge in configured_edges} == {
        "same-file-transitive-callback"
    }


def test_builtin_tool_constructor_approval_is_instance_scoped() -> None:
    ir = scan_repository(ROOT / "cases/builtin_tool_approval")

    tools = {
        component.name: component.attributes["approval_policy"]
        for component in ir.components
        if component.kind == "tool"
    }
    assert tools == {
        "ShellTool@11": "enabled",
        "ApplyPatchTool@12": "disabled-explicit",
        "CustomTool@13": "unresolved",
        "ShellTool@16": "unresolved-handler",
        "ShellTool@17": "disabled-explicit",
    }
    controls = {
        edge.source_name
        for edge in ir.relationships
        if edge.source_kind == "tool"
        and edge.relation == "governed-by"
        and edge.target_name == "human-approval"
    }
    assert controls == {"ShellTool@11"}
    agent_tools = {
        edge.target_name
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.source_name == "operator"
    }
    assert agent_tools == set(tools)
    shell = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "shell-execution"
        and component.evidence.line == 11
    )
    path, analysis = component_context(ir, shell)
    assert path == ("agent:operator", "tool:ShellTool@11", "capability:shell-execution")
    assert analysis["approval_coverage"] == "present"

    handled_shell = next(
        component
        for component in ir.components
        if component.kind == "tool" and component.name == "ShellTool@16"
    )
    assert handled_shell.attributes["approval_handler"] == "configured"
    assert [finding.rule_id for finding in ir.findings] == ["AV-APPROVAL002"]
    assert ir.findings[0].evidence.line == 17
    assert ir.findings[0].result_kind == "review"
    assert ir.findings[0].analysis["approval_coverage"] == "unresolved"


def test_builtin_tool_names_require_openai_agents_import(tmp_path: Path) -> None:
    (tmp_path / "unrelated.py").write_text(
        "ShellTool(executor=object(), needs_approval=True)\n", encoding="utf-8"
    )

    ir = scan_repository(tmp_path)

    assert not any(
        component.kind == "tool" and component.name.startswith("ShellTool@")
        for component in ir.components
    )
    assert not any(
        edge.target_kind == "control" and edge.target_name == "human-approval"
        for edge in ir.relationships
    )


def test_local_shell_tool_requires_exact_import_and_reports_missing_sdk_approval() -> None:
    ir = scan_repository(ROOT / "cases/python_local_shell_tool")
    tools = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "tool" and component.name.startswith("LocalShellTool@")
    }
    assert set(tools) == {9, 12, 17}
    assert {
        (
            tool.attributes["approval_policy"],
            tool.attributes["approval_source"],
            tool.attributes["execution_environment"],
        )
        for tool in tools.values()
    } == {("unavailable", "sdk-no-approval-parameter", "local")}
    capabilities = [
        component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "shell-execution"
        and component.attributes.get("api") == "LocalShellTool"
    ]
    assert {component.evidence.line for component in capabilities} == {9, 12, 17}
    assert all(component.attributes.get("builtin_tool") is True for component in capabilities)
    edges = {
        edge.source_name: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert set(edges) == {
        "assigned-shell",
        "aliased-shell",
        "inline-shell",
        "near-shell",
        "rebound-shell",
    }
    assert edges["assigned-shell"].target_id == "py:positive.py#tool:assigned"
    assert edges["aliased-shell"].target_id == "py:positive.py#tool:aliased"
    assert edges["inline-shell"].target_id == ("py:positive.py#tool:LocalShellTool@17")
    assert edges["near-shell"].target_id is None
    assert edges["rebound-shell"].target_id is None
    assert {
        finding.evidence.line for finding in ir.findings if finding.rule_id == "AV-APPROVAL002"
    } == {9, 12, 17}
    assert all(
        "exposes no per-action decision hook" in finding.message
        for finding in ir.findings
        if finding.rule_id == "AV-APPROVAL002"
    )
    assert all(
        "inside the executor" in finding.remediation and "needs_approval" not in finding.remediation
        for finding in ir.findings
        if finding.rule_id == "AV-APPROVAL002"
    )


def test_code_interpreter_tool_requires_exact_import_and_records_hosted_sandbox() -> None:
    ir = scan_repository(ROOT / "cases/python_code_interpreter_tool")
    tools = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "tool" and component.name.startswith("CodeInterpreterTool@")
    }
    assert set(tools) == {5, 10, 18}
    assert {
        (
            tool.attributes["approval_policy"],
            tool.attributes["approval_source"],
            tool.attributes["execution_environment"],
            tool.attributes["sandbox_policy"],
        )
        for tool in tools.values()
    } == {
        (
            "unavailable",
            "sdk-no-approval-parameter",
            "hosted-sandbox",
            "sdk-hosted",
        )
    }
    assert tools[5].attributes["container_policy"] == "auto"
    assert tools[10].attributes["container_policy"] == "existing-reference"
    assert tools[18].attributes["container_policy"] == "auto"
    capabilities = [
        component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "code-execution"
        and component.attributes.get("api") == "CodeInterpreterTool"
    ]
    assert {component.evidence.line for component in capabilities} == {5, 10, 18}
    assert all(
        component.attributes.get("sandbox_policy") == "sdk-hosted"
        and component.attributes.get("builtin_tool") is True
        for component in capabilities
    )
    edges = {
        edge.source_name: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert set(edges) == {
        "assigned-code",
        "aliased-code",
        "inline-code",
        "near-code",
        "rebound-code",
    }
    assert edges["assigned-code"].target_id == "py:positive.py#tool:assigned"
    assert edges["aliased-code"].target_id == "py:positive.py#tool:aliased"
    assert edges["inline-code"].target_id == ("py:positive.py#tool:CodeInterpreterTool@18")
    assert edges["near-code"].target_id is None
    assert edges["rebound-code"].target_id is None
    assert not any(finding.rule_id == "AV-EXEC002" for finding in ir.findings)


def test_openai_hosted_tools_require_exact_import_and_preserve_scope() -> None:
    ir = scan_repository(ROOT / "cases/python_openai_hosted_tools")
    tools = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "tool"
        and component.attributes.get("hosting_policy") == "sdk-provider-hosted"
    }
    assert set(tools) == {5, 8, 11, 14, 19}
    assert all(
        tool.attributes.get("approval_policy") == "unavailable"
        and tool.attributes.get("approval_source") == "sdk-no-approval-parameter"
        and tool.attributes.get("execution_environment") == "hosted"
        for tool in tools.values()
    )
    assert tools[5].attributes["external_web_access"] == "disabled-explicit"
    assert tools[8].attributes["external_web_access"] == "sdk-default"
    assert tools[11].attributes["vector_store_scope"] == "literal-ids"
    assert tools[14].attributes["vector_store_scope"] == "unresolved"
    capabilities = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "capability"
        and component.attributes.get("hosting_policy") == "sdk-provider-hosted"
    }
    assert {line: component.name for line, component in capabilities.items()} == {
        5: "network",
        8: "network",
        11: "data-retrieval",
        14: "data-retrieval",
        19: "media-generation",
    }
    assert capabilities[5].attributes["dynamic_origin"] is False
    assert capabilities[5].attributes["network_scope"] == ("provider-hosted-web-search")
    assert capabilities[11].attributes["data_scope"] == "hosted-vector-store"
    assert capabilities[19].attributes["generation_scope"] == ("provider-hosted-image")
    edges = {
        edge.source_name: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert edges["web"].target_id == "py:positive.py#tool:web"
    assert edges["aliased-web"].target_id == "py:positive.py#tool:aliased_web"
    assert edges["files"].target_id == "py:positive.py#tool:files"
    assert edges["dynamic-files"].target_id == "py:positive.py#tool:dynamic_files"
    assert edges["images"].target_id == ("py:positive.py#tool:ImageGenerationTool@19")
    assert all(
        edges[name].target_id is None
        for name in (
            "near-web",
            "near-files",
            "near-image",
            "rebound-web",
            "rebound-files",
            "rebound-image",
        )
    )
    assert not any(finding.rule_id == "AV-NET001" for finding in ir.findings)


def test_python_openai_hosted_mcp_approval_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/python_openai_hosted_mcp_approval")

    tools = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "tool" and component.attributes.get("constructor") == "HostedMCPTool"
    }
    assert set(tools) == {
        9,
        10,
        13,
        17,
        18,
        21,
        22,
        32,
        40,
        49,
        60,
        68,
        76,
        84,
        92,
        93,
        94,
        95,
        103,
        104,
    }
    assert tools[32].attributes == {
        "binding": "literal-tools-list-inline-constructor",
        "constructor": "HostedMCPTool",
        "registration": "agent-tool-reference",
        "registration_line": 29,
        "resolution": "literal-inline-constructor",
        "scope": "production",
        "mcp_approval_policy": "disabled-explicit",
        "mcp_approval_requirement": "never",
        "mcp_approval_handler": "none",
    }
    assert tools[40].attributes == {
        "binding": "literal-tools-list-inline-constructor",
        "constructor": "HostedMCPTool",
        "registration": "agent-tool-reference",
        "registration_line": 29,
        "resolution": "literal-inline-constructor",
        "scope": "production",
        "mcp_approval_binding": "require_approval",
        "mcp_approval_resolution": "same-block-literal-string",
        "mcp_approval_policy": "always-required",
        "mcp_approval_requirement": "always",
        "mcp_approval_handler": "configured",
        "mcp_approval_handler_policy": "callback-controlled",
        "mcp_approval_handler_resolution": "same-file-direct-approval-dict-return",
        "mcp_approval_handler_decision": "conditional-approve",
        "mcp_approval_handler_predicate": "request-field-not-equals-literal",
        "mcp_approval_handler_predicate_field": "data.name",
        "mcp_approval_handler_predicate_values": ["delete_page"],
    }
    assert tools[49].attributes == {
        "binding": "literal-tools-list-inline-constructor",
        "constructor": "HostedMCPTool",
        "registration": "agent-tool-reference",
        "registration_line": 29,
        "resolution": "literal-inline-constructor",
        "scope": "production",
        "mcp_approval_never_tool_names": ["read_page"],
        "mcp_approval_never_read_only": True,
        "mcp_approval_always_tool_names": ["write_page"],
        "mcp_approval_policy": "selective",
        "mcp_approval_handler": "manual-run-loop",
    }
    assert tools[60].attributes == {
        "binding": "literal-tools-list-inline-constructor",
        "constructor": "HostedMCPTool",
        "registration": "agent-tool-reference",
        "registration_line": 29,
        "resolution": "literal-inline-constructor",
        "scope": "production",
        "mcp_approval_binding": "dynamic_policy",
        "mcp_approval_policy": "dynamic",
        "mcp_approval_handler": "manual-run-loop",
    }
    assert tools[68].attributes["mcp_approval_binding"] == "IMPORTED_ALWAYS"
    assert tools[68].attributes["mcp_approval_resolution"] == (
        "imported-local-literal:repository-module-single-path"
    )
    assert tools[68].attributes["mcp_approval_policy"] == "always-required"
    assert tools[68].attributes["mcp_approval_requirement"] == "always"
    assert tools[68].attributes["mcp_approval_handler"] == "manual-run-loop"

    assert tools[76].attributes["mcp_approval_binding"] == "IMPORTED_SELECTIVE"
    assert tools[76].attributes["mcp_approval_resolution"] == (
        "imported-local-literal:repository-module-single-path"
    )
    assert tools[76].attributes["mcp_approval_policy"] == "selective"
    assert tools[76].attributes["mcp_approval_never_tool_names"] == ["read_hosted"]
    assert tools[76].attributes["mcp_approval_always_tool_names"] == ["write_hosted"]

    assert tools[84].attributes["mcp_approval_binding"] == "MUTATED_POLICY"
    assert tools[84].attributes["mcp_approval_policy"] == "dynamic"

    assert tools[92].attributes["mcp_tool_config_binding"] == "IMPORTED_TOOL_CONFIG"
    assert tools[92].attributes["mcp_tool_config_resolution"] == (
        "imported-local-tool-config:repository-module-single-path"
    )
    assert tools[92].attributes["mcp_approval_policy"] == "selective"
    assert tools[92].attributes["mcp_approval_never_tool_names"] == ["read_config"]
    assert tools[92].attributes["mcp_approval_never_read_only"] is True
    assert tools[92].attributes["mcp_approval_always_tool_names"] == ["write_config"]

    assert tools[93].attributes["mcp_tool_config_binding"] == (
        "IMPORTED_ALIASED_TOOL_CONFIG"
    )
    assert tools[93].attributes["mcp_tool_config_resolution"] == (
        "imported-local-tool-config:repository-module-single-path"
    )
    assert tools[93].attributes["mcp_approval_policy"] == "always-required"
    assert tools[93].attributes["mcp_approval_requirement"] == "always"

    assert tools[94].attributes["mcp_tool_config_binding"] == "MUTATED_TOOL_CONFIG"
    assert "mcp_tool_config_resolution" not in tools[94].attributes
    assert tools[94].attributes["mcp_approval_policy"] == "dynamic"

    assert tools[95].attributes["mcp_approval_binding"] == "REEXPORTED_ALWAYS"
    assert tools[95].attributes["mcp_approval_resolution"] == (
        "imported-local-reexport-literal:repository-module-single-path"
    )
    assert tools[95].attributes["mcp_approval_policy"] == "always-required"
    assert tools[95].attributes["mcp_approval_requirement"] == "always"

    assert tools[103].attributes["mcp_tool_config_binding"] == "REEXPORTED_TOOL_CONFIG"
    assert tools[103].attributes["mcp_tool_config_resolution"] == (
        "imported-local-reexport-tool-config:repository-module-single-path"
    )
    assert tools[103].attributes["mcp_approval_policy"] == "selective"
    assert tools[103].attributes["mcp_approval_never_tool_names"] == ["read_config"]
    assert tools[103].attributes["mcp_approval_never_read_only"] is True
    assert tools[103].attributes["mcp_approval_always_tool_names"] == ["write_config"]

    assert tools[104].attributes["mcp_tool_config_binding"] == (
        "REEXPORTED_MUTATED_TOOL_CONFIG"
    )
    assert "mcp_tool_config_resolution" not in tools[104].attributes
    assert tools[104].attributes["mcp_approval_policy"] == "dynamic"

    assert tools[13].attributes["mcp_approval_binding"] == "STAR_REEXPORTED_ALWAYS"
    assert tools[13].attributes["mcp_approval_resolution"] == (
        "imported-local-star-reexport-literal:repository-module-single-path"
    )
    assert tools[13].attributes["mcp_approval_policy"] == "always-required"
    assert tools[13].attributes["mcp_approval_requirement"] == "always"

    assert tools[21].attributes["mcp_tool_config_binding"] == (
        "STAR_REEXPORTED_TOOL_CONFIG"
    )
    assert tools[21].attributes["mcp_tool_config_resolution"] == (
        "imported-local-star-reexport-tool-config:repository-module-single-path"
    )
    assert tools[21].attributes["mcp_approval_policy"] == "selective"
    assert tools[21].attributes["mcp_approval_never_tool_names"] == ["read_config"]
    assert tools[21].attributes["mcp_approval_never_read_only"] is True
    assert tools[21].attributes["mcp_approval_always_tool_names"] == ["write_config"]

    assert tools[22].attributes["mcp_tool_config_binding"] == (
        "STAR_REEXPORTED_MUTATED_TOOL_CONFIG"
    )
    assert "mcp_tool_config_resolution" not in tools[22].attributes
    assert tools[22].attributes["mcp_approval_policy"] == "dynamic"

    assert tools[9].attributes["mcp_approval_binding"] == "IMPORTED_ALWAYS"
    assert tools[9].attributes["mcp_approval_resolution"] == (
        "imported-local-star-import-literal:repository-module-single-path"
    )
    assert tools[9].attributes["mcp_approval_policy"] == "always-required"
    assert tools[9].attributes["mcp_approval_requirement"] == "always"

    assert tools[17].attributes["mcp_tool_config_binding"] == "IMPORTED_TOOL_CONFIG"
    assert tools[17].attributes["mcp_tool_config_resolution"] == (
        "imported-local-star-import-tool-config:repository-module-single-path"
    )
    assert tools[17].attributes["mcp_approval_policy"] == "selective"
    assert tools[17].attributes["mcp_approval_never_tool_names"] == ["read_config"]
    assert tools[17].attributes["mcp_approval_never_read_only"] is True
    assert tools[17].attributes["mcp_approval_always_tool_names"] == ["write_config"]

    assert tools[18].attributes["mcp_tool_config_binding"] == "MUTATED_TOOL_CONFIG"
    assert "mcp_tool_config_resolution" not in tools[18].attributes
    assert tools[18].attributes["mcp_approval_policy"] == "dynamic"

    assert tools[10].attributes["mcp_approval_binding"] == "IMPORTED_ALWAYS"
    assert tools[10].attributes["mcp_approval_resolution"] == (
        "imported-local-star-import-literal:repository-module-single-path"
    )
    assert tools[10].attributes["mcp_approval_policy"] == "always-required"
    assert tools[10].attributes["mcp_approval_requirement"] == "always"

    assert not any(
        component.kind == "tool" and component.name.startswith("FakeHostedMCPTool")
        for component in ir.components
    )
    capabilities = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "capability" and component.name == "mcp-access"
    }
    assert set(capabilities) == {
        9,
        10,
        13,
        17,
        18,
        21,
        22,
        32,
        40,
        49,
        60,
        68,
        76,
        84,
        92,
        93,
        94,
        95,
        103,
        104,
    }
    assert capabilities[40].attributes["mcp_approval_resolution"] == (
        "same-block-literal-string"
    )
    assert capabilities[40].attributes["mcp_approval_handler_resolution"] == (
        "same-file-direct-approval-dict-return"
    )
    assert capabilities[40].attributes["mcp_approval_handler_predicate"] == (
        "request-field-not-equals-literal"
    )
    assert capabilities[40].attributes["mcp_approval_handler_predicate_values"] == [
        "delete_page"
    ]
    assert capabilities[49].attributes["mcp_approval_policy"] == "selective"
    assert capabilities[68].attributes["mcp_approval_resolution"] == (
        "imported-local-literal:repository-module-single-path"
    )
    assert capabilities[76].attributes["mcp_approval_policy"] == "selective"
    assert capabilities[84].attributes["mcp_approval_policy"] == "dynamic"
    assert capabilities[92].attributes["mcp_tool_config_resolution"] == (
        "imported-local-tool-config:repository-module-single-path"
    )
    assert capabilities[93].attributes["mcp_approval_requirement"] == "always"
    assert capabilities[94].attributes["mcp_approval_policy"] == "dynamic"
    assert capabilities[95].attributes["mcp_approval_resolution"] == (
        "imported-local-reexport-literal:repository-module-single-path"
    )
    assert capabilities[103].attributes["mcp_tool_config_resolution"] == (
        "imported-local-reexport-tool-config:repository-module-single-path"
    )
    assert capabilities[104].attributes["mcp_approval_policy"] == "dynamic"
    assert capabilities[13].attributes["mcp_approval_resolution"] == (
        "imported-local-star-reexport-literal:repository-module-single-path"
    )
    assert capabilities[21].attributes["mcp_tool_config_resolution"] == (
        "imported-local-star-reexport-tool-config:repository-module-single-path"
    )
    assert capabilities[22].attributes["mcp_approval_policy"] == "dynamic"
    assert capabilities[9].attributes["mcp_approval_resolution"] == (
        "imported-local-star-import-literal:repository-module-single-path"
    )
    assert capabilities[17].attributes["mcp_tool_config_resolution"] == (
        "imported-local-star-import-tool-config:repository-module-single-path"
    )
    assert capabilities[18].attributes["mcp_approval_policy"] == "dynamic"
    assert capabilities[10].attributes["mcp_approval_resolution"] == (
        "imported-local-star-import-literal:repository-module-single-path"
    )
    assert capabilities[10].attributes["mcp_approval_policy"] == "always-required"
    tool_edges = {
        edge.source_name: edge
        for edge in ir.relationships
        if edge.source_kind == "tool" and edge.target_kind == "capability"
    }
    assert set(tool_edges) == {
        "HostedMCPTool@32",
        "HostedMCPTool@40",
        "HostedMCPTool@49",
        "HostedMCPTool@60",
        "HostedMCPTool@68",
        "HostedMCPTool@76",
        "HostedMCPTool@84",
        "HostedMCPTool@92",
        "HostedMCPTool@93",
        "HostedMCPTool@94",
        "HostedMCPTool@95",
        "HostedMCPTool@103",
        "HostedMCPTool@104",
        "HostedMCPTool@13",
        "HostedMCPTool@17",
        "HostedMCPTool@18",
        "HostedMCPTool@21",
        "HostedMCPTool@22",
        "HostedMCPTool@9",
        "HostedMCPTool@10",
    }


def test_python_openai_hosted_mcp_approval_callback_shadow_stays_unresolved(
    tmp_path: Path,
) -> None:
    (tmp_path / "agent.py").write_text(
        textwrap.dedent(
            """
            from agents import Agent, HostedMCPTool

            def prompt_approval(request):
                return {'approve': request.data.name != 'delete_page'}

            def build_agent():
                prompt_approval = lambda request: {'approve': True}
                return Agent(
                    name='shadowed callback',
                    tools=[
                        HostedMCPTool(
                            tool_config={'type': 'mcp', 'require_approval': 'always'},
                            on_approval_request=prompt_approval,
                        )
                    ],
                )
            """
        )
    )
    ir = scan_repository(tmp_path)
    tool = next(
        component
        for component in ir.components
        if component.kind == "tool"
        and component.attributes.get("constructor") == "HostedMCPTool"
    )
    assert tool.attributes["mcp_approval_handler"] == "configured"
    assert tool.attributes["mcp_approval_handler_policy"] == "callback-controlled"
    assert "mcp_approval_handler_resolution" not in tool.attributes


def test_python_openai_hosted_mcp_approval_callback_result_binding_is_exact(
    tmp_path: Path,
) -> None:
    (tmp_path / "agent.py").write_text(
        textwrap.dedent(
            """
            from agents import Agent, HostedMCPTool

            def confirm_with_fallback(message, default=False):
                return default

            def prompt_approval(request):
                approved = confirm_with_fallback(
                    f"Approve running {request.data.name}?",
                    default=True,
                )
                result = {"approve": approved}
                if not approved:
                    result["reason"] = "User denied"
                return result

            def build_agent():
                return Agent(
                    name='result binding callback',
                    tools=[
                        HostedMCPTool(
                            tool_config={'type': 'mcp', 'require_approval': 'always'},
                            on_approval_request=prompt_approval,
                        )
                    ],
                )
            """
        )
    )
    ir = scan_repository(tmp_path)
    tool = next(
        component
        for component in ir.components
        if component.kind == "tool"
        and component.attributes.get("constructor") == "HostedMCPTool"
    )
    assert tool.attributes["mcp_approval_handler_resolution"] == (
        "same-file-result-binding-approval-dict-return"
    )
    assert tool.attributes["mcp_approval_handler_result_binding"] == "result"
    assert tool.attributes["mcp_approval_handler_approve_binding"] == "approved"
    assert tool.attributes["mcp_approval_handler_decision"] == "dynamic-callback-result"
    assert tool.attributes["mcp_approval_handler_approve_source"] == "call-result"
    assert tool.attributes["mcp_approval_handler_approve_call"] == "confirm_with_fallback"


def test_python_computer_tool_has_exact_agent_and_capability_identity() -> None:
    ir = scan_repository(ROOT / "cases/python_computer_tool")
    tools = [
        component
        for component in ir.components
        if component.kind == "tool" and component.name.startswith("ComputerTool@")
    ]
    assert {tool.evidence.line for tool in tools} == {14, 19, 24, 29, 33}
    assert {tool.symbol_id for tool in tools} == {
        "py:agent.py#tool:tool@14",
        "py:agent.py#tool:tool@19",
        "py:agent.py#tool:tool@24",
        "py:agent.py#tool:tool@29",
        "py:agent.py#tool:ComputerTool@33",
    }
    tool_by_line = {tool.evidence.line: tool for tool in tools}
    assert tool_by_line[14].attributes["approval_policy"] == "not-applicable"
    assert tool_by_line[14].attributes["approval_source"] == "sdk-computer-safety-check"
    assert tool_by_line[14].attributes["safety_check_handler"] == "none"
    assert tool_by_line[14].attributes["execution_environment"] == "local"
    assert tool_by_line[19].attributes["safety_check_handler"] == "configured"
    assert tool_by_line[19].attributes["safety_check_policy"] == "auto-acknowledge-all"
    assert tool_by_line[19].attributes["safety_check_resolution"] == "inline-lambda"
    assert tool_by_line[24].attributes["safety_check_policy"] == "auto-acknowledge-all"
    assert tool_by_line[24].attributes["safety_check_resolution"] == "same-file-callback"
    assert tool_by_line[29].attributes["safety_check_handler"] == "configured"
    assert tool_by_line[29].attributes["safety_check_policy"] == "unresolved"

    agent_edges = {
        edge.source_name: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert agent_edges["first"].target_id == "py:agent.py#tool:tool@14"
    assert agent_edges["first"].attributes == {"target_identity": "lexical-single-definition"}
    assert agent_edges["second"].target_id == "py:agent.py#tool:tool@19"
    assert agent_edges["second"].attributes == {"target_identity": "lexical-single-definition"}
    assert agent_edges["third"].target_id == "py:agent.py#tool:tool@24"
    assert agent_edges["third"].attributes == {"target_identity": "lexical-single-definition"}
    assert agent_edges["fourth"].target_id == "py:agent.py#tool:tool@29"
    assert agent_edges["fourth"].attributes == {"target_identity": "lexical-single-definition"}
    assert agent_edges["inline"].target_id == "py:agent.py#tool:ComputerTool@33"
    assert agent_edges["inline"].attributes == {}

    capability_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "tool"
        and edge.relation == "uses"
        and edge.target_name == "computer-control"
    ]
    assert {edge.source_id for edge in capability_edges} == {tool.symbol_id for tool in tools}
    capabilities = [
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "computer-control"
    ]
    assert len(capabilities) == 5
    assert all(
        component.attributes["execution_environment"] == "local" for component in capabilities
    )
    assert not any(edge.evidence.path == "unrelated.py" for edge in capability_edges)
    safety_findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL011"]
    assert [(finding.evidence.line, finding.analysis["tool"]) for finding in safety_findings] == [
        (19, "ComputerTool@19"),
        (24, "ComputerTool@24"),
    ]
    assert {finding.analysis["safety_check_resolution"] for finding in safety_findings} == {
        "inline-lambda",
        "same-file-callback",
    }


def test_assigned_builtin_tool_uses_binding_identity_for_agent_context(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """from agents import Agent, ShellTool

shell = ShellTool(executor=object(), needs_approval=False)
operator = Agent(name="operator", tools=[shell])
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    tool = next(component for component in ir.components if component.kind == "tool")
    edge = next(
        relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent" and relationship.target_kind == "tool"
    )
    finding = next(finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL002")
    assert tool.symbol_id == edge.target_id == "py:agent.py#tool:shell"
    assert edge.source_id == "py:agent.py#agent:operator"
    assert finding.ir_path[:2] == ("agent:operator", "tool:ShellTool@3")
    assert finding.analysis["direct_agents"] == ["operator"]


def test_repeated_python_bindings_get_occurrence_qualified_symbol_ids(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """from agents import Agent, ShellTool

def first():
    shell = ShellTool(executor=object())
    agent = Agent(name="shared", tools=[shell])
    return agent

def second():
    shell = ShellTool(executor=object())
    agent = Agent(name="shared", tools=[shell])
    return agent
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)
    agents = [component for component in ir.components if component.kind == "agent"]
    edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    ]
    assert {component.symbol_id for component in agents} == {
        "py:agent.py#agent:agent@5",
        "py:agent.py#agent:agent@10",
    }
    assert {edge.source_id for edge in edges} == {component.symbol_id for component in agents}
    assert {edge.target_id for edge in edges} == {
        "py:agent.py#tool:shell@4",
        "py:agent.py#tool:shell@9",
    }
    assert all(edge.attributes["target_identity"] == "lexical-single-definition" for edge in edges)

    bom = json.loads(render_bom(ir))
    source_endpoints = [
        relationship["source"]
        for relationship in bom["relationships"]
        if relationship["source"]["kind"] == "agent"
    ]
    assert source_endpoints
    assert all(endpoint["resolution"] == "symbol-id" for endpoint in source_endpoints)
    assert len({endpoint["asset_id"] for endpoint in source_endpoints}) == 2
    target_endpoints = [
        relationship["target"]
        for relationship in bom["relationships"]
        if relationship["source"]["kind"] == "agent"
    ]
    assert all(endpoint["resolution"] == "symbol-id" for endpoint in target_endpoints)


def test_python_scoped_resolution_rejects_reassignment_and_forward_reference(
    tmp_path: Path,
) -> None:
    (tmp_path / "agent.py").write_text(
        """from agents import Agent, ShellTool

def reassigned():
    shell = ShellTool(executor=object())
    shell = ShellTool(executor=object())
    return Agent(name="reassigned", tools=[shell])

def forward():
    agent = Agent(name="forward", tools=[later])
    later = ShellTool(executor=object())
    return agent

def module_forward():
    return Agent(name="module-forward", tools=[global_later])

global_later = ShellTool(executor=object())
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)
    edges = [edge for edge in ir.relationships if edge.source_kind == "agent"]
    assert {edge.source_name for edge in edges} == {
        "forward",
        "module-forward",
        "reassigned",
    }
    assert all(edge.target_id is None for edge in edges)
    reassigned = next(edge for edge in edges if edge.source_name == "reassigned")
    assert reassigned.attributes["target_identity"] == "ambiguous-repeated-binding"
    forward = next(edge for edge in edges if edge.source_name == "forward")
    assert "target_identity" not in forward.attributes


def test_repeated_python_tool_definitions_get_occurrence_qualified_ids(tmp_path: Path) -> None:
    (tmp_path / "tools.py").write_text(
        """from agents import function_tool

def first():
    @function_tool(needs_approval=True)
    def approval_tool():
        return "first"
    return approval_tool

def second():
    @function_tool(needs_approval=True)
    def approval_tool():
        return "second"
    return approval_tool
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)
    tools = [component for component in ir.components if component.kind == "tool"]
    approval_edges = [edge for edge in ir.relationships if edge.relation == "governed-by"]
    assert {component.symbol_id for component in tools} == {
        "py:tools.py#tool:approval_tool@5",
        "py:tools.py#tool:approval_tool@11",
    }
    assert {edge.source_id for edge in approval_edges} == {
        component.symbol_id for component in tools
    }
    bom = json.loads(render_bom(ir))
    assert all(
        relationship["source"]["resolution"] == "symbol-id" for relationship in bom["relationships"]
    )


def test_default_disabled_local_shell_is_reviewed_but_hosted_shell_is_not(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """from agents import Agent, ShellTool

local = Agent(name="local", tools=[ShellTool(executor=object())])
hosted = Agent(
    name="hosted",
    tools=[ShellTool(environment={"type": "container_auto"})],
)
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    approval_reviews = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL002"]
    assert len(approval_reviews) == 1
    assert approval_reviews[0].evidence.line == 3
    assert approval_reviews[0].result_kind == "review"
    assert "disabled by default" in approval_reviews[0].message
    environments = {
        component.evidence.line: component.attributes["execution_environment"]
        for component in ir.components
        if component.kind == "tool"
    }
    assert environments == {3: "local", 6: "hosted"}


def test_non_approval_skip_and_status_flags_are_not_bypasses(tmp_path: Path) -> None:
    (tmp_path / "flags.py").write_text(
        """_sampling_auto_approved_warning_logged = True
dangerously_skip_version_check = True
auto_approve = True
""",
        encoding="utf-8",
    )
    (tmp_path / "flags.ts").write_text(
        """const warning = { autoApprovedWarningLogged: true };
const client = { dangerouslySkipVersionCheck: true };
const policy = { autoApprove: true };
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    approval_findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL001"]
    assert [(finding.evidence.path, finding.evidence.line) for finding in approval_findings] == [
        ("flags.py", 3),
        ("flags.ts", 3),
    ]


def test_environment_auto_approval_requires_a_direct_true_return() -> None:
    ir = scan_repository(ROOT / "cases/approval_env_guard")

    approval_findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL001"]
    assert [(finding.evidence.path, finding.evidence.line) for finding in approval_findings] == [
        ("approval.py", 8),
        ("approval.py", 42),
        ("approval.ts", 4),
        ("approval.ts", 12),
    ]
    controls = {
        (component.evidence.path, component.evidence.line): component.attributes
        for component in ir.components
        if component.kind == "control-setting" and component.name == "auto-approval"
    }
    assert controls[("approval.py", 8)]["environment_names"] == ["SHELL_AUTO_APPROVE"]
    assert controls[("approval.py", 42)] == {
        "enabled": True,
        "source": "environment-approval-short-circuit",
        "environment_names": ["PATCH_AUTO_APPROVE"],
        "scope": "production",
    }
    assert controls[("approval.ts", 4)]["environment_names"] == ["AUTO_APPROVE_HITL"]
    assert controls[("approval.ts", 12)]["environment_names"] == ["SHELL_AUTO_APPROVE"]
    assert all(
        attributes["source"] == "environment-guard"
        for location, attributes in controls.items()
        if location != ("approval.py", 42)
    )


def test_environment_approval_attribute_is_independent_of_method_order(tmp_path: Path) -> None:
    (tmp_path / "gate.py").write_text(
        """import os

class Gate:
    def require_confirmation(self) -> None:
        if self.auto_approve:
            return
        self.prompt()

    def __init__(self) -> None:
        self.auto_approve = os.environ["AUTO_APPROVE_ACTIONS"] == "1"
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line) for finding in ir.findings
    ] == [("AV-APPROVAL001", "gate.py", 5)]


def test_anthropic_and_azure_model_providers() -> None:
    ir = scan_repository(ROOT / "cases/model_providers")

    assert {(item.kind, item.name) for item in ir.components} >= {
        ("provider", "Anthropic"),
        ("provider", "Azure OpenAI"),
        ("model", "gpt-4o-enterprise"),
    }
    assert ("provider", "OpenAI") not in {(item.kind, item.name) for item in ir.components}
    azure_model = next(item for item in ir.components if item.kind == "model")
    assert azure_model.attributes["provider"] == "Azure OpenAI"


def test_dynamic_mcp_forwarding_but_not_fixed_tool_call() -> None:
    ir = scan_repository(ROOT / "cases/mcp_forwarder")

    forwarding = [
        item
        for item in ir.components
        if item.kind == "capability" and item.name == "mcp-tool-forwarding"
    ]
    assert len(forwarding) == 12
    assert [finding.rule_id for finding in ir.findings] == [
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
        "AV-MCP002",
    ]
    assert ir.findings[0].result_kind == "review"
    guarded = next(item for item in forwarding if item.attributes["allowlist_guard"])
    assert guarded.evidence.line == 18
    assert any(
        item.source_kind == "capability"
        and item.relation == "governed-by"
        and item.target_name == "tool-allowlist"
        for item in ir.relationships
    )
    late = next(item for item in forwarding if item.evidence.line == 22)
    assert late.attributes["allowlist_guard"] is False
    registry_guarded = next(item for item in forwarding if item.evidence.line == 36)
    assert registry_guarded.attributes == {
        "api": "session.call_tool",
        "dynamic_tool_name": True,
        "dynamic_arguments": True,
        "allowlist_guard": False,
        "registry_guard": True,
        "fixed_tool_binding": False,
        "scope": "production",
        "guard_control": "tool-registry",
        "guard_path": "proxy.py",
        "guard_line": 35,
    }
    registry_edge = next(
        item
        for item in ir.relationships
        if item.evidence.line == 36 and item.target_name == "tool-registry"
    )
    assert registry_edge.attributes == {
        "control_path": "proxy.py",
        "control_line": 35,
        "policy_effect": "routing-only",
    }
    registry_finding = next(item for item in ir.findings if item.evidence.line == 36)
    assert registry_finding.analysis["governing_controls"] == ["tool-registry"]
    assert registry_finding.analysis["governing_control_effects"] == {
        "tool-registry": ["routing-only"]
    }
    assert (
        next(item for item in forwarding if item.evidence.line == 41).attributes["allowlist_guard"]
        is False
    )
    assert (
        next(item for item in forwarding if item.evidence.line == 49).attributes["allowlist_guard"]
        is False
    )
    bound = next(item for item in forwarding if item.evidence.line == 64)
    assert bound.attributes["fixed_tool_binding"] is True
    assert bound.attributes["binding_line"] == 57
    binding_edge = next(
        item
        for item in ir.relationships
        if item.evidence.line == 64 and item.target_name == "fixed-tool-binding"
    )
    assert binding_edge.attributes == {
        "control_path": "proxy.py",
        "control_line": 57,
        "binding_scope": "instance",
        "policy_effect": "binds-tool-source-per-instance",
    }
    bound_finding = next(item for item in ir.findings if item.evidence.line == 64)
    assert bound_finding.analysis["governing_controls"] == ["fixed-tool-binding"]
    assert bound_finding.analysis["governing_control_effects"] == {
        "fixed-tool-binding": ["binds-tool-source-per-instance"]
    }
    mutable = next(item for item in forwarding if item.evidence.line == 76)
    assert mutable.attributes["fixed_tool_binding"] is False
    assert not any(
        item.evidence.line == 76 and item.target_name == "fixed-tool-binding"
        for item in ir.relationships
    )
    closure = next(item for item in forwarding if item.evidence.line == 81)
    assert closure.attributes["fixed_tool_binding"] is True
    assert closure.attributes["binding_scope"] == "closure"
    closure_edge = next(
        item
        for item in ir.relationships
        if item.evidence.line == 81 and item.target_name == "fixed-tool-binding"
    )
    assert closure_edge.attributes == {
        "control_path": "proxy.py",
        "control_line": 79,
        "binding_scope": "closure",
        "policy_effect": "binds-tool-source-per-closure",
    }
    rebound = next(item for item in forwarding if item.evidence.line == 90)
    assert rebound.attributes["fixed_tool_binding"] is False
    assert not any(
        item.evidence.line == 90 and item.target_name == "fixed-tool-binding"
        for item in ir.relationships
    )
    routed = next(item for item in forwarding if item.evidence.line == 97)
    assert routed.attributes["registry_guard"] is True
    assert routed.attributes["guard_summary"] == "same-class-method"
    routed_edge = next(
        item
        for item in ir.relationships
        if item.evidence.line == 97 and item.target_name == "tool-registry"
    )
    assert routed_edge.attributes == {
        "control_path": "proxy.py",
        "control_line": 101,
        "policy_effect": "routing-only",
        "summary": "same-class-method",
    }
    routed_finding = next(item for item in ir.findings if item.evidence.line == 97)
    assert routed_finding.analysis["governing_control_effects"] == {
        "tool-registry": ["routing-only"]
    }
    fallback = next(item for item in forwarding if item.evidence.line == 108)
    assert fallback.attributes["registry_guard"] is False
    assert not any(
        item.evidence.line == 108 and item.target_name == "tool-registry"
        for item in ir.relationships
    )


def test_mcp_registry_method_summary_requires_literal_path_selection(tmp_path: Path) -> None:
    source = """from mcp.server import Server

class MiddlewareServer:
    async def select_dynamic(self, name: str, arguments: dict, selected: bool):
        return await self.call_tool(name, arguments, run_middleware=selected)

    async def select_core(self, name: str, arguments: dict):
        return await self.call_tool(name, arguments, run_middleware=False)

    async def call_tool(
        self,
        name: str,
        arguments: dict,
        *,
        run_middleware: bool = True,
    ):
        if run_middleware:
            return await self.call_tool(name, arguments, run_middleware=False)
        tool = await self.get_tool(name)
        if tool is None:
            raise ValueError(name)
        return await tool.run(arguments)

class ReturnFallbackServer:
    async def dispatch(self, name: str, arguments: dict):
        return await self.call_tool(name, arguments)

    async def call_tool(self, name: str, arguments: dict):
        tool = await self.get_tool(name)
        if tool is None:
            return await self.default_tool.run(arguments)
        return await tool.run(arguments)

class ConditionalGuardServer:
    async def dispatch(self, name: str, arguments: dict):
        return await self.call_tool(name, arguments)

    async def call_tool(self, name: str, arguments: dict, enforce: bool = True):
        tool = await self.get_tool(name)
        if enforce:
            if tool is None:
                raise ValueError(name)
        return await tool.run(arguments)

class ReassignedFallbackServer:
    async def dispatch(self, name: str, arguments: dict):
        return await self.call_tool(name, arguments)

    async def call_tool(self, name: str, arguments: dict):
        tool = await self.get_tool(name)
        if tool is None:
            tool = self.default_tool
        if tool is None:
            raise ValueError(name)
        return await tool.run(arguments)
"""
    (tmp_path / "server.py").write_text(source, encoding="utf-8")

    ir = scan_repository(tmp_path)
    registry_edges = [
        item
        for item in ir.relationships
        if item.target_name == "tool-registry" and item.evidence.path == "server.py"
    ]

    def line_of(fragment: str) -> int:
        return source[: source.index(fragment)].count("\n") + 1

    dynamic_line = line_of("self.call_tool(name, arguments, run_middleware=selected)")
    core_line = line_of("self.call_tool(name, arguments, run_middleware=False)")
    fallback_line = line_of(
        "return await self.call_tool(name, arguments)\n\n    async def call_tool"
    )
    conditional_line = line_of(
        "return await self.call_tool(name, arguments)\n\n    async def call_tool(self, name: str, arguments: dict, enforce"
    )
    reassigned_line = line_of(
        "return await self.call_tool(name, arguments)\n\n    async def call_tool(self, name: str, arguments: dict):\n        tool = await self.get_tool(name)\n        if tool is None:\n            tool = self.default_tool"
    )
    assert not any(item.evidence.line == dynamic_line for item in registry_edges)
    assert not any(item.evidence.line == fallback_line for item in registry_edges)
    assert not any(item.evidence.line == conditional_line for item in registry_edges)
    assert not any(item.evidence.line == reassigned_line for item in registry_edges)
    core_edge = next(item for item in registry_edges if item.evidence.line == core_line)
    assert core_edge.attributes["required_arguments"] == {"run_middleware": False}
    assert core_edge.attributes["summary"] == "same-class-method"


def test_imported_mcp_registry_manager_requires_immutable_constructor_binding() -> None:
    fixture = ROOT / "cases/mcp_imported_manager"
    ir = scan_repository(fixture)

    forwarding = {
        item.evidence.line: item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "mcp-tool-forwarding"
        and item.evidence.path == "app/server.py"
    }
    assert set(forwarding) == {11, 22, 30}
    routed = forwarding[11]
    assert routed.attributes["registry_guard"] is True
    assert routed.attributes["guard_summary"] == "imported-class-method"
    assert routed.attributes["guard_class"] == "RegistryManager"
    assert routed.attributes["guard_path"] == "app/managers/registry.py"
    assert routed.attributes["guard_line"] == 4
    routed_edge = next(
        item
        for item in ir.relationships
        if item.evidence.path == "app/server.py"
        and item.evidence.line == 11
        and item.target_name == "tool-registry"
    )
    assert routed_edge.attributes == {
        "control_path": "app/managers/registry.py",
        "control_line": 4,
        "policy_effect": "routing-only",
        "summary": "imported-class-method",
        "summary_class": "RegistryManager",
        "summary_path": "app/managers/registry.py",
    }
    assert forwarding[22].attributes["registry_guard"] is False
    assert forwarding[30].attributes["registry_guard"] is False
    assert not any(
        item.target_name == "tool-registry"
        and item.evidence.path == "app/server.py"
        and item.evidence.line in {22, 30}
        for item in ir.relationships
    )
    rebound = next(
        item
        for item in ir.components
        if item.name == "mcp-tool-forwarding"
        and item.evidence.path == "app/rebound_server.py"
        and item.evidence.line == 13
    )
    assert rebound.attributes["registry_guard"] is False
    assert not any(
        item.target_name == "tool-registry"
        and item.evidence.path == "app/rebound_server.py"
        and item.evidence.line == 13
        for item in ir.relationships
    )

    partial = scan_repository(fixture, selected_paths=["app/server.py"])
    assert not any(item.target_name == "tool-registry" for item in partial.relationships)


def test_browser_and_external_action_capabilities_are_linked() -> None:
    ir = scan_repository(ROOT / "cases/external_actions")

    capabilities = {item.name for item in ir.components if item.kind == "capability"}
    assert capabilities >= {"browser", "network", "external-action"}
    tool_capabilities = {
        item.target_name
        for item in ir.relationships
        if item.source_kind == "tool" and item.source_name == "publish"
    }
    assert tool_capabilities >= {"browser", "network", "external-action"}
    assert not ir.findings


def test_parameter_controlled_http_origin_is_reported_but_fixed_host_is_not() -> None:
    ir = scan_repository(ROOT / "cases/network_dynamic_origin")

    network = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability" and item.name == "network" and item.evidence.path == "agent.py"
    }
    assert network[7]["dynamic_origin"] is True
    assert network[12]["dynamic_origin"] is False
    assert network[17]["dynamic_origin"] is False
    assert network[31] == {
        "scope": "production",
        "api": "urlrequest.urlopen",
        "canonical_api": "urllib.request.urlopen",
        "dynamic_origin": True,
    }
    assert network[37] == {
        "scope": "production",
        "api": "open_url",
        "canonical_api": "urllib.request.urlopen",
        "dynamic_origin": True,
    }
    assert network[43] == {
        "scope": "production",
        "api": "request_alias.urlopen",
        "canonical_api": "urllib.request.urlopen",
        "dynamic_origin": False,
    }
    assert sorted(network) == [7, 12, 17, 31, 37, 43]
    assert [
        (finding.rule_id, finding.evidence.line)
        for finding in ir.findings
        if finding.evidence.path == "agent.py"
    ] == [
        ("AV-NET001", 7),
        ("AV-NET001", 31),
        ("AV-NET001", 37),
    ]
    finding = ir.findings[0]
    assert finding.result_kind == "review"
    assert finding.ir_path == (
        "agent:networker",
        "tool:fetch_url",
        "capability:network",
    )
    assert {
        (edge.source_name, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_kind == "capability" and edge.target_name == "network"
    } == {
        ("fetch_url", 7),
        ("search", 12),
        ("status", 17),
        ("urllib_direct", 31),
        ("urllib_request", 37),
        ("urllib_fixed_request", 43),
        ("guarded_fetch", 13),
        ("guarded_alias_fetch", 22),
        ("late_guard", 27),
        ("scheme_only", 39),
        ("continuing_guard", 47),
        ("rebound_parser", 56),
        ("shadowed_parser", 65),
        ("mutable_host_policy", 76),
        ("rejection_branch_request", 83),
    }


def test_python_imported_literal_http_origins_require_exact_immutable_proof() -> None:
    ir = scan_repository(ROOT / "cases/python_imported_literal_origin")

    network = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability" and item.name == "network" and item.evidence.path == "agent.py"
    }
    assert sorted(network) == [23, 28, 33, 38, 43, 48, 53, 58, 63, 68, 75]
    for line, source_line in ((23, 4), (28, 5), (33, 4)):
        assert network[line] == {
            "scope": "production",
            "api": "requests.get",
            "dynamic_origin": False,
            "origin_resolution": "imported-module-literal",
            "origin_path": "pkg/settings.py",
            "origin_line": source_line,
        }
    assert {
        line: attributes["dynamic_origin"] for line, attributes in network.items() if line >= 38
    } == {
        38: True,
        43: True,
        48: True,
        53: True,
        58: True,
        63: True,
        68: True,
        75: True,
    }
    assert [
        finding.evidence.line
        for finding in ir.findings
        if finding.rule_id == "AV-NET001" and finding.evidence.path == "agent.py"
    ] == [38, 43, 48, 53, 58, 63, 68, 75]
    derived = next(
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.evidence.path == "derived_mutation.py"
    )
    assert derived.evidence.line == 17
    assert derived.attributes["dynamic_origin"] is True
    assert "origin_resolution" not in derived.attributes


def test_python_network_origin_guards_require_fail_closed_scheme_and_host_checks() -> None:
    ir = scan_repository(ROOT / "cases/network_dynamic_origin")

    guarded = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.evidence.path == "guards.py"
        and item.attributes.get("network_origin_guard")
    }
    assert sorted(guarded) == [13, 22]
    assert guarded[13]["initial_origin_scope"] == "allowlisted"
    assert guarded[22]["initial_origin_scope"] == "allowlisted"
    controls = [
        item
        for item in ir.components
        if item.kind == "control" and item.name == "network-origin-allowlist"
    ]
    assert [(item.evidence.path, item.evidence.line) for item in controls] == [
        ("guards.py", 11),
        ("guards.py", 20),
    ]
    assert controls[0].attributes == {
        "scope": "production",
        "policy_effect": "restricts-initial-http-origin",
        "frontend": "python",
        "parser": "urlsplit",
        "url": "url",
        "schemes": ["https"],
        "hosts": ["api.example.com", "cdn.example.com"],
        "initial_origin_scope": "allowlisted",
        "redirect_scope": "disabled",
        "dns_scope": "unresolved",
    }
    assert controls[1].attributes["redirect_scope"] == "unresolved"
    governed_lines = {
        edge.evidence.line
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.source_name == "network"
        and edge.relation == "governed-by"
        and edge.target_kind == "control"
        and edge.target_name == "network-origin-allowlist"
    }
    assert governed_lines == {13, 22}
    guarded_finding = next(
        finding
        for finding in ir.findings
        if finding.rule_id == "AV-NET001"
        and finding.evidence.path == "guards.py"
        and finding.evidence.line == 13
    )
    assert guarded_finding.result_kind == "review"
    assert guarded_finding.analysis["governing_controls"] == ["network-origin-allowlist"]


def test_dynamic_http_origin_tracks_aliases_and_keyword_url(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """import requests
from agents import function_tool

@function_tool
def fetch(target: str) -> str:
    alias = target
    return requests.request(method="GET", url=alias).text

class ConfiguredClient:
    @function_tool
    def fetch_configured(self) -> str:
        return requests.get(self.endpoint).text
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    findings = [finding for finding in ir.findings if finding.rule_id == "AV-NET001"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.evidence.line == 7
    assert finding.analysis["tool"] == "fetch"


def test_typescript_dynamic_eval_is_linked_and_reported() -> None:
    ir = scan_repository(ROOT / "cases/typescript_eval")

    assert [finding.rule_id for finding in ir.findings] == ["AV-EXEC002"]
    assert ir.findings[0].ir_path == (
        "agent:evaluator",
        "tool:evaluate",
        "capability:code-execution",
    )


def test_typescript_tool_arrays_are_structure_aware_and_identity_linked() -> None:
    ir = scan_repository(ROOT / "cases/typescript_structured_tools")

    tools = {component.name: component for component in ir.components if component.kind == "tool"}
    assert set(tools) == {
        "applyPatchTool@34",
        "assignedShell",
        "computerTool@38",
        "namespaceTools",
        "safeTool",
    }
    assert tools["assignedShell"].attributes["approval_policy"] == "disabled-explicit"
    assert tools["assignedShell"].attributes["execution_environment"] == "local"
    assert tools["applyPatchTool@34"].attributes["approval_policy"] == "enabled"
    assert tools["applyPatchTool@34"].attributes["execution_environment"] == "local"
    assert tools["computerTool@38"].attributes["approval_policy"] == "callback-controlled"
    assert tools["computerTool@38"].attributes["approval_handler"] == "needsApproval-callback"
    assert tools["computerTool@38"].attributes["approval_decision"] == "dynamic-callback"
    assert tools["computerTool@38"].attributes["approval_predicate"] == "field-in-literal-set"
    assert tools["computerTool@38"].attributes["approval_predicate_field"] == "type"
    assert tools["computerTool@38"].attributes["approval_predicate_values"] == ["click", "type"]

    operator_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.source_name == "operator"
    ]
    assert {(edge.relation, edge.target_kind, edge.target_name) for edge in operator_edges} == {
        ("delegates-to", "agent", "worker"),
        ("uses", "tool", "applyPatchTool@34"),
        ("uses", "tool", "assignedShell"),
        ("uses", "tool", "computerTool@38"),
        ("uses", "tool", "namespaceTools"),
        ("uses", "tool", "safeTool"),
        ("uses", "tool", "unknownFactory"),
        ("uses", "tool", "unrelatedShellTool"),
    }
    assert not {
        "async",
        "description",
        "do",
        "return",
        "toolName",
        "words",
    } & {edge.target_name for edge in operator_edges}
    assert next(edge for edge in operator_edges if edge.target_name == "worker").target_id == (
        "ts:agent.ts#agent:worker"
    )
    as_tool_edges = sorted(
        [
            edge
            for edge in operator_edges
            if edge.relation == "delegates-to" and edge.target_name == "worker"
        ],
        key=lambda edge: edge.evidence.line,
    )
    assert [(edge.evidence.line, edge.attributes) for edge in as_tool_edges] == [
        (42, {"adapter": "asTool", "tool_name": "worker_tool"}),
        (
            46,
            {
                "adapter": "asTool",
                "tool_name": "approved_worker_tool",
                "approval_policy": "enabled",
                "approval_handler": "none",
                "approval_decision": "always",
            },
        ),
        (
            50,
            {
                "adapter": "asTool",
                "tool_name": "conditional_worker_tool",
                "approval_policy": "callback-controlled",
                "approval_handler": "needsApproval-callback",
                "approval_decision": "dynamic-callback",
                "approval_predicate": "field-contains-literal",
                "approval_predicate_field": "input",
                "approval_predicate_values": ["deploy"],
            },
        ),
    ]

    tool_choice_controls = {
        (
            component.evidence.path,
            component.evidence.line,
            component.symbol_id,
            tuple(sorted(component.attributes.items())),
        )
        for component in ir.components
        if component.kind == "control"
        and component.name == "tool-choice-policy"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-agent-tool-choice"
    }
    assert tool_choice_controls == {
        (
            "agent.ts",
            26,
            "ts:agent.ts#control:worker.toolChoice@26",
            (
                ("analysis", "typescript-openai-agents-agent-tool-choice"),
                ("choice_scope", "agent-model-settings"),
                ("configuration", "Agent.modelSettings.toolChoice"),
                ("constructor", "Agent"),
                ("imported_symbol", "Agent"),
                ("module", "@openai/agents"),
                ("scope", "production"),
                ("source_agent", "worker"),
                ("source_agent_id", "ts:agent.ts#agent:worker"),
                ("tool_choice", "required"),
                ("tool_choice_resolution", "literal"),
            ),
        )
    }
    tool_choice_edges = {
        (
            relationship.source_name,
            relationship.source_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "tool-choice-policy"
    }
    assert tool_choice_edges == {
        (
            "worker",
            "ts:agent.ts#agent:worker",
            "agent.ts",
            26,
            "ts:agent.ts#control:worker.toolChoice@26",
            (
                ("analysis", "typescript-openai-agents-agent-tool-choice"),
                ("binding", "toolChoice"),
                ("configuration", "Agent-modelSettings-toolChoice"),
                ("tool_choice", "required"),
            ),
        )
    }
    model_settings_controls = {
        (
            component.evidence.path,
            component.evidence.line,
            component.symbol_id,
            tuple(sorted(component.attributes.items())),
        )
        for component in ir.components
        if component.kind == "control"
        and component.name == "model-settings-policy"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-agent-model-settings"
    }
    assert model_settings_controls == {
        (
            "agent.ts",
            26,
            "ts:agent.ts#control:worker.modelSettings@26",
            (
                ("analysis", "typescript-openai-agents-agent-model-settings"),
                ("configuration", "Agent.modelSettings"),
                ("constructor", "Agent"),
                ("imported_symbol", "Agent"),
                ("module", "@openai/agents"),
                ("reasoning_effort", "low"),
                ("scope", "production"),
                ("settings_scope", "agent-model-settings"),
                ("source_agent", "worker"),
                ("source_agent_id", "ts:agent.ts#agent:worker"),
                ("text_verbosity", "low"),
            ),
        )
    }
    model_settings_edges = {
        (
            relationship.source_name,
            relationship.source_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "model-settings-policy"
    }
    assert model_settings_edges == {
        (
            "worker",
            "ts:agent.ts#agent:worker",
            "agent.ts",
            26,
            "ts:agent.ts#control:worker.modelSettings@26",
            (
                ("analysis", "typescript-openai-agents-agent-model-settings"),
                ("binding", "modelSettings"),
                ("configuration", "Agent-modelSettings"),
                ("reasoning_effort", "low"),
                ("text_verbosity", "low"),
            ),
        )
    }
    turn_limit_controls = {
        (
            component.evidence.path,
            component.evidence.line,
            component.symbol_id,
            tuple(sorted(component.attributes.items())),
        )
        for component in ir.components
        if component.kind == "control"
        and component.name == "agent-turn-limit"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-astool-turn-limit"
    }
    assert turn_limit_controls == {
        (
            "agent.ts",
            44,
            "ts:agent.ts#control:worker.asTool.maxTurns@44:parent42",
            (
                ("adapter", "asTool"),
                ("analysis", "typescript-openai-agents-astool-turn-limit"),
                ("configuration", "asTool.runOptions.maxTurns"),
                ("limit_scope", "delegated-agent-run"),
                ("max_turns", 3),
                ("module", "@openai/agents"),
                ("parent_agent", "operator"),
                ("parent_agent_id", "ts:agent.ts#agent:operator"),
                ("scope", "production"),
                ("source_agent", "worker"),
                ("source_agent_id", "ts:agent.ts#agent:worker"),
                ("tool_name", "worker_tool"),
            ),
        )
    }
    turn_limit_edges = {
        (
            relationship.source_name,
            relationship.source_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "agent-turn-limit"
    }
    assert turn_limit_edges == {
        (
            "worker",
            "ts:agent.ts#agent:worker",
            "agent.ts",
            44,
            "ts:agent.ts#control:worker.asTool.maxTurns@44:parent42",
            (
                ("adapter", "asTool"),
                ("analysis", "typescript-openai-agents-astool-turn-limit"),
                ("binding", "maxTurns"),
                ("configuration", "asTool-runOptions-maxTurns"),
                ("max_turns", 3),
                ("tool_name", "worker_tool"),
            ),
        )
    }
    model_override_controls = {
        (
            component.evidence.path,
            component.evidence.line,
            component.symbol_id,
            tuple(sorted(component.attributes.items())),
        )
        for component in ir.components
        if component.kind == "control"
        and component.name == "agent-model-override"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-astool-model-override"
    }
    assert model_override_controls == {
        (
            "agent.ts",
            44,
            "ts:agent.ts#control:worker.asTool.model@44:parent42",
            (
                ("adapter", "asTool"),
                ("analysis", "typescript-openai-agents-astool-model-override"),
                ("configuration", "asTool.runConfig.model"),
                ("model", "gpt-5.4"),
                ("model_resolution", "literal"),
                ("module", "@openai/agents"),
                ("override_scope", "delegated-agent-run"),
                ("parent_agent", "operator"),
                ("parent_agent_id", "ts:agent.ts#agent:operator"),
                ("provider", "OpenAI"),
                ("reasoning_effort", "low"),
                ("scope", "production"),
                ("source_agent", "worker"),
                ("source_agent_id", "ts:agent.ts#agent:worker"),
                ("text_verbosity", "low"),
                ("tool_name", "worker_tool"),
            ),
        )
    }
    model_override_edges = {
        (
            relationship.source_name,
            relationship.source_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "agent-model-override"
    }
    assert model_override_edges == {
        (
            "worker",
            "ts:agent.ts#agent:worker",
            "agent.ts",
            44,
            "ts:agent.ts#control:worker.asTool.model@44:parent42",
            (
                ("adapter", "asTool"),
                ("analysis", "typescript-openai-agents-astool-model-override"),
                ("binding", "model"),
                ("configuration", "asTool-runConfig-model"),
                ("model", "gpt-5.4"),
                ("provider", "OpenAI"),
                ("reasoning_effort", "low"),
                ("text_verbosity", "low"),
                ("tool_name", "worker_tool"),
            ),
        )
    }
    workflow_controls = {
        (
            component.evidence.path,
            component.evidence.line,
            component.symbol_id,
            tuple(sorted(component.attributes.items())),
        )
        for component in ir.components
        if component.kind == "control"
        and component.name == "trace-workflow"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-astool-workflow-name"
    }
    assert workflow_controls == {
        (
            "agent.ts",
            44,
            "ts:agent.ts#control:worker.asTool.workflowName@44:parent42",
            (
                ("adapter", "asTool"),
                ("analysis", "typescript-openai-agents-astool-workflow-name"),
                ("configuration", "asTool.runConfig.workflowName"),
                ("module", "@openai/agents"),
                ("parent_agent", "operator"),
                ("parent_agent_id", "ts:agent.ts#agent:operator"),
                ("scope", "production"),
                ("source_agent", "worker"),
                ("source_agent_id", "ts:agent.ts#agent:worker"),
                ("tool_name", "worker_tool"),
                ("trace_scope", "openai-workflow"),
                ("workflow_name", "Worker delegation"),
                ("workflow_name_resolution", "literal"),
            ),
        )
    }
    workflow_edges = {
        (
            relationship.source_name,
            relationship.source_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "trace-workflow"
    }
    assert workflow_edges == {
        (
            "worker",
            "ts:agent.ts#agent:worker",
            "agent.ts",
            44,
            "ts:agent.ts#control:worker.asTool.workflowName@44:parent42",
            (
                ("adapter", "asTool"),
                ("analysis", "typescript-openai-agents-astool-workflow-name"),
                ("binding", "workflowName"),
                ("configuration", "asTool-runConfig-workflowName"),
                ("tool_name", "worker_tool"),
                ("workflow_name", "Worker delegation"),
            ),
        )
    }
    assert (
        next(edge for edge in operator_edges if edge.target_name == "unrelatedShellTool").target_id
        is None
    )
    assert [finding.rule_id for finding in ir.findings] == ["AV-APPROVAL002"]
    assert ir.findings[0].ir_path[:2] == ("agent:operator", "tool:assignedShell")


def test_typescript_openai_web_search_tool_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_web_search_policy")

    tools = {
        component.name: component
        for component in ir.components
        if component.kind == "tool" and component.attributes.get("constructor") == "webSearchTool"
    }
    assert tools["webSearchTool@10"].attributes == {
        "constructor": "webSearchTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "web_search_filter_policy": "allowed-domains",
        "web_search_allowed_domains": ["openai.com", "platform.openai.com"],
        "web_search_allowed_domain_count": 2,
        "web_search_context_size": "medium",
        "web_search_policy": "configured",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["webSearchTool@27"].attributes == {
        "constructor": "webSearchTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["webSearchTool@8"].attributes == {
        "constructor": "webSearchTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "web_search_user_location_policy": "configured",
        "web_search_user_location_type": "approximate",
        "web_search_user_location_city": "New York",
        "web_search_user_location_country": "US",
        "web_search_policy": "configured",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["webSearchTool@17"].attributes == {
        "constructor": "webSearchTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "execution_environment": "unresolved",
        "scope": "production",
    }

    web_search_controls = [
        component
        for component in ir.components
        if component.kind == "control"
        and component.name == "web-search-policy"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-web-search-policy"
    ]
    assert {control.symbol_id for control in web_search_controls} == {
        "ts:agent.ts#control:webSearchTool@10.webSearchPolicy@10",
        "ts:location.ts#control:webSearchTool@8.webSearchPolicy@8",
    }
    domain_control = next(
        control
        for control in web_search_controls
        if control.symbol_id == "ts:agent.ts#control:webSearchTool@10.webSearchPolicy@10"
    )
    assert domain_control.attributes == {
        "analysis": "typescript-openai-agents-web-search-policy",
        "module": "@openai/agents",
        "constructor": "webSearchTool",
        "imported_symbol": "webSearchTool",
        "configuration": "webSearchTool",
        "search_scope": "web-search-tool",
        "source_tool": "webSearchTool@10",
        "source_tool_id": "ts:agent.ts#tool:webSearchTool@10",
        "scope": "production",
        "web_search_filter_policy": "allowed-domains",
        "web_search_allowed_domains": ["openai.com", "platform.openai.com"],
        "web_search_allowed_domain_count": 2,
        "web_search_context_size": "medium",
        "web_search_policy": "configured",
    }
    location_control = next(
        control
        for control in web_search_controls
        if control.symbol_id == "ts:location.ts#control:webSearchTool@8.webSearchPolicy@8"
    )
    assert location_control.attributes == {
        "analysis": "typescript-openai-agents-web-search-policy",
        "module": "@openai/agents",
        "constructor": "webSearchTool",
        "imported_symbol": "webSearchTool",
        "configuration": "webSearchTool",
        "search_scope": "web-search-tool",
        "source_tool": "webSearchTool@8",
        "source_tool_id": "ts:location.ts#tool:webSearchTool@8",
        "scope": "production",
        "web_search_user_location_policy": "configured",
        "web_search_user_location_type": "approximate",
        "web_search_user_location_city": "New York",
        "web_search_user_location_country": "US",
        "web_search_policy": "configured",
    }

    provider_controls = [
        component
        for component in ir.components
        if component.kind == "control"
        and component.name == "provider-data-policy"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-provider-data-policy"
    ]
    assert len(provider_controls) == 1
    assert provider_controls[0].symbol_id == (
        "ts:agent.ts#control:docsSearcher.providerDataInclude@19"
    )
    assert provider_controls[0].attributes == {
        "analysis": "typescript-openai-agents-provider-data-policy",
        "module": "@openai/agents",
        "constructor": "Agent",
        "imported_symbol": "Agent",
        "configuration": "Agent.modelSettings.providerData.include",
        "settings_scope": "agent-provider-data",
        "source_agent": "Docs searcher",
        "source_agent_id": "ts:agent.ts#agent:docsSearcher",
        "provider_data_include": ["web_search_call.action.sources"],
        "scope": "production",
        "web_search_sources_included": True,
    }

    policy_edges = {
        (
            relationship.source_kind,
            relationship.source_name,
            relationship.source_id,
            relationship.relation,
            relationship.target_kind,
            relationship.target_name,
            relationship.target_id,
            relationship.evidence.path,
            relationship.evidence.line,
        )
        for relationship in ir.relationships
        if relationship.target_name in {"web-search-policy", "provider-data-policy"}
    }
    assert policy_edges == {
        (
            "tool",
            "webSearchTool@10",
            "ts:agent.ts#tool:webSearchTool@10",
            "configured-by",
            "control",
            "web-search-policy",
            "ts:agent.ts#control:webSearchTool@10.webSearchPolicy@10",
            "agent.ts",
            10,
        ),
        (
            "agent",
            "Docs searcher",
            "ts:agent.ts#agent:docsSearcher",
            "configured-by",
            "control",
            "provider-data-policy",
            "ts:agent.ts#control:docsSearcher.providerDataInclude@19",
            "agent.ts",
            19,
        ),
        (
            "tool",
            "webSearchTool@8",
            "ts:location.ts#tool:webSearchTool@8",
            "configured-by",
            "control",
            "web-search-policy",
            "ts:location.ts#control:webSearchTool@8.webSearchPolicy@8",
            "location.ts",
            8,
        ),
    }


def test_typescript_openai_agent_parallel_tool_calls_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_model_settings_parallel")

    controls = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "control"
        and component.name == "model-settings-policy"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-agent-model-settings"
    }
    assert set(controls) == {
        "ts:agent.ts#control:sequentialAgent.modelSettings@7",
        "ts:agent.ts#control:parallelAgent.modelSettings@14",
    }
    assert controls[
        "ts:agent.ts#control:sequentialAgent.modelSettings@7"
    ].attributes == {
        "analysis": "typescript-openai-agents-agent-model-settings",
        "module": "@openai/agents",
        "constructor": "Agent",
        "imported_symbol": "Agent",
        "configuration": "Agent.modelSettings",
        "settings_scope": "agent-model-settings",
        "source_agent": "Sequential tool agent",
        "source_agent_id": "ts:agent.ts#agent:sequentialAgent",
        "scope": "production",
        "parallel_tool_calls": False,
    }
    assert controls["ts:agent.ts#control:parallelAgent.modelSettings@14"].attributes == {
        "analysis": "typescript-openai-agents-agent-model-settings",
        "module": "@openai/agents",
        "constructor": "Agent",
        "imported_symbol": "Agent",
        "configuration": "Agent.modelSettings",
        "settings_scope": "agent-model-settings",
        "source_agent": "Parallel tool agent",
        "source_agent_id": "ts:agent.ts#agent:parallelAgent",
        "scope": "production",
        "parallel_tool_calls": True,
    }

    edges = {
        (
            relationship.source_name,
            relationship.source_id,
            relationship.target_id,
            relationship.evidence.path,
            relationship.evidence.line,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "model-settings-policy"
    }
    assert edges == {
        (
            "Sequential tool agent",
            "ts:agent.ts#agent:sequentialAgent",
            "ts:agent.ts#control:sequentialAgent.modelSettings@7",
            "agent.ts",
            7,
            (
                ("analysis", "typescript-openai-agents-agent-model-settings"),
                ("binding", "modelSettings"),
                ("configuration", "Agent-modelSettings"),
                ("parallel_tool_calls", False),
            ),
        ),
        (
            "Parallel tool agent",
            "ts:agent.ts#agent:parallelAgent",
            "ts:agent.ts#control:parallelAgent.modelSettings@14",
            "agent.ts",
            14,
            (
                ("analysis", "typescript-openai-agents-agent-model-settings"),
                ("binding", "modelSettings"),
                ("configuration", "Agent-modelSettings"),
                ("parallel_tool_calls", True),
            ),
        ),
    }


def test_typescript_openai_realtime_session_parallel_tool_calls_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_realtime_session_config")

    controls = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "control"
        and component.name == "realtime-session-config-policy"
    }
    assert set(controls) == {
        "ts:agent.ts#control:sequentialSession.config@17",
        "ts:agent.ts#control:parallelSession.config@23",
        "ts:agent.ts#control:reasoningSession.config@30",
        "ts:agent.ts#control:audioSession.config@37",
        "ts:agent.ts#control:audioDetailsSession.config@45",
        "ts:agent.ts#control:modelOnlySession.config@63",
        "ts:agent.ts#control:turnDetectionSession.config@71",
    }
    assert controls["ts:agent.ts#control:sequentialSession.config@17"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.config",
        "session_binding": "sequentialSession",
        "config_scope": "realtime-session-config",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "parallel_tool_calls": False,
        "scope": "production",
    }
    assert controls["ts:agent.ts#control:parallelSession.config@23"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.config",
        "session_binding": "parallelSession",
        "config_scope": "realtime-session-config",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "parallel_tool_calls": True,
        "scope": "production",
    }
    assert controls["ts:agent.ts#control:reasoningSession.config@30"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.config",
        "session_binding": "reasoningSession",
        "config_scope": "realtime-session-config",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "reasoning_effort": "low",
        "scope": "production",
    }
    assert controls["ts:agent.ts#control:audioSession.config@37"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.config",
        "session_binding": "audioSession",
        "config_scope": "realtime-session-config",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "output_modalities": ["audio"],
        "scope": "production",
    }
    assert controls["ts:agent.ts#control:audioDetailsSession.config@45"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.config",
        "session_binding": "audioDetailsSession",
        "config_scope": "realtime-session-config",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "session_model": "gpt-realtime-2.1",
        "session_model_resolution": "literal",
        "audio_input_format": "pcm16",
        "audio_output_format": "pcm16",
        "transcription_model": "gpt-live-transcribe",
        "transcription_delay": "low",
        "transcription_languages": ["en", "ja"],
        "transcription_prompt_literal": True,
        "transcription_prompt_length": 60,
        "transcription_keywords": ["OpenAI Agents SDK", "RealtimeSession"],
        "transcription_keyword_count": 2,
        "scope": "production",
    }
    assert controls["ts:agent.ts#control:modelOnlySession.config@63"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.config",
        "session_binding": "modelOnlySession",
        "config_scope": "realtime-session-config",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "session_model": "gpt-realtime-2.1",
        "session_model_resolution": "literal",
        "scope": "production",
    }
    assert controls["ts:agent.ts#control:turnDetectionSession.config@71"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.config",
        "session_binding": "turnDetectionSession",
        "config_scope": "realtime-session-config",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "turn_detection_type": "semantic_vad",
        "turn_detection_eagerness": "medium",
        "turn_detection_create_response": True,
        "turn_detection_interrupt_response": True,
        "scope": "production",
    }

    edges = {
        (
            relationship.source_name,
            relationship.source_id,
            relationship.target_id,
            relationship.evidence.path,
            relationship.evidence.line,
            tuple(
                sorted(
                    (
                        key,
                        tuple(value) if isinstance(value, list) else value,
                    )
                    for key, value in relationship.attributes.items()
                )
            ),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "realtime-session-config-policy"
    }
    assert edges == {
        (
            "Realtime greeter",
            "ts:agent.ts#agent:greeter",
            "ts:agent.ts#control:sequentialSession.config@17",
            "agent.ts",
            17,
            (
                ("analysis", "typescript-openai-agents-realtime-session-config"),
                ("binding", "config"),
                ("configuration", "RealtimeSession-config"),
                ("parallel_tool_calls", False),
                ("session_binding", "sequentialSession"),
            ),
        ),
        (
            "Realtime greeter",
            "ts:agent.ts#agent:greeter",
            "ts:agent.ts#control:parallelSession.config@23",
            "agent.ts",
            23,
            (
                ("analysis", "typescript-openai-agents-realtime-session-config"),
                ("binding", "config"),
                ("configuration", "RealtimeSession-config"),
                ("parallel_tool_calls", True),
                ("session_binding", "parallelSession"),
            ),
        ),
        (
            "Realtime greeter",
            "ts:agent.ts#agent:greeter",
            "ts:agent.ts#control:reasoningSession.config@30",
            "agent.ts",
            30,
            (
                ("analysis", "typescript-openai-agents-realtime-session-config"),
                ("binding", "config"),
                ("configuration", "RealtimeSession-config"),
                ("reasoning_effort", "low"),
                ("session_binding", "reasoningSession"),
            ),
        ),
        (
            "Realtime greeter",
            "ts:agent.ts#agent:greeter",
            "ts:agent.ts#control:audioSession.config@37",
            "agent.ts",
            37,
            (
                ("analysis", "typescript-openai-agents-realtime-session-config"),
                ("binding", "config"),
                ("configuration", "RealtimeSession-config"),
                ("output_modalities", ("audio",)),
                ("session_binding", "audioSession"),
            ),
        ),
        (
            "Realtime greeter",
            "ts:agent.ts#agent:greeter",
            "ts:agent.ts#control:audioDetailsSession.config@45",
            "agent.ts",
            45,
            (
                ("analysis", "typescript-openai-agents-realtime-session-config"),
                ("audio_input_format", "pcm16"),
                ("audio_output_format", "pcm16"),
                ("binding", "config"),
                ("configuration", "RealtimeSession-config"),
                ("session_binding", "audioDetailsSession"),
                ("session_model", "gpt-realtime-2.1"),
                ("session_model_resolution", "literal"),
                ("transcription_delay", "low"),
                ("transcription_keyword_count", 2),
                ("transcription_keywords", ("OpenAI Agents SDK", "RealtimeSession")),
                ("transcription_languages", ("en", "ja")),
                ("transcription_model", "gpt-live-transcribe"),
                ("transcription_prompt_length", 60),
                ("transcription_prompt_literal", True),
            ),
        ),
        (
            "Realtime greeter",
            "ts:agent.ts#agent:greeter",
            "ts:agent.ts#control:modelOnlySession.config@63",
            "agent.ts",
            63,
            (
                ("analysis", "typescript-openai-agents-realtime-session-config"),
                ("binding", "config"),
                ("configuration", "RealtimeSession-config"),
                ("session_binding", "modelOnlySession"),
                ("session_model", "gpt-realtime-2.1"),
                ("session_model_resolution", "literal"),
            ),
        ),
        (
            "Realtime greeter",
            "ts:agent.ts#agent:greeter",
            "ts:agent.ts#control:turnDetectionSession.config@71",
            "agent.ts",
            71,
            (
                ("analysis", "typescript-openai-agents-realtime-session-config"),
                ("binding", "config"),
                ("configuration", "RealtimeSession-config"),
                ("session_binding", "turnDetectionSession"),
                ("turn_detection_create_response", True),
                ("turn_detection_eagerness", "medium"),
                ("turn_detection_interrupt_response", True),
                ("turn_detection_type", "semantic_vad"),
            ),
        ),
    }


def test_typescript_openai_realtime_session_typed_options_spread_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_realtime_session_options_spread")

    controls = [
        component
        for component in ir.components
        if component.kind == "control"
        and component.name == "realtime-session-config-policy"
    ]
    assert [control.symbol_id for control in controls] == [
        "ts:agent.ts#control:spreadOptionsSession.config@14",
    ]
    assert controls[0].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.config",
        "session_binding": "spreadOptionsSession",
        "config_scope": "realtime-session-config",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "session_options_binding": "stableSessionOptions",
        "session_options_resolution": "typed-const-spread",
        "session_model": "gpt-realtime-2.1",
        "session_model_resolution": "literal",
        "turn_detection_type": "semantic_vad",
        "turn_detection_interrupt_response": True,
        "scope": "production",
    }

    edges = [
        relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "realtime-session-config-policy"
    ]
    assert len(edges) == 1
    assert edges[0].source_name == "Realtime greeter"
    assert edges[0].source_id == "ts:agent.ts#agent:greeter"
    assert edges[0].target_id == "ts:agent.ts#control:spreadOptionsSession.config@14"
    assert edges[0].evidence.path == "agent.ts"
    assert edges[0].evidence.line == 14
    assert edges[0].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-config",
        "configuration": "RealtimeSession-config",
        "binding": "config",
        "session_binding": "spreadOptionsSession",
        "session_options_binding": "stableSessionOptions",
        "session_options_resolution": "typed-const-spread",
        "session_model": "gpt-realtime-2.1",
        "session_model_resolution": "literal",
        "turn_detection_type": "semantic_vad",
        "turn_detection_interrupt_response": True,
    }


def test_typescript_openai_agent_guardrail_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_agent_guardrails")

    controls = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "control" and component.name == "agent-guardrail-policy"
    }
    assert set(controls) == {
        "ts:agent.ts#control:supportAgent.inputGuardrails@26",
        "ts:agent.ts#control:assistantAgent.outputGuardrails@40",
        "ts:agent.ts#control:mutableAgent.outputGuardrails@59",
        "ts:agent.ts#control:dynamicAgent.inputGuardrails@65",
        "ts:agent.ts#control:supportAgent.inputGuardrails@75",
        "ts:agent.ts#control:assistantAgent.outputGuardrails@84",
        "ts:agent.ts#control:supportAgent.inputGuardrails@87",
        "ts:agent.ts#control:throwingAgent.inputGuardrails@108",
    }
    assert controls["ts:agent.ts#control:supportAgent.inputGuardrails@26"].attributes == {
        "analysis": "typescript-openai-agents-agent-guardrails",
        "module": "@openai/agents",
        "constructor": "Agent",
        "imported_symbol": "Agent",
        "configuration": "Agent.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "agent-input",
        "source_agent": "Customer support agent",
        "source_agent_id": "ts:agent.ts#agent:supportAgent",
        "scope": "production",
        "guardrail_source": "inline-array",
        "guardrail_count": 2,
        "guardrail_bindings": ["typedInputGuardrail"],
        "guardrail_names": ["Math homework guardrail", "Inline abuse guardrail"],
        "guardrail_name_count": 2,
        "guardrail_tripwire_sources": ["literal-false", "literal-false"],
        "guardrail_tripwire_count": 2,
        "guardrail_literal_false_tripwire_count": 2,
    }
    assert controls["ts:agent.ts#control:assistantAgent.outputGuardrails@40"].attributes[
        "guardrail_names"
    ] == ["Phone number guardrail"]
    assert controls["ts:agent.ts#control:assistantAgent.outputGuardrails@40"].attributes[
        "guardrail_tripwire_sources"
    ] == ["literal-false"]
    assert controls["ts:agent.ts#control:assistantAgent.outputGuardrails@40"].attributes[
        "guardrail_kind"
    ] == "output"
    assert "guardrail_names" not in controls[
        "ts:agent.ts#control:mutableAgent.outputGuardrails@59"
    ].attributes
    assert "guardrail_tripwire_sources" not in controls[
        "ts:agent.ts#control:mutableAgent.outputGuardrails@59"
    ].attributes
    assert controls["ts:agent.ts#control:mutableAgent.outputGuardrails@59"].attributes[
        "guardrail_bindings"
    ] == ["mutableOutputGuardrail"]
    assert controls["ts:agent.ts#control:dynamicAgent.inputGuardrails@65"].attributes[
        "guardrail_source"
    ] == "binding"
    assert "guardrail_tripwire_sources" not in controls[
        "ts:agent.ts#control:dynamicAgent.inputGuardrails@65"
    ].attributes
    assert controls["ts:agent.ts#control:supportAgent.inputGuardrails@75"].attributes == {
        "analysis": "typescript-openai-agents-agent-guardrails",
        "module": "@openai/agents",
        "constructor": "Agent",
        "imported_symbol": "Agent",
        "configuration": "Agent.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "agent-input",
        "source_agent": "Customer support agent",
        "source_agent_id": "ts:agent.ts#agent:supportAgent",
        "scope": "production",
        "guardrail_source": "inline-array",
        "guardrail_count": 1,
        "guardrail_bindings": ["fallbackInputGuardrail"],
        "guardrail_names": ["Math homework fallback guardrail"],
        "guardrail_name_count": 1,
        "guardrail_update": "property-assignment",
        "guardrail_tripwire_sources": ["literal-false"],
        "guardrail_tripwire_count": 1,
        "guardrail_literal_false_tripwire_count": 1,
    }
    assert controls["ts:agent.ts#control:assistantAgent.outputGuardrails@84"].attributes[
        "guardrail_names"
    ] == ["Phone number fallback guardrail"]
    assert controls["ts:agent.ts#control:assistantAgent.outputGuardrails@84"].attributes[
        "guardrail_update"
    ] == "property-assignment"
    assert controls["ts:agent.ts#control:assistantAgent.outputGuardrails@84"].attributes[
        "guardrail_tripwire_sources"
    ] == ["literal-false"]
    assert controls["ts:agent.ts#control:supportAgent.inputGuardrails@87"].attributes == {
        "analysis": "typescript-openai-agents-agent-guardrails",
        "module": "@openai/agents",
        "constructor": "Agent",
        "imported_symbol": "Agent",
        "configuration": "Agent.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "agent-input",
        "source_agent": "Customer support agent",
        "source_agent_id": "ts:agent.ts#agent:supportAgent",
        "scope": "production",
        "guardrail_source": "binding",
        "guardrail_bindings": ["dynamicAssignedGuardrails"],
        "guardrail_update": "property-assignment",
    }
    assert controls["ts:agent.ts#control:throwingAgent.inputGuardrails@108"].attributes[
        "guardrail_execution_outcomes"
    ] == ["direct-throw"]
    assert controls["ts:agent.ts#control:throwingAgent.inputGuardrails@108"].attributes[
        "guardrail_direct_throw_count"
    ] == 1

    edges = {
        relationship.target_id: relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "agent-guardrail-policy"
    }
    assert set(edges) == set(controls)
    assert edges["ts:agent.ts#control:supportAgent.inputGuardrails@26"].attributes == {
        "analysis": "typescript-openai-agents-agent-guardrails",
        "configuration": "Agent.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "agent-input",
        "guardrail_source": "inline-array",
        "guardrail_count": 2,
        "guardrail_bindings": ["typedInputGuardrail"],
        "guardrail_names": ["Math homework guardrail", "Inline abuse guardrail"],
        "guardrail_name_count": 2,
        "guardrail_tripwire_sources": ["literal-false", "literal-false"],
        "guardrail_tripwire_count": 2,
        "guardrail_literal_false_tripwire_count": 2,
    }
    assert edges["ts:agent.ts#control:supportAgent.inputGuardrails@75"].attributes == {
        "analysis": "typescript-openai-agents-agent-guardrails",
        "configuration": "Agent.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "agent-input",
        "guardrail_source": "inline-array",
        "guardrail_count": 1,
        "guardrail_bindings": ["fallbackInputGuardrail"],
        "guardrail_names": ["Math homework fallback guardrail"],
        "guardrail_name_count": 1,
        "guardrail_update": "property-assignment",
        "guardrail_tripwire_sources": ["literal-false"],
        "guardrail_tripwire_count": 1,
        "guardrail_literal_false_tripwire_count": 1,
    }
    assert edges["ts:agent.ts#control:throwingAgent.inputGuardrails@108"].attributes[
        "guardrail_execution_outcomes"
    ] == ["direct-throw"]


def test_typescript_openai_tool_guardrail_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_tool_guardrails")

    controls = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "control" and component.name == "tool-guardrail-policy"
    }
    assert set(controls) == {
        "ts:agent.ts#control:classifyTool.inputGuardrails@44",
        "ts:agent.ts#control:classifyTool.outputGuardrails@45",
        "ts:agent.ts#control:dynamicTool.inputGuardrails@62",
        "ts:agent.ts#control:mutableTool.inputGuardrails@76",
    }
    assert controls["ts:agent.ts#control:classifyTool.inputGuardrails@44"].attributes == {
        "analysis": "typescript-openai-agents-tool-guardrails",
        "module": "@openai/agents",
        "constructor": "tool",
        "imported_symbol": "tool",
        "configuration": "tool.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "tool-input",
        "source_tool": "classifyTool",
        "source_tool_id": "ts:agent.ts#tool:classifyTool",
        "scope": "production",
        "guardrail_source": "inline-array",
        "guardrail_count": 1,
        "guardrail_bindings": ["blockSecrets"],
        "guardrail_names": ["block_secrets"],
        "guardrail_name_count": 1,
        "guardrail_actions": ["allow", "reject-content"],
        "guardrail_action_count": 2,
        "guardrail_reject_content": True,
        "guardrail_reject_condition_sources": ["string-includes"],
        "guardrail_reject_condition_count": 1,
        "guardrail_reject_condition_literals": ["sk-"],
        "guardrail_reject_condition_literal_count": 1,
    }
    assert controls["ts:agent.ts#control:classifyTool.outputGuardrails@45"].attributes[
        "guardrail_names"
    ] == ["redact_output", "inline_output_allow"]
    assert controls["ts:agent.ts#control:classifyTool.outputGuardrails@45"].attributes[
        "guardrail_count"
    ] == 2
    assert controls["ts:agent.ts#control:classifyTool.outputGuardrails@45"].attributes[
        "guardrail_reject_content"
    ] is True
    assert controls["ts:agent.ts#control:classifyTool.outputGuardrails@45"].attributes[
        "guardrail_reject_condition_sources"
    ] == ["string-includes"]
    assert controls["ts:agent.ts#control:classifyTool.outputGuardrails@45"].attributes[
        "guardrail_reject_condition_literals"
    ] == ["sk-"]
    assert controls["ts:agent.ts#control:dynamicTool.inputGuardrails@62"].attributes == {
        "analysis": "typescript-openai-agents-tool-guardrails",
        "module": "@openai/agents",
        "constructor": "tool",
        "imported_symbol": "tool",
        "configuration": "tool.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "tool-input",
        "source_tool": "dynamicTool",
        "source_tool_id": "ts:agent.ts#tool:dynamicTool",
        "scope": "production",
        "guardrail_source": "binding",
        "guardrail_bindings": ["dynamicGuardrails"],
    }
    assert "guardrail_names" not in controls[
        "ts:agent.ts#control:mutableTool.inputGuardrails@76"
    ].attributes
    assert controls["ts:agent.ts#control:mutableTool.inputGuardrails@76"].attributes[
        "guardrail_bindings"
    ] == ["mutableGuardrail"]
    assert "guardrail_reject_condition_sources" not in controls[
        "ts:agent.ts#control:mutableTool.inputGuardrails@76"
    ].attributes

    edges = {
        relationship.target_id: relationship
        for relationship in ir.relationships
        if relationship.source_kind == "tool"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "tool-guardrail-policy"
    }
    assert set(edges) == set(controls)
    assert edges["ts:agent.ts#control:classifyTool.inputGuardrails@44"].source_id == (
        "ts:agent.ts#tool:classifyTool"
    )
    assert edges["ts:agent.ts#control:classifyTool.inputGuardrails@44"].attributes == {
        "analysis": "typescript-openai-agents-tool-guardrails",
        "configuration": "tool.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "tool-input",
        "guardrail_source": "inline-array",
        "guardrail_count": 1,
        "guardrail_bindings": ["blockSecrets"],
        "guardrail_names": ["block_secrets"],
        "guardrail_name_count": 1,
        "guardrail_actions": ["allow", "reject-content"],
        "guardrail_action_count": 2,
        "guardrail_reject_content": True,
        "guardrail_reject_condition_sources": ["string-includes"],
        "guardrail_reject_condition_count": 1,
        "guardrail_reject_condition_literals": ["sk-"],
        "guardrail_reject_condition_literal_count": 1,
    }

    agent_edges = {
        relationship.target_id: relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "tool-guardrail-policy"
    }
    assert set(agent_edges) == set(controls)
    assert agent_edges["ts:agent.ts#control:classifyTool.inputGuardrails@44"].source_id == (
        "ts:agent.ts#agent:agent"
    )
    assert agent_edges["ts:agent.ts#control:classifyTool.inputGuardrails@44"].attributes == {
        "analysis": "typescript-openai-agents-tool-guardrails",
        "configuration": "Agent.tools.toolGuardrails",
        "tool_configuration": "tool.inputGuardrails",
        "guardrail_kind": "input",
        "guardrail_scope": "tool-input",
        "via_tool": "classifyTool",
        "via_tool_id": "ts:agent.ts#tool:classifyTool",
        "guardrail_source": "inline-array",
        "guardrail_count": 1,
        "guardrail_bindings": ["blockSecrets"],
        "guardrail_names": ["block_secrets"],
        "guardrail_name_count": 1,
        "guardrail_actions": ["allow", "reject-content"],
        "guardrail_action_count": 2,
        "guardrail_reject_content": True,
        "guardrail_reject_condition_sources": ["string-includes"],
        "guardrail_reject_condition_count": 1,
        "guardrail_reject_condition_literals": ["sk-"],
        "guardrail_reject_condition_literal_count": 1,
    }


def test_typescript_openai_agent_clone_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_agent_clone")

    agents = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "agent"
    }
    assert agents["ts:agent.ts#agent:copiedAgent"].attributes == {
        "constructor": "Agent.clone",
        "module": "@openai/agents",
        "imported_symbol": "Agent",
        "configuration": "Agent.clone",
        "clone_source_binding": "baseAgent",
        "clone_source_agent": "Base reviewer",
        "clone_source_agent_id": "ts:agent.ts#agent:baseAgent",
        "scope": "production",
        "clone_omitted_list_properties": [
            "tools",
            "handoffs",
            "mcpServers",
            "inputGuardrails",
            "outputGuardrails",
        ],
        "clone_omitted_list_policy": "shared-from-source-agent",
    }
    assert agents["ts:agent.ts#agent:isolatedAgent"].attributes[
        "clone_list_overrides"
    ] == ["tools"]
    assert agents["ts:agent.ts#agent:isolatedAgent"].attributes[
        "clone_omitted_list_properties"
    ] == ["handoffs", "mcpServers", "inputGuardrails", "outputGuardrails"]
    assert "ts:agent.ts#agent:dynamicClone" not in agents
    assert "ts:agent.ts#agent:reboundClone" not in agents

    clone_edges = {
        relationship.source_id: relationship
        for relationship in ir.relationships
        if relationship.relation == "derived-from"
        and relationship.source_kind == "agent"
        and relationship.target_kind == "agent"
    }
    assert set(clone_edges) == {
        "ts:agent.ts#agent:copiedAgent",
        "ts:agent.ts#agent:isolatedAgent",
    }
    assert clone_edges["ts:agent.ts#agent:copiedAgent"].target_id == (
        "ts:agent.ts#agent:baseAgent"
    )
    assert clone_edges["ts:agent.ts#agent:copiedAgent"].attributes == {
        "analysis": "typescript-openai-agents-agent-clone",
        "configuration": "Agent.clone",
        "clone_source_binding": "baseAgent",
        "clone_omitted_list_properties": [
            "tools",
            "handoffs",
            "mcpServers",
            "inputGuardrails",
            "outputGuardrails",
        ],
        "clone_omitted_list_policy": "shared-from-source-agent",
    }


def test_typescript_openai_imported_agent_clone_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_imported_agent_clone")

    agents = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "agent"
    }
    assert agents["ts:manager.ts#agent:importedClone"].attributes == {
        "constructor": "Agent.clone",
        "module": "@openai/agents",
        "imported_symbol": "Agent",
        "configuration": "Agent.clone",
        "clone_source_binding": "writerAgent",
        "clone_source_agent": "Imported writer",
        "clone_source_agent_id": "ts:agents.ts#agent:writerAgent",
        "scope": "production",
        "clone_list_overrides": ["tools"],
        "clone_omitted_list_properties": [
            "handoffs",
            "mcpServers",
            "inputGuardrails",
            "outputGuardrails",
        ],
        "clone_omitted_list_policy": "shared-from-source-agent",
    }
    assert "ts:manager.ts#agent:fakeClone" not in agents

    clone_edges = [
        relationship
        for relationship in ir.relationships
        if relationship.relation == "derived-from"
        and relationship.source_kind == "agent"
        and relationship.target_kind == "agent"
    ]
    assert len(clone_edges) == 1
    assert clone_edges[0].source_id == "ts:manager.ts#agent:importedClone"
    assert clone_edges[0].target_id == "ts:agents.ts#agent:writerAgent"
    assert clone_edges[0].attributes == {
        "analysis": "typescript-openai-agents-agent-clone",
        "configuration": "Agent.clone",
        "clone_source_binding": "writerAgent",
        "clone_list_overrides": ["tools"],
        "clone_omitted_list_properties": [
            "handoffs",
            "mcpServers",
            "inputGuardrails",
            "outputGuardrails",
        ],
        "clone_omitted_list_policy": "shared-from-source-agent",
    }


def test_typescript_openai_hosted_mcp_approval_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_hosted_mcp_approval")

    tools = {
        component.name: component
        for component in ir.components
        if component.kind == "tool"
    }
    assert tools["hostedMcpTool@27"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_policy": "disabled-default",
        "mcp_approval_handler": "none",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@31"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_policy": "disabled-explicit",
        "mcp_approval_requirement": "never",
        "mcp_approval_handler": "agent-loop",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@36"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_policy": "selective",
        "mcp_approval_never_tool_names": ["read_wiki_structure"],
        "mcp_approval_never_read_only": True,
        "mcp_approval_always_tool_names": ["ask_question"],
        "mcp_approval_handler": "configured",
        "mcp_approval_handler_policy": "callback-controlled",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@45"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_binding": "stablePolicy",
        "mcp_approval_resolution": "same-file-const-object",
        "mcp_approval_policy": "selective",
        "mcp_approval_never_tool_names": ["list_pages"],
        "mcp_approval_never_read_only": True,
        "mcp_approval_always_tool_names": ["write_page"],
        "mcp_approval_handler": "agent-loop",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@50"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_policy": "dynamic",
        "mcp_approval_binding": "mutatedPolicy",
        "mcp_approval_handler": "agent-loop",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@55"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_binding": "importedPolicy",
        "mcp_approval_resolution": "imported-local-const-object",
        "mcp_approval_policy": "selective",
        "mcp_approval_never_tool_names": ["read_imported"],
        "mcp_approval_never_read_only": True,
        "mcp_approval_always_tool_names": ["write_imported"],
        "mcp_approval_handler": "agent-loop",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@60"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_binding": "importedAliasedPolicy",
        "mcp_approval_resolution": "imported-local-const-object",
        "mcp_approval_policy": "selective",
        "mcp_approval_never_tool_names": ["list_imported"],
        "mcp_approval_always_tool_names": ["delete_imported"],
        "mcp_approval_handler": "agent-loop",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@65"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_policy": "dynamic",
        "mcp_approval_binding": "mutatedExport",
        "mcp_approval_handler": "agent-loop",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@70"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_binding": "reexportedPolicy",
        "mcp_approval_resolution": "reexported-local-const-object",
        "mcp_approval_policy": "selective",
        "mcp_approval_never_tool_names": ["read_imported"],
        "mcp_approval_never_read_only": True,
        "mcp_approval_always_tool_names": ["write_imported"],
        "mcp_approval_handler": "agent-loop",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert tools["hostedMcpTool@75"].attributes == {
        "constructor": "hostedMcpTool",
        "approval_policy": "not-applicable",
        "approval_handler": "not-applicable",
        "mcp_approval_policy": "dynamic",
        "mcp_approval_binding": "reexportedMutatedPolicy",
        "mcp_approval_handler": "agent-loop",
        "execution_environment": "unresolved",
        "scope": "production",
    }
    assert "fakeHostedMcpTool@80" not in tools

    capability_by_line = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "capability" and component.name == "mcp-access"
    }
    assert capability_by_line[27].attributes["mcp_approval_policy"] == "disabled-default"
    assert capability_by_line[31].attributes["mcp_approval_requirement"] == "never"
    assert capability_by_line[36].attributes["mcp_approval_always_tool_names"] == [
        "ask_question"
    ]
    assert capability_by_line[45].attributes["mcp_approval_resolution"] == (
        "same-file-const-object"
    )
    assert capability_by_line[50].attributes["mcp_approval_policy"] == "dynamic"
    assert capability_by_line[55].attributes["mcp_approval_resolution"] == (
        "imported-local-const-object"
    )
    assert capability_by_line[60].attributes["mcp_approval_always_tool_names"] == [
        "delete_imported"
    ]
    assert capability_by_line[65].attributes["mcp_approval_policy"] == "dynamic"
    assert capability_by_line[70].attributes["mcp_approval_resolution"] == (
        "reexported-local-const-object"
    )
    assert capability_by_line[75].attributes["mcp_approval_policy"] == "dynamic"


def test_typescript_openai_realtime_session_guardrail_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_realtime_session_guardrails")

    controls = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "control"
        and component.name == "realtime-session-guardrail-policy"
    }
    assert set(controls) == {
        "ts:agent.ts#control:guardedSession.guardrails@34",
        "ts:agent.ts#control:inlineSession.guardrails@38",
        "ts:agent.ts#control:spreadOptionsSession.guardrails@27",
        "ts:agent.ts#control:mutableSession.guardrails@71",
        "ts:agent.ts#control:dynamicSettingsSession.guardrails@76",
    }
    assert controls["ts:agent.ts#control:guardedSession.guardrails@34"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-guardrails",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.outputGuardrails",
        "session_binding": "guardedSession",
        "guardrail_scope": "realtime-session-output",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "scope": "production",
        "guardrail_source": "typed-const-array-binding",
        "guardrail_binding": "namedGuardrails",
        "guardrail_count": 1,
        "guardrail_names": ["No mention of Dom"],
        "guardrail_name_count": 1,
        "guardrail_tripwire_sources": ["dynamic-expression"],
        "guardrail_tripwire_count": 1,
        "guardrail_dynamic_tripwire_count": 1,
    }
    assert controls["ts:agent.ts#control:inlineSession.guardrails@38"].attributes[
        "guardrail_source"
    ] == "inline-array"
    assert controls["ts:agent.ts#control:inlineSession.guardrails@38"].attributes[
        "guardrail_names"
    ] == ["No payment advice"]
    assert controls["ts:agent.ts#control:inlineSession.guardrails@38"].attributes[
        "debounce_text_length"
    ] == -1
    assert controls["ts:agent.ts#control:inlineSession.guardrails@38"].attributes[
        "guardrail_tripwire_sources"
    ] == ["dynamic-expression"]
    assert controls["ts:agent.ts#control:spreadOptionsSession.guardrails@27"].attributes[
        "session_options_binding"
    ] == "typedOptions"
    assert controls["ts:agent.ts#control:spreadOptionsSession.guardrails@27"].attributes[
        "session_options_resolution"
    ] == "typed-const-spread"
    assert controls["ts:agent.ts#control:spreadOptionsSession.guardrails@27"].attributes[
        "debounce_text_length"
    ] == 500
    assert controls["ts:agent.ts#control:mutableSession.guardrails@71"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-guardrails",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.outputGuardrails",
        "session_binding": "mutableSession",
        "guardrail_scope": "realtime-session-output",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "scope": "production",
        "guardrail_source": "binding",
        "guardrail_binding": "mutableGuardrails",
    }
    assert "guardrail_tripwire_sources" not in controls[
        "ts:agent.ts#control:mutableSession.guardrails@71"
    ].attributes
    assert "debounce_text_length" not in controls[
        "ts:agent.ts#control:dynamicSettingsSession.guardrails@76"
    ].attributes

    edges = {
        relationship.target_id: relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "realtime-session-guardrail-policy"
    }
    assert set(edges) == set(controls)
    assert all(edge.source_id == "ts:agent.ts#agent:greeter" for edge in edges.values())
    assert edges["ts:agent.ts#control:spreadOptionsSession.guardrails@27"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-guardrails",
        "configuration": "RealtimeSession.outputGuardrails",
        "session_binding": "spreadOptionsSession",
        "guardrail_scope": "realtime-session-output",
        "session_options_binding": "typedOptions",
        "session_options_resolution": "typed-const-spread",
        "guardrail_source": "typed-const-array-binding",
        "guardrail_binding": "namedGuardrails",
        "guardrail_count": 1,
        "guardrail_names": ["No mention of Dom"],
        "guardrail_name_count": 1,
        "guardrail_tripwire_sources": ["dynamic-expression"],
        "guardrail_tripwire_count": 1,
        "guardrail_dynamic_tripwire_count": 1,
        "output_guardrail_settings_present": True,
        "debounce_text_length": 500,
    }


def test_typescript_openai_realtime_session_auth_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_realtime_session_auth")

    controls = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "control"
        and component.name == "realtime-session-auth-policy"
    }
    assert set(controls) == {
        "ts:agent.ts#control:defaultSession.connect.apiKey@14",
        "ts:agent.ts#control:ephemeralSession.connect.apiKey@18",
        "ts:agent.ts#control:websocketSession.connect.apiKey@24",
        "ts:agent.ts#control:sipSession.connect.apiKey@30",
        "ts:agent.ts#control:browserSession.connect.apiKey@38",
        "ts:agent.ts#control:unresolvedSession.connect.apiKey@48",
    }
    assert controls["ts:agent.ts#control:defaultSession.connect.apiKey@14"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-auth",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.connect.apiKey",
        "session_binding": "defaultSession",
        "auth_scope": "realtime-session-connect",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "scope": "production",
        "api_key_source": "literal-placeholder",
        "api_key_resolution": "immutable-module-literal-binding",
        "api_key_value_redacted": True,
    }
    assert controls["ts:agent.ts#control:ephemeralSession.connect.apiKey@18"].attributes[
        "api_key_kind"
    ] == "ephemeral-client-secret"
    assert controls["ts:agent.ts#control:ephemeralSession.connect.apiKey@18"].attributes[
        "api_key_prefix"
    ] == "ek_"
    assert controls["ts:agent.ts#control:websocketSession.connect.apiKey@24"].attributes[
        "api_key_environment"
    ] == "OPENAI_API_KEY"
    assert controls["ts:agent.ts#control:websocketSession.connect.apiKey@24"].attributes[
        "session_transport"
    ] == "websocket"
    assert controls["ts:agent.ts#control:sipSession.connect.apiKey@30"].attributes[
        "session_transport_constructor"
    ] == "OpenAIRealtimeSIP"
    assert controls["ts:agent.ts#control:browserSession.connect.apiKey@38"].attributes[
        "api_key_source"
    ] == "fetch-json-binding"
    assert controls["ts:agent.ts#control:browserSession.connect.apiKey@38"].attributes[
        "api_key_endpoint_scope"
    ] == "relative"
    assert controls["ts:agent.ts#control:unresolvedSession.connect.apiKey@48"].attributes[
        "api_key_source"
    ] == "dynamic-binding"
    assert not any(
        component.evidence.line == 43
        for component in controls.values()
    )

    edges = {
        relationship.target_id: relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "realtime-session-auth-policy"
    }
    assert set(edges) == set(controls)
    assert all(edge.source_id == "ts:agent.ts#agent:greeter" for edge in edges.values())
    assert edges["ts:agent.ts#control:browserSession.connect.apiKey@38"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-auth",
        "configuration": "RealtimeSession.connect.apiKey",
        "session_binding": "browserSession",
        "api_key_source": "fetch-json-binding",
        "api_key_kind": "ephemeral-client-secret",
        "api_key_binding": "apiKey",
        "api_key_endpoint": "/path/to/ephemeral/key/generation",
        "api_key_endpoint_scope": "relative",
    }


def test_typescript_openai_realtime_tool_approval_event_decisions_are_exact() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_realtime_tool_approval_event")

    controls = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "control" and component.name == "approval-decision"
    }
    assert set(controls) == {
        "ts:agent.ts#control:session.approve@12",
        "ts:agent.ts#control:session.reject@13",
    }
    assert controls["ts:agent.ts#control:session.approve@12"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-approval-decision",
        "module": "@openai/agents/realtime",
        "constructor": "RealtimeSession",
        "imported_symbol": "RealtimeSession",
        "local_constructor": "RealtimeSession",
        "configuration": "RealtimeSession.approve",
        "session_binding": "session",
        "event": "tool_approval_requested",
        "request_binding": "request",
        "approval_item_resolution": "event-request-approvalItem",
        "decision": "approve",
        "source_agent": "Realtime greeter",
        "source_agent_id": "ts:agent.ts#agent:greeter",
        "state_scope": "openai-realtime-session-tool-approval-decision",
        "scope": "production",
    }
    assert controls["ts:agent.ts#control:session.reject@13"].attributes["decision"] == "reject"
    assert controls["ts:agent.ts#control:session.reject@13"].attributes["configuration"] == (
        "RealtimeSession.reject"
    )

    edges = {
        relationship.target_id: relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "approval-decision"
    }
    assert set(edges) == {
        "ts:agent.ts#control:session.approve@12",
        "ts:agent.ts#control:session.reject@13",
    }
    assert edges["ts:agent.ts#control:session.approve@12"].source_name == "Realtime greeter"
    assert edges["ts:agent.ts#control:session.approve@12"].source_id == (
        "ts:agent.ts#agent:greeter"
    )
    assert edges["ts:agent.ts#control:session.approve@12"].attributes == {
        "analysis": "typescript-openai-agents-realtime-session-approval-decision",
        "configuration": "RealtimeSession.approve",
        "session_binding": "session",
        "event": "tool_approval_requested",
        "request_binding": "request",
        "approval_item_resolution": "event-request-approvalItem",
        "decision": "approve",
    }


def test_typescript_openai_computer_safety_check_auto_acknowledgement() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_computer_safety")

    tools = {component.name: component for component in ir.components if component.kind == "tool"}
    assert tools["browser"].attributes["safety_check_policy"] == "auto-acknowledge-all"
    assert tools["browser"].attributes["safety_check_decision"] == "returns-pendingSafetyChecks"
    assert tools["browser"].attributes["computer_provider"] == "inline-object"
    assert tools["browser"].attributes["computer_lifecycle"] == "inline-static"
    assert (
        tools["browser"].attributes["safety_check_acknowledgement_field"]
        == "acknowledgedSafetyChecks"
    )
    assert tools["blindBrowser"].attributes["safety_check_policy"] == "auto-acknowledge-all"
    assert tools["blindBrowser"].attributes["safety_check_decision"] == "return-true"
    assert tools["reviewedBrowser"].attributes["safety_check_handler"] == "configured"
    assert tools["reviewedBrowser"].attributes["safety_check_policy"] == "unresolved"
    assert tools["snakeCaseBrowser"].attributes["safety_check_policy"] == "auto-acknowledge-all"
    assert (
        tools["snakeCaseBrowser"].attributes["safety_check_acknowledgement_field"]
        == "acknowledged_safety_checks"
    )
    assert tools["expressionBrowser"].attributes["safety_check_policy"] == "auto-acknowledge-all"
    assert (
        tools["expressionBrowser"].attributes["safety_check_acknowledgement_field"]
        == "acknowledgedSafetyChecks"
    )
    assert tools["perRequestBrowser"].attributes["computer_provider"] == "factory-object"
    assert tools["perRequestBrowser"].attributes["computer_lifecycle"] == "create-dispose-per-run"
    assert tools["perRequestBrowser"].attributes["computer_create_handler"] == "configured"
    assert tools["perRequestBrowser"].attributes["computer_dispose_handler"] == "configured"
    assert tools["perRequestBrowser"].attributes["computer_create_receives_run_context"] is True
    assert tools["perRequestBrowser"].attributes["computer_dispose_receives_run_context"] is True
    assert tools["perRequestBrowser"].attributes["computer_dispose_receives_computer"] is True
    assert tools["leakyFactoryBrowser"].attributes["computer_provider"] == "factory-object"
    assert tools["leakyFactoryBrowser"].attributes["computer_lifecycle"] == "factory-without-dispose"
    assert tools["leakyFactoryBrowser"].attributes["computer_create_handler"] == "configured"
    assert tools["leakyFactoryBrowser"].attributes["computer_dispose_handler"] == "missing"

    computer_capabilities = [
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "computer-control"
    ]
    assert any(
        capability.attributes.get("computer_lifecycle") == "create-dispose-per-run"
        and capability.attributes.get("computer_dispose_receives_computer") is True
        for capability in computer_capabilities
    )
    assert any(
        capability.attributes.get("computer_lifecycle") == "factory-without-dispose"
        and capability.attributes.get("computer_dispose_handler") == "missing"
        for capability in computer_capabilities
    )

    findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL011"]
    assert [(finding.evidence.line, finding.analysis["tool"]) for finding in findings] == [
        (3, "browser"),
        (11, "blindBrowser"),
        (23, "snakeCaseBrowser"),
        (30, "expressionBrowser"),
    ]
    assert {finding.analysis["safety_check_policy"] for finding in findings} == {
        "auto-acknowledge-all"
    }
    assert all(
        finding.ir_path[-2:] == (f"tool:{finding.analysis['tool']}", "capability:computer-control")
        for finding in findings
    )


def test_repeated_typescript_agent_bindings_get_occurrence_qualified_ids(tmp_path: Path) -> None:
    (tmp_path / "agent.ts").write_text(
        """import { Agent, tool } from "@openai/agents";
function first() {
  const repeatedTool = tool({ name: "first" });
  const agent = new Agent({ name: "shared", tools: [repeatedTool] });
  return agent;
}
function second() {
  const repeatedTool = tool({ name: "second" });
  const agent = new Agent({ name: "shared", tools: [repeatedTool] });
  return agent;
}
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)
    agents = [component for component in ir.components if component.kind == "agent"]
    edges = [edge for edge in ir.relationships if edge.source_kind == "agent"]
    assert {component.symbol_id for component in agents} == {
        "ts:agent.ts#agent:agent@4",
        "ts:agent.ts#agent:agent@9",
    }
    assert {edge.source_id for edge in edges} == {component.symbol_id for component in agents}
    assert all(edge.target_id is None for edge in edges)
    assert all(edge.attributes["target_identity"] == "ambiguous-repeated-binding" for edge in edges)
    bom = json.loads(render_bom(ir))
    assert all(
        relationship["source"]["resolution"] == "symbol-id" for relationship in bom["relationships"]
    )


def test_typescript_builtin_options_variable_stays_unresolved(tmp_path: Path) -> None:
    (tmp_path / "agent.ts").write_text(
        """import { Agent, applyPatchTool, shellTool } from "@openai/agents";
const options = loadPolicyAtRuntime();
const agent = new Agent({ name: "operator", tools: [shellTool(options), applyPatchTool(options)] });
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    tools = [component for component in ir.components if component.kind == "tool"]
    assert len(tools) == 2
    assert all(tool.attributes["approval_policy"] == "unresolved" for tool in tools)
    assert all(tool.attributes["execution_environment"] == "unresolved" for tool in tools)
    assert not ir.findings


def test_typescript_openai_sandbox_agent_capabilities_require_exact_import() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_sandbox_agent")

    agents = {
        (component.evidence.path, component.evidence.line, component.name): component
        for component in ir.components
        if component.kind == "agent"
    }
    assert set(agents) == {
        ("capability-negative.ts", 12, "Capability Shadow Sandbox"),
        ("positive.ts", 9, "Local Sandbox Assistant"),
        ("positive.ts", 15, "Aliased Sandbox Assistant"),
        ("positive.ts", 23, "buildReturnedSandboxAgent"),
        ("positive.ts", 30, "Returned Named Sandbox Assistant"),
        ("positive.ts", 53, "Memory Layout Sandbox"),
        ("positive.ts", 74, "Memory Generation Sandbox"),
    }
    assert all(
        component.attributes["constructor"] == "SandboxAgent"
        and component.attributes["module"] == "@openai/agents/sandbox"
        and component.attributes["resolution"] == "exact-openai-sandbox-import"
        and component.attributes["execution_environment"] == "sdk-sandbox"
        for component in agents.values()
    )
    assert (
        agents[("positive.ts", 15, "Aliased Sandbox Assistant")].attributes["local_constructor"]
        == "AliasedSandboxAgent"
    )
    assert (
        agents[("positive.ts", 23, "buildReturnedSandboxAgent")].attributes["binding"]
        == "return-new"
    )
    assert (
        agents[("positive.ts", 23, "buildReturnedSandboxAgent")].attributes["helper"]
        == "buildReturnedSandboxAgent"
    )
    assert (
        agents[("positive.ts", 30, "Returned Named Sandbox Assistant")].attributes[
            "local_constructor"
        ]
        == "AliasedSandboxAgent"
    )
    assert (
        agents[("positive.ts", 30, "Returned Named Sandbox Assistant")].attributes["binding"]
        == "return-new"
    )

    tools = {
        (component.evidence.path, component.evidence.line, component.name): component
        for component in ir.components
        if component.kind == "tool"
    }
    assert set(tools) == {
        ("memory-policy-negative.ts", 8, "dynamicMemory"),
        ("positive.ts", 12, "filesystem@12"),
        ("positive.ts", 12, "shell@12"),
        ("positive.ts", 12, "skills@12"),
        ("positive.ts", 18, "shell@18"),
        ("positive.ts", 25, "memory@25"),
        ("positive.ts", 25, "shell@25"),
        ("positive.ts", 32, "shell@32"),
        ("positive.ts", 56, "memory@56"),
        ("positive.ts", 65, "generatedMemory"),
    }
    assert all(
        component.attributes["constructor"] == "shell"
        and component.attributes["execution_environment"] == "sdk-sandbox"
        and component.attributes["sandbox_policy"] == "openai-agents-sdk-sandbox"
        and component.attributes["approval_policy"] == "not-applicable"
        for key, component in tools.items()
        if key[2].startswith("shell@")
    )
    assert (
        tools[("positive.ts", 12, "filesystem@12")].attributes["execution_environment"]
        == "sdk-sandbox"
    )
    assert (
        tools[("positive.ts", 12, "filesystem@12")].attributes["sandbox_policy"]
        == "openai-agents-sdk-sandbox"
    )
    assert (
        tools[("positive.ts", 25, "memory@25")].attributes["execution_environment"] == "sdk-sandbox"
    )
    assert (
        tools[("positive.ts", 25, "memory@25")].attributes["sandbox_policy"]
        == "openai-agents-sdk-sandbox"
    )
    assert (
        tools[("positive.ts", 12, "skills@12")].attributes["execution_environment"] == "sdk-sandbox"
    )
    assert (
        tools[("positive.ts", 12, "skills@12")].attributes["sandbox_policy"]
        == "openai-agents-sdk-sandbox"
    )

    capabilities = {
        (
            component.evidence.path,
            component.evidence.line,
            component.name,
            component.attributes["builtin_tool"],
        )
        for component in ir.components
        if component.kind == "capability"
    }
    assert (
        "positive.ts",
        12,
        "filesystem",
        "filesystem",
    ) in capabilities
    assert (
        "positive.ts",
        25,
        "memory",
        "memory",
    ) in capabilities
    assert (
        "positive.ts",
        56,
        "memory",
        "memory",
    ) in capabilities
    assert (
        "positive.ts",
        65,
        "memory",
        "memory",
    ) in capabilities
    assert (
        "positive.ts",
        12,
        "skill-loading",
        "skills",
    ) in capabilities
    assert all(
        component.attributes.get("execution_environment") == "sdk-sandbox"
        and component.attributes.get("sandbox_policy") == "openai-agents-sdk-sandbox"
        for component in ir.components
        if component.kind == "capability"
        and component.attributes.get("builtin_tool") in {"filesystem", "memory", "shell", "skills"}
    )

    assert {
        (edge.source_name, edge.relation, edge.target_kind, edge.target_name, edge.target_id)
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.evidence.path == "positive.ts"
    } == {
        (
            "Local Sandbox Assistant",
            "uses",
            "tool",
            "filesystem@12",
            "ts:positive.ts#tool:filesystem@12",
        ),
        (
            "Local Sandbox Assistant",
            "uses",
            "tool",
            "skills@12",
            "ts:positive.ts#tool:skills@12",
        ),
        (
            "Local Sandbox Assistant",
            "uses",
            "tool",
            "shell@12",
            "ts:positive.ts#tool:shell@12",
        ),
        (
            "Aliased Sandbox Assistant",
            "uses",
            "tool",
            "shell@18",
            "ts:positive.ts#tool:shell@18",
        ),
        (
            "buildReturnedSandboxAgent",
            "uses",
            "tool",
            "memory@25",
            "ts:positive.ts#tool:memory@25",
        ),
        (
            "buildReturnedSandboxAgent",
            "uses",
            "tool",
            "shell@25",
            "ts:positive.ts#tool:shell@25",
        ),
        (
            "Returned Named Sandbox Assistant",
            "uses",
            "tool",
            "shell@32",
            "ts:positive.ts#tool:shell@32",
        ),
        (
            "Memory Layout Sandbox",
            "uses",
            "tool",
            "memory@56",
            "ts:positive.ts#tool:memory@56",
        ),
        (
            "Memory Generation Sandbox",
            "uses",
            "tool",
            "generatedMemory",
            "ts:positive.ts#tool:generatedMemory",
        ),
    }
    memory_policies = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-memory-policy"
    }
    assert set(memory_policies) == {
        (
            "positive.ts",
            25,
            "ts:positive.ts#control:memory@25.memoryPolicy@25",
        ),
        (
            "positive.ts",
            57,
            "ts:positive.ts#control:memory@56.memoryPolicy@57",
        ),
        (
            "positive.ts",
            66,
            "ts:positive.ts#control:generatedMemory.memoryPolicy@66",
        ),
    }
    assert memory_policies[
        (
            "positive.ts",
            25,
            "ts:positive.ts#control:memory@25.memoryPolicy@25",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-memory-config",
        "module": "@openai/agents/sandbox",
        "constructor": "memory",
        "imported_symbol": "memory",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "memory",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "generation_enabled": False,
        "scope": "production",
    }
    assert memory_policies[
        (
            "positive.ts",
            57,
            "ts:positive.ts#control:memory@56.memoryPolicy@57",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-memory-config",
        "module": "@openai/agents/sandbox",
        "constructor": "memory",
        "imported_symbol": "memory",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "memory",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "memories_dir": "memories/engineering",
        "memories_dir_resolution": "immutable-module-literal-binding",
        "sessions_dir": "sessions/engineering",
        "sessions_dir_resolution": "literal",
        "scope": "production",
    }
    assert memory_policies[
        (
            "positive.ts",
            66,
            "ts:positive.ts#control:generatedMemory.memoryPolicy@66",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-memory-config",
        "module": "@openai/agents/sandbox",
        "constructor": "memory",
        "imported_symbol": "memory",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "memory",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "read_enabled": False,
        "generation_configured": True,
        "max_raw_memories_for_consolidation": 128,
        "phase_one_model": "gpt-5.4-mini",
        "phase_one_model_resolution": "literal",
        "phase_two_model": "gpt-5.4",
        "phase_two_model_resolution": "literal",
        "extra_prompt": "Remember exact verification commands.",
        "extra_prompt_resolution": "literal",
        "scope": "production",
    }
    assert [
        (
            relationship.source_id,
            relationship.target_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.attributes,
        )
        for relationship in ir.relationships
        if relationship.source_kind == "tool"
        and relationship.source_name in {"memory@25", "memory@56", "generatedMemory"}
        and relationship.target_name == "sandbox-memory-policy"
    ] == [
        (
            "ts:positive.ts#tool:memory@25",
            "ts:positive.ts#control:memory@25.memoryPolicy@25",
            "positive.ts",
            25,
            {
                "analysis": "typescript-openai-sandbox-memory-config",
                "configuration": "memory",
            },
        ),
        (
            "ts:positive.ts#tool:memory@56",
            "ts:positive.ts#control:memory@56.memoryPolicy@57",
            "positive.ts",
            57,
            {
                "analysis": "typescript-openai-sandbox-memory-config",
                "configuration": "memory",
            },
        ),
        (
            "ts:positive.ts#tool:generatedMemory",
            "ts:positive.ts#control:generatedMemory.memoryPolicy@66",
            "positive.ts",
            66,
            {
                "analysis": "typescript-openai-sandbox-memory-config",
                "configuration": "memory",
            },
        ),
    ]
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind in {"agent", "tool", "capability"}
        for component in ir.components
    )
    assert not any(
        component.evidence.path == "capability-negative.ts"
        and component.kind in {"tool", "capability"}
        for component in ir.components
    )
    assert not any(
        component.evidence.path == "memory-policy-negative.ts"
        and component.kind == "control"
        and component.name == "sandbox-memory-policy"
        for component in ir.components
    )


def test_typescript_openai_sandbox_runtime_requires_exact_local_client_import() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_sandbox_runtime")

    controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-runtime"
    }
    assert set(controls) == {
        ("positive.ts", 12, "ts:positive.ts#control:directClient@12"),
        ("positive.ts", 21, "ts:positive.ts#control:dockerClient@21"),
        ("positive.ts", 36, "ts:positive.ts#control:sandbox-runtime@36"),
        ("positive.ts", 39, "ts:positive.ts#control:client@39"),
        ("positive.ts", 49, "ts:positive.ts#control:conditionalClient@49"),
        ("positive.ts", 76, "ts:positive.ts#control:extensionClient@76"),
        ("positive.ts", 87, "ts:positive.ts#control:inlineCreatedSession@87"),
        ("positive.ts", 150, "ts:positive.ts#control:exposedPortClient@150"),
        ("positive.ts", 156, "ts:positive.ts#control:snapshotClient@156"),
    }
    assert (
        controls[("positive.ts", 12, "ts:positive.ts#control:directClient@12")].attributes[
            "sandbox_runtime"
        ]
        == "unix-local"
    )
    assert (
        controls[("positive.ts", 21, "ts:positive.ts#control:dockerClient@21")].attributes[
            "sandbox_runtime"
        ]
        == "docker-local"
    )
    assert (
        controls[("positive.ts", 36, "ts:positive.ts#control:sandbox-runtime@36")].attributes[
            "sandbox_runtime"
        ]
        == "unix-local"
    )
    assert (
        controls[("positive.ts", 39, "ts:positive.ts#control:client@39")].attributes[
            "sandbox_runtime"
        ]
        == "unix-local"
    )
    conditional = controls[("positive.ts", 49, "ts:positive.ts#control:conditionalClient@49")]
    extension = controls[("positive.ts", 76, "ts:positive.ts#control:extensionClient@76")]
    inline_created = controls[("positive.ts", 87, "ts:positive.ts#control:inlineCreatedSession@87")]
    exposed_port_runtime = controls[
        ("positive.ts", 150, "ts:positive.ts#control:exposedPortClient@150")
    ]
    snapshot_runtime = controls[("positive.ts", 156, "ts:positive.ts#control:snapshotClient@156")]
    assert conditional.attributes["sandbox_runtime"] == "conditional-local"
    assert conditional.attributes["sandbox_runtime_options"] == ["docker-local", "unix-local"]
    assert conditional.attributes["constructors"] == [
        "DockerSandboxClient",
        "UnixLocalSandboxClient",
    ]
    exact_import_controls = [
        component
        for key, component in controls.items()
        if key
        not in {
            ("positive.ts", 49, "ts:positive.ts#control:conditionalClient@49"),
            ("positive.ts", 76, "ts:positive.ts#control:extensionClient@76"),
        }
    ]
    assert all(
        component.attributes["analysis"] == "typescript-openai-sandbox-local-client"
        and component.attributes["module"] == "@openai/agents/sandbox/local"
        and component.attributes["resolution"] == "exact-openai-sandbox-local-import"
        and component.attributes["execution_environment"] == "sdk-sandbox"
        and component.attributes["sandbox_policy"] == "openai-agents-sdk-sandbox"
        for component in exact_import_controls
    )
    assert (
        conditional.attributes["analysis"] == "typescript-openai-sandbox-local-client"
        and conditional.attributes["module"] == "@openai/agents/sandbox/local"
        and conditional.attributes["resolution"] == "exact-openai-sandbox-local-conditional-import"
        and conditional.attributes["execution_environment"] == "sdk-sandbox"
        and conditional.attributes["sandbox_policy"] == "openai-agents-sdk-sandbox"
    )
    assert extension.attributes["analysis"] == "typescript-openai-sandbox-extension-client"
    assert extension.attributes["module"] == "@openai/agents-extensions/sandbox/blaxel"
    assert extension.attributes["constructor"] == "BlaxelSandboxClient"
    assert extension.attributes["resolution"] == "exact-openai-sandbox-extension-import"
    assert extension.attributes["sandbox_runtime"] == "blaxel-cloud"
    assert inline_created.attributes["constructor"] == "DockerSandboxClient"
    assert inline_created.attributes["resolution"] == "exact-openai-sandbox-local-import"
    assert inline_created.attributes["sandbox_runtime"] == "docker-local"
    assert exposed_port_runtime.attributes["constructor"] == "DockerSandboxClient"
    assert exposed_port_runtime.attributes["sandbox_runtime"] == "docker-local"
    assert snapshot_runtime.attributes["sandbox_runtime"] == "unix-local"

    network_exposures = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-network-exposure"
    }
    assert set(network_exposures) == {
        (
            "positive.ts",
            152,
            "ts:positive.ts#control:exposedPortClient.exposedPorts@152",
        ),
    }
    exposed_ports = network_exposures[
        (
            "positive.ts",
            152,
            "ts:positive.ts#control:exposedPortClient.exposedPorts@152",
        )
    ]
    assert exposed_ports.attributes == {
        "analysis": "typescript-openai-sandbox-exposed-ports",
        "module": "@openai/agents/sandbox/local",
        "constructor": "DockerSandboxClient",
        "imported_symbol": "DockerSandboxClient",
        "resolution": "exact-openai-sandbox-local-import",
        "configuration": "exposedPorts",
        "network_exposure": "explicit-exposed-ports",
        "ports": [3000, 8080],
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
    }
    assert [
        (
            relationship.source_id,
            relationship.target_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.attributes,
        )
        for relationship in ir.relationships
        if relationship.source_kind == "control"
        and relationship.source_name == "sandbox-runtime"
        and relationship.target_kind == "control"
        and relationship.target_name == "sandbox-network-exposure"
    ] == [
        (
            "ts:positive.ts#control:exposedPortClient@150",
            "ts:positive.ts#control:exposedPortClient.exposedPorts@152",
            "positive.ts",
            152,
            {
                "analysis": "typescript-openai-sandbox-exposed-ports",
                "configuration": "exposedPorts",
            },
        )
    ]

    concurrency_limits = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-concurrency-limit"
    }
    assert set(concurrency_limits) == {
        (
            "positive.ts",
            192,
            "ts:positive.ts#control:limitedConcurrencyAgent.concurrencyLimits@192",
        ),
    }
    assert concurrency_limits[
        (
            "positive.ts",
            192,
            "ts:positive.ts#control:limitedConcurrencyAgent.concurrencyLimits@192",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-concurrency-limits",
        "module": "@openai/agents",
        "configuration": "sandbox.concurrencyLimits",
        "limits": {"manifestEntries": 4, "localDirFiles": 16},
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
    }
    assert [
        (
            relationship.source_id,
            relationship.target_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.attributes,
        )
        for relationship in ir.relationships
        if relationship.source_kind == "control"
        and relationship.source_name == "sandbox-runtime"
        and relationship.target_kind == "control"
        and relationship.target_name == "sandbox-concurrency-limit"
    ] == [
        (
            "ts:positive.ts#control:directClient@12",
            "ts:positive.ts#control:limitedConcurrencyAgent.concurrencyLimits@192",
            "positive.ts",
            192,
            {
                "analysis": "typescript-openai-sandbox-concurrency-limits",
                "configuration": "sandbox.concurrencyLimits",
            },
        )
    ]

    snapshot_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-state-persistence"
    }
    assert set(snapshot_controls) == {
        (
            "positive.ts",
            157,
            "ts:positive.ts#control:snapshotClient.snapshot@157",
        ),
    }
    assert snapshot_controls[
        (
            "positive.ts",
            157,
            "ts:positive.ts#control:snapshotClient.snapshot@157",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-snapshot-storage",
        "module": "@openai/agents/sandbox/local",
        "constructor": "UnixLocalSandboxClient",
        "imported_symbol": "UnixLocalSandboxClient",
        "resolution": "exact-openai-sandbox-local-import",
        "configuration": "snapshot",
        "snapshot_type": "local",
        "snapshot_type_resolution": "literal",
        "base_dir": "/tmp/agentverify-sandbox-snapshots",
        "base_dir_resolution": "immutable-module-literal-binding",
        "state_persistence": "local-filesystem-snapshot",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
    }
    assert [
        (
            relationship.source_id,
            relationship.target_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.attributes,
        )
        for relationship in ir.relationships
        if relationship.source_kind == "control"
        and relationship.source_name == "sandbox-runtime"
        and relationship.target_kind == "control"
        and relationship.target_name == "sandbox-state-persistence"
    ] == [
        (
            "ts:positive.ts#control:snapshotClient@156",
            "ts:positive.ts#control:snapshotClient.snapshot@157",
            "positive.ts",
            157,
            {
                "analysis": "typescript-openai-sandbox-snapshot-storage",
                "configuration": "snapshot",
            },
        )
    ]

    path_grants = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-path-grant"
    }
    assert set(path_grants) == {
        (
            "positive.ts",
            174,
            "ts:positive.ts#control:grantManifest.extraPathGrant0@174",
        ),
    }
    grant = path_grants[
        (
            "positive.ts",
            174,
            "ts:positive.ts#control:grantManifest.extraPathGrant0@174",
        )
    ]
    assert grant.attributes == {
        "analysis": "typescript-openai-sandbox-path-grant",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "extraPathGrants",
        "path": "/opt/company/agent-skills",
        "path_resolution": "immutable-module-literal-binding",
        "read_only": True,
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "description": "Shared skill bundle.",
    }

    manifest_entries = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-manifest-entry"
    }
    assert set(manifest_entries) == {
        (
            "positive.ts",
            168,
            "ts:positive.ts#control:grantManifest.entry0.task.md@168",
        ),
        (
            "positive.ts",
            169,
            "ts:positive.ts#control:grantManifest.entry1.repo@169",
        ),
        (
            "positive.ts",
            170,
            "ts:positive.ts#control:grantManifest.entry2.localRepo@170",
        ),
        (
            "positive.ts",
            206,
            "ts:positive.ts#control:nestedManifest.entry0.memories@206",
        ),
        (
            "positive.ts",
            209,
            "ts:positive.ts#control:nestedManifest.entry0.memories/gtm@209",
        ),
        (
            "positive.ts",
            212,
            "ts:positive.ts#control:nestedManifest.entry0.memories/gtm/notes.md@212",
        ),
        (
            "positive.ts",
            215,
            "ts:positive.ts#control:nestedManifest.entry0.memories/engineering@215",
        ),
        (
            "positive.ts",
            218,
            "ts:positive.ts#control:nestedManifest.entry0.memories/engineering/notes.md@218",
        ),
        (
            "positive.ts",
            250,
            "ts:positive.ts#control:manifestReturn@248.entry0.linked-task.md@250",
        ),
        (
            "positive.ts",
            279,
            "ts:positive.ts#control:manifestReturn@277.entry0.ambiguous-a.md@279",
        ),
        (
            "positive.ts",
            285,
            "ts:positive.ts#control:manifestReturn@283.entry0.ambiguous-b.md@285",
        ),
    }
    assert manifest_entries[
        (
            "positive.ts",
            168,
            "ts:positive.ts#control:grantManifest.entry0.task.md@168",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "task.md",
        "entry_source": "literal-file",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_factory": "file",
        "content_present": True,
    }
    assert manifest_entries[
        (
            "positive.ts",
            169,
            "ts:positive.ts#control:grantManifest.entry1.repo@169",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "repo",
        "entry_source": "git-repository",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_factory": "gitRepo",
        "repository": "openai/openai-agents-js",
        "repository_resolution": "literal",
        "ref": "main",
        "ref_resolution": "literal",
    }
    assert manifest_entries[
        (
            "positive.ts",
            170,
            "ts:positive.ts#control:grantManifest.entry2.localRepo@170",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "localRepo",
        "entry_source": "local-directory",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_factory": "localDir",
        "source_path": "/opt/company/repo-template",
        "source_path_resolution": "immutable-module-literal-binding",
    }
    assert manifest_entries[
        (
            "positive.ts",
            206,
            "ts:positive.ts#control:nestedManifest.entry0.memories@206",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "memories",
        "entry_source": "literal-directory",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_type": "dir",
        "children_present": True,
        "child_entry_count": 2,
        "child_entry_names": ["gtm", "engineering"],
    }
    assert manifest_entries[
        (
            "positive.ts",
            209,
            "ts:positive.ts#control:nestedManifest.entry0.memories/gtm@209",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "memories/gtm",
        "entry_source": "literal-directory",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_type": "dir",
        "children_present": True,
        "child_entry_count": 1,
        "child_entry_names": ["notes.md"],
    }
    assert manifest_entries[
        (
            "positive.ts",
            212,
            "ts:positive.ts#control:nestedManifest.entry0.memories/gtm/notes.md@212",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "memories/gtm/notes.md",
        "entry_source": "literal-file",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_type": "file",
        "content_present": True,
    }
    assert manifest_entries[
        (
            "positive.ts",
            215,
            "ts:positive.ts#control:nestedManifest.entry0.memories/engineering@215",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "memories/engineering",
        "entry_source": "literal-directory",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_type": "dir",
        "children_present": True,
        "child_entry_count": 1,
        "child_entry_names": ["notes.md"],
    }
    assert manifest_entries[
        (
            "positive.ts",
            218,
            "ts:positive.ts#control:nestedManifest.entry0.memories/engineering/notes.md@218",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "memories/engineering/notes.md",
        "entry_source": "literal-file",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_type": "file",
        "content_present": True,
    }
    assert manifest_entries[
        (
            "positive.ts",
            250,
            "ts:positive.ts#control:manifestReturn@248.entry0.linked-task.md@250",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-entry",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "entries",
        "entry_name": "linked-task.md",
        "entry_source": "literal-file",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "entry_factory": "file",
        "content_present": True,
    }
    assert (
        manifest_entries[
            (
                "positive.ts",
                279,
                "ts:positive.ts#control:manifestReturn@277.entry0.ambiguous-a.md@279",
            )
        ].attributes["entry_name"]
        == "ambiguous-a.md"
    )
    assert (
        manifest_entries[
            (
                "positive.ts",
                285,
                "ts:positive.ts#control:manifestReturn@283.entry0.ambiguous-b.md@285",
            )
        ].attributes["entry_name"]
        == "ambiguous-b.md"
    )

    manifest_environment = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-environment-variable"
    }
    assert set(manifest_environment) == {
        (
            "positive.ts",
            180,
            "ts:positive.ts#control:grantManifest.environment.NODE_ENV@180",
        ),
        (
            "positive.ts",
            181,
            "ts:positive.ts#control:grantManifest.environment.SANDBOX_TOKEN@181",
        ),
        (
            "positive.ts",
            253,
            "ts:positive.ts#control:manifestReturn@248.environment.NODE_ENV@253",
        ),
    }
    assert manifest_environment[
        (
            "positive.ts",
            180,
            "ts:positive.ts#control:grantManifest.environment.NODE_ENV@180",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-environment",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "environment",
        "environment_variable": "NODE_ENV",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "value_resolution": "immutable-module-literal-binding",
        "value": "integration",
    }
    assert manifest_environment[
        (
            "positive.ts",
            181,
            "ts:positive.ts#control:grantManifest.environment.SANDBOX_TOKEN@181",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-environment",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "environment",
        "environment_variable": "SANDBOX_TOKEN",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "value_resolution": "literal",
        "value_redacted": True,
    }
    assert manifest_environment[
        (
            "positive.ts",
            253,
            "ts:positive.ts#control:manifestReturn@248.environment.NODE_ENV@253",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-environment",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "environment",
        "environment_variable": "NODE_ENV",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
        "value_resolution": "literal",
        "value": "test",
    }

    workspace_roots = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-workspace-root"
    }
    assert set(workspace_roots) == {
        (
            "positive.ts",
            201,
            "ts:positive.ts#control:rootedManifest.root@201",
        ),
        (
            "positive.ts",
            270,
            "ts:positive.ts#control:objectManifest.root@270",
        ),
    }
    assert workspace_roots[
        (
            "positive.ts",
            201,
            "ts:positive.ts#control:rootedManifest.root@201",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-root",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "root",
        "root_path": "/workspace",
        "root_path_resolution": "immutable-module-literal-binding",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
    }
    assert workspace_roots[
        (
            "positive.ts",
            270,
            "ts:positive.ts#control:objectManifest.root@270",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-manifest-root",
        "module": "@openai/agents/sandbox",
        "constructor": "Manifest",
        "imported_symbol": "Manifest",
        "resolution": "exact-openai-sandbox-import",
        "configuration": "root",
        "root_path": "/object-workspace",
        "root_path_resolution": "literal",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
    }

    manifest_composition_edges = {
        (
            relationship.source_kind,
            relationship.source_name,
            relationship.source_id,
            relationship.target_name,
            relationship.target_id,
            relationship.evidence.path,
            relationship.evidence.line,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.attributes.get("analysis")
        == "typescript-openai-sandbox-manifest-composition"
    }
    assert manifest_composition_edges == {
        (
            "control",
            "sandbox-runtime",
            "ts:positive.ts#control:client@39",
            "sandbox-environment-variable",
            "ts:positive.ts#control:manifestReturn@248.environment.NODE_ENV@253",
            "positive.ts",
            259,
            (
                ("analysis", "typescript-openai-sandbox-manifest-composition"),
                ("binding", "identifier"),
                ("configuration", "client.create"),
                ("manifest_binding", "linkedManifest"),
            ),
        ),
        (
            "control",
            "sandbox-runtime",
            "ts:positive.ts#control:client@39",
            "sandbox-manifest-entry",
            "ts:positive.ts#control:manifestReturn@248.entry0.linked-task.md@250",
            "positive.ts",
            259,
            (
                ("analysis", "typescript-openai-sandbox-manifest-composition"),
                ("binding", "identifier"),
                ("configuration", "client.create"),
                ("manifest_binding", "linkedManifest"),
            ),
        ),
        (
            "agent",
            "Linked Manifest Sandbox",
            "ts:positive.ts#agent:linkedManifestAgent",
            "sandbox-environment-variable",
            "ts:positive.ts#control:manifestReturn@248.environment.NODE_ENV@253",
            "positive.ts",
            262,
            (
                ("analysis", "typescript-openai-sandbox-manifest-composition"),
                ("binding", "identifier"),
                ("configuration", "defaultManifest"),
                ("manifest_binding", "linkedManifest"),
            ),
        ),
        (
            "agent",
            "Linked Manifest Sandbox",
            "ts:positive.ts#agent:linkedManifestAgent",
            "sandbox-manifest-entry",
            "ts:positive.ts#control:manifestReturn@248.entry0.linked-task.md@250",
            "positive.ts",
            262,
            (
                ("analysis", "typescript-openai-sandbox-manifest-composition"),
                ("binding", "identifier"),
                ("configuration", "defaultManifest"),
                ("manifest_binding", "linkedManifest"),
            ),
        ),
        (
            "control",
            "sandbox-runtime",
            "ts:positive.ts#control:client@39",
            "sandbox-workspace-root",
            "ts:positive.ts#control:objectManifest.root@270",
            "positive.ts",
            272,
            (
                ("analysis", "typescript-openai-sandbox-manifest-composition"),
                ("binding", "manifest-property-identifier"),
                ("configuration", "client.create"),
                ("manifest_binding", "objectManifest"),
            ),
        ),
    }
    assert not any(
        relationship.target_id
        in {
            "ts:positive.ts#control:manifestReturn@277.entry0.ambiguous-a.md@279",
            "ts:positive.ts#control:manifestReturn@283.entry0.ambiguous-b.md@285",
        }
        and relationship.attributes.get("analysis")
        == "typescript-openai-sandbox-manifest-composition"
        for relationship in ir.relationships
    )

    working_directories = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "sandbox-working-directory"
    }
    assert set(working_directories) == {
        (
            "positive.ts",
            235,
            "ts:positive.ts#control:workdirAgent.cwd@235",
        ),
    }
    assert working_directories[
        (
            "positive.ts",
            235,
            "ts:positive.ts#control:workdirAgent.cwd@235",
        )
    ].attributes == {
        "analysis": "typescript-openai-sandbox-working-directory",
        "module": "@openai/agents",
        "configuration": "sandbox.cwd",
        "working_directory": "tasks/a",
        "working_directory_resolution": "immutable-module-literal-binding",
        "execution_environment": "sdk-sandbox",
        "sandbox_policy": "openai-agents-sdk-sandbox",
        "scope": "production",
    }
    working_directory_edges = {
        (
            edge.source_kind,
            edge.source_name,
            edge.source_id,
            edge.evidence.path,
            edge.evidence.line,
            edge.target_id,
        ): edge
        for edge in ir.relationships
        if edge.relation == "configured-by"
        and edge.target_kind == "control"
        and edge.target_name == "sandbox-working-directory"
    }
    assert set(working_directory_edges) == {
        (
            "control",
            "sandbox-runtime",
            "ts:positive.ts#control:client@39",
            "positive.ts",
            235,
            "ts:positive.ts#control:workdirAgent.cwd@235",
        ),
    }
    assert next(iter(working_directory_edges.values())).attributes == {
        "analysis": "typescript-openai-sandbox-working-directory",
        "configuration": "sandbox.cwd",
    }

    conversation_sessions = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "conversation-session"
    }
    assert set(conversation_sessions) == {
        (
            "positive.ts",
            301,
            "ts:positive.ts#control:conversation.sessionId@301",
        ),
        (
            "positive.ts",
            311,
            "ts:positive.ts#control:runnerConversation.sessionId@311",
        ),
    }
    assert conversation_sessions[
        (
            "positive.ts",
            301,
            "ts:positive.ts#control:conversation.sessionId@301",
        )
    ].attributes == {
        "analysis": "typescript-openai-agents-memory-session",
        "module": "@openai/agents",
        "constructor": "MemorySession",
        "imported_symbol": "MemorySession",
        "resolution": "exact-openai-agents-import",
        "local_constructor": "MemorySession",
        "configuration": "MemorySession.sessionId",
        "session_id": "agentverify-sandbox-conversation",
        "session_id_resolution": "immutable-module-literal-binding",
        "state_scope": "conversation-memory",
        "scope": "production",
    }
    assert conversation_sessions[
        (
            "positive.ts",
            311,
            "ts:positive.ts#control:runnerConversation.sessionId@311",
        )
    ].attributes == {
        "analysis": "typescript-openai-agents-memory-session",
        "module": "@openai/agents",
        "constructor": "MemorySession",
        "imported_symbol": "MemorySession",
        "resolution": "exact-openai-agents-import",
        "local_constructor": "MemorySession",
        "configuration": "MemorySession.sessionId",
        "session_id": "agentverify-runner-conversation",
        "session_id_resolution": "literal",
        "state_scope": "conversation-memory",
        "scope": "production",
    }
    conversation_edges = {
        (
            edge.source_name,
            edge.evidence.path,
            edge.evidence.line,
            edge.target_id,
            edge.attributes.get("configuration"),
            edge.attributes.get("binding"),
        )
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.relation == "configured-by"
        and edge.target_kind == "control"
        and edge.target_name == "conversation-session"
    }
    assert conversation_edges == {
        (
            "Conversation Session Sandbox",
            "positive.ts",
            306,
            "ts:positive.ts#control:conversation.sessionId@301",
            "run-session",
            "session",
        ),
        (
            "Runner Conversation Session Sandbox",
            "positive.ts",
            320,
            "ts:positive.ts#control:runnerConversation.sessionId@311",
            "runner-run-session",
            "session",
        ),
    }

    runtime_edges = {
        (
            edge.source_name,
            edge.evidence.path,
            edge.evidence.line,
            edge.target_id,
            edge.attributes.get("binding"),
        )
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.relation == "configured-by"
        and edge.target_kind == "control"
        and edge.target_name == "sandbox-runtime"
    }
    assert runtime_edges == {
        (
            "Direct Client Sandbox",
            "positive.ts",
            17,
            "ts:positive.ts#control:directClient@12",
            "client",
        ),
        (
            "Docker Session Sandbox",
            "positive.ts",
            27,
            "ts:positive.ts#control:dockerClient@21",
            "session",
        ),
        (
            "Inline Client Sandbox",
            "positive.ts",
            35,
            "ts:positive.ts#control:sandbox-runtime@36",
            "inline-client",
        ),
        (
            "Session Shorthand Sandbox",
            "positive.ts",
            45,
            "ts:positive.ts#control:client@39",
            "session-shorthand",
        ),
        (
            "Conditional Runtime Sandbox",
            "positive.ts",
            59,
            "ts:positive.ts#control:conditionalClient@49",
            "session",
        ),
        (
            "Resumed Session Sandbox",
            "positive.ts",
            72,
            "ts:positive.ts#control:client@39",
            "session",
        ),
        (
            "Runner Extension Sandbox",
            "positive.ts",
            85,
            "ts:positive.ts#control:extensionClient@76",
            "runner-client",
        ),
        (
            "Inline Created Session Sandbox",
            "positive.ts",
            94,
            "ts:positive.ts#control:inlineCreatedSession@87",
            "session",
        ),
        (
            "Helper Runtime Sandbox",
            "positive.ts",
            106,
            "ts:positive.ts#control:client@39",
            "session-shorthand",
        ),
        (
            "Runner Option Session Sandbox",
            "positive.ts",
            117,
            "ts:positive.ts#control:client@39",
            "session-shorthand",
        ),
        (
            "Typed Runner Option Session Sandbox",
            "positive.ts",
            130,
            "ts:positive.ts#control:client@39",
            "session",
        ),
        (
            "asTool Runtime Sandbox",
            "positive.ts",
            144,
            "ts:positive.ts#control:client@39",
            "session-shorthand",
        ),
        (
            "Limited Concurrency Sandbox",
            "positive.ts",
            189,
            "ts:positive.ts#control:directClient@12",
            "client",
        ),
        (
            "Workdir Sandbox",
            "positive.ts",
            234,
            "ts:positive.ts#control:client@39",
            "session-shorthand",
        ),
        (
            "Dynamic Cwd Sandbox",
            "positive.ts",
            243,
            "ts:positive.ts#control:client@39",
            "session-shorthand",
        ),
        (
            "Linked Manifest Sandbox",
            "positive.ts",
            265,
            "ts:positive.ts#control:client@39",
            "session",
        ),
    }
    as_tool_edges = [
        edge
        for edge in ir.relationships
        if edge.source_name == "asTool Runtime Sandbox" and edge.target_name == "sandbox-runtime"
    ]
    assert len(as_tool_edges) == 1
    assert as_tool_edges[0].attributes["configuration"] == "asTool-runConfig"
    tracing_disabled_controls = {
        (
            component.evidence.path,
            component.evidence.line,
            component.symbol_id,
            tuple(sorted(component.attributes.items())),
        )
        for component in ir.components
        if component.kind == "control"
        and component.name == "tracing-disabled"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-astool-tracing-disabled"
    }
    assert tracing_disabled_controls == {
        (
            "positive.ts",
            144,
            "ts:positive.ts#control:asToolRuntimeAgent.asTool.tracingDisabled@144:parent141",
            (
                ("adapter", "asTool"),
                ("analysis", "typescript-openai-agents-astool-tracing-disabled"),
                ("configuration", "asTool.runConfig.tracingDisabled"),
                ("module", "@openai/agents"),
                ("parent_agent", "asTool Runtime Orchestrator"),
                ("parent_agent_id", "ts:positive.ts#agent:asToolOrchestrator"),
                ("scope", "production"),
                ("source_agent", "asTool Runtime Sandbox"),
                ("source_agent_id", "ts:positive.ts#agent:asToolRuntimeAgent"),
                ("tool_name", "review_sandbox_workspace"),
                ("trace_scope", "openai-tracing"),
                ("tracing_disabled", True),
            ),
        )
    }
    tracing_disabled_edges = {
        (
            relationship.source_name,
            relationship.source_id,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "tracing-disabled"
        and relationship.attributes.get("analysis")
        == "typescript-openai-agents-astool-tracing-disabled"
    }
    assert tracing_disabled_edges == {
        (
            "asTool Runtime Sandbox",
            "ts:positive.ts#agent:asToolRuntimeAgent",
            "positive.ts",
            144,
            "ts:positive.ts#control:asToolRuntimeAgent.asTool.tracingDisabled@144:parent141",
            (
                ("adapter", "asTool"),
                ("analysis", "typescript-openai-agents-astool-tracing-disabled"),
                ("binding", "tracingDisabled"),
                ("configuration", "asTool-runConfig-tracingDisabled"),
                ("tool_name", "review_sandbox_workspace"),
            ),
        )
    }
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind == "control"
        and component.attributes.get("analysis")
        != "typescript-openai-agents-runner-workflow-name"
        for component in ir.components
    )
    assert not any(
        relationship.evidence.path == "negative.ts"
        and relationship.target_name == "sandbox-runtime"
        for relationship in ir.relationships
    )
    assert not any(
        relationship.evidence.path == "negative.ts"
        and relationship.target_name == "sandbox-network-exposure"
        for relationship in ir.relationships
    )
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind == "control"
        and component.name == "sandbox-path-grant"
        for component in ir.components
    )
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind == "control"
        and component.name == "sandbox-environment-variable"
        for component in ir.components
    )
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind == "control"
        and component.name == "sandbox-manifest-entry"
        for component in ir.components
    )
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind == "control"
        and component.name == "sandbox-concurrency-limit"
        for component in ir.components
    )
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind == "control"
        and component.name == "sandbox-working-directory"
        for component in ir.components
    )
    assert not any(
        relationship.evidence.path == "negative.ts"
        and relationship.attributes.get("analysis")
        == "typescript-openai-sandbox-manifest-composition"
        for relationship in ir.relationships
    )
    assert not ir.findings


def test_typescript_openai_conversation_id_requires_exact_server_conversation() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_conversation_id")

    controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "conversation-session"
    }
    assert set(controls) == {
        ("positive.ts", 9, "ts:positive.ts#control:conversationId@9"),
    }
    assert controls[("positive.ts", 9, "ts:positive.ts#control:conversationId@9")].attributes == {
        "analysis": "typescript-openai-agents-server-conversation",
        "module": "openai",
        "constructor": "OpenAI",
        "imported_symbol": "OpenAI",
        "resolution": "exact-typescript-provider-import",
        "local_constructor": "OpenAI",
        "configuration": "client.conversations.create",
        "client_binding": "client",
        "conversation_id_binding": "conversationId",
        "state_scope": "openai-server-managed-conversation",
        "scope": "production",
    }

    continuity_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "conversation-continuity"
    }
    assert set(continuity_controls) == {
        ("positive.ts", 23, "ts:positive.ts#control:previousResponseId@23"),
        ("positive.ts", 29, "ts:positive.ts#control:messages.history@29"),
        ("positive.ts", 35, "ts:positive.ts#control:carriedItems.history@35"),
        ("positive.ts", 39, "ts:positive.ts#control:directStateFirst.state@39"),
        ("positive.ts", 42, "ts:positive.ts#control:interrupted.state@42"),
        ("positive.ts", 45, "ts:positive.ts#control:resumeState.state@45"),
        ("positive.ts", 49, "ts:positive.ts#control:approvalState.state@49"),
        ("positive.ts", 69, "ts:positive.ts#control:persistedState.fromString@69"),
        ("positive.ts", 79, "ts:positive.ts#control:messageState.state@79"),
        ("positive.ts", 91, "ts:positive.ts#control:loopItems.history@91"),
        ("positive.ts", 101, "ts:positive.ts#control:concatThread.history@101"),
        ("positive.ts", 109, "ts:positive.ts#control:aliasedItems.history@109"),
    }
    assert continuity_controls[
        ("positive.ts", 23, "ts:positive.ts#control:previousResponseId@23")
    ].attributes == {
        "analysis": "typescript-openai-agents-previous-response",
        "module": "@openai/agents",
        "configuration": "run.previousResponseId",
        "result_binding": "first",
        "previous_response_id_binding": "previousResponseId",
        "state_scope": "openai-previous-response-continuity",
        "scope": "production",
    }
    assert continuity_controls[
        ("positive.ts", 29, "ts:positive.ts#control:messages.history@29")
    ].attributes == {
        "analysis": "typescript-openai-agents-history-continuity",
        "module": "@openai/agents",
        "configuration": "run.history",
        "result_binding": "historyFirst",
        "history_binding": "messages",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-history-continuity",
        "scope": "production",
    }
    assert continuity_controls[
        ("positive.ts", 35, "ts:positive.ts#control:carriedItems.history@35")
    ].attributes == {
        "analysis": "typescript-openai-agents-history-continuity",
        "module": "@openai/agents",
        "configuration": "run.history",
        "result_binding": "carriedFirst",
        "history_binding": "carriedItems",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-history-continuity",
        "scope": "production",
    }
    assert continuity_controls[
        ("positive.ts", 39, "ts:positive.ts#control:directStateFirst.state@39")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-state-continuity",
        "module": "@openai/agents",
        "configuration": "run.state",
        "result_binding": "directStateFirst",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-state-continuity",
        "scope": "production",
        "state_binding": "inline-result-state",
    }
    assert continuity_controls[
        ("positive.ts", 42, "ts:positive.ts#control:interrupted.state@42")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-state-continuity",
        "module": "@openai/agents",
        "configuration": "run.state",
        "result_binding": "interrupted",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-state-continuity",
        "scope": "production",
        "state_binding": "inline-result-state",
    }
    assert continuity_controls[
        ("positive.ts", 45, "ts:positive.ts#control:resumeState.state@45")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-state-continuity",
        "module": "@openai/agents",
        "configuration": "run.state",
        "result_binding": "streamed",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-state-continuity",
        "scope": "production",
        "state_binding": "resumeState",
    }
    assert continuity_controls[
        ("positive.ts", 49, "ts:positive.ts#control:approvalState.state@49")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-state-continuity",
        "module": "@openai/agents",
        "configuration": "run.state",
        "result_binding": "interruptedApproval",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-state-continuity",
        "scope": "production",
        "state_binding": "approvalState",
    }
    assert continuity_controls[
        ("positive.ts", 69, "ts:positive.ts#control:persistedState.fromString@69")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-state-from-string",
        "module": "@openai/agents",
        "constructor": "RunState",
        "configuration": "RunState.fromString",
        "result_binding": "persistedApproval",
        "state_binding": "persistedState",
        "serialized_state_binding": "persistedStateText",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-state-continuity",
        "scope": "production",
    }
    assert (
        continuity_controls[
            ("positive.ts", 79, "ts:positive.ts#control:messageState.state@79")
        ].attributes["state_binding"]
        == "messageState"
    )
    assert continuity_controls[
        ("positive.ts", 91, "ts:positive.ts#control:loopItems.history@91")
    ].attributes == {
        "analysis": "typescript-openai-agents-history-continuity",
        "module": "@openai/agents",
        "configuration": "run.history",
        "result_binding": "loopResult",
        "history_binding": "loopItems",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-history-continuity",
        "scope": "production",
    }
    assert continuity_controls[
        ("positive.ts", 101, "ts:positive.ts#control:concatThread.history@101")
    ].attributes == {
        "analysis": "typescript-openai-agents-history-continuity",
        "module": "@openai/agents",
        "configuration": "run.history",
        "result_binding": "concatResult",
        "history_binding": "concatThread",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-history-continuity",
        "scope": "production",
    }
    assert continuity_controls[
        ("positive.ts", 109, "ts:positive.ts#control:aliasedItems.history@109")
    ].attributes == {
        "analysis": "typescript-openai-agents-history-continuity",
        "module": "@openai/agents",
        "configuration": "run.history",
        "result_binding": "aliasedResult",
        "history_binding": "aliasedItems",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-history-continuity",
        "scope": "production",
    }

    trace_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "trace-group"
    }
    assert set(trace_controls) == {
        ("positive.ts", 119, "ts:positive.ts#control:withTrace.groupId@119:run117"),
        (
            "positive.ts",
            133,
            "ts:positive.ts#control:traceGroupedRunner.groupId@133:run135",
        ),
    }
    assert trace_controls[
        ("positive.ts", 119, "ts:positive.ts#control:withTrace.groupId@119:run117")
    ].attributes == {
        "analysis": "typescript-openai-agents-trace-group",
        "module": "@openai/agents",
        "imported_symbol": "withTrace",
        "local_function": "withTrace",
        "configuration": "withTrace.groupId",
        "group_id_resolution": "literal",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "trace_scope": "openai-trace-correlation",
        "scope": "production",
        "trace_name": "AgentVerify trace group",
        "group_id": "agentverify-trace-group",
    }
    assert trace_controls[
        ("positive.ts", 133, "ts:positive.ts#control:traceGroupedRunner.groupId@133:run135")
    ].attributes == {
        "analysis": "typescript-openai-agents-runner-trace-group",
        "module": "@openai/agents",
        "constructor": "Runner",
        "imported_symbol": "Runner",
        "local_constructor": "Runner",
        "configuration": "Runner.groupId",
        "runner_binding": "traceGroupedRunner",
        "group_id_resolution": "immutable-module-literal-binding",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "trace_scope": "openai-trace-correlation",
        "scope": "production",
        "group_id": "agentverify-runner-trace-group",
    }

    trace_id_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "trace-id"
    }
    assert set(trace_id_controls) == {
        ("positive.ts", 128, "ts:positive.ts#control:withTrace.traceId@128:run126"),
    }
    assert trace_id_controls[
        ("positive.ts", 128, "ts:positive.ts#control:withTrace.traceId@128:run126")
    ].attributes == {
        "analysis": "typescript-openai-agents-trace-id",
        "module": "@openai/agents",
        "imported_symbol": "withTrace",
        "local_function": "withTrace",
        "configuration": "withTrace.traceId",
        "trace_id_resolution": "generateTraceId-binding",
        "generated_trace_id": True,
        "trace_url_logged": False,
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "trace_scope": "openai-trace-identity",
        "scope": "production",
        "trace_name": "AgentVerify trace id",
        "trace_id_binding": "traceId",
    }

    tracing_disabled_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "tracing-disabled"
    }
    assert set(tracing_disabled_controls) == {
        (
            "positive.ts",
            137,
            "ts:positive.ts#control:tracingDisabledRunner.tracingDisabled@137:run138",
        ),
    }
    assert tracing_disabled_controls[
        (
            "positive.ts",
            137,
            "ts:positive.ts#control:tracingDisabledRunner.tracingDisabled@137:run138",
        )
    ].attributes == {
        "analysis": "typescript-openai-agents-tracing-disabled",
        "module": "@openai/agents",
        "constructor": "Runner",
        "imported_symbol": "Runner",
        "local_constructor": "Runner",
        "configuration": "Runner.tracingDisabled",
        "runner_binding": "tracingDisabledRunner",
        "tracing_disabled": True,
        "trace_scope": "openai-tracing",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "scope": "production",
    }
    trace_workflow_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control"
        and component.name == "trace-workflow"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-runner-workflow-name"
    }
    assert set(trace_workflow_controls) == {
        ("positive.ts", 16, "ts:positive.ts#control:runner.workflowName@16:run18"),
        ("positive.ts", 16, "ts:positive.ts#control:runner.workflowName@16:run36"),
        ("positive.ts", 16, "ts:positive.ts#control:runner.workflowName@16:run46"),
    }
    assert trace_workflow_controls[
        ("positive.ts", 16, "ts:positive.ts#control:runner.workflowName@16:run18")
    ].attributes == {
        "analysis": "typescript-openai-agents-runner-workflow-name",
        "module": "@openai/agents",
        "constructor": "Runner",
        "imported_symbol": "Runner",
        "local_constructor": "Runner",
        "configuration": "Runner.workflowName",
        "runner_binding": "runner",
        "workflow_name": "server-managed conversation example",
        "workflow_name_resolution": "literal",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "trace_scope": "openai-workflow",
        "scope": "production",
    }
    runner_tool_choice_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control"
        and component.name == "tool-choice-policy"
        and component.attributes.get("analysis")
        == "typescript-openai-agents-runner-tool-choice"
    }
    assert set(runner_tool_choice_controls) == {
        ("positive.ts", 16, "ts:positive.ts#control:runner.toolChoice@16:run18"),
        ("positive.ts", 16, "ts:positive.ts#control:runner.toolChoice@16:run36"),
        ("positive.ts", 16, "ts:positive.ts#control:runner.toolChoice@16:run46"),
    }
    assert runner_tool_choice_controls[
        ("positive.ts", 16, "ts:positive.ts#control:runner.toolChoice@16:run18")
    ].attributes == {
        "analysis": "typescript-openai-agents-runner-tool-choice",
        "module": "@openai/agents",
        "constructor": "Runner",
        "imported_symbol": "Runner",
        "local_constructor": "Runner",
        "configuration": "Runner.modelSettings.toolChoice",
        "runner_binding": "runner",
        "tool_choice": "required",
        "tool_choice_resolution": "literal",
        "choice_scope": "runner-model-settings",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "scope": "production",
    }
    turn_limit_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control"
        and component.name == "agent-turn-limit"
        and component.attributes.get("analysis")
        in {
            "typescript-openai-agents-run-turn-limit",
            "typescript-openai-agents-runner-run-turn-limit",
        }
    }
    assert set(turn_limit_controls) == {
        ("positive.ts", 12, "ts:positive.ts#control:run.maxTurns@12:run11"),
        ("positive.ts", 19, "ts:positive.ts#control:runner.run.maxTurns@19:run18"),
    }
    assert turn_limit_controls[
        ("positive.ts", 12, "ts:positive.ts#control:run.maxTurns@12:run11")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-turn-limit",
        "module": "@openai/agents",
        "configuration": "run.maxTurns",
        "max_turns": 6,
        "limit_scope": "agent-run",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "scope": "production",
        "imported_symbol": "run",
        "local_function": "run",
    }
    assert turn_limit_controls[
        ("positive.ts", 19, "ts:positive.ts#control:runner.run.maxTurns@19:run18")
    ].attributes == {
        "analysis": "typescript-openai-agents-runner-run-turn-limit",
        "module": "@openai/agents",
        "configuration": "Runner.run.maxTurns",
        "max_turns": 7,
        "limit_scope": "agent-run",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "scope": "production",
        "constructor": "Runner",
        "imported_symbol": "Runner",
        "runner_binding": "runner",
    }

    approval_decision_controls = {
        (component.evidence.path, component.evidence.line, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "approval-decision"
    }
    assert set(approval_decision_controls) == {
        ("positive.ts", 51, "ts:positive.ts#control:approvalState.approve@51"),
        ("positive.ts", 52, "ts:positive.ts#control:approvalState.reject@52"),
        ("positive.ts", 58, "ts:positive.ts#control:inlineApproval.state.approve@58"),
        ("positive.ts", 59, "ts:positive.ts#control:inlineApproval.state.reject@59"),
        ("positive.ts", 71, "ts:positive.ts#control:persistedState.approve@71"),
        ("positive.ts", 72, "ts:positive.ts#control:persistedState.reject@72"),
        ("positive.ts", 81, "ts:positive.ts#control:messageState.reject@81"),
        ("positive.ts", 82, "ts:positive.ts#control:messageState.reject@82"),
        ("positive.ts", 83, "ts:positive.ts#control:messageState.reject@83"),
        ("positive.ts", 84, "ts:positive.ts#control:messageState.reject@84"),
    }
    assert approval_decision_controls[
        ("positive.ts", 51, "ts:positive.ts#control:approvalState.approve@51")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-state-approval-decision",
        "module": "@openai/agents",
        "configuration": "run.state.approve",
        "result_binding": "interruptedApproval",
        "state_binding": "approvalState",
        "decision": "approve",
        "source_agent": "Server Conversation Agent",
        "source_agent_id": "ts:positive.ts#agent:agent",
        "state_scope": "openai-run-state-approval-decision",
        "scope": "production",
    }
    assert (
        approval_decision_controls[
            ("positive.ts", 52, "ts:positive.ts#control:approvalState.reject@52")
        ].attributes["decision"]
        == "reject"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 58, "ts:positive.ts#control:inlineApproval.state.approve@58")
        ].attributes["state_binding"]
        == "inline-result-state"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 59, "ts:positive.ts#control:inlineApproval.state.reject@59")
        ].attributes["configuration"]
        == "run.state.reject"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 71, "ts:positive.ts#control:persistedState.approve@71")
        ].attributes["result_binding"]
        == "persistedApproval"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 72, "ts:positive.ts#control:persistedState.reject@72")
        ].attributes["state_binding"]
        == "persistedState"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 81, "ts:positive.ts#control:messageState.reject@81")
        ].attributes["rejection_message_source"]
        == "literal"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 82, "ts:positive.ts#control:messageState.reject@82")
        ].attributes["rejection_message_binding"]
        == "rejectionText"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 82, "ts:positive.ts#control:messageState.reject@82")
        ].attributes["rejection_message_source"]
        == "literal-binding"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 83, "ts:positive.ts#control:messageState.reject@83")
        ].attributes["rejection_message_source"]
        == "template"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 84, "ts:positive.ts#control:messageState.reject@84")
        ].attributes["rejection_message_binding"]
        == "runtimeRejectionText"
    )
    assert (
        approval_decision_controls[
            ("positive.ts", 84, "ts:positive.ts#control:messageState.reject@84")
        ].attributes["rejection_message_source"]
        == "dynamic"
    )

    edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name in {"conversation-session", "conversation-continuity"}
    }
    assert edges == {
        (
            "Server Conversation Agent",
            "positive.ts",
            11,
            "ts:positive.ts#control:conversationId@9",
            (
                ("analysis", "typescript-openai-agents-server-conversation"),
                ("binding", "conversationId-shorthand"),
                ("configuration", "run-session"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            18,
            "ts:positive.ts#control:conversationId@9",
            (
                ("analysis", "typescript-openai-agents-server-conversation"),
                ("binding", "conversationId-shorthand"),
                ("configuration", "runner-run-session"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            24,
            "ts:positive.ts#control:previousResponseId@23",
            (
                ("analysis", "typescript-openai-agents-previous-response"),
                ("binding", "previousResponseId-shorthand"),
                ("configuration", "run-session"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            31,
            "ts:positive.ts#control:messages.history@29",
            (
                ("analysis", "typescript-openai-agents-history-continuity"),
                ("binding", "history-input"),
                ("configuration", "run-history-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            36,
            "ts:positive.ts#control:carriedItems.history@35",
            (
                ("analysis", "typescript-openai-agents-history-continuity"),
                ("binding", "history-input"),
                ("configuration", "runner-run-history-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            90,
            "ts:positive.ts#control:loopItems.history@91",
            (
                ("analysis", "typescript-openai-agents-history-continuity"),
                ("binding", "history-feedback-input"),
                ("configuration", "run-history-feedback-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            97,
            "ts:positive.ts#control:concatThread.history@101",
            (
                ("analysis", "typescript-openai-agents-history-continuity"),
                ("binding", "history-feedback-input"),
                ("configuration", "run-history-feedback-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            108,
            "ts:positive.ts#control:aliasedItems.history@109",
            (
                ("analysis", "typescript-openai-agents-history-continuity"),
                ("binding", "history-feedback-input"),
                ("configuration", "run-history-feedback-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            39,
            "ts:positive.ts#control:directStateFirst.state@39",
            (
                ("analysis", "typescript-openai-agents-run-state-continuity"),
                ("binding", "result-state-input"),
                ("configuration", "run-state-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            42,
            "ts:positive.ts#control:interrupted.state@42",
            (
                ("analysis", "typescript-openai-agents-run-state-continuity"),
                ("binding", "result-state-input"),
                ("configuration", "run-state-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            46,
            "ts:positive.ts#control:resumeState.state@45",
            (
                ("analysis", "typescript-openai-agents-run-state-continuity"),
                ("binding", "state-input"),
                ("configuration", "runner-run-state-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            54,
            "ts:positive.ts#control:approvalState.state@49",
            (
                ("analysis", "typescript-openai-agents-run-state-continuity"),
                ("binding", "state-input"),
                ("configuration", "run-state-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            74,
            "ts:positive.ts#control:persistedState.fromString@69",
            (
                ("analysis", "typescript-openai-agents-run-state-continuity"),
                ("binding", "state-input"),
                ("configuration", "run-state-input"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            86,
            "ts:positive.ts#control:messageState.state@79",
            (
                ("analysis", "typescript-openai-agents-run-state-continuity"),
                ("binding", "state-input"),
                ("configuration", "run-state-input"),
            ),
        ),
    }
    trace_edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "trace-group"
    }
    assert trace_edges == {
        (
            "Server Conversation Agent",
            "positive.ts",
            117,
            "ts:positive.ts#control:withTrace.groupId@119:run117",
            (
                ("analysis", "typescript-openai-agents-trace-group"),
                ("binding", "groupId"),
                ("configuration", "withTrace-groupId"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            135,
            "ts:positive.ts#control:traceGroupedRunner.groupId@133:run135",
            (
                ("analysis", "typescript-openai-agents-runner-trace-group"),
                ("binding", "groupId"),
                ("configuration", "Runner-groupId"),
                ("runner_binding", "traceGroupedRunner"),
            ),
        ),
    }
    trace_id_edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "trace-id"
    }
    assert trace_id_edges == {
        (
            "Server Conversation Agent",
            "positive.ts",
            126,
            "ts:positive.ts#control:withTrace.traceId@128:run126",
            (
                ("analysis", "typescript-openai-agents-trace-id"),
                ("binding", "traceId-binding"),
                ("configuration", "withTrace-traceId"),
            ),
        ),
    }
    tracing_disabled_edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "tracing-disabled"
    }
    assert tracing_disabled_edges == {
        (
            "Server Conversation Agent",
            "positive.ts",
            138,
            "ts:positive.ts#control:tracingDisabledRunner.tracingDisabled@137:run138",
            (
                ("analysis", "typescript-openai-agents-tracing-disabled"),
                ("binding", "tracingDisabled"),
                ("configuration", "Runner-tracingDisabled"),
                ("runner_binding", "tracingDisabledRunner"),
            ),
        ),
    }
    trace_workflow_edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "trace-workflow"
        and relationship.attributes.get("analysis")
        == "typescript-openai-agents-runner-workflow-name"
    }
    assert trace_workflow_edges == {
        (
            "Server Conversation Agent",
            "positive.ts",
            18,
            "ts:positive.ts#control:runner.workflowName@16:run18",
            (
                ("analysis", "typescript-openai-agents-runner-workflow-name"),
                ("binding", "workflowName"),
                ("configuration", "Runner-workflowName"),
                ("runner_binding", "runner"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            36,
            "ts:positive.ts#control:runner.workflowName@16:run36",
            (
                ("analysis", "typescript-openai-agents-runner-workflow-name"),
                ("binding", "workflowName"),
                ("configuration", "Runner-workflowName"),
                ("runner_binding", "runner"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            46,
            "ts:positive.ts#control:runner.workflowName@16:run46",
            (
                ("analysis", "typescript-openai-agents-runner-workflow-name"),
                ("binding", "workflowName"),
                ("configuration", "Runner-workflowName"),
                ("runner_binding", "runner"),
            ),
        ),
    }
    runner_tool_choice_edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "tool-choice-policy"
        and relationship.attributes.get("analysis")
        == "typescript-openai-agents-runner-tool-choice"
    }
    assert runner_tool_choice_edges == {
        (
            "Server Conversation Agent",
            "positive.ts",
            18,
            "ts:positive.ts#control:runner.toolChoice@16:run18",
            (
                ("analysis", "typescript-openai-agents-runner-tool-choice"),
                ("binding", "toolChoice"),
                ("configuration", "Runner-modelSettings-toolChoice"),
                ("runner_binding", "runner"),
                ("tool_choice", "required"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            36,
            "ts:positive.ts#control:runner.toolChoice@16:run36",
            (
                ("analysis", "typescript-openai-agents-runner-tool-choice"),
                ("binding", "toolChoice"),
                ("configuration", "Runner-modelSettings-toolChoice"),
                ("runner_binding", "runner"),
                ("tool_choice", "required"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            46,
            "ts:positive.ts#control:runner.toolChoice@16:run46",
            (
                ("analysis", "typescript-openai-agents-runner-tool-choice"),
                ("binding", "toolChoice"),
                ("configuration", "Runner-modelSettings-toolChoice"),
                ("runner_binding", "runner"),
                ("tool_choice", "required"),
            ),
        ),
    }
    turn_limit_edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "agent-turn-limit"
        and relationship.attributes.get("analysis")
        in {
            "typescript-openai-agents-run-turn-limit",
            "typescript-openai-agents-runner-run-turn-limit",
        }
    }
    assert turn_limit_edges == {
        (
            "Server Conversation Agent",
            "positive.ts",
            11,
            "ts:positive.ts#control:run.maxTurns@12:run11",
            (
                ("analysis", "typescript-openai-agents-run-turn-limit"),
                ("binding", "maxTurns"),
                ("configuration", "run-maxTurns"),
                ("local_function", "run"),
                ("max_turns", 6),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            18,
            "ts:positive.ts#control:runner.run.maxTurns@19:run18",
            (
                ("analysis", "typescript-openai-agents-runner-run-turn-limit"),
                ("binding", "maxTurns"),
                ("configuration", "Runner-run-maxTurns"),
                ("max_turns", 7),
                ("runner_binding", "runner"),
            ),
        ),
    }
    approval_edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            tuple(sorted(relationship.attributes.items())),
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "approval-decision"
    }
    assert approval_edges == {
        (
            "Server Conversation Agent",
            "positive.ts",
            51,
            "ts:positive.ts#control:approvalState.approve@51",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "approvalState"),
                ("configuration", "run.state.approve"),
                ("decision", "approve"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            52,
            "ts:positive.ts#control:approvalState.reject@52",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "approvalState"),
                ("configuration", "run.state.reject"),
                ("decision", "reject"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            58,
            "ts:positive.ts#control:inlineApproval.state.approve@58",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "inline-result-state"),
                ("configuration", "run.state.approve"),
                ("decision", "approve"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            59,
            "ts:positive.ts#control:inlineApproval.state.reject@59",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "inline-result-state"),
                ("configuration", "run.state.reject"),
                ("decision", "reject"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            71,
            "ts:positive.ts#control:persistedState.approve@71",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "persistedState"),
                ("configuration", "run.state.approve"),
                ("decision", "approve"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            72,
            "ts:positive.ts#control:persistedState.reject@72",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "persistedState"),
                ("configuration", "run.state.reject"),
                ("decision", "reject"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            81,
            "ts:positive.ts#control:messageState.reject@81",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "messageState"),
                ("configuration", "run.state.reject"),
                ("decision", "reject"),
                ("rejection_message", "custom"),
                ("rejection_message_source", "literal"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            82,
            "ts:positive.ts#control:messageState.reject@82",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "messageState"),
                ("configuration", "run.state.reject"),
                ("decision", "reject"),
                ("rejection_message", "custom"),
                ("rejection_message_binding", "rejectionText"),
                ("rejection_message_source", "literal-binding"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            83,
            "ts:positive.ts#control:messageState.reject@83",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "messageState"),
                ("configuration", "run.state.reject"),
                ("decision", "reject"),
                ("rejection_message", "custom"),
                ("rejection_message_source", "template"),
            ),
        ),
        (
            "Server Conversation Agent",
            "positive.ts",
            84,
            "ts:positive.ts#control:messageState.reject@84",
            (
                ("analysis", "typescript-openai-agents-run-state-approval-decision"),
                ("binding", "messageState"),
                ("configuration", "run.state.reject"),
                ("decision", "reject"),
                ("rejection_message", "custom"),
                ("rejection_message_binding", "runtimeRejectionText"),
                ("rejection_message_source", "dynamic"),
            ),
        ),
    }
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind == "control"
        and component.name
        in {"approval-decision", "conversation-session", "conversation-continuity"}
        for component in ir.components
    )
    assert not any(
        relationship.evidence.path == "negative.ts"
        and relationship.target_name
        in {"approval-decision", "conversation-session", "conversation-continuity"}
        for relationship in ir.relationships
    )
    assert not ir.findings


def test_typescript_openai_approval_decision_records_env_backed_approval_branch() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_approval_decision_env")

    controls = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "control" and component.name == "approval-decision"
    }
    assert set(controls) == {22, 24, 31, 40}
    assert controls[22].attributes["approval_bypass_environment_names"] == ["AUTO_APPROVE_HITL"]
    assert controls[22].attributes["approval_bypass_resolution"] == ("braced-if-condition-callback")
    assert controls[31].attributes["approval_bypass_environment_names"] == ["AUTO_APPROVE_HITL"]
    assert controls[31].attributes["state_binding"] == "inline-result-state"
    assert "approval_bypass_environment_names" not in controls[24].attributes
    assert controls[24].attributes["decision"] == "reject"
    assert "approval_bypass_environment_names" not in controls[40].attributes

    governed_edges = {
        relationship.evidence.line: relationship.attributes
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "approval-decision"
    }
    assert governed_edges[22]["approval_bypass_environment_names"] == ["AUTO_APPROVE_HITL"]
    assert governed_edges[31]["approval_bypass_resolution"] == ("braced-if-condition-callback")
    assert "approval_bypass_environment_names" not in governed_edges[24]
    assert "approval_bypass_environment_names" not in governed_edges[40]


def test_typescript_openai_helper_hitl_resolves_lexical_agent_call_sites() -> None:
    ir = scan_repository(ROOT / "cases/typescript_openai_helper_hitl")

    controls = {
        (component.evidence.path, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "approval-decision"
    }
    assert set(controls) == {
        ("positive.ts", "ts:positive.ts#control:runWithHitl.state.reject@17:call5"),
        ("positive.ts", "ts:positive.ts#control:runWithHitl.state.reject@17:call10"),
    }
    assert controls[
        ("positive.ts", "ts:positive.ts#control:runWithHitl.state.reject@17:call5")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-state-approval-decision",
        "module": "@openai/agents",
        "configuration": "run.state.reject",
        "result_binding": "runWithHitl.result:call5",
        "state_binding": "runWithHitl.state:call5",
        "decision": "reject",
        "source_agent": "First helper agent",
        "source_agent_id": "ts:positive.ts#agent:agent@4",
        "state_scope": "openai-run-state-approval-decision",
        "scope": "production",
        "rejection_message": "custom",
        "rejection_message_source": "template",
        "resolution": "same-file-helper-parameter-run-state",
        "helper": "runWithHitl",
        "helper_call_line": 5,
        "helper_decision_line": 17,
        "agent_argument": "agent",
    }
    assert (
        controls[
            ("positive.ts", "ts:positive.ts#control:runWithHitl.state.reject@17:call10")
        ].attributes["source_agent_id"]
        == "ts:positive.ts#agent:agent@9"
    )
    assert (
        controls[
            ("positive.ts", "ts:positive.ts#control:runWithHitl.state.reject@17:call10")
        ].attributes["helper_call_line"]
        == 10
    )
    continuity_controls = {
        (component.evidence.path, component.symbol_id): component
        for component in ir.components
        if component.kind == "control" and component.name == "conversation-continuity"
    }
    assert set(continuity_controls) == {
        ("positive.ts", "ts:positive.ts#control:runWithHitl.state.state@15:call5"),
        ("positive.ts", "ts:positive.ts#control:runWithHitl.state.state@15:call10"),
    }
    assert continuity_controls[
        ("positive.ts", "ts:positive.ts#control:runWithHitl.state.state@15:call5")
    ].attributes == {
        "analysis": "typescript-openai-agents-run-state-continuity",
        "module": "@openai/agents",
        "configuration": "run.state",
        "result_binding": "runWithHitl.result:call5",
        "source_agent": "First helper agent",
        "source_agent_id": "ts:positive.ts#agent:agent@4",
        "state_scope": "openai-run-state-continuity",
        "scope": "production",
        "state_binding": "runWithHitl.state:call5",
        "resolution": "same-file-helper-parameter-run-state",
        "helper": "runWithHitl",
        "helper_call_line": 5,
        "agent_argument": "agent",
        "helper_resume_line": 21,
        "helper_state_line": 15,
    }
    assert (
        continuity_controls[
            ("positive.ts", "ts:positive.ts#control:runWithHitl.state.state@15:call10")
        ].attributes["source_agent_id"]
        == "ts:positive.ts#agent:agent@9"
    )
    assert (
        continuity_controls[
            ("positive.ts", "ts:positive.ts#control:runWithHitl.state.state@15:call10")
        ].attributes["helper_call_line"]
        == 10
    )

    edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "approval-decision"
    }
    assert edges == {
        (
            "First helper agent",
            "positive.ts",
            17,
            "ts:positive.ts#control:runWithHitl.state.reject@17:call5",
        ),
        (
            "Second helper agent",
            "positive.ts",
            17,
            "ts:positive.ts#control:runWithHitl.state.reject@17:call10",
        ),
    }
    continuity_edges = {
        (
            relationship.source_name,
            relationship.evidence.path,
            relationship.evidence.line,
            relationship.target_id,
            relationship.attributes["helper_call_line"],
        )
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "configured-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "conversation-continuity"
    }
    assert continuity_edges == {
        (
            "First helper agent",
            "positive.ts",
            21,
            "ts:positive.ts#control:runWithHitl.state.state@15:call5",
            5,
        ),
        (
            "Second helper agent",
            "positive.ts",
            21,
            "ts:positive.ts#control:runWithHitl.state.state@15:call10",
            10,
        ),
    }
    assert not any(
        component.evidence.path == "negative.ts"
        and component.kind == "control"
        and component.name in {"approval-decision", "conversation-continuity"}
        for component in ir.components
    )


def test_cline_inline_tool_links_only_dynamic_bun_shell_execution() -> None:
    ir = scan_repository(ROOT / "cases/typescript_bun_shell")

    shell = [
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "shell-execution"
    ]
    assert [
        (component.evidence.line, component.attributes["dynamic_command"]) for component in shell
    ] == [
        (8, True),
        (12, False),
    ]
    assert [finding.rule_id for finding in ir.findings] == ["AV-EXEC001"]
    assert ir.findings[0].evidence.line == 8
    assert ir.findings[0].ir_path == (
        "agent:operator",
        "tool:createTool@6",
        "capability:shell-execution",
    )


def test_typescript_mastra_properties_and_mcp_registrations_have_exact_tool_spans() -> None:
    ir = scan_repository(ROOT / "cases/typescript_tool_registrations")

    tools = {
        item.name: item
        for item in ir.components
        if item.kind == "tool" and item.evidence.path == "tools.ts"
    }
    assert set(tools) == {"lookup", "requester", "download", "status"}
    assert tools["lookup"].symbol_id == "ts:tools.ts#tool:lookup"
    assert tools["requester"].attributes == {
        "constructor": "createTool",
        "needs_approval": False,
        "binding": "object-property",
    }
    assert tools["download"].attributes == {
        "constructor": "registerTool",
        "needs_approval": False,
        "protocol": "MCP",
        "registry": "server",
    }
    assert tools["download"].symbol_id == "ts:tools.ts#tool:download"

    network_edges = [
        (edge.source_name, edge.evidence.line, edge.source_id)
        for edge in ir.relationships
        if edge.source_kind == "tool"
        and edge.target_kind == "capability"
        and edge.target_name == "network"
    ]
    assert network_edges == [
        ("lookup", 7, "ts:tools.ts#tool:lookup"),
        ("requester", 14, "ts:tools.ts#tool:requester"),
        ("download", 22, "ts:tools.ts#tool:download"),
        ("status", 26, "ts:tools.ts#tool:status"),
    ]
    dynamic_origins = {
        item.evidence.line: item.attributes["dynamic_origin"]
        for item in ir.components
        if item.kind == "capability" and item.name == "network" and item.evidence.path == "tools.ts"
    }
    assert dynamic_origins == {7: False, 14: True, 22: True, 26: False}
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-NET001", 14, "requester"),
        ("AV-NET001", 22, "download"),
    ]
    assert not any(
        item.kind == "tool" and item.evidence.path == "fake.ts" for item in ir.components
    )
    assert not any(
        item.kind == "capability" and item.name == "network" and item.evidence.path == "fake.ts"
        for item in ir.components
    )


def test_typescript_network_origin_tracks_aliases_but_resolves_fixed_module_host(
    tmp_path: Path,
) -> None:
    (tmp_path / "tools.ts").write_text(
        """import { tool } from "ai";
const API = "https://search.example";

const requester = tool({
  execute: async ({ url }) => {
    const target = url;
    return fetch(target);
  },
});

const search = tool({
  execute: async ({ query }) => {
    const target = `${API}/search?q=${query}`;
    return fetch(target);
  },
});
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    network = {
        item.evidence.line: item.attributes["dynamic_origin"]
        for item in ir.components
        if item.kind == "capability" and item.name == "network"
    }
    assert network == {7: True, 14: False}
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [("AV-NET001", 7, "requester")]


def test_typescript_same_file_network_helpers_propagate_only_controlled_origins() -> None:
    ir = scan_repository(ROOT / "cases/typescript_helper_summary")

    summarized = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "same-file-helper"
    }
    assert {
        item.evidence.line
        for item in ir.components
        if item.kind == "capability" and item.name == "network"
    } == {8, 13, 18, 24}
    assert summarized == {
        18: {
            "scope": "production",
            "api": "fetchRemote",
            "dynamic_origin": True,
            "summary": "same-file-helper",
            "helper_line": 7,
            "helper_network_calls": 1,
        },
        24: {
            "scope": "production",
            "api": "searchRemote",
            "dynamic_origin": False,
            "summary": "same-file-helper",
            "helper_line": 11,
            "helper_network_calls": 1,
        },
    }
    assert [
        (edge.source_name, edge.evidence.line, edge.source_id)
        for edge in ir.relationships
        if edge.target_kind == "capability" and edge.target_name == "network"
    ] == [
        ("proxy", 18, "ts:tools.ts#tool:proxy"),
        ("search", 24, "ts:tools.ts#tool:search"),
    ]
    assert [(finding.rule_id, finding.evidence.line) for finding in ir.findings] == [
        ("AV-NET001", 18)
    ]


def test_typescript_network_origin_policy_preserves_optional_open_hostname_scope() -> None:
    ir = scan_repository(ROOT / "cases/typescript_network_origin_policy")

    network = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "same-file-helper"
    }
    assert sorted(network) == [35, 41, 51, 57, 72, 82]
    assert network[35]["network_origin_policy"] is True
    assert network[35]["scheme_scope"] == "allowlisted"
    assert network[35]["hostname_scope"] == "configured-optional"
    assert all("network_origin_policy" not in network[line] for line in (41, 51, 57, 72, 82))
    controls = [
        item
        for item in ir.components
        if item.kind == "control" and item.name == "network-origin-policy"
    ]
    assert len(controls) == 1
    assert controls[0].evidence.path == "policy.ts"
    assert controls[0].evidence.line == 8
    assert controls[0].attributes == {
        "scope": "production",
        "policy_effect": "validates-initial-http-origin",
        "frontend": "typescript",
        "helper": "validateTarget",
        "schemes": ["http", "https"],
        "scheme_scope": "allowlisted",
        "hostname_scope": "configured-optional",
        "hostname_default": "open",
        "hostname_match": "exact-or-subdomain",
        "environment_name": "ALLOWED_DOMAINS",
        "redirect_scope": "unresolved",
        "dns_scope": "unresolved",
    }
    edges = [
        edge
        for edge in ir.relationships
        if edge.target_kind == "control" and edge.target_name == "network-origin-policy"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [("policy.ts", 35)]
    guarded_finding = next(
        finding
        for finding in ir.findings
        if finding.rule_id == "AV-NET001" and finding.evidence.line == 35
    )
    assert guarded_finding.result_kind == "review"
    assert guarded_finding.analysis["governing_control_effects"] == {
        "network-origin-policy": ["validates-initial-http-origin"]
    }


def test_python_secure_network_helper_requires_complete_transport_proof() -> None:
    ir = scan_repository(ROOT / "cases/python_secure_network_helper")

    network = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "secure-imported-function"
    ]
    assert [(item.evidence.path, item.evidence.line) for item in network] == [
        ("app.py", 6),
        ("app.py", 10),
    ]
    assert all(
        item.attributes
        == {
            "scope": "production",
            "api": "safe_get",
            "dynamic_origin": True,
            "summary": "secure-imported-function",
            "helper_path": "secure_transport/safe_requests.py",
            "helper_line": 30,
            "helper_network_lines": [21],
            "network_origin_policy": True,
            "initial_origin_scope": "public-addresses",
            "redirect_scope": "each-hop-validated",
            "dns_scope": "connection-pinned",
            "proxy_scope": "disabled",
            "enforcement_default": "enabled",
        }
        for item in network
    )
    controls = [
        item
        for item in ir.components
        if item.kind == "control" and item.name == "network-ssrf-policy"
    ]
    assert len(controls) == 1
    assert controls[0].evidence.path == "secure_transport/safe_requests.py"
    assert controls[0].evidence.line == 30
    assert controls[0].attributes == {
        "scope": "production",
        "policy_effect": "restricts-http-origin-and-peer",
        "frontend": "python",
        "helper": "safe_get",
        "helper_path": "secure_transport/safe_requests.py",
        "schemes": ["http", "https"],
        "initial_origin_scope": "public-addresses",
        "redirect_scope": "each-hop-validated",
        "dns_scope": "connection-pinned",
        "proxy_scope": "disabled",
        "enforcement_default": "enabled",
        "escape_hatch": "configured-opt-out",
        "bypass_environment": "ALLOW_UNSAFE_NETWORK",
        "force_safe_environment": "FORCE_SAFE_NETWORK",
    }
    edges = [
        edge
        for edge in ir.relationships
        if edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("app.py", 6),
        ("app.py", 10),
    ]

    selected_ir = scan_repository(
        ROOT / "cases/python_secure_network_helper",
        selected_paths={"app.py", "secure_transport/safe_requests.py"},
    )
    assert not any(
        edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
        for edge in selected_ir.relationships
    )


def test_python_proxy_conditional_network_helper_preserves_proxy_residual(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_proxy_conditional_network_helper"
    ir = scan_repository(root)

    network = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "secure-imported-function"
    ]
    assert [(item.evidence.path, item.evidence.line) for item in network] == [
        ("app.py", 6),
        ("app.py", 10),
    ]
    assert [item.attributes["redirect_scope"] for item in network] == [
        "disabled",
        "each-hop-validated",
    ]
    assert all(
        item.attributes["dns_scope"] == "connection-pinned-unless-proxied"
        and item.attributes["proxy_scope"] == "environment-or-caller-dependent"
        and item.attributes["enforcement_default"] == "enabled"
        and item.attributes["helper_network_lines"] == [65]
        for item in network
    )
    controls = {
        item.attributes["helper"]: item
        for item in ir.components
        if item.kind == "control" and item.name == "network-ssrf-policy"
    }
    assert set(controls) == {"safe_get", "safe_request"}
    assert controls["safe_get"].evidence.line == 69
    assert controls["safe_request"].evidence.line == 73
    assert all(
        item.attributes["policy_effect"] == "restricts-http-origin-and-conditionally-pins-peer"
        and item.attributes["escape_hatch"] == "none"
        and "bypass_environment" not in item.attributes
        and "force_safe_environment" not in item.attributes
        for item in controls.values()
    )

    blocking_mutations = [
        (
            "_assert_pinned_peer(sock, address, hostname)",
            "verify_peer(sock, address, hostname)",
        ),
        ("parsed = urlparse(url)", 'parsed = urlparse("https://fixed.example")'),
        (
            "addresses = [result[4][0] for result in socket.getaddrinfo(parsed.hostname, None)]",
            'socket.getaddrinfo(parsed.hostname, None)\n    addresses = ["8.8.8.8"]',
        ),
        (
            '_proxy_applies(url, kwargs.get("proxies"))',
            "_proxy_applies(url, None)",
        ),
    ]
    for index, (before, after) in enumerate(blocking_mutations):
        incomplete = tmp_path / f"incomplete-{index}"
        shutil.copytree(root, incomplete)
        transport = incomplete / "transport/url_safety.py"
        source = transport.read_text(encoding="utf-8")
        assert before in source
        transport.write_text(source.replace(before, after, 1), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
            for edge in incomplete_ir.relationships
        )

    unbounded = tmp_path / "unbounded"
    shutil.copytree(root, unbounded)
    transport = unbounded / "transport/url_safety.py"
    source = transport.read_text(encoding="utf-8")
    transport.write_text(
        source.replace("range(max_redirects + 1)", "range(5)", 1),
        encoding="utf-8",
    )
    unbounded_ir = scan_repository(unbounded)
    assert [
        edge.evidence.line
        for edge in unbounded_ir.relationships
        if edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
    ] == [6]


def test_python_configurable_pinned_network_helper_preserves_noop_state(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_configurable_network_helper"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("app.py", 6),
        ("app.py", 10),
    ]
    assert [edge.attributes["redirect_scope"] for edge in edges] == [
        "disabled-default-each-hop-validated-when-enabled",
        "disabled",
    ]
    assert all(
        edge.attributes["initial_origin_scope"]
        == "public-addresses-with-configured-allowlist-and-loopback-exemption"
        and edge.attributes["dns_scope"] == "connection-pinned-when-enforced"
        and edge.attributes["proxy_scope"] == "disabled-when-enforced"
        and edge.attributes["enforcement_default"] == "enabled"
        and edge.attributes["bypass_environments"]
        == [
            "LANGFLOW_SSRF_PROTECTION_ENABLED",
            "LANGFLOW_CONNECTOR_SSRF_VALIDATION_ENABLED",
        ]
        for edge in edges
    )

    for name, relative, before, after in (
        (
            "disabled-default",
            "lfx/services/settings/groups/security.py",
            "ssrf_protection_enabled: bool = True",
            "ssrf_protection_enabled: bool = False",
        ),
        (
            "unpinned-backend",
            "lfx/utils/ssrf_transport.py",
            "connect_tcp(host=pinned_ip)",
            "connect_tcp(host='re-resolved.example')",
        ),
        (
            "unproven-allowlist",
            "lfx/utils/ssrf_protection.py",
            "return hostname in get_allowed_hosts()",
            "return False",
        ),
        (
            "unproven-loopback-policy",
            "lfx/utils/ssrf_protection.py",
            'os.getenv("LANGFLOW_CONNECTOR_SSRF_ALLOW_LOOPBACK")',
            'os.getenv("UNRELATED_LOOPBACK_FLAG")',
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.target_kind == "control" and edge.target_name == "network-ssrf-policy"
            for edge in incomplete_ir.relationships
        )


def test_typescript_configurable_ssrf_composition_preserves_disabled_default(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_configurable_ssrf_composition"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-configurable-ssrf-composition"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("web-fetch.tool.ts", 18)
    ]
    assert edges[0].attributes == {
        "control_path": "composition.ts",
        "control_line": 14,
        "scope": "production",
        "policy_effect": "validates-url-and-resolved-host-when-enforced",
        "frontend": "typescript",
        "analysis": "typescript-configurable-ssrf-composition",
        "initial_origin_scope": "configured-address-policy-when-enforced",
        "redirect_scope": "bounded-each-hop-hooks-when-enforced",
        "dns_scope": "secure-lookup-configured-when-enforced",
        "proxy_scope": "unresolved",
        "enforcement_default": "disabled",
        "escape_hatch": "default-disabled",
        "enforcement_mode": "configured-opt-in",
        "enable_environment": "N8N_SSRF_PROTECTION_ENABLED",
        "config_path": "config.ts",
        "config_line": 4,
        "service_path": "service.ts",
        "passthrough_path": "ssrf-guard.ts",
        "discovery_path": "discovery.ts",
        "helper_path": "web-fetch.utils.ts",
        "helper_line": 14,
        "approval_scope": "domain-hitl-independent",
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-NET001"
    ] == [("AV-NET001", "web-fetch.tool.ts", 18)]
    assert not any(
        finding.rule_id == "AV-NET001" and finding.evidence.path == "raw.ts"
        for finding in ir.findings
    )

    enabled = tmp_path / "enabled-default"
    shutil.copytree(root, enabled)
    config_path = enabled / "config.ts"
    config_source = config_path.read_text(encoding="utf-8")
    config_path.write_text(
        config_source.replace("enabled: boolean = false", "enabled: boolean = true"),
        encoding="utf-8",
    )
    enabled_ir = scan_repository(enabled)
    enabled_edges = [
        edge
        for edge in enabled_ir.relationships
        if edge.attributes.get("analysis") == "typescript-configurable-ssrf-composition"
    ]
    assert len(enabled_edges) == 1
    assert enabled_edges[0].attributes["enforcement_default"] == "enabled"
    assert enabled_edges[0].attributes["escape_hatch"] == "configured-opt-out"
    assert enabled_edges[0].attributes["enforcement_mode"] == "configured-opt-out"

    for name, relative, before, after in (
        (
            "passthrough-composition",
            "composition.ts",
            "? this.ssrfProtectionService",
            "? createPassthroughSsrfGuard()",
        ),
        (
            "ordinary-lookup",
            "web-fetch.utils.ts",
            "lookup: ssrf.createSecureLookup()",
            "lookup: ordinaryLookup",
        ),
        (
            "unchecked-redirect",
            "web-fetch.utils.ts",
            "ssrf.validateRedirectSync(opts.href)",
            "observeRedirect(opts.href)",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-configurable-ssrf-composition"
            for edge in incomplete_ir.relationships
        )


def test_typescript_flowise_secure_request_composition_preserves_proxy_residual(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_flowise_secure_request"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-flowise-secure-request-composition"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [("HTTP.ts", 31)]
    assert edges[0].attributes == {
        "scope": "production",
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
        "helper_path": "httpSecurity.ts",
        "helper_line": 33,
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-NET001" and finding.evidence.path == "HTTP.ts"
    ] == [("AV-NET001", "HTTP.ts", 31)]
    assert not any(
        finding.rule_id == "AV-NET001" and finding.evidence.path == "raw.ts"
        for finding in ir.findings
    )

    for name, relative, before, after in (
        (
            "default-off",
            "httpSecurity.ts",
            "process.env.HTTP_SECURITY_CHECK !== 'false'",
            "process.env.HTTP_SECURITY_CHECK === 'true'",
        ),
        (
            "automatic-redirects",
            "httpSecurity.ts",
            "maxRedirects: 0",
            "maxRedirects: 5",
        ),
        (
            "unpinned-agent",
            "httpSecurity.ts",
            "cb(null, target.ip, target.family)",
            "cb(null, _host, target.family)",
        ),
        (
            "caller-proxy",
            "HTTP.ts",
            "return await secureAxiosRequest(requestConfig)",
            "requestConfig.proxy = {}\n    return await secureAxiosRequest(requestConfig)",
        ),
        (
            "unnormalized-mapped-ipv6",
            "httpSecurity.ts",
            "parsedIp = ipv6Addr.toIPv4Address()",
            "parsedIp = ipv6Addr",
        ),
        (
            "no-deny-match",
            "httpSecurity.ts",
            "parsedIp.match(parsedRange, adjustedMask)",
            "publicMatch(parsedIp, parsedRange, adjustedMask)",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-flowise-secure-request-composition"
            for edge in incomplete_ir.relationships
        )


def test_typescript_flowise_secure_fetch_composition_overrides_caller_agent(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_flowise_secure_request"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-flowise-secure-fetch-composition"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("WebScraperTool.ts", 9)
    ]
    assert edges[0].attributes == {
        "scope": "production",
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
        "helper_path": "httpSecurity.ts",
        "helper_line": 83,
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-NET001" and finding.evidence.path == "WebScraperTool.ts"
    ] == [("AV-NET001", "WebScraperTool.ts", 9)]
    assert not any(
        finding.rule_id == "AV-NET001" and finding.evidence.path == "raw-fetch.ts"
        for finding in ir.findings
    )
    without_barrel = scan_repository(
        root,
        selected_paths=["WebScraperTool.ts", "httpSecurity.ts"],
    )
    assert not any(
        edge.attributes.get("analysis") == "typescript-flowise-secure-fetch-composition"
        for edge in without_barrel.relationships
    )

    for name, relative, before, after in (
        (
            "fetch-default-off",
            "httpSecurity.ts",
            "process.env.HTTP_SECURITY_CHECK !== 'false'",
            "process.env.HTTP_SECURITY_CHECK === 'true'",
        ),
        (
            "fetch-automatic-redirects",
            "httpSecurity.ts",
            "redirect: 'manual' as const",
            "redirect: 'follow' as const",
        ),
        (
            "fetch-unpinned-agent",
            "httpSecurity.ts",
            "agent: () => agent",
            "agent: init.agent",
        ),
        (
            "fetch-fixed-entrypoint",
            "WebScraperTool.ts",
            "this.scrapeRecursive(initialInput, 1)",
            "this.scrapeRecursive('https://example.test', 1)",
        ),
        (
            "fetch-broken-class-hop",
            "WebScraperTool.ts",
            "this.scrapeSingleUrl(url)",
            "this.scrapeSingleUrl('https://example.test')",
        ),
        (
            "fetch-wrong-import",
            "WebScraperTool.ts",
            "from './index'",
            "from './raw-fetch'",
        ),
        (
            "fetch-broken-barrel",
            "index.ts",
            "export * from './httpSecurity'",
            "export * from './raw-fetch'",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-flowise-secure-fetch-composition"
            for edge in incomplete_ir.relationships
        )


def test_typescript_google_adk_fetch_preserves_preflight_dns_residual(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_google_adk_secure_fetch"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-google-adk-load-web-page-composition"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("load_web_page.ts", 69)
    ]
    assert edges[0].attributes == {
        "scope": "production",
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
        "helper_path": "load_web_page.ts",
        "helper_line": 58,
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-NET001"
    ] == [("AV-NET001", "load_web_page.ts", 69)]
    assert not any(
        finding.rule_id == "AV-NET001" and finding.evidence.path == "raw.ts"
        for finding in ir.findings
    )
    without_tool_class = scan_repository(
        root,
        selected_paths=["load_web_page.ts"],
    )
    assert not any(
        edge.attributes.get("analysis") == "typescript-google-adk-load-web-page-composition"
        for edge in without_tool_class.relationships
    )

    for name, relative, before, after in (
        (
            "adk-auto-redirect",
            "load_web_page.ts",
            "redirect: 'manual'",
            "redirect: 'follow'",
        ),
        (
            "adk-no-preflight",
            "load_web_page.ts",
            "await validateResolvedAddresses(normalizeHost(parsed.hostname))",
            "await Promise.resolve()",
        ),
        (
            "adk-incomplete-address-check",
            "load_web_page.ts",
            "addresses.some(isBlockedAddress)",
            "addresses.every(isBlockedAddress)",
        ),
        (
            "adk-mapped-ip-bypass",
            "load_web_page.ts",
            "value >> 32n === 0xffffn",
            "value >> 32n !== 0xffffn",
        ),
        (
            "adk-fixed-tool-input",
            "load_web_page.ts",
            "execute: ({url}) => loadWebPage(url)",
            "execute: ({url}) => loadWebPage('https://example.test')",
        ),
        (
            "adk-wrong-tool-import",
            "load_web_page.ts",
            "from './function_tool.js'",
            "from './raw.js'",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-google-adk-load-web-page-composition"
            for edge in incomplete_ir.relationships
        )


def test_typescript_axios_instances_preserve_absolute_url_override_semantics(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_axios_instance"
    ir = scan_repository(root)
    capabilities = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.evidence.path == "direct.ts"
    ]
    assert [
        (
            item.evidence.line,
            item.attributes["api"],
            item.attributes["dynamic_origin"],
            item.attributes.get("base_url_scope"),
            item.attributes.get("absolute_url_override"),
        )
        for item in capabilities
    ] == [
        (12, "axios.instance.get", True, "fixed-origin", "allowed"),
        (16, "axios.instance.request", True, "fixed-origin", "allowed"),
        (20, "axios.get", True, None, None),
        (25, "axios.instance.get", False, "fixed-origin", "allowed"),
        (29, "axios.instance.get", False, "fixed-origin", "disabled"),
        (33, "axios.instance.get", True, "absent", "disabled"),
    ]
    assert [
        finding.evidence.line
        for finding in ir.findings
        if finding.rule_id == "AV-NET001" and finding.evidence.path == "direct.ts"
    ] == [12, 16, 20, 33]
    assert not any(
        item.kind == "capability" and item.evidence.path == "shadowed.ts" for item in ir.components
    )

    locked = tmp_path / "locked-override-enabled"
    shutil.copytree(root, locked)
    locked_path = locked / "direct.ts"
    source = locked_path.read_text(encoding="utf-8")
    locked_path.write_text(
        source.replace("allowAbsoluteUrls: false,", "allowAbsoluteUrls: true,", 1),
        encoding="utf-8",
    )
    locked_ir = scan_repository(locked)
    assert any(
        finding.rule_id == "AV-NET001"
        and finding.evidence.path == "direct.ts"
        and finding.evidence.line == 29
        for finding in locked_ir.findings
    )

    wrong_import = tmp_path / "wrong-import"
    shutil.copytree(root, wrong_import)
    wrong_import_path = wrong_import / "direct.ts"
    source = wrong_import_path.read_text(encoding="utf-8")
    wrong_import_path.write_text(
        source.replace('from "axios"', 'from "./local-http"'),
        encoding="utf-8",
    )
    wrong_import_ir = scan_repository(wrong_import)
    assert not any(
        item.attributes.get("summary") == "same-file-axios-instance"
        for item in wrong_import_ir.components
    )


def test_typescript_activepieces_imported_axios_control_preserves_proxy_residual(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_activepieces_safe_http"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-imported-filtering-axios-instance"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [("mcp-transport.ts", 8)]
    assert edges[0].attributes == {
        "scope": "production",
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
        "manifest_path": "package.json",
        "helper_path": "safe-http.ts",
        "helper_line": 31,
        "transport_path": "mcp-transport.ts",
        "transport_line": 19,
        "entry_path": "mcp-tool-validator.ts",
        "entry_line": 4,
    }
    capability = next(
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "imported-axios-client-instance"
    )
    assert capability.attributes["origin_authority"] == "configured-mcp-server"
    assert capability.attributes["dynamic_origin"] is False
    assert not any(
        finding.rule_id == "AV-NET001" and finding.evidence.path == "mcp-transport.ts"
        for finding in ir.findings
    )
    protocol_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "protocol"
        and edge.source_name == "MCP"
        and edge.relation == "uses"
        and edge.target_name == "network"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in protocol_edges] == [
        ("mcp-transport.ts", 8)
    ]

    without_manifest = scan_repository(
        root,
        selected_paths=["safe-http.ts", "mcp-transport.ts", "mcp-tool-validator.ts"],
    )
    assert not any(
        edge.attributes.get("analysis") == "typescript-imported-filtering-axios-instance"
        for edge in without_manifest.relationships
    )

    for name, relative, before, after in (
        (
            "private-addresses-enabled",
            "safe-http.ts",
            "allowPrivateIPAddress: false",
            "allowPrivateIPAddress: true",
        ),
        (
            "caller-overrides-agent",
            "safe-http.ts",
            "...config,\n    httpAgent,\n    httpsAgent,",
            "httpAgent,\n    httpsAgent,\n    ...config,",
        ),
        (
            "wrong-safe-import",
            "mcp-transport.ts",
            'from "./safe-http"',
            'from "./raw-http"',
        ),
        (
            "caller-proxy",
            "mcp-transport.ts",
            "method, url, headers, data: init?.body,",
            "method, url, headers, proxy: {}, data: init?.body,",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-imported-filtering-axios-instance"
            for edge in incomplete_ir.relationships
        )


def test_typescript_composio_safe_fetch_preserves_runtime_and_route_residuals(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_composio_ssrf_safe_fetch"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-imported-undici-ssrf-safe-fetch"
    ]
    assert [
        (
            edge.evidence.path,
            edge.evidence.line,
            edge.attributes["call_helper"],
            edge.attributes["enforcement_mode"],
            edge.attributes["edge_runtime_scope"],
        )
        for edge in edges
    ] == [
        (
            "RemoteFile.ts",
            7,
            "ssrfSafeFetchWhereSupported",
            "node-filtered-edge-unenforced",
            "unguarded-fetch",
        ),
        (
            "RemoteFile.ts",
            11,
            "ssrfSafeFetchWhereSupported",
            "node-filtered-edge-unenforced",
            "unguarded-fetch",
        ),
        (
            "ToolRouterSessionFileMount.ts",
            5,
            "ssrfSafeFetch",
            "node-filtered-edge-fail-closed",
            "fail-closed",
        ),
        (
            "ToolRouterSessionFileMount.ts",
            10,
            "ssrfSafeFetchWhereSupported",
            "node-filtered-edge-unenforced",
            "unguarded-fetch",
        ),
    ]
    assert {edge.attributes["dns_scope"] for edge in edges} == {
        "connection-pinned-unless-configured-route"
    }
    assert {edge.attributes["proxy_scope"] for edge in edges} == {
        "caller-global-or-environment-dependent"
    }
    assert {edge.attributes["filter_library_version"] for edge in edges} == {"^7.29.0"}
    capabilities = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.attributes.get("summary") == "imported-undici-ssrf-safe-fetch"
    ]
    assert [
        (item.evidence.path, item.evidence.line, item.attributes["dynamic_origin"])
        for item in capabilities
    ] == [
        ("RemoteFile.ts", 7, False),
        ("RemoteFile.ts", 11, False),
        ("ToolRouterSessionFileMount.ts", 5, True),
        ("ToolRouterSessionFileMount.ts", 10, False),
    ]

    without_manifest = scan_repository(
        root,
        selected_paths=[
            "RemoteFile.ts",
            "ToolRouterSessionFileMount.ts",
            "pinnedDispatcher.node.ts",
            "ssrfGuard.node.ts",
            "ssrfGuard.workerd.ts",
        ],
    )
    assert not any(
        edge.attributes.get("analysis") == "typescript-imported-undici-ssrf-safe-fetch"
        for edge in without_manifest.relationships
    )

    for name, relative, before, after in (
        (
            "automatic-redirect",
            "ssrfGuard.node.ts",
            "{ ...init, redirect: 'manual', dispatcher }",
            "{ ...init, dispatcher }",
        ),
        (
            "metadata-range-removed",
            "ssrfGuard.node.ts",
            "['169.254.0.0', 16]",
            "['11.0.0.0', 8]",
        ),
        (
            "unpinned-dispatcher",
            "pinnedDispatcher.node.ts",
            "addresses.map(address => ({ address, family: isIP(address) }))",
            "[{ address: _hostname, family: 0 }]",
        ),
        (
            "edge-does-not-fail-closed",
            "ssrfGuard.workerd.ts",
            "throw new ComposioBlockedInternalUrlError('unsupported', { cause: rawUrl });",
            "return fetch(rawUrl);",
        ),
        (
            "wrong-guard-import",
            "ToolRouterSessionFileMount.ts",
            "from '#ssrf_guard'",
            "from './raw'",
        ),
        (
            "wrong-runtime-map",
            "package.json",
            '"workerd": "./dist/utils/ssrfGuard.workerd.mjs"',
            '"workerd": "./dist/utils/ssrfGuard.node.mjs"',
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-imported-undici-ssrf-safe-fetch"
            for edge in incomplete_ir.relationships
        )


def test_typescript_composio_cli_upload_resolves_tool_arguments_to_raw_fetch(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_composio_cli_upload"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-composio-cli-file-upload-flow"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("tool-file-uploads.ts", 2)
    ]
    capability = next(
        item
        for item in ir.components
        if item.kind == "capability"
        and item.attributes.get("analysis") == "typescript-composio-cli-file-upload-flow"
    )
    assert capability.attributes["dynamic_origin"] is True
    assert capability.attributes["origin_authority"] == "tool-execution-arguments"
    assert capability.attributes["destination_policy"] == "absent-on-proven-path"
    assert any(
        finding.rule_id == "AV-NET001"
        and finding.evidence.path == "tool-file-uploads.ts"
        and finding.evidence.line == 2
        for finding in ir.findings
    )

    for name, relative, before, after in (
        (
            "guarded-fetch",
            "tool-file-uploads.ts",
            "fetch(url)",
            "ssrfSafeFetch(url)",
        ),
        (
            "fixed-arguments",
            "tools-executor.ts",
            "arguments_: params.arguments",
            "arguments_: {}",
        ),
        (
            "broken-schema-gate",
            "tool-file-uploads.ts",
            "schema?.file_uploadable === true",
            "schema?.file_uploadable === false",
        ),
        (
            "wrong-import",
            "tools-executor.ts",
            "from 'src/services/tool-file-uploads'",
            "from './raw'",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-composio-cli-file-upload-flow"
            for edge in incomplete_ir.relationships
        )


def test_typescript_google_adk_openapi_tool_keeps_model_input_off_origin(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_google_adk_openapi_rest_tool"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
    ]
    assert {
        (edge.source_kind, edge.relation, edge.target_kind, edge.target_name) for edge in edges
    } == {
        ("tool", "uses", "capability", "network"),
        ("capability", "governed-by", "control", "network-origin-policy"),
    }
    assert {edge.evidence.line for edge in edges} == {15}
    capability = next(
        item
        for item in ir.components
        if item.kind == "capability"
        and item.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
    )
    assert capability.attributes["dynamic_origin"] is False
    assert capability.attributes["configured_origin"] is True
    assert capability.attributes["origin_authority"] == "openapi-server-configuration"
    control = next(
        item
        for item in ir.components
        if item.kind == "control"
        and item.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
    )
    assert control.attributes["model_path_scope"] == "segment-encoded"
    assert control.attributes["dot_segment_policy"] == "rejected"
    assert control.attributes["credential_url_scope"] == "query-only"
    assert not any(finding.rule_id == "AV-NET001" for finding in ir.findings)

    for name, relative, before, after in (
        (
            "model-controlled-base",
            "rest_api_tool.ts",
            "`${endpoint.baseUrl}${resolvedPath}`",
            "`${args.url}${resolvedPath}`",
        ),
        (
            "unencoded-path",
            "rest_api_tool.ts",
            "return encodeURIComponent(value)",
            "return value",
        ),
        (
            "raw-path-binding",
            "rest_api_tool.ts",
            "pathParams[originalName] = encodePathParamValue(originalName, String(argValue))",
            "pathParams[originalName] = String(argValue)",
        ),
        (
            "dynamic-server-variable",
            "openapi_spec_parser.ts",
            "variable?.default || variable?.enum?.[0]",
            "process.env[name]",
        ),
        (
            "credential-rewrites-url",
            "auth_helpers.ts",
            "url += `${separator}key=${encodeURIComponent(credential.apiKey)}`",
            "url = credential.apiKey",
        ),
        (
            "wrong-tool-factory-import",
            "openapi_toolset.ts",
            "from './rest_api_tool.js'",
            "from './raw.js'",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "typescript-google-adk-openapi-rest-tool"
            for edge in incomplete_ir.relationships
        )


def test_openai_agents_python_mcp_tools_inherit_disabled_approval_default(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_openai_mcp_approval_default"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.attributes.get("analysis") == "python-openai-agents-mcp-approval-default"
    ]
    assert {
        (edge.source_kind, edge.relation, edge.target_kind, edge.target_name) for edge in edges
    } == {
        ("agent", "uses", "mcp-server", "Reference Policy Server"),
        ("mcp-server", "configured-by", "control-setting", "mcp-tool-approval"),
    }
    agent_server_edge = next(
        edge for edge in edges if edge.source_kind == "agent" and edge.target_kind == "mcp-server"
    )
    assert agent_server_edge.source_id == "py:app.py#agent:agent"
    assert agent_server_edge.target_id == "py:app.py#mcp-server:server"
    assert agent_server_edge.attributes["target_identity"] == (
        "literal-mcp-servers-list-context-manager"
    )
    server = next(
        item
        for item in ir.components
        if item.kind == "mcp-server" and item.evidence.path == "app.py"
    )
    assert server.symbol_id == "py:app.py#mcp-server:server"
    assert server.attributes["binding_resolution"] == "context-manager-binding"
    setting = next(
        item
        for item in ir.components
        if item.kind == "control-setting"
        and item.name == "mcp-tool-approval"
        and item.attributes.get("analysis") == "python-openai-agents-mcp-approval-default"
    )
    assert setting.attributes["enabled"] is False
    assert setting.attributes["approval_policy"] == "disabled-default"
    assert setting.attributes["policy_scope"] == "all-discovered-mcp-tools"
    assert setting.attributes["missing_tool_mapping_default"] == "disabled"
    assert not any(finding.rule_id == "AV-APPROVAL001" for finding in ir.findings)

    for name, relative, before, after in (
        (
            "explicit-approval",
            "app.py",
            'name="Reference Policy Server",',
            'name="Reference Policy Server", require_approval="always",',
        ),
        (
            "wrong-import",
            "app.py",
            "from agents.mcp import MCPServerStdio",
            "from local_mcp import MCPServerStdio",
        ),
        (
            "enabled-sdk-default",
            "server.py",
            "require_approval=None",
            "require_approval=True",
        ),
        (
            "fail-closed-normalization",
            "server.py",
            "if require_approval is None:\n            return False",
            "if require_approval is None:\n            return True",
        ),
        (
            "hardcoded-wrapper-approval",
            "util.py",
            "needs_approval=needs_approval",
            "needs_approval=True",
        ),
        (
            "different-server-binding",
            "app.py",
            "mcp_servers=[server]",
            "mcp_servers=[other_server]",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.attributes.get("analysis") == "python-openai-agents-mcp-approval-default"
            for edge in incomplete_ir.relationships
        )


def test_openai_agents_python_run_state_approval_decisions_are_exact() -> None:
    ir = scan_repository(ROOT / "cases/python_openai_approval_decision")

    controls = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "control" and component.name == "approval-decision"
    }
    assert set(controls) == {12, 13, 18, 32, 33, 34, 41, 42, 43, 44}
    assert controls[12].symbol_id == "py:agent.py#control:state.approve@12"
    assert controls[12].attributes == {
        "analysis": "python-openai-agents-run-state-approval-decision",
        "module": "agents",
        "configuration": "run.state.approve",
        "result_binding": "result",
        "state_binding": "state",
        "decision": "approve",
        "source_agent": "Python approval decision agent",
        "source_agent_id": "py:agent.py#agent:agent",
        "state_scope": "openai-run-state-approval-decision",
        "scope": "production",
    }
    assert controls[13].attributes["decision"] == "reject"
    assert controls[18].attributes["result_binding"] == "stream_result"
    assert controls[18].attributes["state_binding"] == "stream_state"
    assert controls[32].attributes["decision_persistence_argument"] == "always_approve"
    assert controls[32].attributes["decision_persistence"] == "always"
    assert controls[32].attributes["decision_persistence_value"] is True
    assert controls[33].attributes["decision_persistence_argument"] == "always_reject"
    assert controls[33].attributes["decision_persistence_binding"] == "always"
    assert controls[33].attributes["decision_persistence"] == "always"
    assert controls[33].attributes["decision_persistence_value"] is True
    assert controls[34].attributes["decision_persistence_argument"] == "always_approve"
    assert controls[34].attributes["decision_persistence_binding"] == "once"
    assert controls[34].attributes["decision_persistence"] == "per-call"
    assert controls[34].attributes["decision_persistence_value"] is False
    assert controls[41].attributes["rejection_message"] == "custom"
    assert controls[41].attributes["rejection_message_source"] == "literal"
    assert controls[42].attributes["rejection_message_binding"] == "rejection_text"
    assert controls[42].attributes["rejection_message_source"] == "literal-binding"
    assert controls[43].attributes["rejection_message_source"] == "template"
    assert controls[44].attributes["rejection_message_binding"] == "runtime_message"
    assert controls[44].attributes["rejection_message_source"] == "dynamic"

    governed_edges = {
        relationship.evidence.line: relationship
        for relationship in ir.relationships
        if relationship.source_kind == "agent"
        and relationship.relation == "governed-by"
        and relationship.target_kind == "control"
        and relationship.target_name == "approval-decision"
    }
    assert set(governed_edges) == {12, 13, 18, 32, 33, 34, 41, 42, 43, 44}
    assert governed_edges[12].source_id == "py:agent.py#agent:agent"
    assert governed_edges[12].target_id == "py:agent.py#control:state.approve@12"
    assert governed_edges[13].attributes == {
        "analysis": "python-openai-agents-run-state-approval-decision",
        "configuration": "run.state.reject",
        "binding": "state",
        "decision": "reject",
    }
    assert governed_edges[32].attributes["decision_persistence_argument"] == "always_approve"
    assert governed_edges[32].attributes["decision_persistence"] == "always"
    assert governed_edges[32].attributes["decision_persistence_value"] is True
    assert governed_edges[33].attributes["decision_persistence_argument"] == "always_reject"
    assert governed_edges[33].attributes["decision_persistence_binding"] == "always"
    assert governed_edges[33].attributes["decision_persistence"] == "always"
    assert governed_edges[33].attributes["decision_persistence_value"] is True
    assert governed_edges[34].attributes["decision_persistence_argument"] == "always_approve"
    assert governed_edges[34].attributes["decision_persistence_binding"] == "once"
    assert governed_edges[34].attributes["decision_persistence"] == "per-call"
    assert governed_edges[34].attributes["decision_persistence_value"] is False
    assert governed_edges[41].attributes["rejection_message"] == "custom"
    assert governed_edges[41].attributes["rejection_message_source"] == "literal"
    assert governed_edges[42].attributes["rejection_message_binding"] == "rejection_text"
    assert governed_edges[42].attributes["rejection_message_source"] == "literal-binding"
    assert governed_edges[43].attributes["rejection_message_source"] == "template"
    assert governed_edges[44].attributes["rejection_message_binding"] == "runtime_message"
    assert governed_edges[44].attributes["rejection_message_source"] == "dynamic"


def test_openai_agents_typescript_writable_mcp_tools_inherit_disabled_approval_default(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_openai_mcp_approval"
    ir = scan_repository(root)
    findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL004"]
    assert [
        (finding.evidence.path, finding.evidence.line, finding.ir_path) for finding in findings
    ] == [
        (
            "app.ts",
            3,
            ("agent:Writer", "mcp-server:Writable Files", "capability:filesystem"),
        ),
        (
            "app.ts",
            10,
            (
                "agent:Package Writer",
                "mcp-server:Resolved Package Files",
                "capability:filesystem",
            ),
        ),
        (
            "app.ts",
            30,
            (
                "agent:Unresolved Filter Agent",
                "mcp-server:Unresolved Filter",
                "capability:filesystem",
            ),
        ),
    ]
    assert all(finding.result_kind == "review" for finding in findings)
    assert all(
        finding.analysis["control_settings"] == ["mcp-tool-approval"]
        and finding.analysis["approval_coverage"] == "disabled-default"
        for finding in findings
    )

    read_only = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.evidence.path == "app.ts"
        and component.evidence.line == 20
        and component.attributes.get("analysis") == "typescript-openai-agents-mcp-approval-default"
    )
    assert read_only.attributes["write_access"] is False
    assert read_only.attributes["tool_filter"] == "read-only-static"
    assert any(
        edge.source_kind == "capability"
        and edge.source_name == "filesystem"
        and edge.relation == "governed-by"
        and edge.target_kind == "control"
        and edge.target_name == "mcp-tool-filter"
        and edge.evidence.line == 20
        for edge in ir.relationships
    )
    assert not any(finding.evidence.line in {20, 40} for finding in findings)
    assert not any(
        component.attributes.get("analysis") == "typescript-openai-agents-mcp-approval-default"
        and component.evidence.path == "near_misses.ts"
        for component in ir.components
    )

    incomplete = tmp_path / "missing-sdk-source"
    shutil.copytree(root, incomplete)
    (incomplete / "packages/agents-core/src/tool.ts").unlink()
    incomplete_ir = scan_repository(incomplete)
    assert not any(
        edge.attributes.get("analysis") == "typescript-openai-agents-mcp-approval-default"
        for edge in incomplete_ir.relationships
    )


def test_agno_filesystem_mcp_confirmation_policy_is_resolved_per_mutating_tool(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_agno_mcp_confirmation"
    ir = scan_repository(root)
    findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL005"]
    assert [
        (finding.evidence.path, finding.evidence.line, finding.ir_path) for finding in findings
    ] == [
        (
            "direct.py",
            6,
            (
                "agent:Default Writer",
                "mcp-server:Agno filesystem@6",
                "capability:filesystem",
            ),
        ),
        (
            "partial.py",
            6,
            (
                "agent:Partially Confirmed Writer",
                "mcp-server:Agno filesystem@6",
                "capability:filesystem",
            ),
        ),
        (
            "session.py",
            8,
            (
                "agent:Session Writer",
                "mcp-server:Agno filesystem@8",
                "capability:filesystem",
            ),
        ),
    ]
    assert all(finding.result_kind == "review" for finding in findings)
    assert all(
        finding.analysis["control_settings"] == ["mcp-tool-confirmation"] for finding in findings
    )

    read_only = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.evidence.path == "read_only.py"
        and component.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
    )
    assert read_only.attributes["write_access"] is False
    assert read_only.attributes["unprotected_mutations"] == []
    assert any(
        edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_kind == "control"
        and edge.target_name == "mcp-tool-filter"
        and edge.evidence.path == "read_only.py"
        for edge in ir.relationships
    )

    confirmed = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.evidence.path == "confirmed.py"
        and component.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
    )
    assert confirmed.attributes["approval_policy"] == "enabled-static-mutations"
    assert confirmed.attributes["unprotected_mutations"] == []
    assert any(
        edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_kind == "control"
        and edge.target_name == "human-approval"
        and edge.evidence.path == "confirmed.py"
        for edge in ir.relationships
    )
    assert not any(
        finding.evidence.path
        in {
            "confirmed.py",
            "disconnected_session.py",
            "dynamic_policy.py",
            "read_only.py",
            "unbound.py",
            "wrong_import.py",
        }
        for finding in findings
    )
    assert not any(
        component.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
        and component.evidence.path in {"disconnected_session.py", "unbound.py", "wrong_import.py"}
        for component in ir.components
    )

    changed_sdk = tmp_path / "changed-sdk-default"
    shutil.copytree(root, changed_sdk)
    sdk_path = changed_sdk / "libs/agno/agno/tools/mcp/mcp.py"
    sdk_source = sdk_path.read_text(encoding="utf-8")
    before = "self.requires_confirmation_tools = requires_confirmation_tools or []"
    assert before in sdk_source
    sdk_path.write_text(
        sdk_source.replace(
            before,
            'self.requires_confirmation_tools = requires_confirmation_tools or ["write_file"]',
        ),
        encoding="utf-8",
    )
    changed_ir = scan_repository(changed_sdk)
    assert not any(
        edge.attributes.get("analysis") == "python-agno-mcp-confirmation-default"
        for edge in changed_ir.relationships
    )


def test_openhands_builtin_tools_require_analyzer_and_confirmation_policy() -> None:
    ir = scan_repository(ROOT / "cases/python_openhands_confirmation")

    findings = [finding for finding in ir.findings if finding.rule_id == "AV-APPROVAL006"]
    assert [
        (finding.evidence.path, finding.evidence.line, finding.ir_path) for finding in findings
    ] == [
        (
            "positive.py",
            8,
            (
                "agent:Agent",
                "tool:TerminalTool@8",
                "capability:shell-execution",
            ),
        )
    ]
    assert findings[0].result_kind == "review"
    assert findings[0].analysis["approval_coverage"] == "disabled-default"
    assert findings[0].analysis["governing_controls"] == ["action-risk-analysis"]

    positive_tools = {
        component.name: component
        for component in ir.components
        if component.kind == "tool" and component.evidence.path == "positive.py"
    }
    assert set(positive_tools) == {"TerminalTool@8", "FileEditorTool@9"}
    assert positive_tools["TerminalTool@8"].attributes["approval_policy"] == ("disabled-default")
    assert {
        (edge.source_name, edge.target_name, edge.target_id)
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.relation == "uses"
        and edge.evidence.path == "positive.py"
    } == {
        (
            "Agent",
            "TerminalTool@8",
            "py:positive.py#tool:TerminalTool@8",
        ),
        (
            "Agent",
            "FileEditorTool@9",
            "py:positive.py#tool:FileEditorTool@9",
        ),
    }

    approval_edges = [
        edge
        for edge in ir.relationships
        if edge.evidence.path == "guarded.py"
        and edge.relation == "governed-by"
        and edge.target_name == "human-approval"
    ]
    assert {(edge.source_name, edge.evidence.line) for edge in approval_edges} == {
        ("TerminalTool@9", 9),
        ("FileEditorTool@10", 10),
    }
    assert all(
        edge.attributes["risk_threshold"] == "MEDIUM"
        and edge.attributes["confirm_unknown"] is False
        and edge.attributes["control_line"] == 15
        for edge in approval_edges
    )
    assert not any(
        finding.evidence.path in {"dynamic_policy.py", "guarded.py"} for finding in findings
    )
    assert not any(
        component.attributes.get("analysis") == "python-openhands-conversation-security"
        and component.evidence.path
        in {
            "lookalike.py",
            "near_miss.py",
            "rebound.py",
            "shared_agent.py",
        }
        for component in ir.components
    )
    forward_tools = [
        component
        for component in ir.components
        if component.kind == "tool" and component.evidence.path == "forward_setter.py"
    ]
    assert len(forward_tools) == 1
    assert forward_tools[0].attributes["approval_policy"] == "unresolved"
    assert not any(
        component.kind == "control"
        and component.name == "action-risk-analysis"
        and component.evidence.path == "forward_setter.py"
        for component in ir.components
    )
    assert any(
        component.kind == "framework"
        and component.name == "OpenHands SDK"
        and component.evidence.path == "positive.py"
        for component in ir.components
    )
    assert not any(
        component.kind == "framework"
        and component.name == "OpenHands SDK"
        and component.evidence.path == "lookalike.py"
        for component in ir.components
    )


def test_trae_agent_default_tools_require_the_exact_cross_file_composition(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_trae_agent_default_tools"
    ir = scan_repository(root / "positive")

    findings = [
        (finding.rule_id, finding.evidence.path, finding.evidence.line, finding.ir_path)
        for finding in ir.findings
        if finding.rule_id in {"AV-APPROVAL002", "AV-EXEC001", "AV-FS001"}
    ]
    assert findings == [
        (
            "AV-APPROVAL002",
            "trae_agent/tools/bash_tool.py",
            35,
            (
                "agent:TraeAgent default toolchain",
                "tool:Trae BashTool",
                "capability:shell-execution",
            ),
        ),
        (
            "AV-EXEC001",
            "trae_agent/tools/bash_tool.py",
            35,
            (
                "agent:TraeAgent default toolchain",
                "tool:Trae BashTool",
                "capability:shell-execution",
            ),
        ),
        (
            "AV-FS001",
            "trae_agent/tools/edit_tool.py",
            19,
            (
                "agent:TraeAgent default toolchain",
                "tool:Trae TextEditorTool",
                "capability:filesystem",
            ),
        ),
    ]
    specialized = [
        component
        for component in ir.components
        if component.attributes.get("analysis") == "python-trae-agent-default-tools"
    ]
    assert {(component.kind, component.name) for component in specialized} == {
        ("agent", "TraeAgent default toolchain"),
        ("tool", "Trae BashTool"),
        ("tool", "Trae TextEditorTool"),
        ("capability", "shell-execution"),
        ("capability", "filesystem"),
        ("control-setting", "agent-action-confirmation"),
        ("control-setting", "tool-execution-isolation"),
    }
    shell = next(
        component
        for component in specialized
        if component.kind == "capability" and component.name == "shell-execution"
    )
    filesystem = next(
        component
        for component in specialized
        if component.kind == "capability" and component.name == "filesystem"
    )
    assert shell.attributes["command_sink"] == "shell-process-stdin"
    assert shell.attributes["sandbox_boundary_scope"] == "disabled-default"
    assert filesystem.attributes["path_requirement"] == "absolute-only"
    assert filesystem.attributes["path_boundary_scope"] == "unconstrained"
    assert (
        sum(
            edge.attributes.get("analysis") == "python-trae-agent-default-tools"
            and edge.source_kind == "agent"
            and edge.relation == "uses"
            and edge.target_kind == "tool"
            for edge in ir.relationships
        )
        == 2
    )

    near = scan_repository(root / "near")
    assert not any(
        component.name == "Trae Agent"
        or component.attributes.get("analysis") == "python-trae-agent-default-tools"
        for component in near.components
    )

    changed_default = tmp_path / "changed-default"
    shutil.copytree(root / "positive", changed_default)
    config_path = changed_default / "trae_agent/utils/config.py"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace('"bash",', '"safe_read",'),
        encoding="utf-8",
    )
    changed_ir = scan_repository(changed_default)
    assert not any(
        component.attributes.get("analysis") == "python-trae-agent-default-tools"
        for component in changed_ir.components
    )


def test_roo_command_auto_approval_requires_the_exact_cross_file_composition(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_roo_command_approval"
    ir = scan_repository(root / "positive")

    findings = [
        (finding.rule_id, finding.evidence.path, finding.evidence.line, finding.ir_path)
        for finding in ir.findings
        if finding.rule_id in {"AV-APPROVAL007", "AV-EXEC001"}
    ]
    assert findings == [
        (
            "AV-APPROVAL007",
            "src/core/auto-approval/commands.ts",
            8,
            (
                "agent:Roo Code native tool runtime",
                "tool:Roo ExecuteCommandTool",
                "control:command-allowlist",
            ),
        ),
        (
            "AV-EXEC001",
            "src/core/tools/ExecuteCommandTool.ts",
            18,
            (
                "agent:Roo Code native tool runtime",
                "tool:Roo ExecuteCommandTool",
                "capability:shell-execution",
            ),
        ),
    ]
    specialized = [
        component
        for component in ir.components
        if component.attributes.get("analysis") == "typescript-roo-command-auto-approval"
    ]
    assert {(component.kind, component.name) for component in specialized} == {
        ("agent", "Roo Code native tool runtime"),
        ("tool", "Roo ExecuteCommandTool"),
        ("capability", "shell-execution"),
        ("control", "command-allowlist"),
        ("control-setting", "command-auto-approval"),
    }
    control = next(component for component in specialized if component.kind == "control")
    setting = next(component for component in specialized if component.kind == "control-setting")
    assert control.attributes["match_semantics"] == "raw-string-prefix"
    assert control.attributes["token_boundary"] is False
    assert control.attributes["dangerous_substitution_guard"] is True
    assert setting.attributes["enabled"] is False
    assert (
        sum(
            edge.attributes.get("analysis") == "typescript-roo-command-auto-approval"
            for edge in ir.relationships
        )
        == 4
    )
    assert any(
        component.kind == "framework" and component.name == "Roo Code"
        for component in ir.components
    )

    near = scan_repository(root / "near")
    assert not any(
        component.name == "Roo Code"
        or component.attributes.get("analysis") == "typescript-roo-command-auto-approval"
        for component in near.components
    )

    bounded = tmp_path / "bounded"
    shutil.copytree(root / "positive", bounded)
    commands_path = bounded / "src/core/auto-approval/commands.ts"
    commands_path.write_text(
        commands_path.read_text(encoding="utf-8").replace(
            "trimmedCommand.startsWith(lowerPrefix)",
            "trimmedCommand === lowerPrefix || trimmedCommand.startsWith(`${lowerPrefix} `)",
        ),
        encoding="utf-8",
    )
    bounded_ir = scan_repository(bounded)
    assert not any(
        component.attributes.get("analysis") == "typescript-roo-command-auto-approval"
        for component in bounded_ir.components
    )
    assert not any(finding.rule_id == "AV-APPROVAL007" for finding in bounded_ir.findings)


def test_continue_plan_mode_approval_requires_the_exact_cross_file_composition(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_continue_plan_mode_approval"
    ir = scan_repository(root / "positive")

    findings = [
        (finding.rule_id, finding.evidence.path, finding.evidence.line, finding.ir_path)
        for finding in ir.findings
        if finding.rule_id in {"AV-APPROVAL008", "AV-EXEC001"}
    ]
    assert findings == [
        (
            "AV-APPROVAL008",
            "extensions/cli/src/permissions/permissionChecker.ts",
            21,
            (
                "agent:Continue CLI plan-mode runtime",
                "tool:Continue Bash tool",
                "control:terminal-command-risk-policy",
            ),
        ),
        (
            "AV-EXEC001",
            "extensions/cli/src/tools/runTerminalCommand.ts",
            20,
            (
                "agent:Continue CLI plan-mode runtime",
                "tool:Continue Bash tool",
                "capability:shell-execution",
            ),
        ),
    ]
    specialized = [
        component
        for component in ir.components
        if component.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
    ]
    assert {(component.kind, component.name) for component in specialized} == {
        ("framework", "Continue CLI"),
        ("agent", "Continue CLI plan-mode runtime"),
        ("tool", "Continue Bash tool"),
        ("capability", "shell-execution"),
        ("control-setting", "plan-mode-command-approval"),
        ("control", "terminal-command-risk-policy"),
    }
    control = next(component for component in specialized if component.kind == "control")
    setting = next(component for component in specialized if component.kind == "control-setting")
    assert control.attributes["high_risk_evaluation"] == "allowedWithPermission"
    assert control.attributes["high_risk_effective_permission"] == "allow"
    assert control.attributes["critical_evaluation"] == "disabled"
    assert control.attributes["critical_effective_permission"] == "exclude"
    assert setting.attributes["mode_default"] is False
    assert setting.attributes["normal_mode_shell_permission"] == "ask"
    assert setting.attributes["user_configuration_precedence"] == "ignored-in-plan-mode"
    assert (
        sum(
            edge.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
            for edge in ir.relationships
        )
        == 4
    )

    for directory in ("near", "safe"):
        negative = scan_repository(root / directory)
        assert not any(
            component.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
            for component in negative.components
        )
        assert not any(finding.rule_id == "AV-APPROVAL008" for finding in negative.findings)

    mutations = {
        "plan-bash-asks": (
            "extensions/cli/src/permissions/defaultPolicies.ts",
            '{ tool: "Bash", permission: "allow" }',
            '{ tool: "Bash", permission: "ask" }',
        ),
        "normal-bash-allows": (
            "extensions/cli/src/permissions/defaultPolicies.ts",
            '{ tool: "Bash", permission: "ask" }',
            '{ tool: "Bash", permission: "allow" }',
        ),
        "dynamic-ask-wins": (
            "extensions/cli/src/permissions/permissionChecker.ts",
            (
                "// Otherwise, user preference wins - return the original base permission\n"
                "    return { permission: basePermission };"
            ),
            'if (evaluatedPolicy === "allowedWithPermission") return { permission: "ask" };',
        ),
        "critical-not-hard-blocked": (
            "packages/terminal-security/src/evaluateTerminalCommandSecurity.ts",
            'return "disabled";',
            'return "allowedWithPermission";',
        ),
        "high-risk-auto-allowed": (
            "packages/terminal-security/src/evaluateTerminalCommandSecurity.ts",
            (
                "if (isHighRiskCommand(baseCommand, args, originalCommand)) {\n"
                '    return "allowedWithPermission";\n'
                "  }"
            ),
            (
                "if (isHighRiskCommand(baseCommand, args, originalCommand)) {\n"
                '    return "allowedWithoutPermission";\n'
                "  }"
            ),
        ),
        "argv-without-shell-command": (
            "extensions/cli/src/tools/runTerminalCommand.ts",
            'args: ["-l", "-c", command]',
            'args: ["--fixed"]',
        ),
    }
    for name, (relative, before, after) in mutations.items():
        changed = tmp_path / name
        shutil.copytree(root / "positive", changed)
        path = changed / relative
        original = path.read_text(encoding="utf-8")
        assert before in original
        path.write_text(original.replace(before, after, 1), encoding="utf-8")
        changed_ir = scan_repository(changed)
        assert not any(
            component.attributes.get("analysis") == "typescript-continue-plan-mode-approval"
            for component in changed_ir.components
        )
        assert not any(finding.rule_id == "AV-APPROVAL008" for finding in changed_ir.findings)


def test_continue_plan_mode_mcp_approval_requires_the_exact_cross_file_composition(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_continue_plan_mode_approval"
    ir = scan_repository(root / "positive")

    findings = [
        (finding.rule_id, finding.evidence.path, finding.evidence.line, finding.ir_path)
        for finding in ir.findings
        if finding.rule_id == "AV-APPROVAL009"
    ]
    assert findings == [
        (
            "AV-APPROVAL009",
            "extensions/cli/src/tools/index.tsx",
            11,
            (
                "agent:Continue CLI plan-mode MCP runtime",
                "tool:Continue MCP tool adapter",
                "control:mcp-tool-classification",
            ),
        )
    ]
    specialized = [
        component
        for component in ir.components
        if component.attributes.get("analysis") == "typescript-continue-plan-mode-mcp-approval"
    ]
    assert {(component.kind, component.name) for component in specialized} == {
        ("agent", "Continue CLI plan-mode MCP runtime"),
        ("tool", "Continue MCP tool adapter"),
        ("capability", "mcp-tool-invocation"),
        ("mcp-server", "Continue configured MCP servers"),
        ("control-setting", "plan-mode-mcp-approval"),
        ("control", "mcp-tool-classification"),
    }
    control = next(component for component in specialized if component.kind == "control")
    setting = next(component for component in specialized if component.kind == "control-setting")
    assert control.attributes["readonly_metadata"] == "discarded"
    assert control.attributes["risk_classification"] == "absent-on-proven-path"
    assert control.attributes["approval_prompt_on_allow"] is False
    assert setting.attributes["mode_default"] is False
    assert setting.attributes["normal_mode_external_tool_permission"] == "ask"
    assert setting.attributes["plan_mode_external_tool_permission"] == "allow"
    assert (
        sum(
            edge.attributes.get("analysis") == "typescript-continue-plan-mode-mcp-approval"
            for edge in ir.relationships
        )
        == 5
    )

    for directory in ("near", "safe"):
        negative = scan_repository(root / directory)
        assert not any(
            component.attributes.get("analysis") == "typescript-continue-plan-mode-mcp-approval"
            for component in negative.components
        )
        assert not any(finding.rule_id == "AV-APPROVAL009" for finding in negative.findings)

    mutations = {
        "plan-wildcard-asks": (
            "extensions/cli/src/permissions/defaultPolicies.ts",
            '{ tool: "*", permission: "allow" }',
            '{ tool: "*", permission: "ask" }',
        ),
        "normal-wildcard-allows": (
            "extensions/cli/src/permissions/defaultPolicies.ts",
            '{ tool: "*", permission: "ask" }',
            '{ tool: "*", permission: "allow" }',
        ),
        "plan-policy-not-installed": (
            "extensions/cli/src/services/ToolPermissionService.ts",
            "return [...PLAN_MODE_POLICIES]",
            "return []",
        ),
        "checker-does-not-first-match": (
            "extensions/cli/src/permissions/permissionChecker.ts",
            "      break;",
            "      continue;",
        ),
        "allow-still-prompts": (
            "extensions/cli/src/stream/streamChatResponse.helpers.ts",
            "    return { approved: true };",
            "    return { approved: await requestUserPermission(toolCall, callbacks) };",
        ),
        "adapter-retains-readonly": (
            "extensions/cli/src/tools/index.tsx",
            "    readonly: undefined,",
            "    readonly: mcpTool.annotations?.readOnlyHint === true,",
        ),
        "adapter-does-not-dispatch": (
            "extensions/cli/src/tools/index.tsx",
            "services.mcp?.runTool(mcpTool.name, args)",
            "reviewedMcpTools.run(mcpTool.name, args)",
        ),
        "server-does-not-discover": (
            "extensions/cli/src/services/MCPService.ts",
            "(await connection.client.listTools()).tools",
            "reviewedTools",
        ),
        "server-does-not-invoke": (
            "extensions/cli/src/services/MCPService.ts",
            "connection.client.callTool({",
            "reviewedClient.callTool({",
        ),
    }
    for name, (relative, before, after) in mutations.items():
        changed = tmp_path / name
        shutil.copytree(root / "positive", changed)
        path = changed / relative
        original = path.read_text(encoding="utf-8")
        assert before in original
        path.write_text(original.replace(before, after, 1), encoding="utf-8")
        changed_ir = scan_repository(changed)
        assert not any(
            component.attributes.get("analysis") == "typescript-continue-plan-mode-mcp-approval"
            for component in changed_ir.components
        )
        assert not any(finding.rule_id == "AV-APPROVAL009" for finding in changed_ir.findings)


def test_cline_subagent_approval_requires_the_exact_cross_file_composition(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_cline_subagent_approval"
    ir = scan_repository(root / "positive")

    findings = [
        (finding.rule_id, finding.evidence.path, finding.evidence.line, finding.ir_path)
        for finding in ir.findings
        if finding.rule_id == "AV-APPROVAL010"
    ]
    assert findings == [
        (
            "AV-APPROVAL010",
            "sdk/packages/core/src/runtime/host/local/spawn-tool.ts",
            10,
            (
                "agent:Cline VS Code SDK root agent",
                "tool:Cline spawn_agent tool",
                "control:subagent-tool-approval-propagation",
            ),
        )
    ]
    specialized = [
        component
        for component in ir.components
        if component.attributes.get("analysis") == "typescript-cline-subagent-approval-propagation"
    ]
    assert {(component.kind, component.name) for component in specialized} == {
        ("framework", "Cline SDK"),
        ("agent", "Cline VS Code SDK root agent"),
        ("agent", "Cline SDK spawned sub-agent"),
        ("tool", "Cline spawn_agent tool"),
        ("capability", "subagent-privileged-tool-execution"),
        ("control-setting", "Cline SDK tool approval policy"),
        ("control", "subagent-tool-approval-propagation"),
    }
    control = next(component for component in specialized if component.kind == "control")
    setting = next(component for component in specialized if component.kind == "control-setting")
    assert control.attributes["parent_approval_callback"] == "configured"
    assert control.attributes["child_approval_callback"] == "not-forwarded"
    assert control.attributes["child_tool_policies"] == "not-forwarded"
    assert control.attributes["factory_supports_propagation"] is True
    assert setting.attributes["default_for_unlisted_tools"] == "auto-approved"
    assert setting.attributes["spawn_agent_listed"] is False
    assert (
        sum(
            edge.attributes.get("analysis") == "typescript-cline-subagent-approval-propagation"
            for edge in ir.relationships
        )
        == 5
    )

    near = scan_repository(root / "near")
    assert not any(
        component.attributes.get("analysis") == "typescript-cline-subagent-approval-propagation"
        for component in near.components
    )
    assert not any(finding.rule_id == "AV-APPROVAL010" for finding in near.findings)

    mutations = {
        "spawn-policy-gated": (
            "apps/vscode/src/sdk/sdk-tool-policies.ts",
            '  set(["run_commands", "execute_command"])\n',
            '  set(["run_commands", "execute_command"])\n  set(["spawn_agent"])\n',
        ),
        "policy-default-asks": (
            "sdk/packages/agents/src/agent-runtime.ts",
            "policy.autoApprove === false",
            "policy.autoApprove !== true",
        ),
        "root-policy-not-installed": (
            "apps/vscode/src/sdk/sdk-session-lifecycle.ts",
            "...(toolPolicies ? { toolPolicies } : {}),",
            "toolPolicies: undefined,",
        ),
        "root-callback-not-wired": (
            "apps/vscode/src/sdk/vscode-session-host.ts",
            "requestToolApproval: options.requestToolApproval,",
            "requestToolApproval: undefined,",
        ),
        "spawn-disabled-by-default": (
            "sdk/packages/core/src/runtime/orchestration/runtime-builder.ts",
            "config.enableSpawnAgent ?? preset.enableSpawnAgent ?? true",
            "config.enableSpawnAgent ?? false",
        ),
        "act-preset-does-not-spawn": (
            "sdk/packages/core/src/extensions/tools/presets.ts",
            "enableSpawnAgent: true,",
            "enableSpawnAgent: false,",
        ),
        "wrapper-forwards-approval-state": (
            "sdk/packages/core/src/runtime/host/local/spawn-tool.ts",
            "    createSubAgentTools,\n",
            "    createSubAgentTools,\n    toolPolicies: config.toolPolicies,\n    requestToolApproval: config.requestToolApproval,\n",
        ),
        "factory-does-not-propagate-policy": (
            "sdk/packages/core/src/extensions/tools/team/spawn-agent-tool.ts",
            "toolPolicies: config.toolPolicies,",
            "toolPolicies: undefined,",
        ),
    }
    for name, (relative, before, after) in mutations.items():
        changed = tmp_path / name
        shutil.copytree(root / "positive", changed)
        path = changed / relative
        original = path.read_text(encoding="utf-8")
        assert before in original
        path.write_text(original.replace(before, after, 1), encoding="utf-8")
        changed_ir = scan_repository(changed)
        assert not any(
            component.attributes.get("analysis") == "typescript-cline-subagent-approval-propagation"
            for component in changed_ir.components
        )
        assert not any(finding.rule_id == "AV-APPROVAL010" for finding in changed_ir.findings)

    ignored_host_arguments = tmp_path / "ignored-host-arguments"
    shutil.copytree(root / "positive", ignored_host_arguments)
    host_path = ignored_host_arguments / "sdk/packages/core/src/runtime/host/local-runtime-host.ts"
    host_text = host_path.read_text(encoding="utf-8")
    before = "          sessionToolExecutors,\n"
    assert before in host_text
    host_path.write_text(
        host_text.replace(
            before,
            before
            + "          bootstrap.toolPolicies,\n"
            + "          bootstrap.requestToolApproval,\n",
            1,
        ),
        encoding="utf-8",
    )
    ignored_ir = scan_repository(ignored_host_arguments)
    assert any(finding.rule_id == "AV-APPROVAL010" for finding in ignored_ir.findings)


def test_cline_cli_subagent_approval_requires_the_exact_cross_file_composition(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_cline_subagent_approval_cli"
    ir = scan_repository(root / "positive")

    findings = [
        (finding.rule_id, finding.evidence.path, finding.evidence.line, finding.ir_path)
        for finding in ir.findings
        if finding.rule_id == "AV-APPROVAL010"
    ]
    assert findings == [
        (
            "AV-APPROVAL010",
            "sdk/packages/core/src/runtime/host/local/spawn-tool.ts",
            10,
            (
                "agent:Cline CLI sandbox root agent",
                "tool:Cline CLI spawn_agent tool",
                "control:subagent-tool-approval-propagation",
            ),
        )
    ]
    specialized = [
        component
        for component in ir.components
        if component.attributes.get("analysis")
        == "typescript-cline-cli-subagent-approval-propagation"
    ]
    assert {(component.kind, component.name) for component in specialized} == {
        ("framework", "Cline SDK"),
        ("agent", "Cline CLI sandbox root agent"),
        ("agent", "Cline SDK spawned sub-agent"),
        ("tool", "Cline CLI spawn_agent tool"),
        ("capability", "subagent-privileged-tool-execution"),
        ("control-setting", "Cline CLI tool approval policy"),
        ("control", "subagent-tool-approval-propagation"),
    }
    control = next(component for component in specialized if component.kind == "control")
    setting = next(component for component in specialized if component.kind == "control-setting")
    assert control.attributes["parent_host"] == "cli-sandbox"
    assert control.attributes["root_backend_forced_local_by_sandbox"] is True
    assert control.attributes["parent_approval_callback"] == "configured"
    assert control.attributes["child_approval_callback"] == "not-forwarded"
    assert control.attributes["child_tool_policies"] == "not-forwarded"
    assert control.attributes["factory_supports_propagation"] is True
    assert control.attributes["spawn_agent_policy"] == "parent-approval-required"
    assert setting.attributes["default_for_unlisted_tools"] == ("approval-required-when-disabled")
    assert setting.attributes["spawn_agent_listed"] is False
    assert (
        sum(
            edge.attributes.get("analysis") == "typescript-cline-cli-subagent-approval-propagation"
            for edge in ir.relationships
        )
        == 5
    )

    for directory in ("near", "safe"):
        negative = scan_repository(root / directory)
        assert not any(
            component.attributes.get("analysis")
            == "typescript-cline-cli-subagent-approval-propagation"
            for component in negative.components
        )
        assert not any(finding.rule_id == "AV-APPROVAL010" for finding in negative.findings)

    mutations = {
        "spawn-safe-listed": (
            "apps/cli/src/runtime/tool-policies.ts",
            '  "search_codebase",\n',
            '  "search_codebase",\n  "spawn_agent",\n',
        ),
        "unlisted-tools-auto-approved": (
            "apps/cli/src/runtime/tool-policies.ts",
            "        : false,",
            "        : true,",
        ),
        "cli-spawn-disabled": (
            "apps/cli/src/main.ts",
            "  enableSpawnAgent: !isYoloMode,",
            "  enableSpawnAgent: false,",
        ),
        "cli-not-local-for-sandbox": (
            "apps/cli/src/runtime/run-agent.ts",
            "forceLocalBackend: isYoloMode || config.sandbox === true",
            "forceLocalBackend: isYoloMode",
        ),
        "cli-callback-not-wired": (
            "apps/cli/src/runtime/run-agent.ts",
            "      requestToolApproval,\n",
            "      requestToolApproval: undefined,\n",
        ),
        "cli-policies-not-wired": (
            "apps/cli/src/runtime/run-agent.ts",
            "    toolPolicies: config.toolPolicies,",
            "    toolPolicies: undefined,",
        ),
        "cli-core-not-local": (
            "apps/cli/src/session/session.ts",
            'options?.forceLocalBackend ? "local" : undefined',
            'options?.forceLocalBackend ? "managed" : undefined',
        ),
        "wrapper-forwards-approval-state": (
            "sdk/packages/core/src/runtime/host/local/spawn-tool.ts",
            "    createSubAgentTools,\n",
            "    createSubAgentTools,\n    toolPolicies: config.toolPolicies,\n    requestToolApproval: config.requestToolApproval,\n",
        ),
        "factory-does-not-propagate-policy": (
            "sdk/packages/core/src/extensions/tools/team/spawn-agent-tool.ts",
            "toolPolicies: config.toolPolicies,",
            "toolPolicies: undefined,",
        ),
    }
    for name, (relative, before, after) in mutations.items():
        changed = tmp_path / name
        shutil.copytree(root / "positive", changed)
        path = changed / relative
        original = path.read_text(encoding="utf-8")
        assert before in original
        path.write_text(original.replace(before, after, 1), encoding="utf-8")
        changed_ir = scan_repository(changed)
        assert not any(
            component.attributes.get("analysis")
            == "typescript-cline-cli-subagent-approval-propagation"
            for component in changed_ir.components
        )
        assert not any(finding.rule_id == "AV-APPROVAL010" for finding in changed_ir.findings)


def test_letta_default_tools_require_the_exact_cross_file_composition(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_letta_default_tools"
    ir = scan_repository(root / "positive")

    findings = [
        (finding.rule_id, finding.evidence.path, finding.evidence.line, finding.ir_path)
        for finding in ir.findings
        if finding.rule_id in {"AV-APPROVAL002", "AV-EXEC001", "AV-FS001"}
    ]
    assert findings == [
        (
            "AV-APPROVAL002",
            "src/tools/impl/bash.ts",
            19,
            (
                "agent:Letta Code default client toolchain",
                "tool:Letta Bash tool",
                "capability:shell-execution",
            ),
        ),
        (
            "AV-EXEC001",
            "src/tools/impl/bash.ts",
            19,
            (
                "agent:Letta Code default client toolchain",
                "tool:Letta Bash tool",
                "capability:shell-execution",
            ),
        ),
        (
            "AV-FS001",
            "src/tools/impl/write.ts",
            11,
            (
                "agent:Letta Code default client toolchain",
                "tool:Letta Write tool",
                "capability:filesystem",
            ),
        ),
    ]
    specialized = [
        component
        for component in ir.components
        if component.attributes.get("analysis") == "typescript-letta-default-tools"
    ]
    assert {(component.kind, component.name) for component in specialized} == {
        ("agent", "Letta Code default client toolchain"),
        ("tool", "Letta Bash tool"),
        ("tool", "Letta Write tool"),
        ("capability", "shell-execution"),
        ("capability", "filesystem"),
        ("control-setting", "agent-action-confirmation"),
        ("control-setting", "tool-execution-isolation"),
    }
    approval = next(
        component
        for component in specialized
        if component.kind == "control-setting" and component.name == "agent-action-confirmation"
    )
    isolation = next(
        component
        for component in specialized
        if component.kind == "control-setting" and component.name == "tool-execution-isolation"
    )
    filesystem = next(
        component
        for component in specialized
        if component.kind == "capability" and component.name == "filesystem"
    )
    assert approval.attributes["enabled"] is False
    assert approval.attributes["explicit_deny_precedence"] is True
    assert approval.attributes["cli_deny_precedence"] is True
    assert approval.attributes["always_ask_precedence"] is True
    assert approval.attributes["workspace_guard_precedence"] is True
    assert approval.attributes["cross_agent_guard_precedence"] is True
    assert isolation.attributes["environment_variable"] == "LETTA_FS_SANDBOX"
    assert isolation.attributes["available_controls"] == [
        "workspace-sandbox",
        "kernel-shell-sandbox",
        "cross-agent-memory-guard",
    ]
    assert filesystem.attributes["path_boundary_scope"] == "cross-agent-only-default"
    assert (
        sum(
            edge.attributes.get("analysis") == "typescript-letta-default-tools"
            for edge in ir.relationships
        )
        == 8
    )
    assert any(
        component.kind == "framework" and component.name == "Letta Code"
        for component in ir.components
    )

    near = scan_repository(root / "near")
    assert not any(
        component.name == "Letta Code"
        or component.attributes.get("analysis") == "typescript-letta-default-tools"
        for component in near.components
    )

    standard_default = tmp_path / "standard-default"
    shutil.copytree(root / "positive", standard_default)
    mode_path = standard_default / "src/permissions/mode.ts"
    mode_path.write_text(
        (root / "safe/src/permissions/mode.ts").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    standard_ir = scan_repository(standard_default)
    assert not any(
        component.attributes.get("analysis") == "typescript-letta-default-tools"
        for component in standard_ir.components
    )
    assert not any(
        finding.rule_id in {"AV-APPROVAL002", "AV-EXEC001", "AV-FS001"}
        for finding in standard_ir.findings
    )


def test_semantic_kernel_mcp_sampling_auto_approval_resolves_server_model_authority(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_semantic_kernel_mcp_sampling"
    ir = scan_repository(root)
    findings = [finding for finding in ir.findings if finding.rule_id == "AV-MCP004"]
    assert [
        (finding.evidence.path, finding.evidence.line, finding.ir_path) for finding in findings
    ] == [
        (
            "auto.py",
            9,
            (
                "agent:Sampler",
                "mcp-server:ReleaseNotes",
                "capability:model-sampling",
            ),
        )
    ]
    assert findings[0].result_kind == "review"
    assert findings[0].analysis["control_settings"] == ["mcp-sampling-approval"]
    assert findings[0].analysis["approval_coverage"] == "auto-approved-explicit"

    capabilities = {
        component.evidence.path: component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "model-sampling"
        and component.attributes.get("analysis") == "python-semantic-kernel-mcp-sampling-approval"
    }
    assert set(capabilities) == {
        "auto.py",
        "callback.py",
        "default_deny.py",
        "dynamic.py",
        "explicit_deny.py",
    }
    assert capabilities["auto.py"].attributes == {
        "input_authority": "mcp-server",
        "system_prompt_authority": "mcp-server",
        "model_hint_authority": "mcp-server",
        "sampling_parameters_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": "auto-approved-explicit",
        "auto_approved": True,
        "consent_callback": "absent",
        "configuration_call_line": 6,
        "sdk_source_path": "python/semantic_kernel/connectors/mcp.py",
        "scope": "production",
        "analysis": "python-semantic-kernel-mcp-sampling-approval",
    }
    assert capabilities["callback.py"].attributes["approval_policy"] == "callback-controlled"
    assert capabilities["callback.py"].attributes["consent_callback"] == "configured"
    assert capabilities["dynamic.py"].attributes["approval_policy"] == "unresolved-explicit"
    assert capabilities["default_deny.py"].attributes["approval_policy"] == "denied-default"
    assert capabilities["explicit_deny.py"].attributes["approval_policy"] == "denied-explicit"
    assert all(
        capabilities[path].attributes["auto_approved"] is False
        for path in ("default_deny.py", "explicit_deny.py")
    )

    deny_controls = {
        edge.evidence.path
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.source_name == "model-sampling"
        and edge.relation == "governed-by"
        and edge.target_kind == "control"
        and edge.target_name == "mcp-sampling-consent"
        and edge.attributes.get("policy_effect") == "denies-model-sampling-without-consent"
    }
    assert deny_controls == {"default_deny.py", "explicit_deny.py"}
    assert not any(
        finding.rule_id == "AV-APPROVAL001" and finding.evidence.path in {"auto.py", "callback.py"}
        for finding in ir.findings
    )
    assert not any(
        component.kind == "control-setting"
        and component.name == "auto-approval"
        and component.evidence.path in {"auto.py", "callback.py"}
        for component in ir.components
    )
    assert not any(
        component.attributes.get("analysis") == "python-semantic-kernel-mcp-sampling-approval"
        and component.evidence.path in {"disconnected.py", "unbound.py", "wrong_import.py"}
        for component in ir.components
    )

    changed_sdk = tmp_path / "changed-sdk-default"
    shutil.copytree(root, changed_sdk)
    sdk_path = changed_sdk / "python/semantic_kernel/connectors/mcp.py"
    sdk_source = sdk_path.read_text(encoding="utf-8")
    before = "sampling_auto_approve: bool = False"
    assert before in sdk_source
    sdk_path.write_text(
        sdk_source.replace(before, "sampling_auto_approve: bool = True"),
        encoding="utf-8",
    )
    changed_ir = scan_repository(changed_sdk)
    assert not any(
        edge.attributes.get("analysis") == "python-semantic-kernel-mcp-sampling-approval"
        for edge in changed_ir.relationships
    )


def test_mcp_sampling_callbacks_require_a_proven_user_decision() -> None:
    root = ROOT / "cases/mcp_sampling_consent"
    ir = scan_repository(root)
    analyses = {
        "python-mcp-sampling-callback-consent",
        "python-pydantic-ai-mcp-sampling-model",
        "typescript-mcp-sampling-handler-consent",
    }
    capabilities = {
        component.evidence.path: component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "model-sampling"
        and component.attributes.get("analysis") in analyses
    }
    assert set(capabilities) == {
        "pydantic_automatic.py",
        "python_automatic.py",
        "python_denied.py",
        "python_human.py",
        "python_unresolved.py",
        "typescript_automatic.ts",
        "typescript_human.ts",
        "typescript_late_confirm.ts",
        "typescript_unresolved.ts",
    }
    assert capabilities["pydantic_automatic.py"].attributes == {
        "frontend": "python",
        "input_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": "automatic-fulfilment",
        "response_created": True,
        "fulfilment_target": "model-provider",
        "callback_definition_line": None,
        "request_disclosure": "not-proven",
        "scope": "production",
        "analysis": "python-pydantic-ai-mcp-sampling-model",
        "adapter": "pydantic-ai-mcp-toolset",
        "configuration": "sampling-model",
        "handler_origin": "sdk-generated",
        "protocol_compatibility": "sdk-session-dependent",
    }
    assert capabilities["python_automatic.py"].attributes == {
        "frontend": "python",
        "input_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": "automatic-fulfilment",
        "response_created": True,
        "fulfilment_target": "handler-response",
        "callback_definition_line": 6,
        "request_disclosure": "not-proven",
        "scope": "production",
        "analysis": "python-mcp-sampling-callback-consent",
    }
    assert capabilities["python_denied.py"].attributes["approval_policy"] == "denied-handler"
    assert capabilities["python_denied.py"].attributes["fulfilment_target"] == "denial"
    assert capabilities["python_human.py"].attributes["approval_policy"] == "human-confirmed"
    assert (
        capabilities["python_unresolved.py"].attributes["approval_policy"] == "unresolved-handler"
    )
    assert (
        capabilities["typescript_automatic.ts"].attributes["approval_policy"]
        == "automatic-fulfilment"
    )
    assert capabilities["typescript_human.ts"].attributes == {
        "frontend": "typescript",
        "input_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": "human-confirmed",
        "response_created": True,
        "fulfilment_target": "model-provider",
        "callback_definition_line": 7,
        "request_disclosure": "full-request",
        "scope": "production",
        "analysis": "typescript-mcp-sampling-handler-consent",
    }
    assert capabilities["typescript_late_confirm.ts"].attributes["approval_policy"] == (
        "automatic-fulfilment"
    )
    assert (
        capabilities["typescript_unresolved.ts"].attributes["approval_policy"]
        == "unresolved-handler"
    )

    controls = {
        (component.name, component.evidence.path, component.evidence.line)
        for component in ir.components
        if component.kind == "control" and component.attributes.get("analysis") in analyses
    }
    assert controls == {
        ("mcp-sampling-consent", "python_human.py", 7),
        ("mcp-sampling-token-budget", "typescript_human.ts", 13),
        ("mcp-sampling-consent", "typescript_human.ts", 14),
    }
    findings = [finding for finding in ir.findings if finding.rule_id == "AV-MCP005"]
    assert [
        (finding.evidence.path, finding.evidence.line, finding.ir_path) for finding in findings
    ] == [
        (
            "pydantic_automatic.py",
            3,
            ("protocol:MCP", "capability:model-sampling"),
        ),
        (
            "python_automatic.py",
            16,
            ("protocol:MCP", "capability:model-sampling"),
        ),
        (
            "typescript_automatic.ts",
            8,
            ("protocol:MCP", "capability:model-sampling"),
        ),
        (
            "typescript_late_confirm.ts",
            8,
            ("protocol:MCP", "capability:model-sampling"),
        ),
    ]
    assert all(finding.result_kind == "review" for finding in findings)
    assert all(
        finding.analysis["approval_coverage"] == "automatic-fulfilment" for finding in findings
    )
    assert not any(
        component.attributes.get("analysis") in analyses
        and component.evidence.path
        in {
            "pydantic_conflict.py",
            "pydantic_conditional_import.py",
            "pydantic_none.py",
            "pydantic_reassigned.py",
            "pydantic_wrong_import.py",
            "python_wrong_import.py",
            "typescript_disconnected.ts",
            "typescript_missing_capability.ts",
            "typescript_wrong_import.ts",
        }
        for component in ir.components
    )


def test_mcp_elicitation_acceptance_requires_a_proven_user_decision() -> None:
    root = ROOT / "cases/mcp_elicitation_consent"
    ir = scan_repository(root)
    analyses = {
        "python-fastmcp-elicitation-handler-consent",
        "python-mcp-elicitation-callback-consent",
        "typescript-mcp-elicitation-handler-consent",
    }
    capabilities = {
        component.evidence.path: component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "user-elicitation"
        and component.attributes.get("analysis") in analyses
    }
    assert set(capabilities) == {
        "fastmcp_automatic.py",
        "fastmcp_declined.py",
        "fastmcp_human.py",
        "fastmcp_input_only.py",
        "fastmcp_message_only.py",
        "fastmcp_reassigned.py",
        "fastmcp_rebound_response_type.py",
        "fastmcp_shadowed_callback.py",
        "fastmcp_unknown_return.py",
        "fastmcp_unresolved.py",
        "python_automatic.py",
        "python_declined.py",
        "python_human.py",
        "python_unresolved.py",
        "typescript_automatic.ts",
        "typescript_declined.ts",
        "typescript_human.ts",
        "typescript_nested_action.ts",
        "typescript_unreturned.ts",
        "typescript_unresolved.ts",
    }
    assert capabilities["fastmcp_automatic.py"].attributes["approval_policy"] == (
        "automatic-accept"
    )
    assert capabilities["fastmcp_input_only.py"].attributes["approval_policy"] == (
        "automatic-accept"
    )
    assert capabilities["fastmcp_message_only.py"].attributes["approval_policy"] == (
        "human-confirmed"
    )
    assert capabilities["fastmcp_message_only.py"].attributes["url_disclosure"] == ("not-proven")
    assert capabilities["fastmcp_declined.py"].attributes["approval_policy"] == ("declined-handler")
    assert capabilities["fastmcp_unknown_return.py"].attributes["approval_policy"] == (
        "unresolved-handler"
    )
    assert capabilities["fastmcp_unresolved.py"].attributes["approval_policy"] == (
        "unresolved-handler"
    )
    assert capabilities["fastmcp_reassigned.py"].attributes["approval_policy"] == (
        "unresolved-handler"
    )
    assert (
        capabilities["fastmcp_rebound_response_type.py"].attributes["approval_policy"]
        == "unresolved-handler"
    )
    assert capabilities["fastmcp_shadowed_callback.py"].attributes["approval_policy"] == (
        "unresolved-handler"
    )
    assert capabilities["fastmcp_human.py"].attributes == {
        "frontend": "python",
        "input_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": "human-confirmed",
        "response_created": True,
        "acceptance_created": True,
        "elicitation_modes": ("form", "url"),
        "callback_definition_line": 5,
        "request_disclosure": "message-and-request-details",
        "url_disclosure": "full-url",
        "scope": "production",
        "analysis": "python-fastmcp-elicitation-handler-consent",
        "adapter": "fastmcp-client",
        "acceptance_semantics": "non-result-return-implies-accept",
    }
    assert capabilities["python_automatic.py"].attributes == {
        "frontend": "python",
        "input_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": "automatic-accept",
        "response_created": True,
        "acceptance_created": True,
        "elicitation_modes": ("form", "url"),
        "callback_definition_line": 6,
        "request_disclosure": "not-proven",
        "url_disclosure": "not-proven",
        "scope": "production",
        "analysis": "python-mcp-elicitation-callback-consent",
    }
    assert capabilities["python_declined.py"].attributes["approval_policy"] == ("declined-handler")
    assert capabilities["python_human.py"].attributes["approval_policy"] == ("human-confirmed")
    assert capabilities["python_human.py"].attributes["request_disclosure"] == (
        "message-and-request-details"
    )
    assert capabilities["python_unresolved.py"].attributes["approval_policy"] == (
        "unresolved-handler"
    )
    assert capabilities["typescript_automatic.ts"].attributes["approval_policy"] == (
        "automatic-accept"
    )
    assert capabilities["typescript_automatic.ts"].attributes["elicitation_modes"] == (
        "form",
        "url",
    )
    assert capabilities["typescript_declined.ts"].attributes["approval_policy"] == (
        "declined-handler"
    )
    assert capabilities["typescript_nested_action.ts"].attributes["approval_policy"] == (
        "unresolved-handler"
    )
    assert capabilities["typescript_unreturned.ts"].attributes["approval_policy"] == (
        "declined-handler"
    )
    assert capabilities["typescript_human.ts"].attributes == {
        "frontend": "typescript",
        "input_authority": "mcp-server",
        "response_destination": "mcp-server",
        "approval_policy": "human-confirmed",
        "response_created": True,
        "acceptance_created": True,
        "elicitation_modes": ("form", "url"),
        "callback_definition_line": 8,
        "request_disclosure": "message-and-request-details",
        "url_disclosure": "full-url",
        "scope": "production",
        "analysis": "typescript-mcp-elicitation-handler-consent",
    }
    assert capabilities["typescript_unresolved.ts"].attributes["approval_policy"] == (
        "unresolved-handler"
    )

    controls = {
        (component.evidence.path, component.evidence.line)
        for component in ir.components
        if component.kind == "control"
        and component.name == "mcp-elicitation-consent"
        and component.attributes.get("analysis") in analyses
    }
    assert controls == {
        ("fastmcp_human.py", 7),
        ("fastmcp_message_only.py", 7),
        ("python_human.py", 9),
        ("typescript_human.ts", 10),
    }
    assert (
        sum(
            relationship.source_kind == "protocol"
            and relationship.source_name == "MCP"
            and relationship.relation == "uses"
            and relationship.target_kind == "capability"
            and relationship.target_name == "user-elicitation"
            and relationship.attributes.get("analysis") in analyses
            for relationship in ir.relationships
        )
        == 20
    )
    findings = [finding for finding in ir.findings if finding.rule_id == "AV-MCP006"]
    assert [
        (finding.evidence.path, finding.evidence.line, finding.ir_path) for finding in findings
    ] == [
        (
            "fastmcp_automatic.py",
            8,
            ("protocol:MCP", "capability:user-elicitation"),
        ),
        (
            "fastmcp_input_only.py",
            9,
            ("protocol:MCP", "capability:user-elicitation"),
        ),
        (
            "python_automatic.py",
            15,
            ("protocol:MCP", "capability:user-elicitation"),
        ),
        (
            "typescript_automatic.ts",
            8,
            ("protocol:MCP", "capability:user-elicitation"),
        ),
    ]
    assert all(finding.result_kind == "review" for finding in findings)
    assert all(finding.analysis["approval_coverage"] == "automatic-accept" for finding in findings)
    url_findings = [finding for finding in ir.findings if finding.rule_id == "AV-MCP007"]
    assert [
        (finding.evidence.path, finding.evidence.line, finding.ir_path) for finding in url_findings
    ] == [
        (
            "fastmcp_message_only.py",
            15,
            ("protocol:MCP", "capability:user-elicitation"),
        ),
        (
            "python_human.py",
            17,
            ("protocol:MCP", "capability:user-elicitation"),
        ),
    ]
    assert all(finding.result_kind == "review" for finding in url_findings)
    assert all(
        finding.analysis["approval_coverage"] == "human-confirmed" for finding in url_findings
    )
    assert not any(
        component.attributes.get("analysis") in analyses
        and component.evidence.path
        in {
            "fastmcp_wrong_import.py",
            "python_wrong_import.py",
            "typescript_disconnected.ts",
            "typescript_missing_capability.ts",
            "typescript_reassigned.ts",
            "typescript_wrong_import.ts",
        }
        for component in ir.components
    )


def test_typescript_a2a_remote_cards_preserve_endpoint_authority_and_transport(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/typescript_a2a_card_endpoint"
    ir = scan_repository(root)
    capabilities = [
        item for item in ir.components if item.kind == "capability" and item.name == "a2a-rpc"
    ]
    assert [
        (item.evidence.path, item.evidence.line, item.attributes["analysis"])
        for item in capabilities
    ] == [
        (
            "a2a_remote_agent.ts",
            26,
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "gemini_manager.ts",
            60,
            "typescript-gemini-a2a-card-endpoint-composition",
        ),
    ]
    assert capabilities[0].attributes == {
        "scope": "production",
        "frontend": "typescript",
        "protocol": "a2a",
        "dynamic_origin": False,
        "origin_authority": "remote-agent-card",
        "remote_card_endpoint_scope": "unconstrained",
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
        "resolver_path": "agent_card.ts",
        "resolver_line": 5,
    }
    assert capabilities[1].attributes == {
        "scope": "production",
        "frontend": "typescript",
        "protocol": "a2a",
        "dynamic_origin": False,
        "origin_authority": "remote-agent-card",
        "remote_card_endpoint_scope": "unconstrained",
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
    }
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.rule_id == "AV-A2A001"
    ] == [
        ("AV-A2A001", "a2a_remote_agent.ts", 26),
        ("AV-A2A001", "gemini_manager.ts", 60),
    ]
    assert all(
        finding.ir_path == ("protocol:A2A", "capability:a2a-rpc")
        and finding.analysis["protocol"] == "A2A"
        for finding in ir.findings
        if finding.rule_id == "AV-A2A001"
    )
    assert not any(
        finding.rule_id == "AV-A2A001" and finding.evidence.path == "raw.ts"
        for finding in ir.findings
    )

    without_resolver = scan_repository(
        root,
        selected_paths=["a2a_remote_agent.ts"],
    )
    assert not any(
        item.attributes.get("analysis") == "typescript-adk-a2a-card-endpoint-composition"
        for item in without_resolver.components
    )

    for name, relative, before, after, analysis in (
        (
            "a2a-fixed-resolver",
            "agent_card.ts",
            "resolver.resolve(source)",
            "resolver.resolve('https://fixed.example/card')",
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "a2a-fixed-card",
            "a2a_remote_agent.ts",
            "factory.createFromAgentCard(this.card)",
            "factory.createFromAgentCard({url: 'https://fixed.example/rpc'})",
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "a2a-intervening-validator",
            "a2a_remote_agent.ts",
            "this.card = await resolveAgentCard(this.a2aConfig.agentCard);",
            "this.card = await resolveAgentCard(this.a2aConfig.agentCard);\n      await validateCardOrigin(this.card);",
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "a2a-wrong-resolver-import",
            "a2a_remote_agent.ts",
            "from './agent_card.js'",
            "from './raw.js'",
            "typescript-adk-a2a-card-endpoint-composition",
        ),
        (
            "gemini-fixed-card",
            "gemini_manager.ts",
            "factory.createFromAgentCard(agentCard)",
            "factory.createFromAgentCard({url: 'https://fixed.example/rpc'})",
            "typescript-gemini-a2a-card-endpoint-composition",
        ),
        (
            "gemini-unproven-dispatcher",
            "gemini_manager.ts",
            "dispatcher: this.a2aDispatcher",
            "dispatcher: undefined",
            "typescript-gemini-a2a-card-endpoint-composition",
        ),
        (
            "gemini-intervening-validator",
            "gemini_manager.ts",
            "const agentCard = normalizeAgentCard(rawCard);",
            "const agentCard = normalizeAgentCard(rawCard);\n    validateCardOrigin(agentCard, options);",
            "typescript-gemini-a2a-card-endpoint-composition",
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / relative
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            item.attributes.get("analysis") == analysis for item in incomplete_ir.components
        )


def test_python_a2a_card_policy_requires_all_interfaces_and_dominating_validation(
    tmp_path: Path,
) -> None:
    root = ROOT / "cases/python_a2a_card_endpoint"
    ir = scan_repository(root)
    edges = [
        edge
        for edge in ir.relationships
        if edge.target_kind == "control" and edge.target_name == "a2a-card-rpc-origin-policy"
    ]
    assert [(edge.evidence.path, edge.evidence.line) for edge in edges] == [
        ("remote_a2a_agent.py", 41),
        ("remote_a2a_agent.py", 48),
    ]
    assert all(
        edge.attributes["analysis"] == "python-google-adk-a2a-card-endpoint-policy"
        and edge.attributes["rpc_origin_scope"] == "same-origin-with-card-source"
        and edge.attributes["rpc_scheme_scope"] == "https-or-loopback-http"
        and edge.attributes["advertised_interface_scope"] == "all-rpc-urls"
        and edge.attributes["enforcement_mode"] == "always-on-for-network-cards"
        and edge.attributes["control_line"] == 21
        for edge in edges
    )
    assert not any(finding.rule_id == "AV-A2A001" for finding in ir.findings)

    for name, before, after in (
        (
            "a2a-primary-only",
            "_compat.agent_card_rpc_urls(agent_card)",
            "[_compat.agent_card_url(agent_card)]",
        ),
        (
            "a2a-cross-origin-allowed",
            "card_origin != source_origin",
            "card_origin == source_origin",
        ),
        (
            "a2a-http-allowed",
            'parsed_card.scheme.lower() != "https"',
            'parsed_card.scheme.lower() == "https"',
        ),
    ):
        incomplete = tmp_path / name
        shutil.copytree(root, incomplete)
        source_path = incomplete / "remote_a2a_agent.py"
        source = source_path.read_text(encoding="utf-8")
        assert before in source
        source_path.write_text(source.replace(before, after), encoding="utf-8")
        incomplete_ir = scan_repository(incomplete)
        assert not any(
            edge.target_kind == "control" and edge.target_name == "a2a-card-rpc-origin-policy"
            for edge in incomplete_ir.relationships
        )


def test_typescript_network_helper_summaries_map_object_parameters_and_multiline_aliases(
    tmp_path: Path,
) -> None:
    (tmp_path / "tools.ts").write_text(
        """import { createTool } from "@mastra/core/tools";

class Helpers {
  static async request({ baseUrl, route }: { baseUrl: string; route: string }) {
    const fullUrl = `${baseUrl}${route}`;
    return fetch(fullUrl);
  }
}

const request = createTool({
  id: "request",
  execute: async (inputData) => {
    const {
      baseUrl,
      route,
    } = inputData;
    return Helpers.request({
      baseUrl,
      route,
    });
  },
});
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    summarized = [
        item
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "same-file-helper"
    ]
    assert len(summarized) == 1
    assert summarized[0].attributes == {
        "scope": "production",
        "api": "request",
        "dynamic_origin": True,
        "summary": "same-file-helper",
        "helper_line": 4,
        "helper_network_calls": 1,
    }
    assert [
        (edge.source_name, edge.source_id)
        for edge in ir.relationships
        if edge.target_kind == "capability" and edge.target_name == "network"
    ] == [("request", "ts:tools.ts#tool:request")]
    assert [finding.rule_id for finding in ir.findings] == ["AV-NET001"]


def test_typescript_imported_path_boundary_suppresses_only_proven_guard() -> None:
    ir = scan_repository(ROOT / "cases/typescript_path_boundary")

    filesystem = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "filesystem"
        and item.evidence.path == "tools.ts"
    }
    assert filesystem == {
        10: {
            "scope": "production",
            "write_access": True,
            "dynamic_path": True,
            "path_boundary_guard": True,
            "path_boundary_scope": "constrained",
        },
        16: {
            "scope": "production",
            "write_access": True,
            "dynamic_path": True,
            "path_boundary_guard": False,
            "path_boundary_scope": "unresolved",
        },
        23: {
            "scope": "production",
            "write_access": True,
            "dynamic_path": True,
            "path_boundary_guard": False,
            "path_boundary_scope": "unresolved",
        },
    }
    controls = [
        item for item in ir.components if item.kind == "control" and item.name == "path-boundary"
    ]
    assert len(controls) == 1
    assert controls[0].evidence.path == "guard.ts"
    assert controls[0].evidence.line == 6
    assert controls[0].attributes["policy_effect"] == "restricts-filesystem-path"
    assert controls[0].attributes["predicate_path"] == "path-check.ts"
    assert controls[0].attributes["boundary_scope"] == "constrained"
    class_filesystem = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "filesystem"
        and item.evidence.path == "class-helper.ts"
    }
    assert class_filesystem == {
        9: {
            "scope": "production",
            "write_access": True,
            "dynamic_path": True,
            "path_boundary_guard": False,
            "path_boundary_scope": "unresolved",
            "path_prefix_check": True,
        },
        14: {
            "scope": "production",
            "write_access": True,
            "dynamic_path": True,
            "path_boundary_guard": False,
            "path_boundary_scope": "unresolved",
        },
    }
    assert [
        (
            edge.evidence.line,
            edge.attributes["control_line"],
            edge.attributes["policy_effect"],
            edge.attributes["frontend"],
            edge.attributes["helper"],
            edge.attributes["root"],
        )
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.target_kind == "control"
        and edge.target_name == "path-prefix-check"
        and edge.evidence.path == "class-helper.ts"
    ] == [(9, 19, "weak-string-prefix-validation", "typescript", "this.resolve", "this.root")]
    assert [
        (
            edge.evidence.line,
            edge.target_name,
            edge.attributes.get("control_path"),
            edge.attributes.get("policy_effect"),
            edge.attributes.get("predicate_path"),
            edge.attributes.get("boundary_scope"),
        )
        for edge in ir.relationships
        if edge.source_kind == "capability" and edge.relation == "governed-by"
    ] == [
        (
            9,
            "path-prefix-check",
            "class-helper.ts",
            "weak-string-prefix-validation",
            "class-helper.ts",
            None,
        ),
        (
            10,
            "path-boundary",
            "guard.ts",
            "restricts-filesystem-path",
            "path-check.ts",
            "constrained",
        )
    ]
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-FS001", 16, "unsafe-directory"),
        ("AV-FS001", 23, "reassigned-directory"),
    ]


def test_python_path_boundary_is_ordered_branch_local_and_scope_aware() -> None:
    ir = scan_repository(ROOT / "cases/python_path_boundary")

    filesystem = {
        item.evidence.line: (
            item.attributes["path_boundary_guard"],
            item.attributes["path_boundary_scope"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "filesystem"
    }
    assert filesystem == {
        12: (True, "constrained"),
        13: (True, "constrained"),
        22: (True, "constrained"),
        23: (False, "unresolved"),
        32: (False, "unresolved"),
        42: (False, "unresolved"),
        51: (True, "unresolved"),
        59: (False, "unresolved"),
        69: (False, "unresolved"),
        80: (False, "unresolved"),
        89: (False, "unresolved"),
        100: (True, "constrained"),
        111: (False, "unresolved"),
        123: (False, "unresolved"),
        134: (False, "unresolved"),
        145: (False, "unresolved"),
        152: (False, "unresolved"),
        163: (False, "unresolved"),
        176: (False, "unresolved"),
        189: (False, "unresolved"),
    }
    assert [
        (
            edge.evidence.line,
            edge.attributes["control_line"],
            edge.attributes["policy_effect"],
            edge.attributes["boundary_scope"],
            edge.attributes["frontend"],
            edge.attributes["helper"],
        )
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-boundary"
    ] == [
        (12, 10, "restricts-filesystem-path", "constrained", "python", "Path.is_relative_to"),
        (13, 10, "restricts-filesystem-path", "constrained", "python", "Path.is_relative_to"),
        (22, 21, "restricts-filesystem-path", "constrained", "python", "Path.is_relative_to"),
        (51, 49, "validates-filesystem-path", "unresolved", "python", "Path.is_relative_to"),
        (100, 97, "restricts-filesystem-path", "constrained", "python", "Path.relative_to"),
    ]
    assert [
        (
            edge.evidence.line,
            edge.attributes["control_line"],
            edge.attributes["policy_effect"],
            edge.attributes["strength"],
        )
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-prefix-check"
    ] == [
        (32, 30, "weak-string-prefix-validation", "weak-prefix"),
        (176, 172, "weak-string-prefix-validation", "weak-prefix"),
    ]
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-FS001", 23, "positive_branch"),
        ("AV-FS002", 32, "prefix_check"),
        ("AV-FS001", 42, "reassigned_candidate"),
        ("AV-FS001", 51, "configured_root"),
        ("AV-FS001", 59, "unresolved_candidate"),
        ("AV-FS001", 69, "reassigned_root"),
        ("AV-FS001", 80, "conditionally_reassigned_candidate"),
        ("AV-FS001", 89, "parent_without_strict_descendant"),
        ("AV-FS001", 111, "relative_to_continuing_handler"),
        ("AV-FS001", 123, "relative_to_nonexclusive_try"),
        ("AV-FS001", 134, "relative_to_parent_without_strict_descendant"),
        ("AV-FS001", 145, "relative_to_rebinds_candidate"),
        ("AV-FS001", 152, "prefix_after_write"),
        ("AV-FS001", 163, "separator_aware_prefix"),
        ("AV-FS002", 176, "prefix_inside_terminating_try"),
        ("AV-FS001", 189, "prefix_inside_continuing_try"),
    ]


def test_python_hex_digest_sanitizes_only_joined_path_segments() -> None:
    ir = scan_repository(ROOT / "cases/python_path_segment_sanitizer")

    filesystem = {
        item.evidence.line: item.attributes
        for item in ir.components
        if item.kind == "capability"
        and item.name == "filesystem"
        and item.evidence.path == "agent.py"
    }
    assert filesystem[13]["tool_input_path_sanitized"] is True
    assert all("tool_input_path_sanitized" not in filesystem[line] for line in (19, 25, 31, 38, 45))
    assert [
        (
            edge.evidence.line,
            edge.attributes["algorithm"],
            edge.attributes["output_encoding"],
            edge.attributes["sanitizer_path"],
            edge.attributes["policy_effect"],
        )
        for edge in ir.relationships
        if edge.target_name == "path-segment-sanitizer"
    ] == [
        (
            13,
            "sha256",
            "hexadecimal",
            "helper.py",
            "removes-path-separator-control",
        )
    ]
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-FS001", 19, "unsafe_extra_segment"),
        ("AV-FS001", 25, "unsafe_digest_root"),
        ("AV-FS001", 31, "unsafe_lookalike"),
        ("AV-FS001", 38, "unsafe_rebound"),
        ("AV-FS001", 45, "unsafe_branch_escape"),
        ("AV-FS001", 20, "mutated_join"),
        ("AV-FS001", 26, "mutated_hashlib"),
    ]

    shadowed = scan_repository(ROOT / "cases/python_path_segment_shadowed_hashlib")
    assert not any(edge.target_name == "path-segment-sanitizer" for edge in shadowed.relationships)
    assert [(finding.rule_id, finding.analysis["tool"]) for finding in shadowed.findings] == [
        ("AV-FS001", "shadowed_hashlib")
    ]


def test_python_path_helper_summary_is_return_exact_and_class_local() -> None:
    ir = scan_repository(ROOT / "cases/python_path_helper")

    filesystem = {
        item.evidence.line: (
            item.attributes["path_boundary_guard"],
            item.attributes["path_boundary_scope"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "filesystem"
    }
    assert filesystem == {
        23: (True, "unresolved"),
        24: (False, "unresolved"),
        30: (False, "unresolved"),
        48: (False, "unresolved"),
        67: (False, "unresolved"),
        86: (False, "unresolved"),
        104: (False, "unresolved"),
        125: (False, "unresolved"),
        145: (False, "unresolved"),
        165: (False, "unresolved"),
    }
    assert [
        (
            edge.evidence.line,
            edge.attributes["control_line"],
            edge.attributes["helper"],
            edge.attributes["summary"],
            edge.attributes["boundary_scope"],
        )
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-boundary"
    ] == [(23, 15, "Path.relative_to", "same-class-return", "unresolved")]
    assert [(finding.rule_id, finding.evidence.line) for finding in ir.findings] == [
        ("AV-FS001", 23),
        ("AV-FS001", 24),
        ("AV-FS001", 30),
        ("AV-FS001", 48),
        ("AV-FS001", 67),
        ("AV-FS001", 86),
        ("AV-FS001", 104),
        ("AV-FS001", 125),
        ("AV-FS001", 145),
        ("AV-FS001", 165),
    ]


def test_python_post_definition_tool_registration_is_exact_and_cross_file() -> None:
    ir = scan_repository(ROOT / "cases/python_post_registration")

    tools = {item.name: item for item in ir.components if item.kind == "tool"}
    assert set(tools) == {
        "direct_wrapped_write",
        "factory_wrapped_write",
        "imported_write",
        "local_write",
        "nested_wrapped_write",
    }
    assert tools["imported_write"].attributes == {
        "decorators": [],
        "needs_approval": True,
        "registration": "post-definition",
        "registration_path": "app/server.py",
        "registration_line": 31,
        "registrar": "mcp.tool",
        "resolution": "relative-import-single-definition",
    }
    assert tools["imported_write"].symbol_id == "py:app/tools.py#tool:imported_write"
    assert tools["local_write"].attributes["resolution"] == ("same-module-single-definition")
    assert tools["direct_wrapped_write"].attributes["wrappers"] == ["transparent"]
    assert tools["factory_wrapped_write"].attributes["wrappers"] == ["configured"]
    assert tools["nested_wrapped_write"].attributes["wrappers"] == [
        "transparent",
        "transparent",
    ]
    assert all(
        tools[name].attributes["wrapper_summary"] == "metadata-preserving-forwarder"
        for name in (
            "direct_wrapped_write",
            "factory_wrapped_write",
            "nested_wrapped_write",
        )
    )
    assert {
        (edge.source_name, edge.relation, edge.target_name, edge.evidence.path, edge.evidence.line)
        for edge in ir.relationships
    } == {
        ("imported_write", "governed-by", "human-approval", "app/server.py", 31),
        ("imported_write", "uses", "filesystem", "app/tools.py", 5),
        ("local_write", "uses", "filesystem", "app/server.py", 23),
        ("direct_wrapped_write", "uses", "filesystem", "app/tools.py", 21),
        ("factory_wrapped_write", "uses", "filesystem", "app/tools.py", 25),
        ("nested_wrapped_write", "uses", "filesystem", "app/tools.py", 29),
    }
    assert [
        (
            finding.rule_id,
            finding.evidence.path,
            finding.evidence.line,
            finding.analysis["tool"],
            finding.analysis["approval_coverage"],
        )
        for finding in ir.findings
    ] == [
        ("AV-FS001", "app/server.py", 23, "local_write", "unresolved"),
        ("AV-FS001", "app/tools.py", 5, "imported_write", "present"),
        ("AV-FS001", "app/tools.py", 21, "direct_wrapped_write", "unresolved"),
        ("AV-FS001", "app/tools.py", 25, "factory_wrapped_write", "unresolved"),
        ("AV-FS001", "app/tools.py", 29, "nested_wrapped_write", "unresolved"),
    ]


def test_python_browser_evaluate_requires_browser_import_and_tracks_dynamic_input(
    tmp_path: Path,
) -> None:
    ir = scan_repository(ROOT / "cases/python_browser_evaluate")

    executions = [
        (
            item.evidence.path,
            item.evidence.line,
            item.attributes["api"],
            item.attributes["execution_context"],
            item.attributes["dynamic_input"],
            item.attributes["receiver_proof"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "code-execution"
    ]
    assert executions == [
        ("agent.py", 9, "page.evaluate", "browser-page", True, "parameter-annotation"),
        ("agent.py", 14, "page.evaluate", "browser-page", False, "parameter-annotation"),
        ("agent.py", 20, "page.evaluate", "browser-page", True, "parameter-annotation"),
        (
            "agent.py",
            26,
            "browser_page.evaluate",
            "browser-page",
            True,
            "typed-parameter-alias",
        ),
        (
            "agent.py",
            34,
            "self.page.evaluate",
            "browser-page",
            True,
            "class-attribute-annotation",
        ),
        (
            "agent.py",
            43,
            "self.browser_page.evaluate",
            "browser-page",
            True,
            "class-attribute-annotation",
        ),
        (
            "agent.py",
            48,
            "first.evaluate",
            "browser-page",
            True,
            "playwright-derived-receiver",
        ),
        (
            "agent.py",
            54,
            "locator.evaluate",
            "browser-page",
            True,
            "playwright-derived-receiver",
        ),
        (
            "alternate.py",
            10,
            "page.eval_on_selector",
            "browser-page",
            True,
            "parameter-annotation",
        ),
        (
            "alternate.py",
            15,
            "page.eval_on_selector_all",
            "browser-page",
            False,
            "parameter-annotation",
        ),
        (
            "alternate.py",
            20,
            "page.evaluate_handle",
            "browser-page",
            True,
            "parameter-annotation",
        ),
        (
            "alternate.py",
            25,
            "locator.evaluate_all",
            "browser-page",
            True,
            "parameter-annotation",
        ),
        (
            "alternate.py",
            30,
            "page.evaluate",
            "browser-page",
            True,
            "parameter-annotation",
        ),
        (
            "branching_lifecycle.py",
            34,
            "self.page.evaluate",
            "browser-page",
            False,
            "branching-lifecycle-playwright-page",
        ),
        (
            "branching_lifecycle.py",
            53,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "branching_lifecycle.py",
            79,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "branching_lifecycle.py",
            99,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "branching_lifecycle.py",
            115,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "branching_lifecycle.py",
            135,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "branching_lifecycle.py",
            153,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "branching_lifecycle.py",
            180,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "constructor.py",
            16,
            "self.page.evaluate",
            "browser-page",
            True,
            "constructor-bound-playwright-page",
        ),
        (
            "constructor.py",
            21,
            "page.evaluate",
            "browser-page",
            True,
            "constructor-bound-playwright-page-alias",
        ),
        (
            "constructor.py",
            33,
            "self.page.evaluate",
            "browser-page",
            True,
            "constructor-bound-playwright-page",
        ),
        (
            "contextmanager.py",
            25,
            "page.evaluate",
            "browser-page",
            True,
            "local-playwright-contextmanager-yield",
        ),
        (
            "contextmanager.py",
            43,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "contextmanager.py",
            54,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "contextmanager.py",
            61,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "imported_field.py",
            12,
            "popup.evaluate",
            "browser-page",
            False,
            "imported-class-playwright-field-alias",
        ),
        (
            "imported_field.py",
            17,
            "popup.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "imported_field.py",
            22,
            "popup.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "imported_field.py",
            28,
            "popup.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "imported_field.py",
            34,
            "popup.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "local_construction.py",
            16,
            "page.evaluate",
            "browser-page",
            True,
            "local-playwright-page",
        ),
        (
            "module_annotation.py",
            19,
            "locator.evaluate",
            "browser-page",
            True,
            "module-variable-derived-receiver",
        ),
        (
            "module_guarded_import.py",
            20,
            "guarded_page.evaluate",
            "browser-page",
            True,
            "module-variable-annotation",
        ),
        (
            "property.py",
            18,
            "self.page.evaluate",
            "browser-page",
            True,
            "class-property-return-annotation",
        ),
        (
            "same_class_helper.py",
            19,
            "page.evaluate",
            "browser-page",
            False,
            "same-class-helper-parameter",
        ),
        (
            "same_class_helper.py",
            36,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_class_helper.py",
            53,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_class_helper.py",
            72,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_class_helper.py",
            93,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_class_helper.py",
            109,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_class_helper.py",
            124,
            "self.page.evaluate",
            "browser-page",
            False,
            "lifecycle-bound-playwright-page",
        ),
        (
            "same_class_helper.py",
            140,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_class_helper.py",
            156,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_class_helper.py",
            172,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_class_helper.py",
            187,
            "self.page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_module_helper.py",
            16,
            "page.evaluate",
            "browser-page",
            False,
            "same-module-contextmanager-page-parameter",
        ),
        (
            "same_module_helper.py",
            25,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_module_helper.py",
            39,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_module_helper.py",
            49,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_module_helper.py",
            60,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "same_module_helper.py",
            69,
            "page.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "type_checking.py",
            17,
            "self.page.evaluate",
            "browser-page",
            True,
            "class-attribute-annotation",
        ),
        (
            "wrapper_scope.py",
            13,
            "first.evaluate",
            "browser-page",
            False,
            "imported-browser-wrapper-scope",
        ),
        (
            "wrapper_scope.py",
            21,
            "first.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "wrapper_scope.py",
            29,
            "first.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "wrapper_scope.py",
            37,
            "first.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
        (
            "wrapper_scope.py",
            45,
            "first.evaluate",
            "browser-page",
            False,
            "unresolved-browser-import-context",
        ),
    ]
    assert [
        (edge.source_name, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "code-execution"
    ] == [
        ("dynamic_evaluate", 9),
        ("literal_evaluate", 14),
        ("aliased_evaluate", 20),
        ("aliased_page", 26),
        ("class_evaluate", 34),
        ("init_class_evaluate", 43),
        ("locator_evaluate", 48),
        ("locator_alias_evaluate", 54),
        ("selector_script", 10),
        ("selector_only", 15),
        ("handle_script", 20),
        ("locator_all_script", 25),
        ("keyword_evaluate", 30),
        ("direct_evaluate", 16),
        ("aliased_evaluate", 21),
        ("evaluate_script", 33),
        ("yielded_page", 25),
        ("branch_yield", 43),
        ("ordinary_yield", 54),
        ("reassigned_yield", 61),
        ("local_page_evaluate", 16),
        ("module_page_evaluate", 19),
        ("guarded_module_page_evaluate", 20),
        ("property_evaluate", 18),
        ("evaluate_script", 17),
    ]
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line) for finding in ir.findings
    ] == [
        ("AV-EXEC002", "agent.py", 9),
        ("AV-EXEC002", "agent.py", 20),
        ("AV-EXEC002", "agent.py", 26),
        ("AV-EXEC002", "agent.py", 34),
        ("AV-EXEC002", "agent.py", 43),
        ("AV-EXEC002", "agent.py", 48),
        ("AV-EXEC002", "agent.py", 54),
        ("AV-EXEC002", "alternate.py", 10),
        ("AV-EXEC002", "alternate.py", 20),
        ("AV-EXEC002", "alternate.py", 25),
        ("AV-EXEC002", "alternate.py", 30),
        ("AV-EXEC002", "constructor.py", 16),
        ("AV-EXEC002", "constructor.py", 21),
        ("AV-EXEC002", "constructor.py", 33),
        ("AV-EXEC002", "contextmanager.py", 25),
        ("AV-EXEC002", "local_construction.py", 16),
        ("AV-EXEC002", "module_annotation.py", 19),
        ("AV-EXEC002", "module_guarded_import.py", 20),
        ("AV-EXEC002", "property.py", 18),
        ("AV-EXEC002", "type_checking.py", 17),
    ]

    module_shadowed = tmp_path / "module-shadowed-getattr"
    shutil.copytree(ROOT / "cases/python_browser_evaluate", module_shadowed)
    wrapper_path = module_shadowed / "wrapper_scope.py"
    wrapper_source = wrapper_path.read_text(encoding="utf-8")
    marker = "BrowserReceiver = Page"
    assert marker in wrapper_source
    wrapper_path.write_text(
        wrapper_source.replace(
            marker,
            f"{marker}\ngetattr = lambda value, name, default: default",
        ),
        encoding="utf-8",
    )
    shadowed_ir = scan_repository(module_shadowed)
    shadowed_exact = next(
        item
        for item in shadowed_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "wrapper_scope.py"
        and item.evidence.line == 14
    )
    assert shadowed_exact.attributes["receiver_proof"] == ("unresolved-browser-import-context")

    rebound_class = tmp_path / "rebound-imported-browser-class"
    shutil.copytree(ROOT / "cases/python_browser_evaluate", rebound_class)
    imported_field_path = rebound_class / "imported_field.py"
    imported_field_source = imported_field_path.read_text(encoding="utf-8")
    imported_marker = "BrowserReceiver = Page"
    assert imported_marker in imported_field_source
    imported_field_path.write_text(
        imported_field_source.replace(
            imported_marker,
            f"{imported_marker}\nBrowserContext = object",
        ),
        encoding="utf-8",
    )
    rebound_ir = scan_repository(rebound_class)
    rebound_exact = next(
        item
        for item in rebound_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "imported_field.py"
        and item.evidence.line == 13
    )
    assert rebound_exact.attributes["receiver_proof"] == ("unresolved-browser-import-context")

    near_type = tmp_path / "near-browser-field-type"
    shutil.copytree(ROOT / "cases/python_browser_evaluate", near_type)
    context_path = near_type / "imported_field_context.py"
    context_source = context_path.read_text(encoding="utf-8")
    exact_import = "from playwright.async_api import Page"
    assert exact_import in context_source
    context_path.write_text(
        context_source.replace(exact_import, "from near_playwright.async_api import Page"),
        encoding="utf-8",
    )
    near_ir = scan_repository(near_type)
    near_exact = next(
        item
        for item in near_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "imported_field.py"
        and item.evidence.line == 12
    )
    assert near_exact.attributes["receiver_proof"] == ("unresolved-browser-import-context")

    rebound_export = tmp_path / "rebound-browser-class-export"
    shutil.copytree(ROOT / "cases/python_browser_evaluate", rebound_export)
    export_context_path = rebound_export / "imported_field_context.py"
    export_context_source = export_context_path.read_text(encoding="utf-8")
    export_context_path.write_text(
        f"{export_context_source}\nBrowserContext = object\n",
        encoding="utf-8",
    )
    rebound_export_ir = scan_repository(rebound_export)
    rebound_export_exact = next(
        item
        for item in rebound_export_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "imported_field.py"
        and item.evidence.line == 12
    )
    assert rebound_export_exact.attributes["receiver_proof"] == (
        "unresolved-browser-import-context"
    )


def test_python_imported_browser_method_returns_require_exact_closure_proof(
    tmp_path: Path,
) -> None:
    case = ROOT / "cases/python_imported_browser_method"
    ir = scan_repository(case)

    assert [
        (
            item.evidence.line,
            item.attributes["api"],
            item.attributes["dynamic_input"],
            item.attributes["receiver_proof"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "code-execution"
    ] == [
        (19, "page.evaluate", False, "imported-class-playwright-method-return-alias"),
        (26, "page.evaluate", False, "imported-class-playwright-method-return-alias"),
        (31, "page.evaluate", False, "unresolved-browser-import-context"),
        (36, "page.evaluate", False, "unresolved-browser-import-context"),
        (41, "page.evaluate", False, "unresolved-browser-import-context"),
        (46, "page.evaluate", False, "unresolved-browser-import-context"),
        (52, "page.evaluate", False, "unresolved-browser-import-context"),
        (58, "page.evaluate", False, "unresolved-browser-import-context"),
        (64, "page.evaluate", False, "unresolved-browser-import-context"),
        (70, "page.evaluate", False, "unresolved-browser-import-context"),
        (77, "page.evaluate", False, "unresolved-browser-import-context"),
        (82, "page.evaluate", False, "unresolved-browser-import-context"),
        (92, "page.evaluate", False, "unresolved-browser-import-context"),
    ]
    assert not ir.findings

    near_type = tmp_path / "near-browser-method-type"
    shutil.copytree(case, near_type)
    state_path = near_type / "browser_state.py"
    state_source = state_path.read_text(encoding="utf-8")
    exact_import = "from playwright.async_api import Page"
    assert exact_import in state_source
    state_path.write_text(
        state_source.replace(
            exact_import,
            "from near_playwright.async_api import Page",
        ),
        encoding="utf-8",
    )
    near_ir = scan_repository(near_type)
    near_exact = next(
        item
        for item in near_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "consumer.py"
        and item.evidence.line == 19
    )
    assert near_exact.attributes["receiver_proof"] == ("unresolved-browser-import-context")

    rebound_import = tmp_path / "rebound-browser-method-import"
    shutil.copytree(case, rebound_import)
    consumer_path = rebound_import / "consumer.py"
    consumer_source = consumer_path.read_text(encoding="utf-8")
    consumer_path.write_text(
        f"{consumer_source}\nBrowserState = object\n",
        encoding="utf-8",
    )
    rebound_import_ir = scan_repository(rebound_import)
    rebound_import_exact = next(
        item
        for item in rebound_import_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "consumer.py"
        and item.evidence.line == 19
    )
    assert rebound_import_exact.attributes["receiver_proof"] == (
        "unresolved-browser-import-context"
    )

    rebound_export = tmp_path / "rebound-browser-method-export"
    shutil.copytree(case, rebound_export)
    export_path = rebound_export / "browser_state.py"
    export_source = export_path.read_text(encoding="utf-8")
    export_path.write_text(
        f"{export_source}\nBrowserState = object\n",
        encoding="utf-8",
    )
    rebound_export_ir = scan_repository(rebound_export)
    rebound_export_exact = next(
        item
        for item in rebound_export_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "consumer.py"
        and item.evidence.line == 19
    )
    assert rebound_export_exact.attributes["receiver_proof"] == (
        "unresolved-browser-import-context"
    )

    conditional_rebound = tmp_path / "conditional-browser-method-rebound"
    shutil.copytree(case, conditional_rebound)
    conditional_path = conditional_rebound / "browser_state.py"
    conditional_source = conditional_path.read_text(encoding="utf-8")
    method_marker = "    async def get_page(self) -> Page | None: ..."
    assert method_marker in conditional_source
    conditional_path.write_text(
        conditional_source.replace(
            method_marker,
            f"{method_marker}\n\n    if True:\n        get_page = object()",
            1,
        ),
        encoding="utf-8",
    )
    conditional_ir = scan_repository(conditional_rebound)
    conditional_exact = next(
        item
        for item in conditional_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "consumer.py"
        and item.evidence.line == 19
    )
    assert conditional_exact.attributes["receiver_proof"] == ("unresolved-browser-import-context")

    required_argument = tmp_path / "required-browser-method-argument"
    shutil.copytree(case, required_argument)
    required_path = required_argument / "browser_state.py"
    required_source = required_path.read_text(encoding="utf-8")
    assert method_marker in required_source
    required_path.write_text(
        required_source.replace(
            method_marker,
            "    async def get_page(self, required: str) -> Page | None: ...",
            1,
        ),
        encoding="utf-8",
    )
    required_ir = scan_repository(required_argument)
    required_exact = next(
        item
        for item in required_ir.components
        if item.kind == "capability"
        and item.name == "code-execution"
        and item.evidence.path == "consumer.py"
        and item.evidence.line == 19
    )
    assert required_exact.attributes["receiver_proof"] == ("unresolved-browser-import-context")


def test_python_registry_decorators_are_import_proven_and_entrypoint_scoped() -> None:
    ir = scan_repository(ROOT / "cases/python_registry_tools")

    assert [
        (
            item.name,
            item.evidence.path,
            item.evidence.line,
            item.attributes.get("framework"),
            item.attributes.get("entrypoints"),
        )
        for item in ir.components
        if item.kind == "tool"
    ] == [
        ("direct_tool", "meta.py", 7, "MetaGPT", None),
        ("Runner", "meta.py", 12, "MetaGPT", ["run"]),
        ("OpaqueRunner", "meta.py", 24, "MetaGPT", []),
        ("memory_write", "meta.py", 30, "MetaGPT", None),
        ("fixed_write", "meta.py", 37, "MetaGPT", None),
        ("code_runner", "qwen.py", 7, "Qwen-Agent", ["call"]),
        ("fixed_search", "qwen.py", 25, "Qwen-Agent", ["call"]),
    ]
    assert [
        (edge.source_name, edge.evidence.path, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "code-execution"
    ] == [
        ("direct_tool", "meta.py", 8),
        ("Runner", "meta.py", 14),
        ("code_runner", "qwen.py", 9),
    ]
    assert [
        (item.evidence.path, item.evidence.line, item.attributes["tool_input_path"])
        for item in ir.components
        if item.name == "filesystem"
    ] == [("meta.py", 38, False)]
    assert [
        (item.evidence.line, item.attributes["dynamic_origin"])
        for item in ir.components
        if item.name == "network"
    ] == [(32, False), (33, False)]
    assert [
        (edge.source_name, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "network"
    ] == [("fixed_search", 32), ("fixed_search", 33)]
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line) for finding in ir.findings
    ] == [
        ("AV-EXEC002", "meta.py", 8),
        ("AV-EXEC002", "meta.py", 14),
        ("AV-EXEC002", "qwen.py", 9),
    ]


def test_python_imported_network_helpers_require_exact_unrebound_imports() -> None:
    ir = scan_repository(ROOT / "cases/python_imported_network_helper")

    assert [
        (
            item.evidence.line,
            item.attributes["dynamic_origin"],
            item.attributes["summary"],
            item.attributes["helper_path"],
            item.attributes["helper_network_lines"],
        )
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "imported-function"
        and item.evidence.path == "pkg/tools.py"
    ] == [
        (15, True, "imported-function", "pkg/helpers.py", [7]),
        (16, False, "imported-function", "pkg/helpers.py", [11]),
        (26, False, "imported-function", "pkg/helpers.py", [7]),
    ]
    assert [
        (edge.source_name, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "network" and edge.evidence.path == "pkg/tools.py"
    ] == [
        ("remote_loader", 15),
        ("remote_loader", 16),
        ("fixed_loader", 26),
    ]
    assert [
        (finding.rule_id, finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.evidence.path == "pkg/tools.py"
    ] == [("AV-NET001", "pkg/tools.py", 15)]


def test_python_imported_class_network_helpers_are_iterative_and_binding_scoped() -> None:
    ir = scan_repository(ROOT / "cases/python_imported_network_helper")

    assert [
        (
            item.evidence.path,
            item.evidence.line,
            item.attributes["dynamic_origin"],
            item.attributes["api"],
            item.attributes["callee_network_lines"],
        )
        for item in ir.components
        if item.kind == "capability"
        and item.name == "network"
        and item.attributes.get("summary") == "imported-class-method"
    ] == [
        ("pkg/chain.py", 12, True, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 14, True, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 23, True, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 29, False, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 35, True, "ChainParser.call", [12]),
        ("pkg/class_tools.py", 53, True, "UrlParser.call", [10]),
        ("pkg/class_tools.py", 87, False, "UrlParser.call", [10]),
    ]
    assert [
        (edge.source_name, edge.evidence.path, edge.evidence.line)
        for edge in ir.relationships
        if edge.target_name == "network"
        and edge.evidence.path in {"pkg/chain.py", "pkg/class_tools.py"}
    ] == [
        ("chain_parser", "pkg/chain.py", 12),
        ("direct_class_loader", "pkg/class_tools.py", 14),
        ("bound_class_loader", "pkg/class_tools.py", 23),
        ("fixed_class_loader", "pkg/class_tools.py", 29),
        ("multi_hop_loader", "pkg/class_tools.py", 35),
        ("module_class_loader", "pkg/class_tools.py", 53),
        ("mixed_field_loader", "pkg/class_tools.py", 87),
    ]
    assert [
        (finding.evidence.path, finding.evidence.line)
        for finding in ir.findings
        if finding.evidence.path in {"pkg/chain.py", "pkg/class_tools.py"}
    ] == [
        ("pkg/chain.py", 12),
        ("pkg/class_tools.py", 14),
        ("pkg/class_tools.py", 23),
        ("pkg/class_tools.py", 35),
        ("pkg/class_tools.py", 53),
    ]


def test_python_filesystem_mutations_resolve_destinations_aliases_and_guards() -> None:
    ir = scan_repository(ROOT / "cases/filesystem_mutations")

    filesystem = {
        item.evidence.line: (
            item.attributes["canonical_api"],
            item.attributes["operation"],
            item.attributes["path_role"],
            item.attributes["dynamic_path"],
            item.attributes["path_boundary_scope"],
        )
        for item in ir.components
        if item.kind == "capability" and item.name == "filesystem"
    }
    assert filesystem == {
        13: ("shutil.copytree", "copy", "destination", True, "unresolved"),
        18: ("shutil.move", "move", "destination", True, "unresolved"),
        23: ("os.replace", "move", "destination", True, "unresolved"),
        28: ("shutil.copy2", "copy", "destination", True, "unresolved"),
        33: ("os.remove", "delete", "target", True, "unresolved"),
        38: ("shutil.copy2", "copy", "destination", False, "unresolved"),
        47: ("shutil.copy2", "copy", "destination", True, "constrained"),
        56: ("shutil.copy2", "copy", "destination", True, "unresolved"),
        74: (
            "shutil.copy|shutil.copy2",
            "copy",
            "destination",
            True,
            "unresolved",
        ),
        85: (
            "shutil.copy|shutil.copy2",
            "copy",
            "destination",
            True,
            "unresolved",
        ),
        97: (
            "shutil.copy|shutil.copy2",
            "copy",
            "destination",
            True,
            "constrained",
        ),
        132: (
            "pathlib.Path.replace",
            "move",
            "destination",
            True,
            "unresolved",
        ),
        138: (
            "pathlib.Path.rename",
            "move",
            "destination",
            True,
            "unresolved",
        ),
        147: (
            "pathlib.Path.rename",
            "move",
            "destination",
            True,
            "constrained",
        ),
        177: ("shutil.copy2", "copy", "destination", True, "unresolved"),
        200: ("shutil.copy2", "copy", "destination", True, "unresolved"),
    }
    callable_aliases = {
        item.evidence.line: item.attributes["possible_apis"]
        for item in ir.components
        if item.kind == "capability"
        and item.name == "filesystem"
        and item.attributes["callable_alias"]
    }
    assert callable_aliases == {
        74: ["shutil.copy", "shutil.copy2"],
        85: ["shutil.copy", "shutil.copy2"],
        97: ["shutil.copy", "shutil.copy2"],
        177: ["shutil.copy2"],
        200: ["shutil.copy2"],
    }
    path_receivers = {
        item.evidence.line: item.attributes["receiver_proof"]
        for item in ir.components
        if item.kind == "capability"
        and item.name == "filesystem"
        and item.attributes.get("receiver_proof") is not None
    }
    assert path_receivers == {
        132: "explicit-constructor",
        138: "immutable-local",
        147: "explicit-constructor",
    }
    assert [
        (edge.evidence.line, edge.attributes["control_line"])
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-boundary"
    ] == [(47, 45), (97, 94), (147, 145)]
    assert [
        (edge.evidence.line, edge.attributes["control_line"])
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "path-prefix-check"
    ] == [(56, 54)]
    assert [
        (finding.rule_id, finding.evidence.line, finding.analysis["tool"])
        for finding in ir.findings
    ] == [
        ("AV-FS001", 13, "copy_tree"),
        ("AV-FS001", 18, "move_path"),
        ("AV-FS001", 23, "replace_path"),
        ("AV-FS001", 28, "copy_file"),
        ("AV-FS001", 33, "delete_file"),
        ("AV-FS002", 56, "weak_prefix_copy"),
        ("AV-FS001", 74, "local_copy_choice"),
        ("AV-FS001", 85, "branch_copy_choice"),
        ("AV-FS001", 132, "direct_path_replace"),
        ("AV-FS001", 138, "immutable_path_rename"),
        ("AV-FS001", 177, "chained_copy_alias"),
        ("AV-FS001", 200, "deeper_chained_copy_alias"),
    ]


def test_python_filesystem_callable_rebinding_invalidates_state(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """
import shutil
from langchain.tools import tool

def wrapper(source: str, destination: str) -> None:
    pass

@tool
def walrus_rebind(source: str, destination: str) -> None:
    copy_fn = shutil.copy2
    (copy_fn := wrapper)
    copy_fn(source, destination)

@tool
def import_rebind(source: str, destination: str) -> None:
    copy_fn = shutil.copy2
    import json as copy_fn
    copy_fn(source, destination)
""".lstrip(),
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    assert not any(
        item.kind == "capability" and item.name == "filesystem" for item in ir.components
    )
    assert not ir.findings


def test_dynamic_writable_tool_path_but_not_fixed_path_is_reviewed() -> None:
    ir = scan_repository(ROOT / "cases/filesystem_scope")

    filesystem_findings = [finding for finding in ir.findings if finding.rule_id == "AV-FS001"]
    assert len(filesystem_findings) == 1
    assert filesystem_findings[0].ir_path == (
        "agent:writer",
        "tool:write_file",
        "capability:filesystem",
    )
    assert filesystem_findings[0].result_kind == "review"


def test_container_host_boundaries_but_not_safe_compose_are_reviewed() -> None:
    ir = scan_repository(ROOT / "cases/sandbox_boundary")

    findings = [finding for finding in ir.findings if finding.rule_id == "AV-SANDBOX001"]
    assert {finding.message for finding in findings} == {
        "A container mounts the host Docker socket",
        "A container runs in privileged mode",
        "A container shares the host network namespace",
        "A container shares the host process namespace",
        "A container shares the host IPC namespace",
        "A workload automatically mounts a Kubernetes service-account token",
        "A container explicitly allows privilege escalation",
        "A container mounts the host filesystem root",
        "A Kubernetes workload mounts a host path",
        "A container mounts host credential material",
    }
    assert len(findings) == 21
    assert ir.config_files_scanned == 5
    assert all(finding.result_kind == "review" for finding in findings)
    host_path = next(
        component
        for component in ir.components
        if component.kind == "sandbox-boundary" and component.name == "host-path-mount"
    )
    assert host_path.attributes["host_path"] == "/srv/agent-workspace"
    assert any(
        component.kind == "sandbox-boundary"
        and component.name == "privileged-container"
        and component.attributes.get("api") == "client.containers.run"
        for component in ir.components
    )
    credential_mounts = [
        component
        for component in ir.components
        if component.kind == "sandbox-boundary" and component.name == "host-credential-mount"
    ]
    assert {component.attributes["credential_kind"] for component in credential_mounts} == {
        "aws",
        "docker-registry",
        "gcp",
        "git",
        "kubernetes",
        "netrc",
        "npm",
        "pypi",
        "ssh",
    }
    assert all(component.attributes["read_only"] is True for component in credential_mounts)
    credential_findings = [
        finding
        for finding in findings
        if finding.message == "A container mounts host credential material"
    ]
    assert all("short-lived credentials" in finding.remediation for finding in credential_findings)
    assert not any(
        component.evidence.path == "docker-compose.credentials.yml"
        and component.evidence.line in {13, 14, 15}
        for component in credential_mounts
    )


def test_action_trace_only_governs_capabilities_inside_the_span() -> None:
    ir = scan_repository(ROOT / "cases/audit_trace")

    trace = next(
        component
        for component in ir.components
        if component.kind == "control" and component.name == "action-trace"
    )
    assert trace.attributes == {
        "instrumentation": "opentelemetry",
        "durability": "unresolved",
        "scope": "production",
        "tool": "send_email",
    }
    governed_lines = {
        edge.evidence.line
        for edge in ir.relationships
        if edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.target_name == "action-trace"
    }
    assert governed_lines == {11}
    assert any(
        edge.source_kind == "tool"
        and edge.source_name == "send_email"
        and edge.relation == "contains-control"
        for edge in ir.relationships
    )
    assert not any(
        edge.source_kind == "capability"
        and edge.relation == "governed-by"
        and edge.evidence.line == 16
        for edge in ir.relationships
    )
    traced_action = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "external-action"
        and component.evidence.line == 11
    )
    _, analysis = component_context(ir, traced_action)
    assert analysis["governing_controls"] == ["action-trace"]
    assert analysis["audit_coverage"] == "instrumented; exporter durability unresolved"


def test_google_adk_bigquery_plugin_proves_durable_attributable_action_audit() -> None:
    ir = scan_repository(ROOT / "cases/python_google_adk_bigquery_audit")

    storage = next(
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "audit-storage"
    )
    assert storage.attributes == {
        "analysis": "python-google-adk-bigquery-action-audit",
        "api": "BigQueryWriteAsyncClient.append_rows",
        "sink": "bigquery-storage-write-api",
        "durability": "durable-remote-database",
        "scope": "production",
    }
    deployed = next(
        component
        for component in ir.components
        if component.kind == "control"
        and component.name == "durable-action-audit"
        and component.evidence.path == "app.py"
    )
    assert deployed.attributes["deployment_state"] == "enabled"
    assert deployed.attributes["event_types"] == [
        "TOOL_STARTING",
        "TOOL_COMPLETED",
        "TOOL_ERROR",
    ]
    assert deployed.attributes["attribution_fields"] == [
        "event_id",
        "agent",
        "user_id",
        "session_id",
        "invocation_id",
        "tool",
    ]
    actions = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "external-action"
        and component.evidence.path == "app.py"
    }
    _, audited = component_context(ir, actions[13])
    _, disabled = component_context(ir, actions[18])
    assert audited["governing_controls"] == ["durable-action-audit"]
    assert audited["audit_coverage"] == "durable and attributable; delivery best-effort"
    assert disabled["governing_controls"] == []
    assert disabled["audit_coverage"] == "unresolved"
    setting = next(
        component
        for component in ir.components
        if component.kind == "control-setting" and component.name == "action-audit"
    )
    assert setting.attributes["enabled"] is False
    assert setting.attributes["state"] == "disabled-explicit"
    assert any(
        edge.source_name == "disabled_agent"
        and edge.relation == "configured-by"
        and edge.target_name == "action-audit"
        for edge in ir.relationships
    )
    assert not any(finding.rule_id == "AV-AUDIT001" for finding in ir.findings)


def test_google_adk_audit_control_requires_the_full_framework_path(tmp_path: Path) -> None:
    source = ROOT / "cases/python_google_adk_bigquery_audit"
    mutations = (
        (
            "google/adk/plugins/bigquery_agent_analytics_plugin.py",
            "enabled: bool = True",
            "enabled: bool = False",
        ),
        (
            "google/adk/plugins/bigquery_agent_analytics_plugin.py",
            "await self.write_client.append_rows(row)",
            "print(row)",
        ),
        (
            "google/adk/runners.py",
            "plugins=app.plugins",
            "plugins=[]",
        ),
        (
            "google/adk/flows/llm_flows/functions.py",
            "await invocation_context.plugin_manager.run_after_tool_callback(",
            "await invocation_context.plugin_manager.after_tool_callback(",
        ),
    )
    for index, (relative, before, after) in enumerate(mutations):
        incomplete = tmp_path / str(index)
        shutil.copytree(source, incomplete)
        target = incomplete / relative
        text = target.read_text(encoding="utf-8")
        assert before in text
        target.write_text(text.replace(before, after, 1), encoding="utf-8")

        ir = scan_repository(incomplete)

        assert not any(
            component.name in {"durable-action-audit", "audit-storage", "action-audit"}
            for component in ir.components
        )


def test_google_adk_audit_control_withholds_mutable_or_filtered_compositions(
    tmp_path: Path,
) -> None:
    source = ROOT / "cases/python_google_adk_bigquery_audit"
    mutations = (
        (
            "audit_plugin = BigQueryAgentAnalyticsPlugin(",
            "audit_plugin = BigQueryAgentAnalyticsPlugin(",
            "audit_plugin = object()\n",
        ),
        (
            'project_id="project", dataset_id="audit")',
            ('project_id="project", dataset_id="audit", ' + 'event_allowlist=["TOOL_STARTING"])'),
            "",
        ),
    )
    for index, (before, after, suffix) in enumerate(mutations):
        incomplete = tmp_path / str(index)
        shutil.copytree(source, incomplete)
        target = incomplete / "app.py"
        text = target.read_text(encoding="utf-8")
        assert before in text
        target.write_text(text.replace(before, after, 1) + suffix, encoding="utf-8")

        ir = scan_repository(incomplete)

        assert not any(
            edge.source_kind == "capability"
            and edge.evidence.path == "app.py"
            and edge.evidence.line == 13
            and edge.relation == "governed-by"
            and edge.target_name == "durable-action-audit"
            for edge in ir.relationships
        )


def test_skyvern_taskv3_proves_durable_execution_record_with_actor_gap() -> None:
    ir = scan_repository(ROOT / "cases/python_skyvern_action_history")

    action = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.name == "external-action"
        and component.attributes.get("analysis") == "python-skyvern-taskv3-action-history"
    )
    path, analysis = component_context(ir, action)
    assert path == (
        "agent:Skyvern Task v3 agent loop",
        "tool:Task v3 recordable action dispatch",
        "capability:external-action",
    )
    assert analysis["governing_controls"] == ["durable-action-record"]
    assert analysis["audit_coverage"] == (
        "durable execution record; actor attribution unresolved; delivery best-effort"
    )
    control = next(
        component
        for component in ir.components
        if component.kind == "control" and component.name == "durable-action-record"
    )
    assert control.attributes["deployment_state"] == "enabled"
    assert control.attributes["scope"] == "production"
    assert control.attributes["actor_attribution"] == ("unresolved-created-by-nullable-and-unset")
    assert control.attributes["failure_behavior"] == "persistence-errors-contained"
    storage = next(
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "audit-storage"
    )
    assert storage.attributes == {
        "analysis": "python-skyvern-taskv3-action-history",
        "scope": "production",
        "api": "SQLAlchemy AsyncSession.commit",
        "sink": "sqlalchemy-actions-table",
        "table": "actions",
        "durability": "durable-relational-database",
    }
    audit_findings = [finding for finding in ir.findings if finding.rule_id == "AV-AUDIT001"]
    assert len(audit_findings) == 1
    finding = audit_findings[0]
    assert finding.evidence.path == "skyvern/forge/taskv3/loop.py"
    assert finding.evidence.line == 9
    assert finding.severity == "medium"
    assert finding.confidence == "high"
    assert finding.result_kind == "review"
    assert finding.analysis["audit_coverage"] == (
        "durable execution record; actor attribution unresolved; delivery best-effort"
    )
    assert not any(
        candidate.rule_id == "AV-AUDIT001" and candidate.evidence.path == "untracked.py"
        for candidate in ir.findings
    )


def test_skyvern_action_record_requires_dispatch_callback_and_commit_path(
    tmp_path: Path,
) -> None:
    source = ROOT / "cases/python_skyvern_action_history"
    mutations = (
        (
            "skyvern/forge/taskv3/loop.py",
            "result = await spec.handler(args)",
            'result = ToolResult(status="unknown")',
        ),
        (
            "skyvern/forge/taskv3/loop.py",
            "await on_action_round(round_actions)",
            "await observe_round(round_actions)",
        ),
        (
            "skyvern/forge/agent.py",
            "on_action_round=_on_action_round",
            "on_action_round=None",
        ),
        (
            "skyvern/forge/agent.py",
            "await app.DATABASE.workflow_params.create_action(action=action)",
            "await app.DATABASE.workflow_params.preview_action(action=action)",
        ),
        (
            "skyvern/forge/sdk/db/repositories/workflow_parameters.py",
            "await session.commit()",
            "await session.flush()",
        ),
        (
            "skyvern/forge/sdk/db/models.py",
            "created_by = Column(String, nullable=True)",
            "created_by = Column(String, nullable=False)",
        ),
    )
    for index, (relative, before, after) in enumerate(mutations):
        incomplete = tmp_path / str(index)
        shutil.copytree(source, incomplete)
        target = incomplete / relative
        text = target.read_text(encoding="utf-8")
        assert before in text
        target.write_text(text.replace(before, after, 1), encoding="utf-8")

        ir = scan_repository(incomplete)

        assert not any(
            component.attributes.get("analysis") == "python-skyvern-taskv3-action-history"
            for component in ir.components
        )


def test_delegation_expands_transitive_capability_path() -> None:
    ir = scan_repository(ROOT / "cases/delegation")

    assert ir.findings[0].ir_path == (
        "agent:coordinator",
        "agent:worker",
        "tool:run_command",
        "capability:shell-execution",
    )
    assert ir.findings[0].analysis["direct_agents"] == ["worker"]
    assert ir.findings[0].analysis["reachable_agents"] == ["coordinator", "worker"]


def test_same_named_cross_file_edges_do_not_leak_into_context() -> None:
    ir = scan_repository(ROOT / "cases/symbol_collision")

    finding = next(finding for finding in ir.findings if finding.rule_id == "AV-EXEC001")
    assert finding.ir_path == (
        "agent:operator",
        "tool:run_command",
        "capability:shell-execution",
    )
    assert finding.analysis["direct_agents"] == ["operator"]
    assert finding.analysis["approval_coverage"] == "unresolved"
    assert finding.analysis["governing_controls"] == []
    tool_symbols = {
        component.evidence.path: component.symbol_id
        for component in ir.components
        if component.kind == "tool" and component.name == "run_command"
    }
    assert tool_symbols == {
        "approved.py": "py:approved.py#tool:run_command",
        "dangerous.py": "py:dangerous.py#tool:run_command",
    }
    operator_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_name == "operator" and edge.relation == "uses"
    )
    approval_edge = next(edge for edge in ir.relationships if edge.relation == "governed-by")
    assert operator_edge.target_id == tool_symbols["dangerous.py"]
    assert approval_edge.source_id == tool_symbols["approved.py"]


def test_relative_python_tool_import_resolves_only_existing_sibling_module() -> None:
    ir = scan_repository(ROOT / "cases/imported_relative_tool")

    operator_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.source_name == "operator"
        and edge.target_name == "run_command"
    )
    assert operator_edge.attributes == {"target_path": "pkg/tools.py"}
    assert operator_edge.target_id == "py:pkg/tools.py#tool:run_command"
    unresolved_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.source_name == "unresolved"
    )
    assert unresolved_edge.attributes == {}
    assert unresolved_edge.target_id is None


def test_contextual_absolute_class_tool_import_requires_one_path_and_exact_export() -> None:
    ir = scan_repository(ROOT / "cases/python_contextual_class_tool")

    positive = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.evidence.path == "project_a/agent.py"
    )
    assert positive.target_name == "WebTools.browse"
    assert positive.attributes == {
        "target_path": "project_a/tools/browser.py",
        "target_identity": "contextual-absolute-import-single-export",
    }
    assert positive.target_id == ("py:project_a/tools/browser.py#tool:BrowserTools.browse")
    assert any(
        finding.rule_id == "AV-NET001"
        and finding.ir_path
        == (
            "agent:Agent",
            "tool:browse",
            "capability:network",
        )
        for finding in ir.findings
    )

    unresolved = {
        edge.evidence.path: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.evidence.path != "project_a/agent.py"
    }
    assert set(unresolved) == {
        "ambiguous/nested/agent.py",
        "project_a/missing.py",
        "project_a/reimported.py",
        "project_a/shadowed.py",
    }
    assert all(edge.attributes == {} for edge in unresolved.values())
    assert all(edge.target_id is None for edge in unresolved.values())


def test_local_import_resolves_cross_file_agent_tool_path() -> None:
    ir = scan_repository(ROOT / "cases/imported_tool")

    finding = next(finding for finding in ir.findings if finding.rule_id == "AV-EXEC001")
    assert finding.ir_path == (
        "agent:operator",
        "tool:run_command",
        "capability:shell-execution",
    )
    assert finding.analysis["direct_agents"] == ["operator"]
    assert finding.analysis["approval_coverage"] == "present"
    agent_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_name == "run_command"
    )
    assert agent_edge.attributes["target_path"] == "tools.py"
    tool = next(
        component
        for component in ir.components
        if component.kind == "tool" and component.evidence.path == "tools.py"
    )
    assert agent_edge.target_id == tool.symbol_id == "py:tools.py#tool:run_command"


def test_python_local_bindings_do_not_inherit_module_import_identity() -> None:
    ir = scan_repository(ROOT / "cases/python_import_shadowing")
    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_name == "tool"
    }

    assert edges[4].attributes == {"target_path": "pkg/__init__.py"}
    assert edges[4].target_id == "py:pkg/__init__.py#tool:tool"
    assert edges[8].attributes == {}
    assert edges[8].target_id is None
    assert edges[13].attributes == {}
    assert edges[13].target_id is None


def test_python_repeated_bindings_require_same_block_dominance() -> None:
    ir = scan_repository(ROOT / "cases/python_block_dominance")
    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_name == "agent"
    }

    assert edges[10].attributes == {"target_identity": "block-dominating-definition"}
    assert edges[10].target_id == "py:app.py#agent:agent@9"
    assert edges[16].attributes == {"target_identity": "block-dominating-definition"}
    assert edges[16].target_id == "py:app.py#agent:agent@15"
    assert edges[22].attributes == {"target_identity": "ambiguous-repeated-binding"}
    assert edges[22].target_id is None
    assert edges[29].attributes == {"target_identity": "ambiguous-repeated-binding"}
    assert edges[29].target_id is None
    assert edges[35].attributes == {"target_identity": "block-dominating-definition"}
    assert edges[35].target_id == "py:app.py#agent:agent@34"
    assert edges[42].attributes == {"target_identity": "block-dominating-definition"}
    assert edges[42].target_id == "py:app.py#agent:agent@41"


def test_python_direct_callable_tools_require_same_block_definition() -> None:
    ir = scan_repository(ROOT / "cases/python_direct_callable_tool")
    tools = {component.name: component for component in ir.components if component.kind == "tool"}
    assert set(tools) == {"branch_tool", "run_command", "unique_tool"}
    assert tools["run_command"].symbol_id == "py:app.py#tool:run_command"
    assert tools["run_command"].attributes == {
        "decorators": [],
        "needs_approval": False,
        "registration": "agent-tool-reference",
        "registration_path": "app.py",
        "registration_line": 9,
        "resolution": "same-block-single-definition",
    }
    assert tools["branch_tool"].symbol_id == "py:app.py#tool:branch_tool"
    assert tools["branch_tool"].attributes["registration_line"] == 16
    assert tools["unique_tool"].symbol_id == "py:app.py#tool:unique_tool"
    assert tools["unique_tool"].attributes["registration_line"] == 49

    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert edges[9].target_id == "py:app.py#tool:run_command"
    assert edges[9].attributes == {}
    assert edges[16].target_id == "py:app.py#tool:branch_tool"
    assert edges[16].attributes == {}
    assert edges[24].target_id is None
    assert edges[31].target_id is None
    assert edges[35].target_id is None
    assert edges[39].target_id is None
    assert edges[49].target_id == "py:app.py#tool:unique_tool"
    assert edges[53].target_id is None

    shell = next(
        component
        for component in ir.components
        if component.kind == "capability" and component.name == "shell-execution"
    )
    assert shell.evidence.line == 8
    shell_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_id == "py:app.py#tool:run_command" and edge.target_name == "shell-execution"
    )
    assert shell_edge.evidence.line == 8
    finding = next(
        finding
        for finding in ir.findings
        if finding.rule_id == "AV-EXEC001" and finding.evidence.line == 8
    )
    assert finding.ir_path[:2] == ("agent:Agent", "tool:run_command")


def test_python_function_tool_wrappers_require_import_and_same_block_proof() -> None:
    ir = scan_repository(ROOT / "cases/python_function_tool_wrapper")
    tools = {
        component.symbol_id: component
        for component in ir.components
        if component.kind == "tool"
        and component.attributes.get("registration") == "function-tool-wrapper"
    }
    assert set(tools) == {
        "py:app.py#tool:wrapped@12",
        "py:app.py#tool:wrapped@20",
    }
    approved = tools["py:app.py#tool:wrapped@12"]
    assert approved.name == "wrapped"
    assert approved.evidence.line == 12
    assert approved.attributes == {
        "decorators": [],
        "needs_approval": True,
        "registration": "function-tool-wrapper",
        "registration_path": "app.py",
        "registration_line": 13,
        "wrapper_factory": "agents.function_tool",
        "wrapper_line": 12,
        "wrapped_function": "run_command",
        "resolution": "same-block-single-definition",
    }

    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }
    assert edges[13].target_id == "py:app.py#tool:wrapped@12"
    assert edges[21].target_id == "py:app.py#tool:wrapped@20"
    for line in (29, 37, 46, 55, 64, 69):
        assert edges[line].target_id is None
    multiple_edges = [
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool" and edge.evidence.line == 78
    ]
    assert len(multiple_edges) == 2
    assert all(edge.target_id is None for edge in multiple_edges)

    capability = next(
        edge
        for edge in ir.relationships
        if edge.source_id == "py:app.py#tool:wrapped@12" and edge.target_name == "shell-execution"
    )
    assert capability.evidence.line == 10
    approval = next(
        edge
        for edge in ir.relationships
        if edge.source_id == "py:app.py#tool:wrapped@12" and edge.target_name == "human-approval"
    )
    assert approval.evidence.line == 12
    finding = next(
        finding
        for finding in ir.findings
        if finding.rule_id == "AV-EXEC001" and finding.evidence.line == 10
    )
    assert finding.ir_path[:2] == ("agent:Agent", "tool:wrapped")
    assert finding.analysis["approval_coverage"] == "present"


def test_literal_tool_bindings_require_role_and_exact_local_identity() -> None:
    ir = scan_repository(ROOT / "cases/python_literal_tool_bindings")
    edges = {
        (edge.source_name, edge.target_name): edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }

    assert edges[("module-bindings", "module_tools")].target_id == (
        "py:positive.py#tool:module_tools"
    )
    assert edges[("module-bindings", "module_callable")].target_id == (
        "py:positive.py#tool:module_callable"
    )
    assert edges[("local-binding", "local_tools")].target_id == ("py:positive.py#tool:local_tools")
    assert edges[("inline-binding", "InlineTools@31")].target_id == (
        "py:positive.py#tool:InlineTools@31"
    )
    assert edges[("inline-binding", "InlineTools@31")].attributes == {
        "target_identity": "literal-tools-list-inline-constructor"
    }
    assert edges[("inline-binding", "LocalToolkit@31")].target_id == (
        "py:positive.py#tool:LocalToolkit@31"
    )
    assert edges[("context-binding", "context_tools")].target_id == (
        "py:positive.py#tool:context_tools"
    )
    assert edges[("context-binding", "context_tools")].attributes == {
        "target_identity": "literal-tools-list-context-manager"
    }

    unresolved_agents = {
        "reassigned-binding",
        "cross-branch-binding",
        "parameter-binding",
        "unproven-factory",
        "unproven-builtin",
        "ambiguous-constructor",
        "shadowed-constructor",
        "reassigned-context",
        "nested-context",
        "callable-rebound",
    }
    assert all(
        edges[
            (agent_name, "rebound_callable" if agent_name == "callable-rebound" else "tools")
        ].target_id
        is None
        for agent_name in unresolved_agents
    )

    components = {
        component.symbol_id: component for component in ir.components if component.kind == "tool"
    }
    assert components["py:positive.py#tool:module_tools"].attributes == {
        "binding": "literal-tools-list-constructor",
        "constructor": "ImportedTools",
        "registration": "agent-tool-reference",
        "registration_line": 17,
        "resolution": "module-single-definition",
        "scope": "production",
    }
    assert (
        components["py:positive.py#tool:module_callable"].attributes["resolution"]
        == "module-single-definition"
    )


def test_imported_literal_tools_require_immutable_binding_or_exact_export() -> None:
    ir = scan_repository(ROOT / "cases/python_imported_literal_tool")
    edges = {
        (edge.source_name, edge.target_name): edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_kind == "tool"
    }

    imported = edges[("imported-operator", "imported_writer")]
    assert imported.target_id == "py:pkg/tools.py#tool:imported_writer"
    assert imported.attributes == {
        "target_path": "pkg/tools.py",
        "target_identity": "imported-callable-single-export",
    }
    star_imported = edges[("star-import-operator", "star_writer")]
    assert star_imported.target_id == "py:pkg/star_tools.py#tool:star_writer"
    assert star_imported.attributes == {
        "target_path": "pkg/star_tools.py",
        "target_identity": "imported-callable-single-export",
    }
    external = edges[("imported-operator", "sdk_tool")]
    assert external.target_id == "py:positive.py#tool:sdk_tool"
    assert external.attributes == {"target_identity": "literal-tools-list-import-binding"}

    for agent_name, tool_name in {
        ("parameter-shadow", "parameter_tool"),
        ("local-shadow", "local_shadow"),
        ("class-shadow", "class_shadow"),
        ("duplicate-import", "duplicated"),
        ("forward-import", "forward_tool"),
        ("duplicate-local-import", "duplicate_local"),
        ("star-import-filtered", "filtered_hidden"),
    }:
        assert edges[(agent_name, tool_name)].target_id is None

    components = {
        component.symbol_id: component for component in ir.components if component.kind == "tool"
    }
    assert components["py:pkg/tools.py#tool:imported_writer"].attributes == {
        "decorators": [],
        "needs_approval": False,
        "registration": "agent-tool-reference",
        "registration_path": "positive.py",
        "registration_line": 6,
        "resolution": "imported-callable-single-export",
        "import_line": 3,
    }
    assert components["py:pkg/star_tools.py#tool:star_writer"].attributes == {
        "decorators": [],
        "needs_approval": False,
        "registration": "agent-tool-reference",
        "registration_path": "star_positive.py",
        "registration_line": 5,
        "resolution": "imported-callable-single-export",
        "import_line": 2,
    }
    assert components["py:positive.py#tool:sdk_tool"].attributes == {
        "binding": "literal-tools-list-import",
        "module": "external_sdk.tools",
        "imported_name": "sdk_tool",
        "registration": "agent-tool-reference",
        "registration_lines": [6],
        "resolution": "literal-import-binding",
        "scope": "production",
    }
    assert any(
        finding.rule_id == "AV-FS001"
        and finding.evidence.path == "pkg/tools.py"
        and finding.evidence.line == 5
        for finding in ir.findings
    )
    assert any(
        finding.rule_id == "AV-FS001"
        and finding.evidence.path == "pkg/star_tools.py"
        and finding.evidence.line == 7
        for finding in ir.findings
    )


def test_tool_factory_and_agent_adapters_require_exact_local_proof() -> None:
    ir = scan_repository(ROOT / "cases/python_tool_factory_adapters")
    edges = {
        (edge.source_kind, edge.source_name, edge.target_kind, edge.target_name): edge
        for edge in ir.relationships
    }

    for tool_name in ("graph_tool", "mcp_tool", "langchain_tool", "worker_tool"):
        assert edges[("agent", "root", "tool", tool_name)].target_id == (
            f"py:positive.py#tool:{tool_name}"
        )
    assert edges[("agent", "root", "tool", "worker_tool")].attributes == {
        "target_identity": "agent-as-tool-adapter"
    }
    delegation = edges[("tool", "worker_tool", "agent", "worker")]
    assert delegation.source_id == "py:positive.py#tool:worker_tool"
    assert delegation.target_id == "py:positive.py#agent:worker"
    assert delegation.attributes == {
        "adapter": "as_tool",
        "target_identity": "same-block-agent-as-tool",
    }
    assert edges[("tool", "mcp_tool", "capability", "mcp-access")].source_id == (
        "py:positive.py#tool:mcp_tool"
    )

    unresolved = {
        "unknown-factory": "unknown_factory",
        "arbitrary-adapter": "arbitrary_adapter",
        "ambiguous-adapter": "ambiguous_adapter",
        "parameter-receiver": "worker_tool",
        "nonagent-receiver": "worker_tool",
        "reassigned-receiver": "worker_tool",
        "reassigned-adapter": "worker_tool",
        "forward-receiver": "worker_tool",
    }
    assert all(
        edges[("agent", agent_name, "tool", tool_name)].target_id is None
        for agent_name, tool_name in unresolved.items()
    )

    components = {
        component.symbol_id: component for component in ir.components if component.kind == "tool"
    }
    assert components["py:positive.py#tool:graph_tool"].attributes["constructor"] == (
        "GlobalSearchTool.from_settings"
    )
    assert components["py:positive.py#tool:mcp_tool"].attributes["constructor"] == ("HostedMCPTool")
    assert (
        components["py:positive.py#tool:langchain_tool"].attributes["constructor"]
        == "LangchainTool"
    )
    assert components["py:positive.py#tool:worker_tool"].attributes == {
        "binding": "agent-as-tool-adapter",
        "adapter": "worker.as_tool",
        "registration": "agent-tool-reference",
        "registration_line": 13,
        "target_agent": "worker",
        "target_agent_id": "py:positive.py#agent:worker",
        "resolution": "same-block-agent-as-tool",
        "scope": "production",
    }


def test_python_agent_helper_returns_require_exact_same_class_flow() -> None:
    ir = scan_repository(ROOT / "cases/python_agent_helper_return")
    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.evidence.path == "app.py"
        and edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_kind == "agent"
    }

    assert edges[11].target_id == "py:app.py#agent:Agent@7"
    assert edges[11].attributes == {"target_identity": "same-class-helper-return"}
    assert edges[20].target_id == "py:app.py#agent:agent@14"
    assert edges[20].attributes == {"target_identity": "same-class-helper-return"}
    for line in (29, 38, 46, 51, 56, 67, 82):
        assert edges[line].target_id is None
        assert edges[line].attributes == {"target_identity": "ambiguous-repeated-binding"}

    function_edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.evidence.path == "local_function.py"
        and edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_kind == "agent"
    }
    for edge in (function_edges[10],):
        assert edge.target_id == "py:local_function.py#agent:Agent@6"
        assert edge.attributes == {"target_identity": "same-block-function-factory-return"}
    assert (
        len(
            [
                edge
                for edge in ir.relationships
                if edge.evidence.path == "local_function.py"
                and edge.evidence.line == 10
                and edge.source_kind == "agent"
                and edge.source_name == "Crew"
                and edge.target_kind == "agent"
                and edge.target_id == "py:local_function.py#agent:Agent@6"
            ]
        )
        == 2
    )
    negative_function_edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.evidence.path == "local_function_negative.py"
        and edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_kind == "agent"
    }
    for line in (11, 20, 29, 38, 46, 55):
        assert negative_function_edges[line].target_id is None
        assert negative_function_edges[line].attributes == {}


def test_imported_agent_factory_requires_exact_class_and_same_block_flow() -> None:
    ir = scan_repository(ROOT / "cases/python_imported_agent_factory")
    edges = {
        (edge.evidence.path, edge.evidence.line): edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.source_name == "Crew"
        and edge.target_kind == "agent"
    }

    positive = edges[("project_a/main.py", 8)]
    assert positive.target_id == ("py:project_a/factory.py#agent:imported-worker@6")
    assert positive.attributes == {
        "target_identity": "contextual-imported-class-factory-return",
        "target_path": "project_a/factory.py",
    }

    unresolved = {
        ("ambiguous/nested/main.py", 8),
        ("project_a/main.py", 12),
        ("project_a/main.py", 19),
        ("project_a/main.py", 25),
        ("project_a/main.py", 32),
        ("project_a/missing.py", 8),
        ("project_a/reimported.py", 9),
        ("project_a/unsupported.py", 14),
        ("project_a/unsupported.py", 18),
        ("project_a/unsupported.py", 22),
        ("project_a/unsupported.py", 26),
        ("project_a/unsupported.py", 30),
    }
    assert unresolved <= edges.keys()
    assert all(edges[key].target_id is None for key in unresolved)
    assert all(edges[key].attributes == {} for key in unresolved)


def test_python_typed_tool_parameters_require_callsite_constructor_consensus() -> None:
    ir = scan_repository(ROOT / "cases/python_typed_tool_parameter")
    edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.relation == "uses"
        and edge.target_kind == "tool"
        and edge.target_name == "tool"
    }

    assert edges[5].target_id == "py:app.py#tool:tool@4"
    assert edges[5].attributes == {"target_identity": "typed-parameter-callsite-consensus"}
    for line in (23, 33, 42, 50, 62, 72, 81, 90, 99, 112, 121, 131, 145):
        assert edges[line].target_id is None
        assert edges[line].attributes == {"target_identity": "ambiguous-repeated-binding"}

    parameter = next(
        component for component in ir.components if component.symbol_id == "py:app.py#tool:tool@4"
    )
    assert parameter.name == "ApplyPatchTool parameter tool@4"
    assert parameter.evidence.line == 4
    assert parameter.attributes == {
        "binding": "typed-parameter",
        "constructor": "ApplyPatchTool",
        "callsite_proof": "same-module-constructor-consensus",
        "verified_call_sites": 3,
        "callsite_target_ids": [
            "py:app.py#tool:ApplyPatchTool@19",
            "py:app.py#tool:patch",
            "py:app.py#tool:tool@9",
        ],
        "scope": "production",
    }
    inline_edge = next(
        edge
        for edge in ir.relationships
        if edge.evidence.path == "inline_only.py"
        and edge.evidence.line == 5
        and edge.source_kind == "agent"
        and edge.target_name == "patch"
    )
    assert inline_edge.target_id == "py:inline_only.py#tool:patch@4"
    assert inline_edge.attributes == {"target_identity": "typed-parameter-callsite-consensus"}


def test_relative_typescript_import_resolves_cross_file_tool_path() -> None:
    ir = scan_repository(ROOT / "cases/imported_ts_tool")

    finding = next(finding for finding in ir.findings if finding.rule_id == "AV-EXEC001")
    assert finding.ir_path == (
        "agent:operator",
        "tool:runCommand",
        "capability:shell-execution",
    )
    assert finding.analysis["direct_agents"] == ["operator"]
    assert finding.analysis["approval_coverage"] == "present"
    agent_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent" and edge.target_name == "importedCommand"
    )
    assert agent_edge.attributes["target_path"] == "tools.ts"
    assert agent_edge.attributes["target_name"] == "runCommand"
    tool = next(
        component
        for component in ir.components
        if component.kind == "tool" and component.evidence.path == "tools.ts"
    )
    assert agent_edge.target_id == tool.symbol_id == "ts:tools.ts#tool:runCommand"


def test_typescript_import_outside_root_or_ambiguous_stays_unresolved(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "external.ts").write_text("export const externalTool = {};\n", encoding="utf-8")
    (project / "tools.ts").write_text("export const localTool = {};\n", encoding="utf-8")
    (project / "tools.js").write_text("export const localTool = {};\n", encoding="utf-8")
    (project / "agent.ts").write_text(
        """import { Agent } from "@openai/agents";
import { externalTool } from "../external";
import { localTool } from "./tools";
const agent = new Agent({ name: "operator", tools: [externalTool, localTool] });
""",
        encoding="utf-8",
    )

    ir = scan_repository(project)

    agent_edges = [edge for edge in ir.relationships if edge.source_kind == "agent"]
    assert len(agent_edges) == 2
    assert all("target_path" not in edge.attributes for edge in agent_edges)


def test_test_scope_findings_are_opt_in() -> None:
    default_ir = scan_repository(ROOT / "cases/test_scope")
    complete_ir = scan_repository(ROOT / "cases/test_scope", include_tests=True)

    assert not default_ir.findings
    assert {finding.rule_id for finding in complete_ir.findings} == {
        "AV-APPROVAL001",
        "AV-EXEC001",
    }


def test_regex_exec_is_not_code_or_shell_execution(tmp_path: Path) -> None:
    (tmp_path / "parser.ts").write_text(
        "const match = pattern.exec(line);\nconst score = engine.eval(line);\n",
        encoding="utf-8",
    )
    (tmp_path / "parser.py").write_text("match = pattern.exec(line)\n", encoding="utf-8")

    ir = scan_repository(tmp_path)

    assert not [item for item in ir.components if item.kind == "capability"]
    assert not ir.findings


def test_typescript_literal_shell_commands_are_inventory_only(tmp_path: Path) -> None:
    (tmp_path / "commands.ts").write_text(
        """import { execSync } from \"node:child_process\";
execSync("npm install");
execSync(`npm run build`);
execSync(`npm run ${target}`);
execSync("npm " + command);
execSync(command);
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    shell = [item for item in ir.components if item.name == "shell-execution"]
    assert [item.attributes["dynamic_command"] for item in shell] == [
        False,
        False,
        True,
        True,
        True,
    ]
    assert [finding.evidence.line for finding in ir.findings] == [4, 5, 6]


def test_inline_suppression_is_rule_scoped_and_requires_reason(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """import subprocess

# agentverify: ignore AV-EXEC001 -- reviewed wrapper; input is allowlisted upstream
subprocess.run(command, shell=True)
# agentverify: ignore AV-EXEC002 -- wrong rule
subprocess.run(other_command, shell=True)
# agentverify: ignore AV-EXEC001
subprocess.run(third_command, shell=True)
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    assert ir.suppressed_findings == 1
    assert [finding.evidence.line for finding in ir.findings] == [6, 8]
    assert len(ir.suppressions) == 1
    assert ir.suppressions[0].rule_id == "AV-EXEC001"
    assert ir.suppressions[0].directive.line == 3
    assert ir.suppressions[0].reason == "reviewed wrapper; input is allowlisted upstream"
    report = json.loads(render_json(ir))
    assert report["report_format"] == "AgentVerify JSON Report"
    assert report["schema_version"] == 1
    assert report["suppressions"][0]["finding"]["line"] == 4
    assert report["risk_summary"] == {
        "by_result_kind": {"finding": 2},
        "by_rule": {"AV-EXEC001": 2},
        "by_severity": {"high": 2},
    }
    assert ir.suppressions[0].expires_on is None
    assert ir.suppressions[0].status == "active"
    assert "Inline suppression directives:" in render_text(ir)


def test_suppression_expiry_restores_expired_or_noncompliant_findings(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """import subprocess
# agentverify: ignore AV-EXEC001 until 2025-01-01 -- expired exception
subprocess.run(expired, shell=True)
# agentverify: ignore AV-EXEC001 until 2027-01-01 -- active exception
subprocess.run(active, shell=True)
# agentverify: ignore AV-EXEC001 -- missing expiry
subprocess.run(no_expiry, shell=True)
# agentverify: ignore AV-EXEC001 until tomorrow -- malformed expiry
subprocess.run(invalid, shell=True)
""",
        encoding="utf-8",
    )

    ir = scan_repository(
        tmp_path,
        require_suppression_expiry=True,
        current_date=date(2026, 8, 21),
    )

    assert [finding.evidence.line for finding in ir.findings] == [3, 7, 9]
    assert ir.suppressed_findings == 1
    assert [suppression.status for suppression in ir.suppressions] == [
        "expired",
        "active",
        "missing-expiry",
        "invalid-expiry",
    ]


def test_typescript_and_compose_inline_suppressions(tmp_path: Path) -> None:
    (tmp_path / "agent.ts").write_text(
        """import { exec } from "node:child_process";
// agentverify: ignore AV-EXEC001 -- command policy is enforced by the caller
exec(command);
""",
        encoding="utf-8",
    )
    (tmp_path / "docker-compose.yml").write_text(
        """services:
  agent:
    # agentverify: ignore AV-SANDBOX001 -- dedicated isolated build host
    privileged: true
""",
        encoding="utf-8",
    )

    ir = scan_repository(tmp_path)

    assert not ir.findings
    assert ir.suppressed_findings == 2
    assert {suppression.rule_id for suppression in ir.suppressions} == {
        "AV-EXEC001",
        "AV-SANDBOX001",
    }


def test_oversized_source_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "large.py").write_text("#" * 2_000_001, encoding="utf-8")

    ir = scan_repository(tmp_path)

    assert ir.files_scanned == 0
    assert ir.errors == ["large.py: skipped file larger than 2000000 bytes"]


def test_utf8_bom_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_bytes(b"\xef\xbb\xbffrom agents import Agent\n")

    ir = scan_repository(tmp_path)

    assert not ir.errors
    assert ("framework", "OpenAI Agents SDK") in {(item.kind, item.name) for item in ir.components}


def test_typescript_and_mcp_config() -> None:
    ir = scan_repository(ROOT / "cases/typescript_mcp")

    assert {(item.kind, item.name) for item in ir.components} >= {
        ("framework", "OpenAI Agents SDK"),
        ("protocol", "MCP"),
        ("mcp-server", "local-shell"),
        ("agent", "operator"),
        ("tool", "runCommand"),
        ("capability", "shell-execution"),
    }
    assert {
        (item.source_kind, item.source_name, item.relation, item.target_kind, item.target_name)
        for item in ir.relationships
    } >= {
        ("agent", "operator", "uses", "tool", "runCommand"),
        ("tool", "runCommand", "uses", "capability", "shell-execution"),
    }
    assert any(finding.rule_id == "AV-APPROVAL001" for finding in ir.findings)
    report = json.loads(render_json(ir))
    assert report["files_scanned"] == 1
    assert {finding["rule_id"] for finding in report["findings"]} == {
        "AV-APPROVAL001",
        "AV-EXEC001",
        "AV-MCP002",
    }
    serialized = json.dumps(report)
    assert "fixture-secret-value" not in serialized
    servers = {item["name"]: item for item in report["components"] if item["kind"] == "mcp-server"}
    assert servers["local-shell"]["attributes"]["environment_names"] == ["SERVICE_API_KEY"]
    assert servers["remote"]["attributes"]["url"] == "https://[REDACTED]@example.invalid/mcp"


def test_python_agent_mcp_servers_require_exact_direct_literal_bindings() -> None:
    ir = scan_repository(ROOT / "cases/python_agent_mcp_binding")

    servers = [
        component
        for component in ir.components
        if component.kind == "mcp-server" and component.evidence.path == "positive.py"
    ]
    assert {
        (component.evidence.line, component.name, component.symbol_id) for component in servers
    } == {
        (
            5,
            "MCPServerStdio@5",
            "py:positive.py#mcp-server:python_server",
        ),
        (9, "MCPServerStdio@9", "py:positive.py#mcp-server:git_server"),
    }
    assert "package" not in next(
        component.attributes for component in servers if component.evidence.line == 5
    )
    assert (
        next(
            component.attributes["package"] for component in servers if component.evidence.line == 9
        )
        == "mcp-server-git"
    )
    assert {
        finding.evidence.line
        for finding in ir.findings
        if finding.rule_id == "AV-MCP003" and finding.evidence.path == "positive.py"
    } == {9}

    edges = {
        edge.target_name: edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.target_kind == "mcp-server"
        and edge.evidence.path == "positive.py"
    }
    assert set(edges) == {"MCPServerStdio@5", "MCPServerStdio@9"}
    assert edges["MCPServerStdio@5"].target_id == ("py:positive.py#mcp-server:python_server")
    assert edges["MCPServerStdio@9"].target_id == "py:positive.py#mcp-server:git_server"
    assert {edge.source_id for edge in edges.values()} == {"py:positive.py#agent:agent"}
    assert {tuple(sorted(edge.attributes.items())) for edge in edges.values()} == {
        (
            ("binding", "git_server"),
            ("target_identity", "literal-mcp-servers-list-binding"),
        ),
        (
            ("binding", "python_server"),
            ("target_identity", "literal-mcp-servers-list-binding"),
        ),
    }
    assert not any(
        edge.source_kind == "agent"
        and edge.target_kind == "mcp-server"
        and edge.evidence.path in {"negative.py", "module_negative.py", "context_negative.py"}
        for edge in ir.relationships
    )

    managed_server = next(
        component
        for component in ir.components
        if component.kind == "mcp-server" and component.evidence.path == "context_positive.py"
    )
    assert managed_server.evidence.line == 6
    assert managed_server.name == "MCPServerStdio@6"
    assert managed_server.symbol_id == ("py:context_positive.py#mcp-server:managed_server")
    assert managed_server.attributes["binding_resolution"] == ("context-manager-binding")
    managed_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.target_kind == "mcp-server"
        and edge.evidence.path == "context_positive.py"
    )
    assert managed_edge.evidence.line == 10
    assert managed_edge.source_id == "py:context_positive.py#agent:managed_agent"
    assert managed_edge.target_id == ("py:context_positive.py#mcp-server:managed_server")
    assert managed_edge.attributes == {
        "binding": "managed_server",
        "target_identity": "literal-mcp-servers-list-context-manager",
    }
    assert not any(
        component.kind == "agent"
        and component.evidence.path == "context_negative.py"
        and component.evidence.line == 24
        for component in ir.components
    )
    assert not any(
        edge.source_kind == "agent"
        and edge.source_name == "duplicate-context"
        and edge.target_kind == "mcp-server"
        for edge in ir.relationships
    )

    adapter_server = next(
        component
        for component in ir.components
        if component.attributes.get("analysis") == "python-imported-mcp-server-subclass"
        and component.evidence.path == "subclass_positive.py"
    )
    assert adapter_server.name == "ProjectMCPServer@7"
    assert adapter_server.symbol_id == ("py:subclass_positive.py#mcp-server:project_server")
    assert adapter_server.attributes["adapter_definition_path"] == ("subclass_adapter.py")
    assert adapter_server.attributes["adapter_base_module"] == "agents.mcp.server"
    adapter_edge = next(
        edge
        for edge in ir.relationships
        if edge.source_name == "subclass-agent" and edge.target_kind == "mcp-server"
    )
    assert adapter_edge.source_id == ("py:subclass_positive.py#agent:subclass-agent@8")
    assert adapter_edge.target_id == ("py:subclass_positive.py#mcp-server:project_server")
    assert not any(
        edge.source_kind == "agent"
        and edge.source_name
        in {"near-subclass", "incomplete-subclass", "rebound-subclass", "forward-subclass"}
        and edge.target_kind == "mcp-server"
        for edge in ir.relationships
    )

    module_servers = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "mcp-server" and component.evidence.path == "module_positive.py"
    }
    assert set(module_servers) == {6, 7}
    assert module_servers[6].symbol_id == ("py:module_positive.py#mcp-server:module_stdio_server")
    assert module_servers[6].attributes["transport"] == "stdio"
    assert module_servers[7].symbol_id == ("py:module_positive.py#mcp-server:module_fastmcp_server")
    assert module_servers[7].attributes["transport"] == "in-process"
    assert module_servers[7].attributes["constructor"] == "FastMCP"
    assert module_servers[7].attributes["analysis"] == (
        "python-import-bound-mcp-server-constructor"
    )

    module_edges = {
        edge.evidence.line: edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.target_kind == "mcp-server"
        and edge.evidence.path == "module_positive.py"
    }
    assert set(module_edges) == {11, 15}
    assert module_edges[11].target_id == ("py:module_positive.py#mcp-server:module_stdio_server")
    assert module_edges[15].target_id == ("py:module_positive.py#mcp-server:module_fastmcp_server")
    assert {edge.attributes["target_identity"] for edge in module_edges.values()} == {
        "literal-mcp-servers-list-module-binding"
    }
    assert not any(
        component.kind == "mcp-server"
        and component.evidence.path == "module_negative.py"
        and component.evidence.line == 26
        for component in ir.components
    )

    fastmcp_registration = next(
        edge
        for edge in ir.relationships
        if edge.source_kind == "mcp-server"
        and edge.target_kind == "tool"
        and edge.evidence.path == "fastmcp_chain_positive.py"
    )
    assert fastmcp_registration.evidence.line == 10
    assert fastmcp_registration.source_id == ("py:fastmcp_chain_positive.py#mcp-server:server")
    assert fastmcp_registration.target_id == ("py:fastmcp_chain_positive.py#tool:write_file")
    assert fastmcp_registration.attributes == {
        "registrar": "server.tool",
        "target_identity": "exact-fastmcp-registrar",
    }
    filesystem = next(
        component
        for component in ir.components
        if component.kind == "capability"
        and component.evidence.path == "fastmcp_chain_positive.py"
        and component.evidence.line == 12
    )
    path, context = component_context(ir, filesystem)
    assert path == (
        "agent:filesystem-agent",
        "mcp-server:FastMCP@7",
        "tool:write_file",
        "capability:filesystem",
    )
    assert context["mcp_server"] == "FastMCP@7"
    assert context["reachable_agents"] == ["filesystem-agent"]
    assert not any(
        edge.source_kind == "mcp-server"
        and edge.target_kind == "tool"
        and edge.evidence.path in {"fastmcp_chain_negative.py", "module_negative.py"}
        for edge in ir.relationships
    )
    optional_server = next(
        component
        for component in ir.components
        if component.kind == "mcp-server"
        and component.evidence.path == "module_negative.py"
        and component.evidence.line == 34
    )
    assert optional_server.symbol_id is None


def test_python_openai_mcp_server_approval_policy_is_exact() -> None:
    ir = scan_repository(ROOT / "cases/python_openai_mcp_approval_policy")

    servers = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "mcp-server" and component.evidence.path == "app.py"
    }
    assert set(servers) == {22, 26, 30, 34, 38, 42, 46, 50, 54, 58}
    for line in (22, 26, 30, 34, 38, 42, 46, 50, 54):
        assert servers[line].attributes["mcp_approval_contract"] == (
            "openai-agents-python-mcp-server"
        )
        assert servers[line].attributes["mcp_approval_source"] == "callsite-require-approval"
        assert servers[line].attributes["mcp_approval_constructor"] == "MCPServerStdio"

    assert servers[22].attributes["mcp_approval_policy"] == "disabled-explicit"
    assert servers[22].attributes["mcp_approval_requirement"] == "never"
    assert servers[22].attributes["approval_policy"] == "disabled-explicit"

    assert servers[26].attributes["mcp_approval_binding"] == "require_approval"
    assert servers[26].attributes["mcp_approval_resolution"] == "same-block-literal-string"
    assert servers[26].attributes["mcp_approval_policy"] == "always-required"
    assert servers[26].attributes["mcp_approval_requirement"] == "always"

    assert servers[30].attributes["mcp_approval_binding"] == "selective_policy"
    assert servers[30].attributes["mcp_approval_resolution"] == "same-block-literal"
    assert servers[30].attributes["mcp_approval_policy"] == "selective"
    assert servers[30].attributes["mcp_approval_never_tool_names"] == ["read_file"]
    assert servers[30].attributes["mcp_approval_never_read_only"] is True
    assert servers[30].attributes["mcp_approval_always_tool_names"] == ["write_file"]

    assert servers[34].attributes["mcp_approval_binding"] == "dynamic_policy"
    assert servers[34].attributes["mcp_approval_policy"] == "dynamic"

    assert servers[38].attributes["mcp_approval_binding"] == "IMPORTED_ALWAYS"
    assert servers[38].attributes["mcp_approval_resolution"] == (
        "imported-local-literal:repository-module-single-path"
    )
    assert servers[38].attributes["mcp_approval_policy"] == "always-required"
    assert servers[38].attributes["mcp_approval_requirement"] == "always"

    assert servers[42].attributes["mcp_approval_binding"] == "IMPORTED_SELECTIVE"
    assert servers[42].attributes["mcp_approval_resolution"] == (
        "imported-local-literal:repository-module-single-path"
    )
    assert servers[42].attributes["mcp_approval_policy"] == "selective"
    assert servers[42].attributes["mcp_approval_never_tool_names"] == ["read_policy"]
    assert servers[42].attributes["mcp_approval_always_tool_names"] == ["write_policy"]

    assert servers[46].attributes["mcp_approval_binding"] == "MUTATED_POLICY"
    assert servers[46].attributes["mcp_approval_policy"] == "dynamic"

    assert servers[50].attributes["mcp_approval_binding"] == "REEXPORTED_SELECTIVE"
    assert servers[50].attributes["mcp_approval_resolution"] == (
        "imported-local-reexport-literal:repository-module-single-path"
    )
    assert servers[50].attributes["mcp_approval_policy"] == "selective"
    assert servers[50].attributes["mcp_approval_never_tool_names"] == ["read_policy"]
    assert servers[50].attributes["mcp_approval_always_tool_names"] == ["write_policy"]

    assert servers[54].attributes["mcp_approval_binding"] == "REEXPORTED_MUTATED_POLICY"
    assert servers[54].attributes["mcp_approval_policy"] == "dynamic"

    assert "mcp_approval_policy" not in servers[58].attributes

    star_servers = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "mcp-server" and component.evidence.path == "star_app.py"
    }
    assert set(star_servers) == {10, 14}
    for line in (10, 14):
        assert star_servers[line].attributes["mcp_approval_contract"] == (
            "openai-agents-python-mcp-server"
        )
        assert star_servers[line].attributes["mcp_approval_source"] == (
            "callsite-require-approval"
        )
        assert star_servers[line].attributes["mcp_approval_constructor"] == "MCPServerStdio"
    assert star_servers[10].attributes["mcp_approval_binding"] == (
        "STAR_REEXPORTED_SELECTIVE"
    )
    assert star_servers[10].attributes["mcp_approval_resolution"] == (
        "imported-local-star-reexport-literal:repository-module-single-path"
    )
    assert star_servers[10].attributes["mcp_approval_policy"] == "selective"
    assert star_servers[10].attributes["mcp_approval_never_tool_names"] == [
        "read_policy"
    ]
    assert star_servers[10].attributes["mcp_approval_always_tool_names"] == [
        "write_policy"
    ]
    assert star_servers[14].attributes["mcp_approval_binding"] == (
        "STAR_REEXPORTED_MUTATED_POLICY"
    )
    assert star_servers[14].attributes["mcp_approval_policy"] == "dynamic"

    star_import_servers = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "mcp-server" and component.evidence.path == "star_import_app.py"
    }
    assert set(star_import_servers) == {7, 11}
    for line in (7, 11):
        assert star_import_servers[line].attributes["mcp_approval_contract"] == (
            "openai-agents-python-mcp-server"
        )
        assert star_import_servers[line].attributes["mcp_approval_source"] == (
            "callsite-require-approval"
        )
        assert star_import_servers[line].attributes["mcp_approval_constructor"] == (
            "MCPServerStdio"
        )
    assert star_import_servers[7].attributes["mcp_approval_binding"] == (
        "IMPORTED_SELECTIVE"
    )
    assert star_import_servers[7].attributes["mcp_approval_resolution"] == (
        "imported-local-star-import-literal:repository-module-single-path"
    )
    assert star_import_servers[7].attributes["mcp_approval_policy"] == "selective"
    assert star_import_servers[7].attributes["mcp_approval_never_tool_names"] == [
        "read_policy"
    ]
    assert star_import_servers[7].attributes["mcp_approval_always_tool_names"] == [
        "write_policy"
    ]
    assert star_import_servers[11].attributes["mcp_approval_binding"] == (
        "MUTATED_POLICY"
    )
    assert star_import_servers[11].attributes["mcp_approval_policy"] == "dynamic"

    ambiguous_star_import_server = next(
        component
        for component in ir.components
        if component.kind == "mcp-server"
        and component.evidence.path == "ambiguous_star_import_app.py"
    )
    assert ambiguous_star_import_server.evidence.line == 8
    assert ambiguous_star_import_server.attributes["mcp_approval_contract"] == (
        "openai-agents-python-mcp-server"
    )
    assert ambiguous_star_import_server.attributes["mcp_approval_binding"] == (
        "IMPORTED_SELECTIVE"
    )
    assert ambiguous_star_import_server.attributes["mcp_approval_resolution"] == (
        "imported-local-star-import-literal:repository-module-single-path"
    )
    assert ambiguous_star_import_server.attributes["mcp_approval_policy"] == "selective"
    assert ambiguous_star_import_server.attributes["mcp_approval_never_tool_names"] == [
        "read_policy"
    ]
    assert ambiguous_star_import_server.attributes["mcp_approval_always_tool_names"] == [
        "write_policy"
    ]

    subclass_server = next(
        component
        for component in ir.components
        if component.kind == "mcp-server" and component.evidence.path == "subclass_app.py"
    )
    assert subclass_server.evidence.line == 7
    assert subclass_server.attributes["analysis"] == "python-imported-mcp-server-subclass"
    assert subclass_server.attributes["adapter_base_module"] == "agents.mcp.server"
    assert subclass_server.attributes["mcp_approval_constructor"] == "ProjectMCPServer"
    assert subclass_server.attributes["mcp_approval_policy"] == "always-required"
    assert subclass_server.attributes["mcp_approval_requirement"] is True

    remote_servers = {
        component.evidence.line: component
        for component in ir.components
        if component.kind == "mcp-server" and component.evidence.path == "remote_app.py"
    }
    assert set(remote_servers) == {7, 11, 19}
    assert remote_servers[7].attributes["transport"] == "sse"
    assert remote_servers[7].attributes["url"] == "https://[REDACTED]@example.com/sse"
    assert remote_servers[7].attributes["mcp_remote_headers"] == "configured"
    assert remote_servers[7].attributes["mcp_remote_header_names"] == ["Authorization"]
    assert remote_servers[7].attributes["mcp_remote_auth_sources"] == [
        "authorization-header"
    ]
    assert remote_servers[7].attributes["mcp_approval_constructor"] == "MCPServerSse"
    assert remote_servers[7].attributes["mcp_approval_policy"] == "always-required"
    assert remote_servers[11].attributes["transport"] == "streamable-http"
    assert remote_servers[11].attributes["url"] == "https://api.example.com/mcp"
    assert remote_servers[11].attributes["mcp_remote_auth"] == "configured"
    assert remote_servers[11].attributes["mcp_remote_auth_binding"] == "auth"
    assert remote_servers[11].attributes["mcp_remote_auth_sources"] == ["auth-param"]
    assert remote_servers[11].attributes["mcp_remote_http_client_factory"] == "configured"
    assert remote_servers[11].attributes["mcp_remote_http_client_factory_binding"] == "factory"
    assert remote_servers[11].attributes["mcp_approval_constructor"] == (
        "MCPServerStreamableHttp"
    )
    assert remote_servers[11].attributes["mcp_approval_policy"] == "selective"
    assert remote_servers[11].attributes["mcp_approval_never_tool_names"] == ["read"]
    assert remote_servers[11].attributes["mcp_approval_always_tool_names"] == ["write"]
    assert remote_servers[19].attributes["transport"] == "sse"
    assert remote_servers[19].attributes["url"] == "https://fake.example.com/sse"
    assert "mcp_approval_policy" not in remote_servers[19].attributes

    remote_edges = {
        edge.target_id: edge
        for edge in ir.relationships
        if edge.source_kind == "agent"
        and edge.target_kind == "mcp-server"
        and edge.evidence.path == "remote_app.py"
    }
    assert set(remote_edges) == {
        "py:remote_app.py#mcp-server:sse_server",
        "py:remote_app.py#mcp-server:http_server",
        "py:remote_app.py#mcp-server:fake_server",
    }


def test_mcp_package_launchers_require_literal_mcp_structure_and_auto_install() -> None:
    ir = scan_repository(ROOT / "cases/mcp_package_launchers")
    servers = [component for component in ir.components if component.kind == "mcp-server"]

    assert len(servers) == 25
    assert {
        (component.evidence.path, component.evidence.line)
        for component in servers
        if "package" not in component.attributes
    } >= {("launchers.py", 31), ("launchers.py", 45)}
    assert {component.attributes["frontend"] for component in servers} == {
        "json",
        "python",
        "typescript",
    }
    assert {
        (
            component.attributes["package_spec"],
            component.attributes["version_scope"],
            component.attributes["auto_install"],
        )
        for component in servers
        if "package_spec" in component.attributes
    } >= {
        ("@modelcontextprotocol/server-filesystem", "unpinned", True),
        ("@x402scan/mcp@latest", "floating", True),
        ("mcp-server-git", "unpinned", True),
        ("mcp-server-fetch==2026.7.10", "exact", True),
        ("alternate-mcp-server==1.0.0rc1", "exact", True),
        ("restored-server@3.0.0", "exact", True),
        ("repomix@1.4.2", "exact", True),
        ("@scope/local-server", "unpinned", False),
        ("unreviewed-server", "unpinned", False),
        ("@playwright/mcp", "unpinned", True),
        ("@scope/server@2.3.4", "exact", True),
    }
    assert {
        (finding.rule_id, finding.evidence.path, finding.evidence.line) for finding in ir.findings
    } == {
        ("AV-MCP003", ".mcp.json", 1),
        ("AV-MCP003", "launchers.py", 11),
        ("AV-MCP003", "launchers.py", 15),
        ("AV-MCP003", "launchers.py", 16),
        ("AV-MCP003", "launchers.py", 36),
        ("AV-MCP003", "launchers.py", 37),
        ("AV-MCP003", "launchers.ts", 9),
        ("AV-MCP003", "launchers.ts", 31),
        ("AV-MCP003", "launchers.ts", 32),
        ("AV-MCP003", "launchers.ts", 40),
        ("AV-MCP003", "official-client.ts", 3),
    }
    assert not any(
        component.attributes.get("package")
        in {
            "not-an-mcp-constructor",
            "ordinary-package",
            "shadowed-package",
            "rebound-package",
            "lookalike-package",
            "same-scope-lookalike-package",
        }
        for component in servers
    )


def test_cli_fail_on_high(capsys) -> None:
    exit_code = main(["scan", str(ROOT / "cases/python_dangerous"), "--fail-on", "high"])
    assert exit_code == 1
    assert "AV-EXEC001" in capsys.readouterr().out


def test_sarif_contains_location_fingerprint_and_ir_context() -> None:
    ir = scan_repository(ROOT / "cases/python_dangerous")

    sarif = json.loads(render_sarif(ir))
    result = sarif["runs"][0]["results"][0]
    descriptor = sarif["runs"][0]["tool"]["driver"]["rules"][0]
    assert sarif["version"] == "2.1.0"
    assert "informationUri" not in sarif["runs"][0]["tool"]["driver"]
    assert sarif["runs"][0]["properties"] == {
        "scanScope": "repository",
        "pathFilters": [],
        "baselineSummary": {},
        "policySummary": {},
    }
    assert result["ruleId"] == "AV-EXEC001"
    assert descriptor["shortDescription"] == {
        "text": "A dynamic command is executed through a system shell"
    }
    assert descriptor["properties"] == {
        "defaultSeverity": "high",
        "precision": "high",
        "resultKind": "finding",
    }
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 13
    assert result["partialFingerprints"]["agentverify/v1"]
    assert result["properties"]["irPath"][0] == "agent:operator"


def test_native_ai_bom_is_deterministic_evidence_first_and_schema_shaped() -> None:
    ir = scan_repository(ROOT / "cases/python_dangerous")

    rendered = render_bom(ir)
    assert rendered == render_bom(ir)
    bom = json.loads(rendered)
    schema = json.loads(
        (ROOT / "src/agentverify/schemas/agentverify-ai-bom-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(bom)
    assert set(bom) == set(schema["required"])
    assert bom["bom_format"] == "AgentVerify AI BOM"
    assert bom["spec_version"] == "1.2"
    assert bom["metadata"]["root"] == "."
    assert bom["metadata"]["scan_scope"] == "repository"
    assert len({asset["id"] for asset in bom["assets"]}) == len(bom["assets"])
    shell = next(
        asset
        for asset in bom["assets"]
        if asset["kind"] == "capability" and asset["name"] == "shell-execution"
    )
    assert shell["evidence"] == {
        "path": "agent.py",
        "line": 13,
        "excerpt": "return subprocess.run(command, shell=True, capture_output=True, text=True).stdout",
    }
    assert bom["governance"]["risk_summary"] == {
        "by_result_kind": {"finding": 1},
        "by_rule": {"AV-EXEC001": 1},
        "by_severity": {"high": 1},
    }
    assert bom["risks"][0]["ir_path"][-1] == "capability:shell-execution"


def test_native_ai_bom_does_not_hide_ambiguous_display_names() -> None:
    bom = json.loads(render_bom(scan_repository(ROOT / "cases/symbol_collision")))

    assert len({asset["id"] for asset in bom["assets"]}) == len(bom["assets"])
    assert len({edge["id"] for edge in bom["relationships"]}) == len(bom["relationships"])
    run_command_endpoints = [
        endpoint
        for relationship in bom["relationships"]
        for endpoint in (relationship["source"], relationship["target"])
        if endpoint["kind"] == "tool" and endpoint["name"] == "run_command"
    ]
    assert run_command_endpoints
    resolutions = [endpoint["resolution"] for endpoint in run_command_endpoints]
    assert resolutions.count("symbol-id") == 3
    assert resolutions.count("ambiguous") == 1
    ambiguous = next(
        endpoint for endpoint in run_command_endpoints if endpoint["resolution"] == "ambiguous"
    )
    assert len(ambiguous["candidate_asset_ids"]) == 2


def test_native_ai_bom_resolves_relationship_endpoints_by_exact_evidence() -> None:
    bom = json.loads(render_bom(scan_repository(ROOT / "cases/mcp_forwarder")))

    registry_edge = next(
        relationship
        for relationship in bom["relationships"]
        if relationship["evidence"]["line"] == 36
        and relationship["target"]["name"] == "tool-registry"
    )
    assert registry_edge["source"]["resolution"] == "evidence-location"
    assert registry_edge["target"]["resolution"] == "evidence-location"
    assert (
        registry_edge["source"]["resolution_path"],
        registry_edge["source"]["resolution_line"],
    ) == ("proxy.py", 36)
    assert (
        registry_edge["target"]["resolution_path"],
        registry_edge["target"]["resolution_line"],
    ) == ("proxy.py", 35)
    assert registry_edge["source"]["asset_id"] != registry_edge["target"]["asset_id"]


def test_native_ai_bom_does_not_embed_checkout_path(tmp_path: Path) -> None:
    source = (ROOT / "examples/safe_agent/agent.py").read_text(encoding="utf-8")
    outputs = []
    for directory_name in ("checkout-one", "checkout-two"):
        checkout = tmp_path / directory_name
        checkout.mkdir()
        (checkout / "agent.py").write_text(source, encoding="utf-8")
        outputs.append(render_bom(scan_repository(checkout)))

    assert outputs[0] == outputs[1]
    assert str(tmp_path) not in outputs[0]


def test_policy_decision_evidence_is_retained_by_all_reporters() -> None:
    ir = scan_repository(ROOT / "cases/python_dangerous")
    policy = normalize_policy(
        {
            "schema_version": 1,
            "name": "release",
            "gates": [{"id": "high", "max_count": 0}],
        }
    )
    assert evaluate_policy(ir, policy, source="policy.json", digest="a" * 64) is False

    json_report = json.loads(render_json(ir))
    bom = json.loads(render_bom(ir))
    sarif = json.loads(render_sarif(ir))
    text_report = render_text(ir)
    assert json_report["policy_summary"]["gates"][0]["matched_count"] == 1
    assert json_report["policy_summary"]["gates"][0]["matched_summary"] == {
        "by_result_kind": {"finding": 1},
        "by_rule": {"AV-EXEC001": 1},
        "by_severity": {"high": 1},
    }
    bom_schema = json.loads(
        (ROOT / "src/agentverify/schemas/agentverify-ai-bom-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    report_schema = json.loads(
        (ROOT / "src/agentverify/schemas/agentverify-report-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(bom_schema).validate(bom)
    Draft202012Validator(report_schema).validate(json_report)
    assert bom["metadata"]["policy_summary"] == json_report["policy_summary"]
    assert sarif["runs"][0]["properties"]["policySummary"] == json_report["policy_summary"]
    assert "Policy: release [failed; 1 gates]" in text_report
    assert "high: 1 matched / 0 allowed [failed] (AV-EXEC001=1)" in text_report
