import {
  RealtimeAgent,
  RealtimeOutputGuardrail,
  RealtimeSession,
  RealtimeSessionOptions,
} from "@openai/agents/realtime";

const greeter = new RealtimeAgent({
  name: "Realtime greeter",
  instructions: "Greet the user with cheer and answer questions.",
});

const namedGuardrails: RealtimeOutputGuardrail[] = [
  {
    name: "No mention of Dom",
    async execute({ agentOutput }) {
      const domInOutput = agentOutput.includes("Dom");
      return {
        tripwireTriggered: domInOutput,
        outputInfo: { domInOutput },
      };
    },
  },
];

const typedOptions: RealtimeSessionOptions = {
  outputGuardrails: namedGuardrails,
  outputGuardrailSettings: {
    debounceTextLength: 500,
  },
};

const guardedSession = new RealtimeSession(greeter, {
  outputGuardrails: namedGuardrails,
});

const inlineSession = new RealtimeSession(greeter, {
  outputGuardrails: [
    {
      name: "No payment advice",
      async execute({ agentOutput }) {
        return {
          tripwireTriggered: agentOutput.includes("wire transfer"),
        };
      },
    },
  ],
  outputGuardrailSettings: {
    debounceTextLength: -1,
  },
});

const spreadOptionsSession = new RealtimeSession(greeter, {
  ...typedOptions,
});

const looseSession = {
  outputGuardrails: namedGuardrails,
};
void looseSession;

const mutableGuardrails: RealtimeOutputGuardrail[] = [];
mutableGuardrails.push({
  name: "Added later",
  async execute() {
    return { tripwireTriggered: true };
  },
});

const mutableSession = new RealtimeSession(greeter, {
  outputGuardrails: mutableGuardrails,
});

const dynamicDebounce = Number(process.env.REALTIME_GUARDRAIL_DEBOUNCE);
const dynamicSettingsSession = new RealtimeSession(greeter, {
  outputGuardrails: [],
  outputGuardrailSettings: {
    debounceTextLength: dynamicDebounce,
  },
});
