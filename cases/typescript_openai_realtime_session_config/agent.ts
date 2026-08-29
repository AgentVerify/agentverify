import { RealtimeAgent, RealtimeSession } from "@openai/agents/realtime";

const dynamicParallelToolCalls = Boolean(process.env.REALTIME_PARALLEL_TOOL_CALLS);
const dynamicOutputModalities = ["audio"];
const dynamicAudioFormat = process.env.REALTIME_AUDIO_FORMAT;
const dynamicTranscriptionLanguages = ["en"];
const dynamicTranscriptionKeywords = ["OpenAI Agents SDK"];

const greeter = new RealtimeAgent({
  name: "Realtime greeter",
});

export const sequentialSession = new RealtimeSession(greeter, {
  config: {
    parallelToolCalls: false,
  },
});

export const parallelSession = new RealtimeSession(greeter, {
  config: {
    parallelToolCalls: true,
  },
});

export const reasoningSession = new RealtimeSession(greeter, {
  config: {
    reasoning: {
      effort: "low",
    },
  },
});

export const audioSession = new RealtimeSession(greeter, {
  config: {
    outputModalities: ["audio"],
  },
});

export const audioDetailsSession = new RealtimeSession(greeter, {
  config: {
    audio: {
      input: {
        format: "pcm16",
        transcription: {
          model: "gpt-live-transcribe",
          delay: "low",
          prompt: "A software support conversation about the OpenAI Agents SDK.",
          keywords: ["OpenAI Agents SDK", "RealtimeSession"],
          languages: ["en", "ja"],
        },
      },
      output: {
        format: "pcm16",
      },
    },
  },
});

export const dynamicSession = new RealtimeSession(greeter, {
  config: {
    parallelToolCalls: dynamicParallelToolCalls,
    outputModalities: dynamicOutputModalities,
    audio: {
      input: {
        format: dynamicAudioFormat,
        transcription: {
          model: process.env.REALTIME_TRANSCRIPTION_MODEL,
          prompt: process.env.REALTIME_TRANSCRIPTION_PROMPT,
          keywords: dynamicTranscriptionKeywords,
          languages: dynamicTranscriptionLanguages,
        },
      },
    },
  },
});
