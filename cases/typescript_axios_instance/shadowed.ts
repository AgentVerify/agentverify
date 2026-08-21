import { tool } from "ai";
import http from "./local-http";

const client = http.create({ baseURL: "https://api.example.com" });

export const shadowed = tool({
  execute: async ({ url }) => client.get(url),
});

void shadowed;
