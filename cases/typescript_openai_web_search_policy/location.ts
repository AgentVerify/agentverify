import { Agent, webSearchTool } from "@openai/agents";

const dynamicLocation = { type: "approximate", city: "Boston" };

export const localNews = new Agent({
  name: "Local news searcher",
  tools: [
    webSearchTool({
      userLocation: { type: "approximate", city: "New York", country: "US" },
    }),
  ],
});

export const dynamicNews = new Agent({
  name: "Dynamic location searcher",
  tools: [
    webSearchTool({
      userLocation: dynamicLocation,
    }),
  ],
});
