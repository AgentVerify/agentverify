import {
  RealtimeAgent,
  RealtimeSession,
  type RealtimeSessionOptions,
} from "@openai/agents/realtime";

const dynamicTurnDetectionType = process.env.REALTIME_TURN_DETECTION_TYPE;

const greeter = new RealtimeAgent({
  name: "Realtime greeter",
});

const stableSessionOptions: Partial<RealtimeSessionOptions> = {
  model: "gpt-realtime-2.1",
  config: {
    audio: {
      input: {
        turnDetection: {
          type: "semantic_vad",
          interruptResponse: true,
        },
      },
    },
  },
};

const dynamicSessionOptions: Partial<RealtimeSessionOptions> = {
  config: {
    audio: {
      input: {
        turnDetection: {
          type: dynamicTurnDetectionType,
        },
      },
    },
  },
};

export const spreadOptionsSession = new RealtimeSession(greeter, {
  ...stableSessionOptions,
});

export const dynamicSpreadOptionsSession = new RealtimeSession(greeter, {
  ...dynamicSessionOptions,
});
