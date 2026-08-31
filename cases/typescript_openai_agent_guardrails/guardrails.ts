import {
  InputGuardrail,
  OutputGuardrail,
} from "@openai/agents";

export const importedInputGuardrails: InputGuardrail[] = [
  {
    name: "Imported homework guardrail",
    async execute() {
      return { tripwireTriggered: false };
    },
  },
];

const schema = {};

export const importedOutputGuardrails: OutputGuardrail<typeof schema>[] = [
  {
    name: "Imported answer guardrail",
    async execute() {
      return { tripwireTriggered: true };
    },
  },
];
