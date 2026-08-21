import { safeHttp } from "./safe-http";

function createSafeMcpFetch({ extraHeaders, timeoutMs, maxResponseBytes }: any): typeof fetch {
  return async (input, init) => {
    const url = input instanceof URL ? input.toString() : (typeof input === 'string' ? input : input.url);
    const headers = { ...extraHeaders, ...(init?.headers ?? {}) };
    const method = init?.method ?? 'GET';
    const response = await safeHttp.axios.request<ReadableStream | ArrayBuffer>({
      method, url, headers, data: init?.body,
      validateStatus: () => true,
      maxContentLength: maxResponseBytes,
      maxBodyLength: maxResponseBytes,
      timeout: timeoutMs,
    });
    return new Response(response.data, { status: response.status });
  };
}

function createSafeMcpTransport({ protocol, serverUrl, auth, timeoutMs = 15000, maxResponseBytes = 65536 }: any) {
  const headers = auth;
  const url = new URL(serverUrl);
  const fetch = createSafeMcpFetch({ extraHeaders: headers, timeoutMs, maxResponseBytes });
  if (protocol === "SSE") {
    return new SSEClientTransport(url, { requestInit: { headers }, fetch });
  }
  return new StreamableHTTPClientTransport(url, { requestInit: { headers }, fetch });
}

export const mcpTransport = {
  createTransport: createSafeMcpTransport,
};
