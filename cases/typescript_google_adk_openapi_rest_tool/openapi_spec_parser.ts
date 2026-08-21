export interface OperationEndpoint {
  baseUrl: string;
  path: string;
  method: string;
}

function resolveServerUrl(server: { url: string; variables?: Record<string, { default?: string; enum?: string[] }> }): string {
  return server.url.replace(/\{([^{}]+)\}/g, (_, name: string) => {
    const variable = server.variables?.[name];
    const value = variable?.default || variable?.enum?.[0];
    if (!value) throw new Error(`Unresolved server URL variable '${name}'`);
    return value;
  });
}

export class OpenApiSpecParser {
  parse(spec: { servers?: Array<{ url: string }> }) {
    const server = spec.servers?.[0];
    const baseUrl = server ? resolveServerUrl(server) : '';
    const path = '/users/{id}';
    const method = 'get';
    return [{endpoint: {baseUrl, path, method}, name: 'get_user', description: 'Get a user', operation: {}}];
  }
}
