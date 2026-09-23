# AVM: A Curated-Package WebAssembly Sandbox for ARKlight

## Status

**Not accepted. Filed for maintainer review.** Belongs in `docs/Proposals/`
(unsettled). If accepted it ships as an **experimental API** behind the gate in
`docs/Foundational/EXPERIMENTAL-APIS.md` and graduates to a staging doc in
`docs/Implementation/`. It is not part of the default surface and does not touch
the `v1.0` scope in `V1-DEFINITION.md`.

**Version-number note.** No slot is requested. `v0.079` is held by Miko Stage A
and `v0.080` by the Android backend. The ladder in section 10 uses `A0`-`A6` and
receives real versions only if a maintainer accepts it.

**Origin:** a design suggestion that ARKlight should be able to use existing
JavaScript libraries without ever exposing JavaScript or npm to the site author.
Each library runs in its own Docker-like WebAssembly sandbox, takes input,
returns output, and is discarded. A small orchestrator (the "AVM", ARKlight
Virtual Machine) coordinates the sandboxes. Refined in review: the set of usable
packages is a **curated ARKlight catalog**, not "whatever is on npm."

Read against `PITCH.md`, `WHAT-ARKLIGHT-IS.md`, `ARCHITECTURE.md`,
`SYSTEM-DESIGN-AGREEMENTS.md`, `EXPERIMENTAL-APIS.md`, `ACC-CAPABILITIES.md` and
`ARKlight-ISSUE-REGISTER.md` on `alpha`, plus `arklight/experimental.py` and
`arklight/backend/html/csp.py`.

## TL;DR

`ARKlight-ISSUE-REGISTER.md` #40 names the ecosystem cost of a closed
vocabulary: ARKlight cannot consume arbitrary npm packages as native vocabulary,
and ACC is "an ecosystem mechanism, not yet a mature ecosystem." This proposal
closes part of that gap **without opening the vocabulary**, using three ideas
that only work together:

1. **A curated catalog.** ARKlight (and later ACC contributors) maintain a short
   list of packages judged to work well in the sandbox. Each entry is pinned,
   hash-verified, schema-typed, tested, and exposed to authors by **capability
   name** (`text.slugify`), never by package name. Authors cannot point at
   arbitrary packages.
2. **A sandbox per call.** Each invocation runs one package as a pure function
   (input in, output out) in its own worker and WebAssembly instance, with no
   DOM, network, storage or clock. The instance is terminated afterward.
3. **Async as vocabulary.** Because a sandbox call takes time, its result is a
   closed three-state value (loading, failed, ready) that authors handle
   declaratively and the compiler checks.

```text
 author's Python           compile time                       run time (browser)
 ---------------------   ------------------------------   ------------------------------------
 Derive.avm(              resolve capability -> catalog     AVM orchestrator
   "text.slugify",        entry; pin id + integrity into    |
   Bind("title"))         avm.lock; vendor the bytes;       +-- verify bytes vs avm.lock
                          add to SBOM; fold if input is     +-- spawn sandbox (worker + wasm)
                          static                            +-- input in -> output out
                                                            +-- validate output vs schema
                                                            +-- terminate worker, drop instance
```

The vocabulary stays closed. What runs in the sandbox is not ARKlight's code,
and the proposal says so plainly (section 7) instead of pretending the central
claim survives unchanged.

## 1. Why this is not "a fetch primitive with extra steps"

| Gap | Where it is recorded |
|---|---|
| No way to reuse existing JS libraries as vocabulary | Issue register #40; `WHAT-ARKLIGHT-IS.md` section 5 (Astro row) |
| No client-side computation beyond closed `Derive.*` | Issue register #8 |
| `script-extension` is the only route for hand-written JS, and it is unchecked | `EXPERIMENTAL-APIS.md` |

`script-extension` says "write your own JS, no guarantees." The AVM catalog says
"name a capability, get a typed function; third-party code never touches your
page." It is deliberately **not** a `Provider` (external services; the AVM has no
network), a Platform API (device capabilities; the AVM has none), or a Node
emulator (section 9).

