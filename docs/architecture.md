# Architecture

```text
Repository
  ├─ Python AST frontend
  ├─ TypeScript/JavaScript frontend
  └─ MCP configuration frontend
           │
           ▼
Agent IR: components + source evidence + relationships
           │
           ▼
Context analysis: reachability + governing controls + unresolved state
           │
           ▼
Rule engine: inventory, review candidates, and findings
           │
           ▼
Deterministic text / JSON / native AI BOM / SARIF reports
```

## Agent IR

Components represent frameworks, providers, agents, tools, MCP servers, capabilities, controls, and
control settings. Relationships currently represent `uses`, `delegates-to`, `contains-control`, and
`governed-by` edges. Every object carries source path, line, and excerpt evidence.

Names are intentionally not treated as globally unique. Python and TypeScript agent/tool definitions
carry stable frontend-and-module-qualified `symbol_id` values; relationships carry `source_id` and
`target_id` when resolution succeeds. Context analysis prefers those IDs and falls back to the older
location-gated display-name logic only for unresolved syntax. Capability-to-tool resolution still
requires the relationship and capability observation to share a source location, preventing
same-named definitions in separate modules from leaking reachability or control coverage.
Unambiguous absolute Python
`from local_module import tool` references and filesystem-resolved relative imports point to an exact
repository file and can safely form cross-file agent paths. Function parameters and local
assignments/imports are scope-isolated: a same-named local binding cannot inherit a module import's
target ID, and an explicit function-local import is restored only within that function. TypeScript
named imports resolve when a
relative module maps to exactly one in-repository `.ts`, `.tsx`, `.js`, or `.jsx` file; aliases retain
the original exported name. Imports that escape the scan root, target missing files, or have multiple
candidate files remain unresolved. Python class methods use class-qualified IDs, and assigned agent
or built-in-tool instances use their binding name. The TypeScript frontend balances delimiters and
reads only direct properties and top-level tool-array entries; it models OpenAI tool namespaces,
built-ins, inline/assigned agent adapters, and Cline inline tools without treating nested tokens as
symbols. Python constructor and callable bindings gain a target ID inside a `with`, branch, or other
statement body only when one exact assignment or function definition is the sole same-block mutation
before use. Literal Agent `tools=[name]` entries promote the exact preceding callable definition to a
tool and record its registration site. This block-local proof takes precedence over a broader lexical
candidate, while any local binding prevents fallback to a same-named module definition. Cross-branch
definitions, reassignments, forward definitions, parameters, helper returns, and tuple unpacking
remain unresolved. Package re-exports, wildcard imports, dynamic lookups, conditional tool
expressions, and unrecognized wrapper-factory forms
remain unresolved.

A repository prepass also resolves direct module-level Python
`server.tool(...)(function)` decorator applications. The registrar must be a uniquely bound
FastMCP instance, and the target must be one uniquely bound same-module definition or one exact
relative import leading to a unique module-level definition. The resulting tool keeps definition
evidence and a module-qualified ID while recording registration path, line, registrar, resolution
basis, and literal approval metadata. Exact IDs allow registration-site controls to govern a
cross-file tool body. A bounded wrapper summary follows direct wrappers and decorator factories only
when their returned callback uses `functools.wraps` for exactly one callable parameter and directly
forwards its own `*args, **kwargs` to that parameter. Wrapper chains are capped at four layers and
record every wrapper name on the tool. Metadata-only or branch-only wrappers, nested registrations,
rebound bindings, wildcard imports, duplicate registrations, and unrelated `.tool` factories remain
unresolved.

Two import-proven registry decorators extend Python tool identity without treating every
`register_tool` spelling as a framework API. MetaGPT function decorators resolve the decorated body
directly; MetaGPT classes expose only direct methods named in a literal `include_functions` list.
Qwen-Agent class decorators require a literal registered tool name and resolve one direct `call`
method. Class capabilities are attached to the class tool identity rather than inventing duplicate
method tools. Exact source modules and statement-ordered alias rebinding are part of the proof;
nonliteral entrypoints, unrelated imports, and rebound decorators remain unresolved.

