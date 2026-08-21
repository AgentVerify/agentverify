const SSRF_DEFAULT_BLOCKED_IP_RANGES = ["127.0.0.0/8"];

export class SsrfProtectionConfig {
  enabled: boolean = false;
  blockedIpRanges: string[] = [...SSRF_DEFAULT_BLOCKED_IP_RANGES];
  allowedIpRanges: string[] = [];
  allowedHostnames: string[] = [];
}
