class BaseTool {}

export class FunctionTool<T> extends BaseTool {
  constructor(_options: T) {
    super()
  }
}