Within decorated Python tools and structurally resolved TypeScript execution callbacks, tool
parameters begin as potential dynamic HTTP origins. Direct assignment aliases preserve that state,
while reassignment to a literal or a URL expression whose literal prefix contains a complete HTTP
scheme and host clears it. Python also propagates a proven fixed origin through unique module string
assignments, immutable `self` fields initialized in `__init__`, concatenation, and `.format(...)`;
dynamic paths and queries on that origin remain inventory-only. The TypeScript frontend also resolves unique module string constants used
as a template prefix. For a uniquely named same-file free function or static method containing a
recognized network call, a bounded summary records which formal parameters can control the origin;
tool calls map positional and destructured-object arguments back to those parameters. `AV-NET001`
consumes only this origin-specific attribute; it does not equate a dynamic path or query on a fixed
host with a dynamic destination. A separate Python proof recognizes exact module-level
`urllib.parse.urlparse`/`urlsplit` imports, an immutable parse result derived from a tool parameter or
one direct alias, and fail-closed scheme plus hostname rejection before the request. Static nonempty
literal collections may be local or immutable module constants. The resulting
`network-origin-allowlist` control constrains only the initial origin: explicit redirect disabling is
recorded, while redirect behavior and DNS scope otherwise stay unresolved. These controls enrich the
review path but do not suppress `AV-NET001` or claim SSRF prevention. Positive branches, helper-based
validators, normalized hostname expressions, redirects, DNS, proxies, imported/transitive helpers,
arrow functions, and general client request-object data flow remain unresolved.

The TypeScript network reader also proves immutable same-file Axios instances created through an
exact default import or CommonJS binding. Direct verbs and `.request(...)` preserve URL origin flow;
literal `baseURL` and `allowAbsoluteUrls: false` state distinguish a locked configured origin from an
absolute-URL override. Rebinding, mutation, interceptors, computed options, and generic cross-file
clients are withheld.

The Python frontend also recognizes `urllib.request.urlopen` only through an exact module-level
`urllib`/`urllib.request` import, `from urllib import request`, or named `urlopen` import. Aliases are
canonicalized to the stdlib API, while module rebinding or any same-function binding with the same
root withholds the proof. A direct import-proven `Request(url)` passed inline or through
statement-ordered local assignment is unwrapped to its original URL before origin classification,
so a fixed scheme and host are not lost behind the request object. Custom openers, locally imported
bindings, assigned opener aliases, and Request factories remain unresolved.

The TypeScript frontend can attach one same-file validator policy through a direct validated-result
assignment and immutable aliases to a direct or summarized network call. The validator proof requires
`new URL(parameter)`, a fail-closed literal scheme set, and an exact/subdomain hostname predicate over
an immutable normalized environment list. An empty environment default is represented as
`hostname_scope: configured-optional` and `hostname_default: open`; it is validation evidence, not an
allowlist that satisfies destination policy. Late validation, rebound results, nested validator calls,
scheme-only helpers, DNS, and redirect behavior remain unresolved, and `AV-NET001` is not suppressed.

A separate Python prepass recognizes two source-proven imported secure-transport families. The
fully pinned family validates the initial URL and each redirect, disables automatic redirects and
all proxy sources, mounts protected adapters for both HTTP schemes, rejects private/reserved
resolution results, and checks the connected peer. The proxy-conditional family proves the same
public-address and peer checks for direct connections, but preserves environment or caller proxy
selection as `dns_scope: connection-pinned-unless-proxied` and
`proxy_scope: environment-or-caller-dependent`; redirect-disabled and bounded each-hop helpers stay
distinct. Both produce `network-ssrf-policy` with `enforcement_default: enabled`. Environment escape
and force-safe names are retained when present, and proxy residuals are never promoted to full
pinning. Exact named imports and aliases apply the summary, while rebinding or any missing transport
proof withholds it; helper names and docstrings alone do not contribute evidence.

A third structural family models configurable connector protection without flattening its disabled
state into unconditional safety. It requires versioned, selected evidence for default-on global and
connector settings; both gate functions; configured allowlist and literal-loopback handling; the
core public-address validator; async and sync backends that connect to validated addresses; protected
transports that reject proxies; and factory fallbacks to ordinary clients. Resulting edges use
`connection-pinned-when-enforced` and `disabled-when-enforced`, retain both opt-out environment names,
and record the configured allowlist/default loopback exemption in the initial-origin scope. Helpers
that reject redirects remain distinct from the bounded synchronous GET helper that disables them by
default and revalidates each hop only when explicitly enabled. Any missing composition proof,
disabled default, unpinned backend, non-exact import, or rebinding withholds the summary.

