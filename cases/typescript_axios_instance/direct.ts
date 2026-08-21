import http from "axios";
import { tool } from "ai";

const client = http.create({ baseURL: "https://api.example.com" });
const lockedClient = http.create({
  baseURL: "https://api.example.com",
  allowAbsoluteUrls: false,
});
const unbasedClient = http.create({ allowAbsoluteUrls: false });

export const dynamicGet = tool({
  execute: async ({ url }) => client.get(url),
});

export const dynamicRequest = tool({
  execute: async ({ url }) => client.request({ method: "GET", url }),
});

export const directAlias = tool({
  execute: async ({ url }) => http.get(url),
});

export const fixedOrigin = tool({
  execute: async ({ query }) =>
    client.get(`https://api.example.com/search?q=${query}`),
});

export const lockedOrigin = tool({
  execute: async ({ url }) => lockedClient.get(url),
});

export const noBaseToLock = tool({
  execute: async ({ url }) => unbasedClient.get(url),
});

void dynamicGet;
void dynamicRequest;
void directAlias;
void fixedOrigin;
void lockedOrigin;
void noBaseToLock;
