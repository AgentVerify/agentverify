import { tool } from "ai";

const ALLOWED_DOMAINS = (process.env.ALLOWED_DOMAINS ?? "")
  .split(",")
  .map((domain) => domain.trim().toLowerCase())
  .filter((domain) => domain.length > 0);

function validateTarget(target: string): URL {
  const parsed = new URL(target);
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("unsupported protocol");
  }
  if (
    ALLOWED_DOMAINS.length > 0 &&
    (parsed.protocol === "http:" || parsed.protocol === "https:")
  ) {
    const domain = parsed.hostname;
    const allowed = ALLOWED_DOMAINS.some((allowedDomain) => {
      return domain === allowedDomain || domain.endsWith(`.${allowedDomain}`);
    });
    if (!allowed) {
      throw new Error("domain is not allowed");
    }
  }
  return parsed;
}

async function fetchRemote(target: URL | string) {
  return fetch(target);
}

const guarded = tool({
  execute: async ({ url }) => {
    const target = validateTarget(url);
    return fetchRemote(target);
  },
});

const late = tool({
  execute: async ({ url }) => {
    const response = await fetchRemote(url);
    const target = validateTarget(url);
    return { response, target };
  },
});

const rebound = tool({
  execute: async ({ url }) => {
    let target = validateTarget(url);
    target = url;
    return fetchRemote(target);
  },
});

const nested = tool({
  execute: async ({ url }) => {
    return fetchRemote(validateTarget(url));
  },
});

function validateSchemeOnly(target: string): URL {
  const parsed = new URL(target);
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("unsupported protocol");
  }
  return parsed;
}

const partial = tool({
  execute: async ({ url }) => {
    const target = validateSchemeOnly(url);
    return fetchRemote(target);
  },
});

const conditional = tool({
  execute: async ({ url, enabled }) => {
    let target = url;
    if (enabled) {
      target = validateTarget(url);
    }
    return fetchRemote(target);
  },
});

void guarded;
void late;
void rebound;
void nested;
void partial;
void conditional;
