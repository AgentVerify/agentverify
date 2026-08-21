import { applyCredential } from './auth_helpers.js';
import { OperationEndpoint } from './openapi_spec_parser.js';

class BaseTool {}

export class RestApiTool extends BaseTool {
  constructor(private readonly endpoint: OperationEndpoint) {
    super();
  }

  async runAsync(request: { args: Record<string, unknown> }) {
    const args = request.args;
    const { url: initialUrl, headers } = prepareRequestParams(this.endpoint, args);
    const url = applyCredential(initialUrl, headers, undefined);
    return globalThis.fetch(url, { headers });
  }
}

function encodePathParamValue(name: string, value: string): string {
  if (value === '.' || value === '..') throw new Error(`Invalid ${name}`);
  return encodeURIComponent(value);
}

export function prepareRequestParams(endpoint: OperationEndpoint, args: Record<string, unknown>) {
  const headers: Record<string, string> = {};
  const pathParams: Record<string, string> = {};
  for (const [argName, argValue] of Object.entries(args)) {
    const originalName = argName;
    const location = 'path';
    if (location === 'path') {
      pathParams[originalName] = encodePathParamValue(originalName, String(argValue));
    }
  }
  const resolvedPath = endpoint.path.replace(
    /\{([^{}]+)\}/g,
    (placeholder, name: string) =>
      Object.hasOwn(pathParams, name) ? pathParams[name] : placeholder,
  );
  let url = `${endpoint.baseUrl}${resolvedPath}`;
  return { url, headers };
}

export function createRestApiTool(parsed: { endpoint: OperationEndpoint }): RestApiTool {
  return new RestApiTool(parsed.endpoint);
}
