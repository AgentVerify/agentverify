import {
  OpenAIRealtimeSIP,
  RealtimeAgent,
  RealtimeSession,
} from "@openai/agents/realtime";

const API_KEY_PLACEHOLDER = "<your api key>";

const greeter = new RealtimeAgent({
  name: "Realtime greeter",
});

const defaultSession = new RealtimeSession(greeter);
await defaultSession.connect({ apiKey: API_KEY_PLACEHOLDER });

const ephemeralSession = new RealtimeSession(greeter);
await ephemeralSession.connect({
  apiKey: "ek_test_client_secret",
});

const websocketSession = new RealtimeSession(greeter, {
  transport: "websocket",
});
await websocketSession.connect({ apiKey: process.env.OPENAI_API_KEY! });

const sipSession = new RealtimeSession(greeter, {
  transport: new OpenAIRealtimeSIP(),
});
await sipSession.connect({
  apiKey: process.env["OPENAI_API_KEY"]!,
  callId: "call_123",
});

const { apiKey } = await fetch("/path/to/ephemeral/key/generation").then((resp) =>
  resp.json(),
);
const browserSession = new RealtimeSession(greeter);
await browserSession.connect({ apiKey });

const looseSession = {
  connect(_options: unknown) {},
};
looseSession.connect({ apiKey: process.env.OPENAI_API_KEY! });

const unresolvedSession = new RealtimeSession(greeter);
let dynamicApiKey = process.env.OPENAI_API_KEY!;
dynamicApiKey = "changed";
await unresolvedSession.connect({ apiKey: dynamicApiKey });
