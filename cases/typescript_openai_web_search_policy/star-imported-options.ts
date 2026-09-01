import { Agent, webSearchTool } from "@openai/agents";
import { importedSearchOptions as starSearchOptions } from "./star-options";
import {
  importedSearchOptions as ambiguousStarSearchOptions,
} from "./ambiguous-star-options";

export const starOptionsSearcher = new Agent({
  name: "Star options searcher",
  tools: [webSearchTool(starSearchOptions)],
});

export const ambiguousStarOptionsSearcher = new Agent({
  name: "Ambiguous star options searcher",
  tools: [webSearchTool(ambiguousStarSearchOptions)],
});
