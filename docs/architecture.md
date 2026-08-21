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
repository file and can safely form cross-file agent paths. TypeScript named imports resolve when a
relative module maps to exactly one in-repository `.ts`, `.tsx`, `.js`, or `.jsx` file; aliases retain
the original exported name. Imports that escape the scan root, target missing files, or have multiple
candidate files remain unresolved. Python class methods use class-qualified IDs, and assigned agent
or built-in-tool instances use their binding name. The TypeScript frontend balances delimiters and
reads only direct properties and top-level tool-array entries; it models OpenAI tool namespaces,
built-ins, inline/assigned agent adapters, and Cline inline tools without treating nested tokens as
symbols. Package re-exports, wildcard imports, dynamic lookups, conditional tool expressions, and
unrecognized wrapper-factory forms remain unresolved.

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
host with a dynamic destination. URL parsing guards, redirects, DNS, proxies, imported/transitive
helpers, arrow functions, and request-object data flow remain unresolved.

A repository prepass builds bounded Python network summaries for unique top-level free functions in
selected files. A summary records direct recognized HTTP calls and the formal parameters that can
control their origins after fixed-prefix discrimination. At a tool call site, only an exact named
absolute or relative import can apply the summary; positional and keyword arguments map back to the
controlled formals, and the capability retains the helper path and sink lines. Import state is
function-local and statement-ordered, so reassignment, deletion, or replacement imports invalidate
the edge. Module-object calls, reexports, nested/transitive helpers, client instances, helper-local
aliases, and rebound HTTP clients remain unresolved rather than being inferred by name.

The same Python tool-parameter state distinguishes browser-page code execution from ordinary code
inventory. In a module importing Playwright, Selenium, or Puppeteer, an attribute
`.evaluate(...)` call becomes a `code-execution` capability with
`execution_context: browser-page`. `dynamic_input` is true only when the script expression contains
a current tool parameter or its direct assignment alias; literals, module constants, and values
derived solely from normalized intermediates remain inventory-only. The capability still receives
an exact tool edge when it occurs in a resolved tool body, including post-definition FastMCP tools.
Receiver types, sanitizer proofs, imported/transitive script builders, and alternate browser
evaluator APIs remain unresolved, so import context alone never promotes an evaluator to a finding.

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

## Safety boundary

AgentVerify reads source and configuration as data. It never imports project modules, evaluates their
code, installs their dependencies, or launches configured MCP servers. Repository traversal excludes
and prunes dependency, build, VCS, cache, and virtual-environment directories. The research collector
preserves its 220 root-file cap and may materialize up to 20 additional local Python imports reached
from MCP forwarding roots. Selected-path scans reject absolute and parent-traversal paths; their
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
own outgoing edges stay exact. When a file-level identity is repeated, Python target references
resolve only when one direct definition in the same lexical or module scope appears earlier; the edge
records `target_identity: lexical-single-definition` or `module-single-definition`. Reassignments and
unproven references do not inherit an arbitrary occurrence; repeated ones carry
`target_identity: ambiguous-repeated-binding` and remain unresolved.

Policy evaluation is a post-baseline reporting stage, not a rule filter. Gates count matching
fingerprints by rule, result kind, and minimum severity; findings remain in every output. JSON, text,
AI BOM, and SARIF retain the policy file digest and per-gate decision evidence.