## 2. Prior art, and what this adds

Nothing here is a new idea in isolation. The combination is what this proposal
claims; a few searches did not find a browser-side equivalent, which is not proof
that none exists.

| Prior art | What it does | Difference from this proposal |
|---|---|---|
| **Afterburner** (2026, BSL-licensed) | Sandboxed WebAssembly runtime; packages take JSON in and return JSON out; sealed by default; npm dependencies fetched, integrity-checked, installed with no scripts, native addons rejected; lockfile; multi-threaded scheduler | Native/server-side Rust (Wasmtime), not the browser; general package system, not a curated catalog owned by a UI compiler; source-available license, so not adoptable as a base |
| **LavaMoat / SES / Endo** | Per-package least-authority policies enforced in the JS engine; used in production by MetaMask and Agoric | In-engine confinement rather than a wasm boundary; author-visible JS |
| **Nano-processes (Lin Clark, 2020)** | The original argument for per-module capability isolation as the fix for npm supply-chain risk | A talk-level vision; this is a concrete browser design |
| **WebContainers** | Runs Node and `npm install` in the page | Needs cross-origin isolation, relies on hosted proxies, commercial license; contradicts closed vocabulary |
| **quickjs-emscripten / Figma plugins** | JS interpreter compiled to wasm as a sandbox for untrusted JS | Building block, not a product; documents that it is unaudited |
| **Wasmer JS SDK** | WASIX on Web Workers | Needs cross-origin isolation for threads |

What is (as far as searched) new: a **compiler-owned lock**, a **curated closed
catalog**, **per-call purge**, and a **Python-authored** surface, all in the
browser. The most useful design lessons from the prior art are Afterburner's
"no install scripts, no native addons, hash-pinned" rule set and LavaMoat's
"policy is reviewable before anything runs."

## 3. The curated catalog

### 3.1 What an entry is

A catalog entry is the unit of trust. Sketch, not a final schema:

| Field | Purpose |
|---|---|
| `id` | Capability name, namespaced by what it does (`text.slugify`, `text.markdown`, `date.format`). The author-facing key. |
| `package`, `version`, `integrity` | Exact upstream identity; sha512 recorded at review time |
| `bundle` | The reviewed, flattened, dependency-free file actually shipped (built reproducibly from the pinned tarball) |
| `entry` | Exported function |
| `input`, `output` | Closed schemas (`Text`, `Number`, `Bool`, `List[..]`, `Record{..}`, `Bytes`; **never `Html`**) |
| `limits` | Memory and time ceilings |
| `vectors` | Test vectors run in CI inside the real sandbox |
| `license`, `size_bytes` | Feeds `sbom.py` and the page-size budget |
| `tier` | `core` (maintained in-repo) or `community` (ACC-contributed, outside the stability promise) |

**Capability-first naming** matches how ARKlight already treats interfaces
(`Provider`, Platform APIs, ACC): the author states what they need; the
implementation is swappable. A catalog maintainer can move `text.slugify` from one
library to another, or bump a version, without touching any site's source; the
site's `avm.lock` still records exactly which entry revision it built against, so
builds stay reproducible.

### 3.2 Inclusion bar (draft)

An entry is admitted only if it is a **pure function** (no Node built-ins, no DOM,
no globals it needs at runtime), deterministic, permissively licensed, within a
size budget, actively maintained, and has a dependency tree that reduces to
**one reviewed bundle with no install scripts**. It must pass its vectors under
the same limits production uses. This answers the "compatibility corpus" question:
compatibility is not a promise about npm, it is a property of each entry, checked
in CI.

Candidate categories to *evaluate* (none has been run in the sandbox yet): text
slugging and normalization, Markdown rendering, date and number formatting, fuzzy
search, diffing. Whether any qualifies is what stage `A1` measures.

### 3.3 Where it lives, and how it relates to ACC

`core` entries live in the repository and ship with the wheel like the vendored
`htmx`/`snabbdom` files. `community` entries arrive through ACC collections, which
`ACC-CAPABILITIES.md` already scopes as outside the stability promise; the existing
`discover_capabilities()` scan already feeds `sbom.py`. ACC is the **curation
layer** (which packages earn a capability name); the AVM is the **isolation layer**
(what still holds if curation fails).

