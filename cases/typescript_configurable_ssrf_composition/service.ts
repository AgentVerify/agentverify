export class SsrfProtectionService {
  allowedIps = { check: (_ip: string) => false };
  blockedIps = { check: (_ip: string) => true };
  dnsResolver = { lookup: async (_host: string) => [{ address: "203.0.113.1" }] };

  validateIp(ip: string) {
    if (this.allowedIps.check(ip)) return { ok: true };
    if (this.blockedIps.check(ip)) return { ok: false };
    return { ok: true };
  }

  async lookupAndValidate(hostname: string) {
    const resolved = await this.dnsResolver.lookup(hostname);
    return resolved.map((value) => this.validateIp(value.address));
  }

  async validateUrl(url: string) {
    return await this.lookupAndValidate(new URL(url).hostname);
  }

  validateRedirectSync(url: string) {
    return this.validateIp(new URL(url).hostname);
  }

  createSecureLookup() {
    return async (hostname: string) => await this.lookupAndValidate(hostname);
  }
}