The TypeScript composition pass handles a different boundary: dependency injection can choose a real
SSRF service or a no-op guard before the value crosses multiple constructors into a tool factory. The
current proof requires a literal boolean config default, exact service/passthrough ternary, repeated immutable
guard propagation, tool-input validation, a bounded Axios redirect configuration, custom lookup, and
redirect hook to coexist in selected source. It adds the `web_fetch → network → network-ssrf-policy`
path at the tool call while retaining the helper sink and composition/config locations as attributes.
The custom lookup is recorded as configured rather than connection-pinned, and proxy scope stays
unresolved because selected source does not prove how Axios routes proxied destinations. Missing any
stage withholds both the tool capability and control edge.

A second TypeScript composition pass resolves Flowise's CommonJS-registered Agentflow HTTP node through a
request object into its imported secure transport. It requires the variable URL descriptor, exact
`nodeData.inputs.url` flow, one fixed `url: finalUrl` config without Axios transport overrides or
spreads, a default-on deny list with mapped-address normalization, manual bounded redirects, all-DNS
answer validation, and a pinned agent lookup. The resulting edge retains the configured opt-out and
`environment-dependent` proxy scope; proxy routing can move destination resolution away from the
pinned lookup. Default-off settings, automatic redirects, caller transport fields, or incomplete
address normalization withhold the proof.

The same pass independently resolves Flowise's `node-fetch` Web Scraper path. It requires the exact
`Tool` subclass identity, an import proven directly or through one star-export barrel,
`_call(initialInput) → scrapeRecursive(url) → scrapeSingleUrl(url)`
parameter chain, a default-on helper with the same address proof, a bounded manual redirect loop,
and a pinned agent supplied after the caller-options spread. That ordering proves caller agent
options cannot replace the pinned connection for this structural family. Its edge records
`connection-pinned`, `pinned-agent`, and `caller-agent-overridden`; changing a hop to a fixed URL,
restoring automatic redirects, or moving an untrusted agent after the pin withholds the proof.

A fourth TypeScript composition pass resolves Google ADK JS's `LOAD_WEB_PAGE` only when the selected
`FunctionTool` definition is reached by an exact import and its URL callback maps directly into
`loadWebPage`. The helper must reject disallowed schemes and localhost, validate every DNS answer
against explicit IPv4/IPv6 ranges with mapped-address handling, and disable redirects before global
fetch. Because that fetch performs a separate connection-time lookup, the control is recorded as
preflight-only with an unpinned-transport residual. Removing any stage withholds both reachability and
the control edge.

A fifth TypeScript composition pass resolves Activepieces only through an exact named `safeHttp`
import and the selected MCP transport/entry chain. It requires `request-filtering-agent` 3.2.0 in the
nearest package manifest, both HTTP and HTTPS filtering agents constructed after caller config, URL
shorthand at `safeHttp.axios.request`, and no caller proxy or agent override. The control records
connection-time address filtering and `AP_SSRF_ALLOW_LIST` IP/CIDR exceptions, but retains
environment-proxy dependence because a proxy can become the directly filtered connection target.

A sixth TypeScript pass resolves Composio's conditional `#ssrf_guard` import only when its package
map selects the Node guard by default and the edge-specific implementation for edge runtimes. The
Node helper must validate every DNS answer and manual redirect, then pass those addresses to an
Undici dispatcher's lookup. Caller dispatchers, a non-stock global dispatcher, and environment-proxy
mode are retained as preflight-only route residuals. The edge helper's two exports stay distinct:
`ssrfSafeFetch` fails closed, while `ssrfSafeFetchWhereSupported` deliberately uses unguarded fetch.

A separate Composio CLI pass models a real unsafe counterpart. It requires the exact
`ToolsExecutor.execute` import and `params.arguments` mapping, schema `file_uploadable` recursion,
URL-versus-local-file split, and final raw `fetch(url)`. The pass replaces that sink's generic
inventory component with a dynamic network capability and a symbolized tool edge, allowing
`AV-NET001` to report the proven tool-execution-argument origin without generalizing from filenames.

