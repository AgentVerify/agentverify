import path from "path";

export function isWithinRoots(candidate: string, roots: string[]): boolean {
  if (!candidate || roots.length === 0) return false;
  const normalizedPath = path.resolve(path.normalize(candidate));
  return roots.some((root) => {
    const normalizedRoot = path.resolve(path.normalize(root));
    if (normalizedPath === normalizedRoot) return true;
    return normalizedPath.startsWith(normalizedRoot + path.sep);
  });
}
