import { Agent, webSearchTool } from "@openai/agents";

const dynamicDomains = ["example.com"];
const dynamicProviderInclude = ["web_search_call.action.sources"];
let mutableContextSize = "high";

export const docsSearcher = new Agent({
  name: "Docs searcher",
  tools: [
    webSearchTool({
      filters: {
        allowedDomains: ["openai.com", "platform.openai.com"],
      },
      searchContextSize: "medium",
    }),
  ],
  modelSettings: {
    providerData: {
      include: ["web_search_call.action.sources"],
    },
  },
});

export const dynamicSearcher = new Agent({
  name: "Dynamic searcher",
  tools: [
    webSearchTool({
      filters: {
        allowedDomains: dynamicDomains,
      },
      searchContextSize: mutableContextSize,
    }),
  ],
  modelSettings: {
    providerData: {
      include: dynamicProviderInclude,
    },
  },
});