The catalog **replaces runtime registry access**. Site builds and browsers never
talk to npm. Only a maintainer-side refresh tool does, and its output is a
reviewable diff (new version, new integrity, new bundle hash, test results).

## 4. Authoring surface and async

### 4.1 Closed vocabulary

Illustrative, not final:

```python
from arklight import Site, State, Text, Bind, Show, Derive, Avm

site = Site(avm=Avm.declare("text.slugify"))     # capability names only

State("title", initial="Hello World")
slug = Derive.avm("text.slugify", Bind("title")) # async value: loading | failed | ready

Show(slug.ready,   Text(slug.result))
Show(slug.loading, Text("Working..."))
Show(slug.failed,  Text("Could not compute a slug."))
```

`Avm.*` and `Derive.avm` are registry entries in the same shape as
`ACTION_REGISTRY` / `DERIVATION_REGISTRY`. An unknown capability, a schema
mismatch, or a request for a package name instead of a capability fails during
`arklight build` with a `ValidationError`, the "fail loudly at build time" rule
applied to dependencies. Output is data, never markup, and is rendered through the
existing bound-text machinery, which keeps it compatible with the existing
`require-trusted-types-for 'script'` policy.

### 4.2 Async as something authors learn

`Computed`/`Derive.*` are synchronous today, and a sandbox call is not. Rather than
hide that, the proposal makes it a small, closed concept, following an established
pattern: Phoenix LiveView tracks an async operation as one value carrying loading,
failed and result states, and renders each declaratively.

- An AVM-derived value has exactly three states: `loading`, `failed`, `ready`
  (with `result` when ready).
- The compiler checks that every use of an AVM value handles `failed`. A missing
  failure branch is a **build error**. A missing `loading` branch defaults to
  rendering nothing. (Details are open, Q1.)
- Failures (timeout, refused hash, schema violation) surface through the closed
  error vocabulary and the `arkReportError` sink from
  `USER-DEFINED-ERROR-HANDLING-PROPOSAL.md`, not a new channel.

This adds one concept to teach, which cuts against ARKlight's "fewer things to
know" pitch, but it is three closed states the compiler can enforce, and it means
no page can silently hang because a package timed out.

### 4.3 Compiler first

Applying `SYSTEM-DESIGN-AGREEMENTS.md` sections 1 and 8: for **static inputs**
nothing needs the runtime, so `Derive.avm("text.slugify", "Hello World")` is
evaluated during `arklight build` and baked in (ships zero AVM bytes). Only
interaction-dependent calls reach the browser. The AVM adds no capability the page
lacks; it adds a **trust boundary**, and should be judged as a security feature,
not feature parity (agreement section 17).

## 5. Runtime model

### 5.1 Per-call sandbox

```text
page (arklight.js)
  |  1. Derive.avm("text.slugify", input) -> enqueue call; value = loading
  v
AVM orchestrator
  |  2. fetch bundle bytes (same-origin, content-addressed)
  |  3. SHA-512 == avm.lock integrity ?  else -> failed
  |  4. take/spawn a worker from the pool
  v
sandbox (worker)
  |  5. instantiate engine (JS-in-wasm, or the package's own .wasm)
  |  6. load bundle into a fresh context, no host imports
  |  7. run entry(input) under memory + deadline limits
  v
AVM orchestrator
  |  8. copy output back, validate against schema  -> ready | failed
  |  9. terminate worker / drop instance           <- purge
```

The sandbox gets no DOM, no `fetch`/XHR/WebSocket, no storage, no clock or
randomness by default (identical inputs give identical outputs), no Node
built-ins, no `eval` of author strings, and **no lifecycle scripts, ever**.

### 5.2 What "abstract JS away with WASM" delivers

