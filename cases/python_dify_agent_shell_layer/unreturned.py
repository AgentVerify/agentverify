from dify_agent.layers.runtime import DIFY_RUNTIME_LAYER_TYPE_ID, DifyRuntimeLayerConfig
from dify_agent.layers.shell import DIFY_SHELL_LAYER_TYPE_ID, DifyShellLayerConfig
from dify_agent.protocol import CreateRunRequest, RunComposition, RunLayerSpec

DIFY_RUNTIME_LAYER_ID = "runtime"


def shell_dependencies() -> dict[str, str]:
    return {"runtime": DIFY_RUNTIME_LAYER_ID}


class AgentRunInput:
    include_shell: bool = False
    config_layer_config: object | None = None
    shell_config: DifyShellLayerConfig | None = None
    backend_binding_ref: str


class RequestBuilder:
    def build(self, run_input: AgentRunInput) -> CreateRunRequest:
        layers: list[RunLayerSpec] = []
        include_shell = run_input.include_shell or run_input.config_layer_config is not None
        if include_shell:
            layers.append(
                RunLayerSpec(
                    type=DIFY_RUNTIME_LAYER_TYPE_ID,
                    config=DifyRuntimeLayerConfig(
                        backend_binding_ref=run_input.backend_binding_ref
                    ),
                )
            )
            layers.append(
                RunLayerSpec(
                    type=DIFY_SHELL_LAYER_TYPE_ID,
                    deps=shell_dependencies(),
                    config=run_input.shell_config or DifyShellLayerConfig(),
                )
            )
        return CreateRunRequest(composition=RunComposition(layers=[]))
