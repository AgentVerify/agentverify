import { RealtimeAgent, RealtimeSession } from "@openai/agents/realtime";

const greeter = new RealtimeAgent({
  name: "Realtime greeter",
});

const session = new RealtimeSession(greeter, {
  model: "gpt-realtime-2.1",
});

session.on("tool_approval_requested", (_context, _agent, request) => {
  session.approve(request.approvalItem);
  session.reject(request.approvalItem);
});

session.on("response_done", (_context, _agent, request) => {
  session.approve(request.approvalItem);
});

session.on("tool_approval_requested", (_context, _agent, request) => {
  session.approve(other.approvalItem);
});

const looseSession = {
  on(_event: string, _callback: unknown) {},
  approve(_approvalItem: unknown) {},
};

looseSession.on("tool_approval_requested", (_context, _agent, request) => {
  looseSession.approve(request.approvalItem);
});
