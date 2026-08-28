import path from "path";
import { rm, writeFile } from "fs/promises";

class WorkspaceEditor {
  constructor(private root: string) {}

  async write(requestedPath: string, content: string) {
    const checked = await this.resolve(requestedPath);
    await writeFile(checked, content, "utf8");
  }

  async deleteWithoutHelper(requestedPath: string) {
    const unchecked = path.resolve(this.root, requestedPath);
    await rm(unchecked, { force: true });
  }

  private async resolve(requestedPath: string): Promise<string> {
    const resolved = path.resolve(this.root, requestedPath);
    if (!resolved.startsWith(this.root)) {
      throw new Error("outside root");
    }
    return resolved;
  }
}
