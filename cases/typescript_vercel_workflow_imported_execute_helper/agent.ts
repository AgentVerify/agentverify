import { WorkflowAgent } from "@ai-sdk/workflow";
import { z } from "zod";
import { importedCalculate, shared as importedShared } from "./helpers";
import { namedReexportCalculate } from "./barrel";
import { importedCalculate as starCalculate } from "./star";
import { ambiguousHelper } from "./ambiguous";

const tools = {
  importedCalculate: {
    inputSchema: z.object({ expression: z.string() }),
    execute: importedCalculate,
  },
  namedReexportCalculate: {
    inputSchema: z.object({ expression: z.string() }),
    execute: namedReexportCalculate,
  },
  starCalculate: {
    inputSchema: z.object({ expression: z.string() }),
    execute: starCalculate,
  },
  firstShared: {
    inputSchema: z.object({ value: z.string() }),
    execute: importedShared,
  },
  secondShared: {
    inputSchema: z.object({ value: z.string() }),
    execute: importedShared,
  },
  ambiguous: {
    inputSchema: z.object({ value: z.string() }),
    execute: ambiguousHelper,
  },
};

const agent = new WorkflowAgent({ model: {}, tools });
void agent;
