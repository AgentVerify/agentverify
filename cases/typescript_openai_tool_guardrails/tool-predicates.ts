export function containsExportControlledTerm(value: string | undefined): boolean {
  return String(value ?? "").includes("export-controlled");
}
