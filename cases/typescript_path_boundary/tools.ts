import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import fs from "fs/promises";
import { validatePath } from "./guard.js";
import { validatePath as pretendValidatePath } from "./weak-guard.js";

const server = new McpServer({ name: "files", version: "1.0.0" });

server.registerTool("safe-directory", {}, async ({ path }) => {
  const validPath = await validatePath(path);
  await fs.mkdir(validPath, { recursive: true });
  return { content: [] };
});

server.registerTool("unsafe-directory", {}, async ({ path }) => {
  const uncheckedPath = pretendValidatePath(path);
  await fs.mkdir(uncheckedPath, { recursive: true });
  return { content: [] };
});

server.registerTool("reassigned-directory", {}, async ({ path }) => {
  let validPath = await validatePath(path);
  validPath = path;
  await fs.mkdir(validPath, { recursive: true });
  return { content: [] };
});
