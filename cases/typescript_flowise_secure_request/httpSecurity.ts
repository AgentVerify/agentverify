import axios from 'axios'
import dns from 'dns/promises'
import http from 'http'
import https from 'https'
import * as ipaddr from 'ipaddr.js'

const DEFAULT_DENY_LIST = ['10.0.0.0/8', '127.0.0.0/8', '169.254.169.254', '::1']

function getHttpDenyList() {
  const securityCheckEnabled = process.env.HTTP_SECURITY_CHECK !== 'false'
  const customList: string[] = []
  if (securityCheckEnabled) {
    return [...new Set([...DEFAULT_DENY_LIST, ...customList])]
  }
  return customList
}

function isDeniedIP(ip: string, denyList: string[]) {
  let parsedIp = ipaddr.parse(ip)
  const ipv6Addr = parsedIp as ipaddr.IPv6
  if (ipv6Addr.isIPv4MappedAddress()) {
    parsedIp = ipv6Addr.toIPv4Address()
  }
  for (const entry of denyList) {
    if (!entry.includes('/')) continue
    const [parsedRange, adjustedMask] = ipaddr.parseCIDR(entry)
    if (parsedIp.match(parsedRange, adjustedMask)) {
      throw new Error('Access to this host is denied by policy.')
    }
  }
}

export async function secureAxiosRequest(config: any, maxRedirects: number = 5) {
  let currentUrl = config.url
  let redirects = 0
  let currentConfig = {
    ...config,
    maxRedirects: 0,
    httpAgent: undefined,
    httpsAgent: undefined,
  }
  while (redirects <= maxRedirects) {
    const target = await resolveAndValidate(currentUrl)
    const agent = createPinnedAgent(target)
    currentConfig = {
      ...currentConfig,
      url: currentUrl,
      ...(target.protocol === 'http' ? { httpAgent: agent } : { httpsAgent: agent }),
    }
    const response = await axios(currentConfig)
    const location = response.headers.location
    if (!location) return response
    redirects++
    currentUrl = new URL(location, currentUrl).toString()
  }
  throw new Error('Too many redirects')
}

async function resolveAndValidate(url: string) {
  const denyList = getHttpDenyList()
  const hostname = new URL(url).hostname
  if (ipaddr.isValid(hostname)) {
    isDeniedIP(hostname, denyList)
    return { hostname, ip: hostname, family: 4, protocol: 'https' }
  }
  const records = await dns.lookup(hostname, { all: true })
  for (const r of records) {
    isDeniedIP(r.address, denyList)
  }
  const chosen = records.find((r) => r.family === 4) ?? records[0]
  return { hostname, ip: chosen.address, family: chosen.family, protocol: 'https' }
}

function createPinnedAgent(target: any) {
  const Agent = target.protocol === 'https' ? https.Agent : http.Agent
  return new Agent({
    lookup: (_host, _opts, cb) => {
      cb(null, target.ip, target.family)
    },
  })
}

export async function secureFetch(url: string, init: any = {}, maxRedirects: number = 5) {
  let currentUrl = url
  let redirectCount = 0
  let currentInit = { ...init, redirect: 'manual' as const }
  while (redirectCount <= maxRedirects) {
    const resolved = await resolveAndValidate(currentUrl)
    const agent = createPinnedAgent(resolved)
    const response = await fetch(currentUrl, { ...currentInit, agent: () => agent })
    const location = response.headers.get('location')
    if (!location) return response
    redirectCount++
    currentUrl = new URL(location, currentUrl).toString()
  }
  throw new Error('Too many redirects')
}
