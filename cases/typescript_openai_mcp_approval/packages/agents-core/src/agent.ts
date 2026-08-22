export class Agent {
  constructor(config: any) {
    this.mcpServers = config.mcpServers ?? [];
  }

  async getMcpTools() {
    return getAllMcpTools({
      mcpServers: this.mcpServers,
    });
  }

  async getAllTools() {
    const mcpTools = await this.getMcpTools();
    const enabledTools = [];
    return [...mcpTools, ...enabledTools];
  }
}
