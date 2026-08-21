const example = `server.registerTool("string-only", {}, async () => {})`;

const registry = {
  registerTool(_name: string, _handler: unknown) {},
};

registry.registerTool("ordinary-registry", () => example);

const unrelated = {
  nested: createTool({ execute: async () => "not imported" }),
};

void unrelated;

const handler = { fetch: (value: string) => value };
handler.fetch("not-a-network-client");