For a JavaScript package the wasm module is a JS interpreter (for example QuickJS
compiled to wasm), so the package's JS still runs, inside a wall. What is
abstracted away is JavaScript **from the author and the page**. Catalog entries
that ship their own `.wasm` (Rust/C/Go compiled to wasm) need no interpreter layer
and are the ideal citizens.

### 5.3 Threads, workers and cost

The tempting reading of "WASM multithreading" is shared-memory wasm threads, which
need `SharedArrayBuffer`, which browsers expose only to **cross-origin isolated**
pages (COOP `same-origin` + COEP `require-corp` HTTP headers). ARKlight delivers
policy via a `<meta>` tag, and COOP/COEP cannot be set that way. Separately, the
Chromium issue tracker records `SharedArrayBuffer` as unavailable in Android
WebView even with correct headers (re-verify per target WebView in `A5`), and
`WebViewAssetLoader` underpins ARKlight's Android backend.

The isolation model does not need shared memory. **One worker per sandbox,
communicating by `postMessage`** gives real parallelism across packages with no
`SharedArrayBuffer`, no headers, and support anywhere Workers work. True wasm
threads become an opt-in tier (`A5`) gated on `self.crossOriginIsolated`, with the
single-worker path as the guaranteed fallback.

Worker cost is real, though. Analyses of browser sandboxing note that a separate
Worker or iframe per sandbox becomes impractical at dozens or hundreds of
instances. So the runtime uses a **small pool** with a hard cap, and per-call purge
means terminating and replacing pool members, not spawning without limit. Pool
size and the purge-versus-reuse trade-off are measured in `A3` (Q4).

Standards context, so nobody bets on the wrong horse: `wasi-threads` is a legacy
proposal superseded by `shared-everything-threads` (still early), and at least one
downstream project reports Wasmtime removing its `-Sthreads` flag in v47. WASI
0.3.0 shipped June 11, 2026, but the browser path here is plain WebAssembly plus
Workers, not WASI.

### 5.4 Why "purge" means terminate

WebAssembly linear memory can grow but not shrink; `memory.discard` is still a
proposal. The only reliable purge is dropping the whole instance:
`worker.terminate()`, null every reference, let the engine collect. That fits the
one-call-one-sandbox model. Its cost is re-instantiation, hence Q4.

## 6. Threat model

The 2026 npm landscape is the strongest argument for this feature. Self-propagating
worms have repeatedly poisoned popular packages, including caching libraries on
August 4, 2026, whose malicious versions carried valid provenance; lifecycle scripts
were the main trigger. A curated catalog plus a sandbox addresses different layers.

| Threat | Mitigation | Residual risk |
|---|---|---|
| Install-time payloads (`preinstall`, `postinstall`, `node-gyp`) | The AVM never runs a package manager or lifecycle scripts; only reviewed, pre-built bundles are loaded | None from this vector |
| Poisoned new version | Catalog bumps are maintainer-reviewed diffs with pinned integrity and a reproducible bundle; no `latest`/ranges anywhere; sites pin a catalog revision in `avm.lock` | **A maintainer pinning an already-poisoned version.** Provenance did not stop the August 2026 case. Review plus sandbox contain the blast radius but cannot make output *correct* |
| Credential/data theft | Sandbox has no network, storage, DOM or environment | A poisoned package can still return misleading *data* |
| Exfiltration via output | Closed output schema; unexpected shapes rejected | Data-shaped covert channels within the schema |
| Runaway CPU/memory | Per-sandbox memory limit and deadline (a real `quickjs-emscripten` feature) plus `worker.terminate()` backstop | Cost of wasted work |
| Cross-call contamination | Fresh instance per call | Warm-reuse mode (Q4) would weaken this and must be opt-in |
| Dependency confusion / typosquatting | Authors cannot name packages at all, only catalog capabilities | Catalog maintainer error |
| Output injection into the page | Typed data, never `Html`, rendered via text binding | Bugs in the binding layer |
| Engine escape (wasm JS engine or browser bug) | Defense in depth: wasm + worker + strict CSP | Non-zero; `quickjs-emscripten` documents that it is unaudited |

