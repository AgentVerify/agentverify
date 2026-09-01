import { Agent, webSearchTool } from "@openai/agents";
import {
  importedSearchOptions,
  mutableImportedSearchOptions,
} from "./options";
import { reexportedSearchOptions } from "./option-barrel";

export const importedOptionsSearcher = new Agent({
  name: "Imported options searcher",
  tools: [
    webSearchTool(importedSearchOptions),
    webSearchTool(reexportedSearchOptions),
  ],
});

export const mutableImportedOptionsSearcher = new Agent({
  name: "Mutable imported options searcher",
  tools: [webSearchTool(mutableImportedSearchOptions)],
});
