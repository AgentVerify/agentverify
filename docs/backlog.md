# Issue-ready backlog

Items are ordered by evidence-backed roadmap priority. They are written to become GitHub issues once
the local repository has an approved remote.

## P0 — module-qualified symbols and graph identities

Python and TypeScript agent/tool components now carry module-qualified IDs, including Python class
methods, built-in tools, tool namespaces, and Cline/OpenAI inline factories. The structure-aware
TypeScript tools-array reader resolves all 81 observed agent-to-tool edges and 14 agent-as-tool
delegations in the pinned sample without treating nested tokens as tools. Repeated constructor and
decorated-tool bindings now receive occurrence-qualified IDs for exact source edges; repeated target
references resolve only for a single direct, earlier definition in the same Python lexical/module
scope. Next add branch- and reassignment-sensitive dataflow, then resolve Python/TS package re-exports,
wildcard imports, unrecognized wrapper factories, and type-driven symbols.
Preserve unresolved state for ambiguity and validate on larger real monorepository graphs.

Exact module-level Python `mcp.tool(...)(function)` applications now resolve through unique local or
relative-imported definitions when both registrar and target bindings are immutable. The pinned
Skyvern module contributes 115 recovered tools and 21 capability edges. Twenty-two tools pass through
structurally proven metadata-preserving forwarders, including one two-wrapper chain. Next support
package reexports and additional wrapper forms without falling back to display-name matching.

Python browser-page execution now inventories import-gated `.evaluate(...)` calls and promotes only
direct tool-parameter/alias script flow. Dynamic calls additionally require an exact Playwright
receiver annotation, one immutable alias of that parameter, or Skyvern's exact imported `get_page`
factory result. Schema v38 proves seven of 80 corpus receivers; the other 73 fixed-script observations
retain explicit unresolved state. Skyvern contributes 30 evaluator observations but one finding;
normalized numeric scroll JavaScript remains inventory-only. Next resolve constructor-bound page
fields, locator chains, sanitizer and bounded builder summaries, imported helper flow, and other
browser evaluator APIs without treating every dynamic JavaScript expression as tool-controlled.

## P0 — configuration and policy resolution

Resolve environment defaults, config objects, CLI flags, MCP allowlists, tool policies, and approval
overrides into control edges. Suppress `AV-MCP002` and `AV-FS001` only when the resolved policy governs
the exact reachable path. Same-function MCP rejection guards and uncaught internal tool-registry
lookups are statement-ordered, so later checks cannot govern earlier calls. A bounded imported
TypeScript path guard now suppresses `AV-FS001` only when a normalized, separator-aware roots
predicate rejects before the write and its roots are a statically narrow literal set. MCP Servers'
dynamic CLI/MCP roots retain a review plus an explicit unresolved-scope control edge. Python now
resolves statement-ordered `Path.resolve()` plus `is_relative_to()` boundaries, including positive
branch-local and fail-closed guards. Literal narrow roots may suppress; configured roots retain the
review, and prefix checks or reassignment remain unresolved. Next resolve imported policy objects,
and bounded root constants without widening name-based inference. Fail-closed `relative_to()`
exception guards now require an exclusive check plus a terminating ValueError handler; continuing
handlers, mixed try bodies, and parent writes remain negative. Unique same-class helpers now
propagate an exact checked-and-returned Path into callers while preserving unresolved root scope;
duplicate/rebound methods, opaque transforms, and changed return values remain negative. Next add
bounded imported helper summaries and root-scope resolution without trusting semantic names.
Exact Python `str(resolved).startswith(str(root))` guards now remain non-suppressing weak-control
edges and receive the specialized `AV-FS002` review; checks after a sink and separator-aware forms
remain negative. Next recognize additional component-aware weak patterns only when a real reachable
sink justifies them.
Python filesystem inventory now models canonical and import-aliased `os`/`shutil` create, copy,
move, replace, and delete calls, using the destination rather than the source for two-path APIs.
Statement-ordered local callable aliases now cover direct assignments, conditional expressions, and
compatible branch-local `copy`/`copy2` choices. Calls before assignment, conditionally rebound
wrappers, and incompatible operation choices remain negative. Proven `Path.rename`/`Path.replace`
receivers now cover explicit constructors, exact Path annotations, and single immutable derived
locals while rejecting conditional, reassigned, and shadowed bindings. Next resolve chained callable
aliases and imported filesystem wrappers without matching arbitrary same-named methods.
Constructor-only MCP wrapper fields, pure accessors, and unchanged parameters captured by
returned/registered callbacks now produce fixed-binding edges. Mutable fields, rebound parameters,
and same-operation retry closures remain unresolved. Same-class methods and immutable
constructor-bound imported registry managers now summarize exact `get_tool`-then-reject paths. The
collector retains a bounded dependency closure so the imported proof is reproducible. Next resolve
aliased/module-qualified constructors and deeper manager composition, without treating class names
or discovery as authorization.
Keep unresolved distinct from absent.