Verified while drafting: the npm registry served both a package's metadata and its
tarball with `access-control-allow-origin: *`, and each version carries a
`dist.integrity` sha512. That matters only to the **maintainer refresh tool**;
because the catalog ships reviewed bundles, site builds and browsers do not contact
the registry.

## 7. Cost to ARKlight's central claim

`WHAT-ARKLIGHT-IS.md` section 7 says ARKlight is "provably incapable of running
code it didn't itself generate." The AVM changes that sentence and honest docs must
change with it:

> ARKlight runs third-party code only inside an opt-in, capability-less
> WebAssembly sandbox, only for packages in the ARKlight catalog, and only on
> hash-verified bytes shipped with the site.

That is a narrower, checkable promise, comparable to how `Provider` and
`script-extension` already qualify the original. It should be listed with the
escape-hatch-class features in register section P, and the experimental banner
exists so no site adopts it unseen. Against the current implementation:

1. **CSP.** `_render_csp_meta_tag` emits `script-src 'self'` with no WebAssembly
   allowance. Compiling or instantiating wasm is blocked unless the policy includes
   `'wasm-unsafe-eval'` (or the much broader `'unsafe-eval'`). The AVM needs the
   narrower keyword **only on pages that use an AVM capability**; it permits wasm
   compilation, not JavaScript `eval`, and would be the first per-feature CSP
   loosening, so `csp.py` needs a documented record of it. Workers are same-origin
   files (covered by `worker-src` falling back to `script-src 'self'`), not `blob:`.
2. **Trusted Types.** The `Worker` constructor's script URL is a Trusted Types
   sink, so workers under `require-trusted-types-for 'script'` likely need a
   registered policy even though `csp.py` registers none today. Verify in `A2`.
3. **`connect-src`.** Stays unset. Because the catalog ships bytes with the site,
   no network destination is ever needed.

## 8. Targets

| Target | Expected behavior | Notes |
|---|---|---|
| Web (http/https) | Full pooled single-worker-per-sandbox model | Baseline |
| Web with COOP/COEP headers | Optional shared-memory tier (`A5`) | Needs a deploy adapter that can send headers; check `DEPLOYMENT-CLI.md` |
| PWA | Same, AVM assets in the service-worker precache | Interacts with register #3 (PWA inline scripts vs CSP) |
| `.ark` / air-gapped | Works fully, since bundles ship with the site | Why the catalog is bundled-only |
| `file://` | Expected limited (workers/wasm from opaque origins) | Verify in `A2`; document like the `persist=True` `file://` caveat |
| Android (WebView) | Single-worker path only | `WebViewAssetLoader` gives a stable origin |
| Desktop (WebKit2GTK) | Unverified | Q7 |
| iOS | N/A | Documented non-target |

## 9. Out of scope

- **Arbitrary packages.** Authors cannot name npm packages, versions or URLs. If an
  escape hatch is ever wanted, it would be a separate, louder experimental gate and
  is not proposed here (Q3).
- **Runtime registry access.** No live fetch of package bytes from npm in browsers
  or in site builds.
- **A Node.js runtime in the browser**, Node built-ins, native addons, or packages
  needing a filesystem, sockets or child processes (WebContainers is the prior art
  and is not a foundation: cross-origin isolation, hosted proxies, commercial
  license).
- **Author-typed code at runtime**, floating versions, Python in the browser.
- **A general fetch primitive.** The AVM has no network; it does not close the
  register's client-side-fetch gap.

## 10. Staged ladder

Same rung discipline as `PROVIDER-SDK-ADDENDUM.md`: each rung is independently
shippable and the feature stays experimental throughout.

