import path from "path";
import { isWithinRoots } from "./path-check.js";

const allowedRoots = ["/workspace"];

export async function validatePath(requestedPath: string): Promise<string> {
  const absolute = path.resolve(requestedPath);
  const isAllowed = isWithinRoots(absolute, allowedRoots);
  if (!isAllowed) {
    throw new Error("outside configured roots");
  }
  return absolute;
}
