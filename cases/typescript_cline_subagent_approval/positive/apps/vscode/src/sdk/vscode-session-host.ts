export class VscodeSessionHost {
  static async create(options: HostOptions) {
    const inner = await ClineCore.create({
      capabilities: {
        requestToolApproval: options.requestToolApproval,
      },
      toolPolicies: options.toolPolicies,
    })
    return new VscodeSessionHost(inner)
  }
}