## P0 — approval coverage rule

`AV-APPROVAL002` now reports the narrow provable subset where an Agent directly reaches a local
OpenAI Agents Python or TypeScript shell tool and its SDK approval is explicitly or default-disabled.
It remains a review: an executor may enforce an equivalent internal control. Promote absence to a
finding only when the complete destructive path and executor policy are resolved. Extend coverage to
delegated agents and other frameworks without treating callbacks or automatic handlers as absent
controls.

## P1 — sandbox containment quality

Kubernetes privileged mode, host network/PID/IPC, service-account token mounts, explicit privilege
escalation, arbitrary `hostPath` mounts, and literal privileged Docker SDK calls are covered alongside
Compose. Next resolve network policy, Linux capabilities, device passthrough, and credential-volume
semantics. Model containment as a control attached to the exact code/shell capability.

## P1 — network destination policy

`AV-NET001` now reports Python and structurally resolved TypeScript tool parameters and their direct
aliases when they determine the HTTP origin. Literal URLs and formatted URLs with a fixed scheme and
host remain inventory-only; Python fixed-origin state propagates through module constants, immutable
instance fields, concatenation, and `.format(...)`. TypeScript coverage includes Mastra `createTool` object properties and
MCP `registerTool` callbacks with exact tool identities. Unique same-file free/static network helpers
now propagate positional/destructured parameter flow to exact tool edges. Python additionally resolves
unique top-level functions through exact named local imports when one of their parameters directly
controls a recognized HTTP origin; local rebinding, nested helpers, and module-object calls remain
unresolved. Single-entrypoint registered classes now propagate that proven behavior through exact
direct construction or immutable constructor-bound fields for up to four graph layers. Mutable
fields, module-qualified constructors, ambiguous classes, and rebound/shadowed constructors remain
unresolved. Exact module-level `urllib.request.urlopen` imports and aliases now add network inventory;
`Request(url)` is unwrapped so a fixed host plus a dynamic query stays inventory-only, while local
shadowing and module rebinding invalidate the API proof.
Exact same-function Python `urlparse`/`urlsplit` guards now add a control edge only when immutable
tool-origin data is rejected outside a static scheme and hostname set before the request. Redirect
disabling is recorded separately; DNS and other redirect states stay unresolved. Schema v40 finds
zero such controls on the Python corpus reviews, making the absence visible without calling every review
SSRF. A same-file TypeScript validator summary now resolves MCP Servers' scheme allowlist and
environment-backed exact/subdomain predicate, while preserving its empty hostname default as open.
Schema v40 separately proves two CrewAI loader calls through a locally defined `safe_get` transport:
both validate every redirect hop, pin the connected peer after DNS checks, disable proxies, and are
enabled by default. The `CREWAI_TOOLS_ALLOW_UNSAFE_PATHS` opt-out and
`CREWAI_TOOLS_FORCE_SAFE_PATHS` override remain explicit governance state. Next resolve normalized
predicates and other imported validators or transports without generalizing from names. Two Composio
session-file calls are also proven, but retain proxy-dependent DNS pinning as an explicit residual:
one disables redirects and one validates each bounded hop. Ten Langflow connector call sites are now
proven through default-on settings, explicit opt-out gates, a configured allowlist and default
literal-loopback exemption, and DNS-pinned/proxy-rejecting transports when enforcement is active.
n8n's AI Builder `web_fetch` path now resolves from its CLI composition root through the injected
guard to Axios: protection defaults off, the disabled branch is a real passthrough, enabled requests
use preflight validation, a custom lookup, and bounded redirect hooks, while proxy behavior remains
unresolved and independent domain HITL does not satisfy address policy. Flowise's Agentflow HTTP node
now resolves its variable URL through a fixed Axios request object into a default-on helper that
normalizes mapped addresses, validates each redirect, and pins direct DNS; environment proxy routing
and the explicit opt-out remain residuals. Its Web Scraper path also resolves through `secureFetch`,
whose post-spread pinned agent overrides caller transport options on every validated hop. Google ADK
JS's `LOAD_WEB_PAGE` now preserves the opposite transport state: always-on public-address preflight
and disabled redirects, but unpinned global fetch with a DNS-rebinding residual. Immutable same-file
Axios instances now preserve verb/`.request(...)` flow and `allowAbsoluteUrls: false` origin locking.
Activepieces' configured MCP transport additionally resolves through imported `safeHttp.axios` into
`request-filtering-agent` 3.2.0: both HTTP agents are forced after caller options and filter each
direct connection, while `AP_SSRF_ALLOW_LIST` exceptions and environment-proxy routing remain
explicit. Next resolve general imported clients, mutated/interceptor-configured instances, fetch and
Undici dispatchers, and runtime egress controls.