| Rung | What ships | Runtime cost | Done when |
|---|---|---|---|
| **A0** | Gate `avm-sandbox` in `experimental.py`; `Avm.declare`/`Derive.avm` in the IR; catalog schema and loader; closed schemas; validation; `avm.lock` and SBOM entries; three paper entries | None (nothing reaches the browser) | Unknown capabilities and schema errors fail the build; `avm.lock` is byte-reproducible |
| **A1** | Maintainer catalog tooling (refresh, reproducible bundle, diff, vector runner); compile-time folding of static-input calls; measure which candidate packages actually qualify | None | At least one real package passes its vectors in a QuickJS-wasm sandbox; static-only sites ship zero AVM bytes |
| **A2** | Browser orchestrator, single sandbox, bundled bytes, vendored engine, CSP `'wasm-unsafe-eval'` for AVM pages only, Trusted Types policy if required, three-state async value with build-time `failed` check | Page-gated | Round-trip works under the real strict CSP; `file://`/Android behavior documented |
| **A3** | Worker pool with hard cap, limits, purge policy, size and startup measurements | Page-gated | Limits proven by tests that hang and allocate on purpose; pool cost measured |
| **A4** | Community tier: ACC-contributed catalog entries, outside the stability promise | None new | An ACC collection ships an entry that passes the same vectors |
| **A5** | Optional wasm-threads tier when `crossOriginIsolated`; deploy adapter emits isolation headers where the host allows | Page-gated | Same outputs as the single-worker path, measurably faster; fallback proven |
| **A6** | Backend matrix (PWA precache, `.ark`, Android, Desktop) and docs graduation | None new | Section 8 matrix verified, not assumed |

Compared with an open-registry design, the curated catalog **removes** live
registry fetching and its `connect-src` change from the plan entirely.

## 11. Experimental-gate entry (draft)

Following the three-step process in `EXPERIMENTAL-APIS.md`:

- id: `avm-sandbox`
- inline note: *"This site runs catalog packages inside a WebAssembly sandbox.
  ARKlight vets the catalog but does not guarantee any package's output."*
- detail lines: what is pinned and hashed; what the sandbox withholds; that a
  poisoned pinned version can still return wrong data; that AVM pages relax CSP to
  allow WebAssembly compilation (not JavaScript `eval`).
- `upstream_candidate=True`: heavy reliance suggests a missing catalog entry, the
  same "open a PR" nudge the heavy-reliance heuristic exists for.

## 12. Open questions