The Google ADK OpenAPI pass models the fixed-origin counterpart. It follows `OpenAPIToolset` through
`OpenApiSpecParser` and `createRestApiTool` into `RestApiTool.runAsync`, then proves that request
arguments can affect only encoded path segments, query, headers, and body. The origin remains the
first spec server after declared-default/enum variable expansion; `applyCredential` may append a
query credential but cannot replace the URL. The raw global-fetch capability is inventoried with a
`network-origin-policy` edge and `dynamic_origin: false`. Dynamic server variables, unencoded model
paths, URL-rewriting credentials, or broken factory imports withhold the proof.

The A2A endpoint-provenance passes model a different authority transition from tool-input SSRF.
They create an `a2a-rpc` capability at SDK client construction when a network-resolved AgentCard can
select the later RPC endpoint. The ADK JS proof requires an exact named import of its resolver and a
direct resolved-card flow into `createFromAgentCard`; the Gemini proof requires configured URL versus
inline JSON resolution, card normalization, SDK interface selection, and its Undici agent/proxy
dispatcher. Both preserve `dynamic_origin: false` and `origin_authority: remote-agent-card`, allowing
`AV-A2A001` to report the missing card-source binding without changing AV-NET001's model-parameter
contract. The ADK Python counterproof requires validation to dominate both cached and per-invocation
factory calls, enumeration of every advertised RPC URL, HTTPS-or-loopback rejection, and normalized
source-origin equality. Those paths receive `a2a-card-rpc-origin-policy`; missing any stage withholds
the control rather than inferring it from validator names.

An exact OpenAI Agents Python MCP pass follows a directly imported `MCPServerStdio` context binding
into `SandboxAgent(mcp_servers=[server])`. It verifies the SDK constructor default, `None → False`
normalization, missing-name fallback, and propagation into `_build_wrapped_function_tool`. The IR
records both the agent→server edge and a disabled-default `mcp-tool-approval` setting. Explicit
approval, changed defaults, hard-coded wrapper approval, wrong imports, or a different server binding
withhold the edge; the policy does not itself create an approval finding.

A repository prepass builds bounded Python network summaries for unique top-level free functions in
selected files. A summary records direct recognized HTTP calls and the formal parameters that can
control their origins after fixed-prefix discrimination. At a tool call site, only an exact named
absolute or relative import can apply the summary; positional and keyword arguments map back to the
controlled formals, and the capability retains the helper path and sink lines. Import state is
function-local and statement-ordered, so reassignment, deletion, or replacement imports invalidate
the edge. Module-object calls, reexports, nested/transitive helpers, client instances, helper-local
aliases, and rebound HTTP clients remain unresolved rather than being inferred by name.

After all direct frontends run, a bounded graph pass promotes proven dynamic network behavior across
registered Python classes. A summary requires a unique class tool, exactly one literal entrypoint,
and an existing dynamic network edge. Callers resolve only an exact named imported constructor used
directly or assigned once to `self.<field>` in `__init__`; all class-local assignments, deletion,
`setattr`, constructor shadowing, and ambiguous definitions invalidate the field proof. The caller's
first positional or matching keyword argument is evaluated with statement-ordered assignment and
loop-variable taint. When the callee reads one unique literal object key, only that caller field is
treated as the origin; a dynamic sibling field cannot taint a fixed URL. Fixed arguments remain
inventory-only. Newly resolved class tools can become
summaries for the next pass, capped at four iterations. Each capability retains the callee class,
method, definition line, and prior network-edge lines.