## P1 — A2A AgentCard endpoint provenance

`AV-A2A001` distinguishes configured card discovery from the downstream origin selected by a
remotely supplied AgentCard. Exact TypeScript compositions cover Google ADK JS and Gemini CLI; both
pass the resolved card into `ClientFactory` without a proven source-origin binding. Gemini's edge
also preserves its Undici agent/proxy choice, unpinned DNS state, and insecure-gRPC possibility.
Google ADK Python is the guarded counterexample: both cached and per-invocation client paths validate
every advertised RPC interface, require HTTPS except explicit loopback development, and bind it to
the network card source origin before client construction. Next generalize across A2A SDK versions,
custom client factories, redirect policy, and authenticated-card replacement without converting
configuration-controlled card URLs into model-controlled SSRF findings.

## P1 — consequential-action audit coverage

Lexically scoped OpenTelemetry spans now create action-level control edges, without treating imports
or sibling spans as coverage. Next recognize framework tracing and tool middleware, then resolve span
processors/exporters to durable audit sinks. Implement `AV-AUDIT001` only when durable, attributable
records can be distinguished from instrumentation alone.

## P1 — benchmark truth set

The curated regression set has reached 328 pinned positive/negative locations, with 241 separately
scored IR relationship labels. Schema-v40 engine results and `docs/frontend-coverage.md` publish
category-stratified observations and unsupported syntax. Next create a separately sampled, externally
reviewed holdout set and keep its labels sealed until rule changes are complete. Keep discovery
sampling metrics separate from detection-quality metrics.

## P2 — CI adoption workflow

The repository now includes a GitHub code-scanning workflow and copy-ready SARIF upload guidance
with a stable category, an auditable `--paths-from` mode for changed-file scans, and baseline diff
counts that avoid false resolution claims on partial scans. Inline suppressions now retain optional
expiry status, and CI can require an active ISO date. A distributable pre-commit manifest and local
setup are included; publishing its remote form waits for an approved repository URL and release tag.
Schema-backed JSON policies now provide per-rule/result-kind/severity count budgets with decision
evidence in every report. Next add organization policy composition and signed policy provenance
without weakening strict unknown-field validation.

## P2 — AI BOM standards adapters

The native schema-backed AI BOM 1.1 now preserves assets, relationships, evidence, governance
summaries, risks, and ambiguous identities without information loss. Exact relationship evidence
resolves capability/control endpoints while genuinely ambiguous agent/tool references remain explicit.
Next design separately validated CycloneDX
and SPDX AI-profile adapters. Map only concepts supported by the target specification and retain a
link to the native evidence graph rather than presenting agent-specific extensions as standard fields.
