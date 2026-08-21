import { OpenApiSpecParser } from './openapi_spec_parser.js';
import { createRestApiTool, RestApiTool } from './rest_api_tool.js';

class BaseToolset {}

export class OpenAPIToolset extends BaseToolset {
  private tools: RestApiTool[] = [];

  constructor(spec: object) {
    super();
    const parser = new OpenApiSpecParser();
    const parsedOperations = parser.parse(spec);
    for (const op of parsedOperations) {
      const tool = createRestApiTool({ endpoint: op.endpoint });
      this.tools.push(tool);
    }
  }

  async getTools(): Promise<RestApiTool[]> {
    return this.tools;
  }
}
