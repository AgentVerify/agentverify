import { WorkflowAgent } from "@ai-sdk/workflow";
import { z } from "zod";
import { importedCalculate, shared as importedShared } from "./helpers";

const tools = {
  importedCalculate: {
    inputSchema: z.object({ expression: z.string() }),
    execute: importedCalculate,
  },
  firstShared: {
    inputSchema: z.object({ value: z.string() }),
    execute: importedShared,
  },
  secondShared: {
    inputSchema: z.object({ value: z.string() }),
    execute: importedShared,
  },
};

const agent = new WorkflowAgent({ model: {}, tools });
void agent;
