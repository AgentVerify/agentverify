export class MCPService {
  connections = new Map<string, any>();

  async discover(connection: any) {
    connection.tools = (await connection.client.listTools()).tools;
  }

  public async runTool(name: string, args: Record<string, any>) {
    for (const connection of this.connections.values()) {
      const tool = connection.tools.find((candidate: any) => candidate.name === name);
      if (tool) {
        return await connection.client.callTool({
          name,
          arguments: args,
        });
      }
    }
    throw new Error(`Tool ${name} not found`);
  }
}
