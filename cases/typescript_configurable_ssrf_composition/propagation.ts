type SsrfGuard = object;

class BuilderService {
  constructor(private readonly ssrf?: SsrfGuard) {}

  create() {
    return { ssrf: this.ssrf };
  }
}

class WorkflowAgent {
  constructor(private readonly ssrf?: SsrfGuard) {}

  create() {
    return { ssrf: this.ssrf };
  }
}

export { BuilderService, WorkflowAgent };
