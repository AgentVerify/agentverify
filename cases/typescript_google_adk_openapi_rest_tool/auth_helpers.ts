export function applyCredential(
  url: string,
  headers: Record<string, string>,
  credential?: { apiKey?: string },
): string {
  if (!credential?.apiKey) return url;
  const separator = url.includes('?') ? '&' : '?';
  url += `${separator}key=${encodeURIComponent(credential.apiKey)}`;
  headers.Authorization = credential.apiKey;
  return url;
}
