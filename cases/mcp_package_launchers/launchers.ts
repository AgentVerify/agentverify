import { StdioClientTransport as Stdio } from "@modelcontextprotocol/sdk/client/stdio.js";
import { StdioClientTransport as Shadowed } from "@modelcontextprotocol/sdk/client/stdio.js";
import { StdioClientTransport as Rebound } from "@modelcontextprotocol/sdk/client/stdio.js";
import { StdioClientTransport as Fake } from "ordinary-package";

const workspace = getWorkspace();
const dynamicPackage = getPackage();

const automatic = new Stdio({
  command: "npx",
  args: ["-y", "@modelcontextprotocol/server-filesystem", workspace],
});
const pinned = new Stdio({ command: "npx", args: ["-y", "repomix@1.4.2"] });
const cached = new Stdio({
  command: "npx",
  args: ["--no-install", "@scope/local-server"],
});
const prompted = new Stdio({ command: "npx", args: ["unreviewed-server"] });
const unresolved = new Stdio({ command: "uvx", args: [dynamicPackage] });

function shadowedConstructor(Shadowed: unknown) {
  return new Shadowed({ command: "npx", args: ["-y", "shadowed-package"] });
}

Rebound = getTransport();
const rebound = new Rebound({ command: "npx", args: ["-y", "rebound-package"] });
const fake = new Fake({ command: "npx", args: ["-y", "lookalike-package"] });

const config = {
  mcpServers: {
    time: { command: "uvx", args: ["mcp-server-time"] },
    floating: { command: "npx", args: ["-y", "@x402scan/mcp@latest"] },
    pinned: { command: "npx", args: ["-y", "@scope/server@2.3.4"] },
    dynamic: { command: "uvx", args: [dynamicPackage] },
  },
};

const quoted = {
  "mcpServers": {
    "memory": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"] },
  },
};

const ordinary = {
  servers: { fake: { command: "npx", args: ["-y", "ordinary-package"] } },
};

import { StdioClientTransport as SiblingPackage } from "@modelcontextprotocol/not-the-sdk";
const siblingPackage = new SiblingPackage({
  command: "npx",
  args: ["-y", "same-scope-lookalike-package"],
});
