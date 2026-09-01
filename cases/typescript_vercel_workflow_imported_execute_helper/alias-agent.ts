import { WorkflowAgent } from "@ai-sdk/workflow";
import { z } from "zod";
import { importedCalculate, shared as importedShared } from "./helpers";

const aliasedCalculate = importedCalculate;
const aliasedShared = importedShared;

const aliasTools = {
  aliasedCalculate: {
    inputSchema: z.object({ expression: z.string() }),
    execute: aliasedCalculate,
  },
  directShared: {
    inputSchema: z.object({ value: z.string() }),
    execute: importedShared,
  },
  aliasedShared: {
    inputSchema: z.object({ value: z.string() }),
    execute: aliasedShared,
  },
};

const aliasAgent = new WorkflowAgent({ model: {}, tools: aliasTools });
void aliasAgent;
