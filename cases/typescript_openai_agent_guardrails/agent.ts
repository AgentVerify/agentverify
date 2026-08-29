import {
  Agent,
  InputGuardrail,
  OutputGuardrail,
} from "@openai/agents";

const typedInputGuardrail: InputGuardrail = {
  name: "Math homework guardrail",
  async execute() {
    return { tripwireTriggered: false };
  },
};

const outputSchema = {};

const typedOutputGuardrail: OutputGuardrail<typeof outputSchema> = {
  name: "Phone number guardrail",
  async execute() {
    return { tripwireTriggered: false };
  },
};

const supportAgent = new Agent({
  name: "Customer support agent",
  instructions: "You help customers with their questions.",
  inputGuardrails: [
    typedInputGuardrail,
    {
      name: "Inline abuse guardrail",
      async execute() {
        return { tripwireTriggered: false };
      },
    },
  ],
});

const assistantAgent = new Agent<unknown, typeof outputSchema>({
  name: "Assistant",
  instructions: "You are a helpful assistant.",
  outputGuardrails: [typedOutputGuardrail],
});

const looseAgent = {
  name: "Loose",
  inputGuardrails: [typedInputGuardrail],
};
void looseAgent;

const mutableOutputGuardrail: OutputGuardrail = {
  name: "Initial mutable guardrail",
  async execute() {
    return { tripwireTriggered: false };
  },
};
mutableOutputGuardrail.name = "Changed guardrail";

const mutableAgent = new Agent({
  name: "Mutable output agent",
  outputGuardrails: [mutableOutputGuardrail],
});

const dynamicGuardrails = process.env.ENABLE_GUARDRAILS ? [typedInputGuardrail] : [];
const dynamicAgent = new Agent({
  name: "Dynamic guardrail agent",
  inputGuardrails: dynamicGuardrails,
});
