import { tool } from "ai";

const API = "https://search.example";
const sanitized = "input".replace(/[;&|`$(){}]/g, "");
const fakePattern = /fetch\(url\)|`/;

async function fetchRemote(url: string) {
  return fetch(url);
}

async function searchRemote(query: string) {
  const target = `${API}/search?q=${query}`;
  return fetch(target);
}

const proxy = tool({
  execute: async ({ url }) => {
    return fetchRemote(url);
  },
});

const search = tool({
  execute: async ({ query }) => {
    return searchRemote(query);
  },
});

void sanitized;
void fakePattern;