The same Python tool-parameter state distinguishes browser-page code execution from ordinary code
inventory. In a module importing Playwright, Selenium, or Puppeteer, an attribute
`.evaluate(...)` call becomes a `code-execution` capability with
`execution_context: browser-page`. `dynamic_input` is true only when the script expression contains
a current tool parameter or its direct assignment alias; literals, module constants, and values
derived solely from normalized intermediates remain inventory-only. A dynamic browser evaluator is
emitted only when its receiver is an exact imported Playwright `Page`/`Locator`/handle annotation,
one immutable alias of such a parameter, or the first result of Skyvern's exact imported `get_page`
factory. Reassignment invalidates the proof, and module browser imports alone cannot promote an
ordinary object's `.evaluate(...)`. Fixed-script observations remain inventory with
`unresolved-browser-import-context` when their receiver is not yet proven. The capability still
receives an exact tool edge when it occurs in a resolved tool body, including post-definition
FastMCP tools. Constructor-bound fields, chained locators, sanitizer proofs, imported/transitive
script builders, and alternate browser evaluator APIs remain unresolved.

For TypeScript filesystem writes, a relative import can prove a `path-boundary` control only through
an exact two-file chain: the guard must pass the tool-derived path into a uniquely resolved predicate,
reject a false result before the write, and the predicate must normalize both candidate and roots and
use separator-aware containment. The control edge retains both source paths and carries
`policy_effect: restricts-filesystem-path` only when the roots are a statically narrow literal set;
otherwise it carries `validates-filesystem-path` with unresolved boundary scope. `AV-FS001`
suppresses only the former. Names such as `validatePath`, prefix-only comparisons, broad/dynamic
roots, and checks after the action do not establish sufficient coverage.

For Python filesystem writes, the AST frontend first proves same-function `pathlib.Path` flows. A
tool parameter must feed a candidate constructed under an explicitly resolved root, the candidate
must itself be resolved, and `candidate.is_relative_to(root)` must dominate the exact write. Both a
fail-closed rejecting branch and the positive branch of the predicate can govern a write; the latter
does not escape its branch. A `.parent` directory write additionally requires proof that the
candidate is not equal to the root. Reassigning either binding invalidates the proof. Literal absolute,
non-filesystem roots carry `restricts-filesystem-path`; parameter/configured roots carry
`validates-filesystem-path` with unresolved scope and retain `AV-FS001`. String-prefix checks,
unresolved candidates and shadowed `Path` imports are not treated as equivalent controls.

Filesystem capabilities separately record whether the governed path is derived from a current tool
input. AV-FS001 requires that fact in addition to a writable dynamic path and unresolved narrow
boundary, so configured and literal write locations remain visible inventory rather than reviews.
AV-FS002 intentionally does not require this immediate taint fact: a proven weak string-prefix
boundary remains reportable. Built-in `open(...)` retains its ordinary path semantics, while an
attribute `.open(...)` is classified as filesystem access only for a proven `pathlib.Path` receiver;
the receiver is the path and the first argument is the mode.

A fail-closed `candidate.relative_to(root)` exception check can establish the same Python boundary
fact. The try body must contain only that check, the first handler capable of catching `ValueError`
must always terminate, and the candidate/root bindings must already be resolved and unchanged.
Continuing handlers, mixed mutation/check blocks, and parent writes without strict-descendant proof
remain unresolved. IR preserves `Path.relative_to` separately from `Path.is_relative_to` as the
control helper.

A unique same-class helper can propagate that `relative_to` fact to its caller. The helper must be a
synchronous, undecorated method; map exactly one formal path parameter through restricted `Path`
construction and an explicit zero-argument `resolve()`; perform one exclusive check with a
terminating handler; and return the same unchanged name. The caller must invoke it through its
unchanged `self`/`cls` receiver and consume the exact assigned return. Duplicate or explicitly
rebound members, generators, opaque transforms, alternate returns, post-check reassignment, and
caller reassignment invalidate the summary. Construction before the check is straight-line, and a
try `else` or `finally` block disqualifies it. These edges carry `summary: same-class-return` and keep
configured member roots unresolved, so the summary records validation without inventing a narrow
policy or suppressing `AV-FS001`.

The same flow engine records an exact `str(resolved).startswith(str(root))` predicate separately as
`path-prefix-check`, never as `path-boundary`. It follows parameter taint through tuple unpacking and
self-derived string assignments, preserves unresolved `root / input` joins until an explicit
`resolve()`, and propagates a check out of a try only when continuing handlers cannot bypass it.
The weak edge carries `policy_effect: weak-string-prefix-validation`: string prefixes do not compare
path components and can admit sibling-prefix targets. `AV-FS002` takes precedence over the generic
`AV-FS001` review at those exact sinks. Checks after the action and separator-aware expressions do
not match this specialized contract.