1. **Async details.** Exact vocabulary (`Show` branches versus a dedicated
   component), whether `failed` is a hard build error, and stale-while-recomputing
   behavior. (Register #12/#13 already flag state-update rescan cost.)
2. **Governance.** Who curates, what is the review process, and how are entries
   retired? Does the core tier ship bundle bytes in the wheel (size) or fetch them
   at build time from a pinned release?
3. **Escape hatch.** Should an author-declared arbitrary package ever exist,
   behind a louder gate? Default answer here: no.
4. **Per instance, purge and worker cost.** Per call, per page load, or per package
   per session? Purge every call, or idle-timeout warm reuse? Pool size?
5. **Engine choice and payload.** JS-in-wasm interpreter versus package `.wasm`
   versus both; measure size and startup in `A2`.
6. **Trusted Types and workers.** Confirm the `Worker` sink behavior and what
   default policy is acceptable.
7. **WebKit2GTK, `file://`, `.ark` viewers.** Confirm behavior.
8. **Licensing.** Bundled third-party code needs attribution and a compatible
   license; how does that flow into `sbom.py` and the wheel?
9. **Naming.** "AVM" already means the Algorand Virtual Machine and Adobe's
   ActionScript VM. Keep it, or choose something searchable?

## 13. Relationship to other proposals

- `PROVIDER-SDK-PROPOSAL.md`: external services; the AVM has no network.
- `PLATFORM-API-IR-PROPOSAL.md`: device capabilities; the AVM has none. Both share
  the "compiler owns the interface, runtime owns the implementation" shape.
- `JS-VOCABULARY-EXPANSION-PROPOSAL.md`: adds vocabulary the compiler understands;
  the AVM is for logic that will never be vocabulary. Pure math/string derivations
  stay `Derive.*`.
- `USER-DEFINED-ERROR-HANDLING-PROPOSAL.md`: AVM failures use its error vocabulary
  and `arkReportError`.
- `APP-SHELL-CAPABILITY-PROPOSAL.md`: workers do not survive navigations; check
  `app_shell=True` before assuming warm sandboxes persist.
- `ACC-CAPABILITIES.md`: the community tier and curation model (section 3.3).

## 14. Filing checklist (per `docs/README.md`'s one-pass rule)

On filing, the same change touches:

1. This file, `docs/Proposals/AVM-WASM-SANDBOX-PROPOSAL.md`, with its Status line.
2. Its row in `docs/Proposals/README.md`'s Index.
3. Its row in `docs/README.md`'s Folder Guide for `docs/Proposals/`.
4. If accepted: `docs/Implementation/AVM-ADDENDUM.md`, its rows in
   `docs/Implementation/README.md` and the Folder Guide, the `ARCHITECTURE.md`
   Milestones row, the `PROGRESS.md` Snapshot row, and the `EXPERIMENTAL-APIS.md`
   entry.

Suggested Index row text:

> | [`AVM-WASM-SANDBOX-PROPOSAL.md`](AVM-WASM-SANDBOX-PROPOSAL.md) | Proposal for the AVM, an experimental orchestrator that runs a curated catalog of pinned, hash-verified, schema-typed third-party packages as pure input->output functions, one per WebAssembly sandbox, each purged after use. Authors name capabilities (`text.slugify`), never packages; static-input calls fold at build time; results are a closed three-state async value the compiler checks. Shared-nothing parallelism via a capped worker pool (no `SharedArrayBuffer` required); optional threads tier behind cross-origin isolation. Ladder `A0`-`A6`. **Not accepted.** |

## 15. References

External claims rest on these; repo claims rest on the files named inline.

- Cross-origin isolation, COOP/COEP and `SharedArrayBuffer`:
  https://web.dev/articles/coop-coep
- Chromium issue on `SharedArrayBuffer` in Android WebView:
  https://issues.chromium.org/issues/40914606
- WebAssembly CSP proposal (`wasm-unsafe-eval`):
  https://github.com/WebAssembly/content-security-policy/blob/main/proposals/CSP.md
- WebAssembly memory-control and `memory.discard`:
  https://github.com/WebAssembly/memory-control/blob/main/proposals/memory-control/Overview.md
- `wasi-threads` (legacy status): https://github.com/WebAssembly/wasi-threads
- WASI 0.3 release notes: https://wasi.dev/releases/wasi-p3
- Wasmer JS SDK and cross-origin isolation:
  https://docs.wasmer.io/sdk/wasmer-js/explainers/troubleshooting
- WebContainers: https://www.npmjs.com/package/@webcontainer/api and
  https://developer.stackblitz.com/guides/user-guide/general-faqs
- `quickjs-emscripten`: https://github.com/justjake/quickjs-emscripten
- Afterburner (sandboxed wasm runtime, JSON in/out, npm with integrity checks and no
  install scripts): https://docs.rs/crate/afterburner/latest
- LavaMoat / SES / Endo: https://github.com/Agoric/ses-shim and
  https://github.com/lavamoat/lavamoat-browserify
- Lin Clark, nano-processes and capability-based module isolation (InfoQ, 2020):
  https://www.infoq.com/news/2020/05/webassembly-security-nanoprocess/
- Worker/iframe-per-sandbox cost:
  https://dev.to/alexgriss/the-architecture-of-browser-sandboxes-a-deep-dive-into-javascript-code-isolation-1dnj
- Phoenix LiveView async results (loading/failed/result, declarative rendering):
  https://hexdocs.pm/phoenix_live_view/Phoenix.LiveView.html
- npm supply-chain incidents, 2026: Datadog Security Labs on the August 4, 2026
  worm
  (https://securitylabs.datadoghq.com/articles/npm-worm-compromises-popular-npm-packages/),
  Aikido on the keyv compromise and provenance
  (https://www.aikido.dev/blog/keyv-and-friends-compromised-in-npm-supply-chain-attack),
  Snyk on the June 2026 node-gyp wave
  (https://snyk.io/blog/node-gyp-supply-chain-compromise-self-propagating-npm-worm-binding-gyp/).
- npm registry CORS and `dist.integrity`: verified directly against
  `registry.npmjs.org` while drafting; see section 6.
