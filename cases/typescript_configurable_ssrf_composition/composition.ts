function createPassthroughSsrfGuard() {
  return {};
}

class AiWorkflowBuilderService {
  constructor(..._args: unknown[]) {}
}

export class CompositionRoot {
  ssrfConfig = { enabled: false };
  ssrfProtectionService = {};

  build() {
    const webFetchSsrfGuard = this.ssrfConfig.enabled
      ? this.ssrfProtectionService
      : createPassthroughSsrfGuard();
    return new AiWorkflowBuilderService(
      "nodes",
      "session",
      "client",
      webFetchSsrfGuard,
    );
  }
}