Python filesystem mutation calls preserve API semantics in Agent IR. Canonical and top-level
import-aliased `os`/`shutil` functions resolve only while their bindings remain unshadowed. One-path
create/delete APIs use their target argument; copy, move, rename, and replace APIs use the
destination argument, so a fixed source cannot hide a dynamic write boundary. Components record the
canonical API, `copy`/`move`/`create`/`delete` operation, and `target` or `destination` path role.
Destination expressions can inherit the same `path-boundary` proof as `open()` and `Path` writes.
Within a function, direct and conditional local callable assignments are resolved in statement
order. Branches merge only when every path leaves an alias bound to filesystem APIs with identical
path semantics; the component retains every possible API. Calls before assignment, conditional
rebinding to an unknown wrapper, and copy/delete choices are withheld. Arbitrary `.replace()`
methods and rebound import names are not promoted from their spelling alone. `Path.rename()` and
`Path.replace()` require an explicit unshadowed `pathlib.Path` constructor, an exact Path parameter
annotation, or a single immutable local derived from either. Conditional and reassigned bindings are
withheld; the destination argument remains the governed path and can inherit a boundary proof.

## Result kinds and uncertainty

- `inventory`: observed architecture facts without a risk judgment.
- `review`: a risky configuration candidate that needs surrounding context.
- `finding`: a locally demonstrated dangerous primitive or resolved unsafe flow.

Control analysis reports `present` only for a resolved governing edge. It reports `unresolved` when
coverage cannot be proven and never silently converts missing lexical evidence into “control absent.”
The first policy resolver recognizes same-function MCP tool-name allowlists that reject unknown tools
before forwarding. It also resolves literal approval on OpenAI Agents TypeScript function and
built-in tools, preserving local versus hosted shell execution. For Python files importing the
OpenAI Agents SDK, literal
`needs_approval=True` on `ShellTool`, `ApplyPatchTool`, and `CustomTool` creates an instance-scoped
tool-to-control edge when no automatic approval handler is configured; literal false is recorded as
explicitly disabled. An omitted value records the SDK's documented disabled default. Callback,
handler-controlled, and other non-literal approval policies remain unresolved.
Import-proven `ComputerTool` instances instead emit a local computer-control capability. Their
optional `on_safety_check` callback is recorded as SDK safety-check state, not promoted to a generic
human-approval control because it applies only when the model response carries safety checks.

Control presence is not automatically policy satisfaction. An uncaught lookup in an internal MCP
tool registry creates a `tool-registry` edge because it proves the name is routable and rejects
unknown names before forwarding. That edge carries `policy_effect: routing-only`; it does not satisfy
an explicit allowlist requirement or suppress `AV-MCP002`, because a discovery registry can contain
every tool advertised by the server. Finding analysis exposes both the governing control and its
effect even when no Agent-to-Tool edge is resolved.

A constructor-only instance attribute used directly, through a pure property, or through a
zero-argument getter creates a `fixed-tool-binding` edge with
`policy_effect: binds-tool-source-per-instance`. The proof is class-local and invalidated by any
second assignment, augmented assignment, or deletion. It removes a direct call-parameter selector
but, like a discovery registry, does not prove authorization or argument policy and therefore does
not suppress `AV-MCP002`.

The same control can carry `binding_scope: closure` when an unchanged enclosing parameter feeds a
nested callback that escapes by being returned or passed to a recognized tool/action registration
decorator. A retry or local helper closure invoked within the same caller-selected operation is not
an escaping binding. Reassigning the captured parameter also invalidates the edge. This distinction
prevents lexical nesting alone from being reported as governance.

Same-class calls receive a bounded method summary when the callee maps its tool-name parameter into
`self.get_tool(...)` or a `self.*tool*.get(...)` registry, then directly raises or returns on a
missing value in the same statement block. A return with a fallback value does not qualify. Earlier
return paths disqualify the summary unless a simple boolean parameter guard is ruled out by a
literal call argument; those required arguments are retained on the edge. The edge cites the
rejecting branch and carries `summary: same-class-method`. A fallback assignment does not qualify.
Imported or unselected manager implementations remain unresolved until their bodies are available;
class and field names are not proof of enforcement.

