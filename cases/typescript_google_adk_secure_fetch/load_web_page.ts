import { lookup } from 'node:dns/promises'
import { isIP } from 'node:net'
import { FunctionTool } from './function_tool.js'

declare const z: any

const ALLOWED_SCHEMES = new Set(['http:', 'https:'])
const BLOCKED_IPV4_CIDRS = [
  '0.0.0.0/8',
  '10.0.0.0/8',
  '127.0.0.0/8',
  '169.254.0.0/16',
  '192.168.0.0/16',
]
const BLOCKED_IPV6_CIDRS = ['::1/128', 'fc00::/7', 'fe80::/10']

function isBlockedHostname(hostname: string): boolean {
  return hostname === 'localhost'
}

function normalizeHost(hostname: string): string {
  return hostname
}

function isBlockedIpv4(_octets: number[]): boolean {
  return BLOCKED_IPV4_CIDRS.length > 0
}

function isBlockedIpv6(hextets: number[]): boolean {
  const value = hextets.reduce((result, item) => (result << 16n) | BigInt(item), 0n)
  if (value >> 32n === 0xffffn) {
    return isBlockedIpv4([0, 0, 0, 0])
  }
  return BLOCKED_IPV6_CIDRS.length > 0
}

function isBlockedAddress(address: string): boolean {
  return isIP(address) === 4 ? isBlockedIpv4([]) : isBlockedIpv6([])
}

async function resolveHostAddresses(hostname: string): Promise<string[]> {
  const records = await lookup(hostname, {all: true})
  return [...new Set(records.map((record) => record.address))]
}

function assertUrlAllowed(url: string): URL {
  const parsed = new URL(url)
  if (!ALLOWED_SCHEMES.has(parsed.protocol)) throw new Error('scheme')
  if (isBlockedHostname(parsed.hostname)) throw new Error('host')
  return parsed
}

async function validateResolvedAddresses(hostname: string): Promise<void> {
  const addresses = await resolveHostAddresses(hostname)
  if (addresses.some(isBlockedAddress)) throw new Error('address')
}

export async function loadWebPage(url: string): Promise<string> {
  const parsed = assertUrlAllowed(url)
  await validateResolvedAddresses(normalizeHost(parsed.hostname))
  const response = await fetch(url, { redirect: 'manual' })
  return response.text()
}

export const LOAD_WEB_PAGE = new FunctionTool({
  name: 'load_web_page',
  description: 'Fetch a page',
  parameters: z.object({ url: z.string() }),
  execute: ({url}) => loadWebPage(url),
})
