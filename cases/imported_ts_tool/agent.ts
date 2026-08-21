import { Agent } from "@openai/agents";
import { runCommand as importedCommand } from "./tools.js";

const agent = new Agent({
  name: "operator",
  tools: [importedCommand],
});

void agent;