When a selected package reexports a registry class, the Python frontend follows only exact local
`from ... import ...` paths. A caller may inherit that class's method summary when one `__init__`
assignment binds `self.<attribute>` to the imported constructor and no other direct assignment,
deletion, or augmentation of that attribute occurs in the class. Rebound imported constructor names,
mutable attributes, fallback-returning managers, wildcard imports, and module-qualified constructor
aliases remain unresolved. The relationship cites both the consumer call and the imported rejecting
branch and carries `summary: imported-class-method`; its effect remains `routing-only`.

For audit modeling, a tool capability lexically inside an OpenTelemetry
`start_as_current_span(...)` block receives an exact capability-to-`action-trace` control edge. A
span elsewhere in the same tool does not cover the action. The edge records exporter durability as
unresolved: instrumentation is not proof that an attributable record reaches durable storage.
An exact Google ADK Python path separately resolves `Runner` plugin composition, `PluginManager`
tool callbacks, and the BigQuery Agent Analytics Storage Write API. It emits a
`durable-action-audit` control only for enabled literal/default configurations and records event,
agent, user, session, invocation, and tool attribution. Delivery remains best-effort with explicit
drop accounting; nonliteral filters/configuration and incomplete framework source paths are withheld.
Skyvern Task v3 is modeled separately as `durable-action-record`: the resolver follows a
billable/recordable tool dispatch into the round callback and then through `create_action` to an
SQLAlchemy commit on the `actions` table. It preserves organization/workflow/task/step/action
correlation and completed/failed status, but does not upgrade the record to a fully attributable
audit because `created_by` is nullable and unset and persistence exceptions are contained.
`AV-AUDIT001` consumes that explicit relationship state: it reports only when a production-scope
durable action-record edge carries unresolved actor attribution. It does not treat missing tracing,
missing audit edges, or repository-level logging vocabulary as proof of an audit failure.

## Safety boundary

AgentVerify reads source and configuration as data. It never imports project modules, evaluates their
code, installs their dependencies, or launches configured MCP servers. Repository traversal excludes
and prunes dependency, build, VCS, cache, and virtual-environment directories. The research collector
preserves its 220 root-file cap and may materialize up to 20 additional local source dependencies
reached from MCP forwarding/URL-security roots or listed as versioned audited evidence hints.
Selected-path scans reject absolute and parent-traversal paths; their
reports are explicitly marked partial.

Configuration discovery includes Compose, devcontainers, and Kubernetes/Helm paths. Exact dangerous
boolean settings are reported as review results; templates and values are not rendered or executed,
and AgentVerify does not infer that a chart value governs a workload unless that relationship is
explicitly resolved.

The native AI BOM serializes the same evidence graph with stable observation IDs. Relationship
endpoints expose symbol-ID, evidence-location, unique-display-name, ambiguous, or unresolved
identity instead of collapsing same-named assets. It is a lossless AgentVerify format, not a claim of
CycloneDX or SPDX conformance.

Source-symbol IDs are module-qualified. When a Python or TypeScript file constructs multiple
agents/tools through the same binding, each definition receives an `@line` occurrence suffix so its
own outgoing edges stay exact. Python target references are scope-aware even when a display name has
only one observed definition: a local shadow cannot fall back to that definition. Repeated identities
resolve only when one direct definition in the same lexical or module scope appears earlier; the edge
records `target_identity: lexical-single-definition` or `module-single-definition`. One exact
constructor assignment or callable definition that is the sole same-block mutation before use records
`block-dominating-definition`. Reassignments and unproven references do not inherit an arbitrary
occurrence; repeated ones carry
`target_identity: ambiguous-repeated-binding` and remain unresolved.

Policy evaluation is a post-baseline reporting stage, not a rule filter. Gates count matching
fingerprints by rule, result kind, and minimum severity; findings remain in every output. JSON, text,
AI BOM, and SARIF retain the policy file digest and per-gate decision evidence. Local `extends`
composition loads base policies depth first, deduplicates shared files by resolved path, rejects
cycles and duplicate gate identities, and attaches the contributing file digest to every gate.
