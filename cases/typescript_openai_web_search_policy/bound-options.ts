import { Agent, webSearchTool } from "@openai/agents";

const boundedSearchOptions = {
  filters: {
    allowedDomains: ["docs.example.com", "help.example.com"],
  },
  searchContextSize: "low",
};

let mutableSearchOptions = {
  filters: {
    allowedDomains: ["mutable.example.com"],
  },
};
mutableSearchOptions = {};

export const boundedSearcher = new Agent({
  name: "Bounded searcher",
  tools: [webSearchTool(boundedSearchOptions)],
});

export const mutableSearcher = new Agent({
  name: "Mutable searcher",
  tools: [webSearchTool(mutableSearchOptions)],
});
