# AVM: A WebAssembly Sandbox Orchestrator for Third-Party Packages

## Status

**Not accepted. Filed for maintainer review.** Belongs in `docs/Proposals/`
(unsettled). If accepted it would ship as an **experimental API** under
`docs/Foundational/EXPERIMENTAL-APIS.md`'s existing gate and graduate to a
staging doc in `docs/Implementation/`; it is not part of ARKlight's default
surface and does not touch the `v1.0` scope in `V1-DEFINITION.md`.

**Version-number note.** No slot is requested. `v0.079` is held by Miko
Stage A and `v0.080` by the Android backend; the ladder in section 10 is
numbered `A0`-`A6` and is assigned real versions only if a maintainer
accepts it.

**Origin:** a design suggestion that ARKlight should be able to use the
npm ecosystem without ever exposing JavaScript or npm to the site author:
every package runs inside its own Docker-like WebAssembly sandbox, takes
input, returns output, and is thrown away afterward, with a small
WebAssembly-hosted orchestrator (the "AVM", ARKlight Virtual Machine)
coordinating the whole thing. Read against `PITCH.md`,
`WHAT-ARKLIGHT-IS.md`, `ARCHITECTURE.md`, `SYSTEM-DESIGN-AGREEMENTS.md`,
`EXPERIMENTAL-APIS.md`, `ACC-CAPABILITIES.md` and `ARKlight-ISSUE-REGISTER.md`
on `alpha`, plus the source of `arklight/experimental.py` and
`arklight/backend/html/csp.py`.

## TL;DR

`ARKlight-ISSUE-REGISTER.md` #40 states the central ecosystem cost of the
closed vocabulary plainly: ARKlight "cannot simply consume arbitrary npm
packages as native semantic vocabulary," and ACC is "an ecosystem
mechanism, not yet a mature ecosystem." This proposal is a way to close
part of that gap **without opening the vocabulary**.

The AVM treats a third-party package as a **pure function running behind a
wall**:

```text
   site author's Python            compile time                      run time (browser)
  ------------------------   ------------------------------   ------------------------------------
   Avm.package("slugify",     resolve -> pin name@version      AVM orchestrator
      version="1.6.6", ...)   + sha512 integrity into          |
   Derive.avm(slugify, ...)   avm.lock, vendor the bytes,      +-- verify bytes vs avm.lock
                              add to SBOM                      +-- spawn sandbox (worker + wasm)
                                                               +-- input in  ->  output out
                                                               +-- validate output against schema
                                                               +-- terminate worker, drop instance
```

The vocabulary stays closed: the author can only name packages that were
declared, pinned and schema-typed at build time. What runs in the sandbox
is not ARKlight's code, and the proposal says so explicitly (section 7)
rather than pretending the "provably incapable of running code it didn't
itself generate" claim survives unchanged. It becomes a weaker, still
checkable claim: *third-party code runs only inside a capability-less
sandbox, and only when the site opted in by name.*

## 1. Why this is not just "a fetch primitive with extra steps"

Three existing gaps point at the same missing thing:

| Gap | Where it is recorded |
|---|---|
| No way to use existing JS libraries as vocabulary | Issue register #40, `WHAT-ARKLIGHT-IS.md` section 5 (Astro row) |
| No arbitrary client-side computation beyond closed `Derive.*` | Issue register #8 |
| `script-extension` is the only route for hand-written JS, and it is unchecked | `EXPERIMENTAL-APIS.md`, `script-extension` |

`script-extension` gives a site author unsandboxed JS in `arklight.js`. The
AVM would be the **safe sibling**: instead of "write your own JS, no
guarantees," it is "name a pinned package, get a typed function, third-party
code never touches your page."

It is deliberately *not*:

- `Provider` (`PROVIDER-SDK-PROPOSAL.md`): that is an interface to an
  external *service* the site talks to. The AVM has no network access.
- A Platform API (`PLATFORM-API-IR-PROPOSAL.md`): those are device/OS
  capabilities. The AVM has no capabilities at all.
- A Node emulator. See section 9.

## 2. What "AVM" means precisely

| Term | Meaning |
|---|---|
| **AVM** | The orchestrator: a small runtime (vendored JS glue plus a WebAssembly module) that loads, runs and discards sandboxes. It never runs package code itself. |
| **Sandbox** | One package invocation: its own worker, its own WebAssembly instance, its own linear memory. Shared-nothing with every other sandbox and with the page. |
| **Package entry** | A build-time-declared record: `name`, exact `version`, `integrity` (sha512), entry point, input schema, output schema, limits. |
| **`avm.lock`** | Compiler-emitted, deterministic lockfile of every package entry. Analogue of `package-lock.json`, but written by ARKlight, not npm. |
| **Purge** | Terminate the worker and drop every reference to the instance so the engine can reclaim the memory (see section 5, "why purge means terminate"). |

The wall has exactly two holes: **input** (structured data the orchestrator
copies in) and **output** (structured data copied out, validated against the
declared schema before anything sees it).

## 3. How it maps onto the existing architecture

### 3.1 Compiler first (`SYSTEM-DESIGN-AGREEMENTS.md` sections 1, 16)

The agreement's decision order is compile > target-native > minimal bridge >
runtime abstraction, and section 8 lists seven questions a runtime feature
must answer. Honest answers:

1. *What is unavailable at compile time?* For **static inputs, nothing**.
   For inputs that depend on user interaction (`Bind("title")`), the value.
2. *Why runtime?* Only for the interactive case. **Static-input calls are
   folded at build time and ship zero runtime** (stage `A1`).
3. *Does the target provide it?* The browser can already run a package's JS
   directly in the page. The AVM does **not** add a capability; it adds a
   **trust boundary**. That is its entire justification, and it should be
   judged as a security feature, not a feature-parity one (section 17 of
   the agreement, "Anti-Pattern: Framework Feature Parity").
4. *Can ARKlight delegate?* Workers and WebAssembly are delegated to the
   browser; ARKlight ships only the orchestration bridge.
5. *Smallest runtime?* Emitted only when a site declares an AVM package
   (same "only ship what's used" gate `arklight/backend/js/render.py` already
   applies). The register's #17/#18 measurement (htmx was ~58% of a small
   page's JS) is the cautionary tale: the AVM must not become a
   page-level tax.
6. *Removable when unused?* Yes, by construction.
7. *Different per target?* Yes, see section 8.

### 3.2 Closed vocabulary (`WHAT-ARKLIGHT-IS.md` section 1)

Sketch only, not a final API:

```python
from arklight import Site, State, Text, Bind, Computed, Derive, Avm

slugify = Avm.package(
    "slugify", version="1.6.6",          # exact version only; ranges/"latest" refused
    entry="default",
    input=Avm.Text, output=Avm.Text,     # closed schema vocabulary
    limits=Avm.Limits(memory_mb=16, time_ms=200),
)

site = Site(avm=Avm.declare(packages=[slugify]))

State("title", initial="Hello World")
Computed("slug", Derive.avm(slugify, Bind("title")))
Text(Bind("slug"))
```

`Avm.*` and `Derive.avm` would be new **registry entries** (same shape as
`ACTION_REGISTRY` / `DERIVATION_REGISTRY`), validated in `ir/validate.py`.
An unknown package, a missing pin, a schema mismatch or a range instead of
an exact version raises a `ValidationError` during `arklight build`. This is
the "fail loudly at build time" rule applied to dependencies.

Schema vocabulary (closed, provisional): `Text`, `Number`, `Bool`,
`List[...]`, `Record{...}`, `Bytes`. **Never `Html`.** Output is data, and
rendering goes through the existing bound-text/`Repeat` machinery, so
nothing a package returns is ever parsed as markup (compatible with the
existing `require-trusted-types-for 'script'` policy in
`arklight/backend/html/csp.py`).

### 3.3 ACC (`ACC-CAPABILITIES.md`)

The natural long-term home for curated packages is ACC: an ACC collection
could publish a capability such as `markdown.render` whose *implementation*
is a pinned, schema-typed AVM package. The compiler's existing
`discover_capabilities()` scan already feeds `sbom.py`; AVM package entries
would be listed the same way. That makes ACC the **curation layer** (which
packages are trusted enough to wrap) and the AVM the **isolation layer**
(what happens even if curation fails). The two layers reinforce each other,
and `V1-DEFINITION.md`'s "ACC stays outside the stability promise" rule
applies unchanged.

## 4. Runtime model

### 4.1 Per-package sandbox

```text
page (arklight.js)
  |  1. Derive.avm(slugify, "Hello World")  -> enqueue call
  v
AVM orchestrator
  |  2. fetch bytes (same-origin, content-addressed)   [or registry, stage A4]
  |  3. crypto.subtle.digest("SHA-512") == avm.lock integrity ? else refuse
  |  4. new Worker("arklight-avm-worker.js")           [one worker per sandbox]
  v
sandbox (worker)
  |  5. instantiate engine module (JS-engine-in-wasm, or package's own .wasm)
  |  6. load package source into a fresh context, no host imports
  |  7. call entry(input) under memory + deadline limits
  v
AVM orchestrator
  |  8. structured-clone output back, validate against schema
  |  9. worker.terminate(); drop all references          <- "purge"
  v
page: State updated with validated output
```

### 4.2 What the sandbox is *not* given

No DOM, no `fetch`/`XMLHttpRequest`/WebSocket, no storage, no clock or
randomness by default (so identical inputs give identical outputs), no
`eval` of author-supplied strings, no Node built-ins (`fs`, `net`,
`child_process`, ...), and **no lifecycle scripts, ever** (see the threat
model, section 6). Anything a package needs beyond pure computation
means it is out of scope for this feature, not a reason to add a capability.

### 4.3 What "JS is terrible, abstract it away with WASM" does and does not deliver

Worth being straightforward here: for a package written in JavaScript, the
WebAssembly module is a **JavaScript interpreter** (for example QuickJS
compiled to wasm; `quickjs-emscripten` is the well-known packaging and
Figma's plugin sandbox is the well-known precedent), so the package's JS
still runs, just inside a wall. What is abstracted away is JavaScript **from
the ARKlight author and from the ARKlight page**: they never write, load
or see it. Packages that ship their own `.wasm` (Rust/C/Go compiled to
wasm) run directly with no interpreter layer, and would be the ideal
citizens of this design.

## 5. Threads, memory and "purge"

### 5.1 Multithreading, without the usual cost

The tempting reading of "WASM multithreading" is WebAssembly *threads*
(shared linear memory + atomics). That needs `SharedArrayBuffer`, which
browsers only expose to **cross-origin isolated** pages, i.e. documents
served with `Cross-Origin-Opener-Policy: same-origin` and
`Cross-Origin-Embedder-Policy: require-corp` HTTP headers. ARKlight
currently delivers its policy via a `<meta>` tag
(`_render_csp_meta_tag`), and COOP/COEP cannot be set that way; they need
the host to send headers. On top of that, the Chromium issue tracker
records `SharedArrayBuffer` as unavailable in Android WebView even with
correct headers (the exact status should be re-verified against target
WebView versions in `A5`), and `WebViewAssetLoader` is the backbone of
ARKlight's Android backend.

The proposal's answer is that **the isolation model does not need shared
memory**. One worker per sandbox, communicating by `postMessage`, gives:

- real parallelism across packages (a pool of sandboxes),
- no `SharedArrayBuffer`, no COOP/COEP, no header requirements,
- works wherever Workers work, including the WebView backends.

True wasm threads (shared memory inside one sandbox) become an **opt-in
optimization tier** (`A5`) gated on `self.crossOriginIsolated`, with the
single-worker path as the guaranteed fallback. Threading must be a speed-up,
never a requirement.

Related standards context, so nobody bets on the wrong horse:
`wasi-threads` is a legacy proposal superseded by `shared-everything-threads`
(which is still early), and at least one downstream project reports that
Wasmtime removed its `-Sthreads` flag in v47. WASI 0.3.0 shipped on
June 11, 2026, but the browser path here is plain WebAssembly + Workers, not
WASI. The design should not depend on any WASI threading story.

### 5.2 Why "purge" means terminate

WebAssembly linear memory can grow but cannot shrink; the
`memory.discard` instruction that would let a module release pages is still
a proposal. So a sandbox cannot "free" its way back to small. The only
reliable purge is **drop the whole instance**: `worker.terminate()`, null
every reference, let the engine collect. This is actually a good fit for the
one-package-per-sandbox model, which was already shared-nothing. The cost
is re-instantiation on the next call, so the policy question (purge after
*every* call vs after an idle timeout) is an explicit open question (Q3),
not a hidden default.

## 6. Threat model

The 2026 npm landscape is the strongest argument *for* this feature and
also for its constraints. Self-propagating worms (Shai-Hulud lineage) have
repeatedly poisoned popular packages, including a family of caching
libraries on August 4, 2026, where the malicious versions carried valid
GitHub-Actions-signed provenance, and lifecycle scripts
(`preinstall`/`postinstall`) were the main trigger.

| Threat | Mitigation in this design | Residual risk |
|---|---|---|
| Install-time payloads (`preinstall`, `postinstall`, `node-gyp`) | The AVM **never runs lifecycle scripts** and never invokes a package manager; it only loads pinned bytes | None from this vector |
| Poisoned new version | Exact-version pins + sha512 integrity in `avm.lock`; the AVM refuses bytes that do not match; no `latest`/ranges at runtime | **Pinning a version that is already poisoned.** Provenance signatures did not stop the August 2026 case. The sandbox contains the blast radius but cannot make the output *correct* |
| Credential/data theft | Sandbox has no network, storage, DOM or env | A poisoned package can still return misleading *data* |
| Exfiltration via output | Output must satisfy a closed schema; large or unexpected shapes are rejected | Data-shaped covert channels within the schema |
| Runaway CPU/memory | Per-sandbox memory limit and deadline (a real `quickjs-emscripten` feature), plus `worker.terminate()` as the hard backstop | Cost of the wasted work |
| Cross-call contamination (prototype pollution, globals) | Fresh instance per call; nothing survives a purge | Warm-reuse mode (Q3) would weaken this and must be opt-in |
| Dependency confusion / typosquatting | Package names fixed at build time and reviewable in `avm.lock`; never derived from runtime input | Author picking the wrong package |
| Output injection into the page | Output is typed data, never `Html`; rendered via existing text binding | Bugs in the binding layer |
| Sandbox-engine escape (bug in the wasm JS engine or the browser) | Defense in depth: wasm sandbox plus worker isolation plus strict CSP | Non-zero; `quickjs-emscripten` itself documents that it has not been audited |

Registry hosts (verified from a live request for this proposal): the npm
registry served both a package's metadata document and its tarball with
`access-control-allow-origin: *`, so a plain cross-origin `GET` from a page
works, and each version's metadata carries a `dist.integrity` sha512 that
the AVM can check with `SubtleCrypto`. (Only simple `GET`s were tested; a
CORS preflight to the metadata URL returned 404, which does not matter for
simple requests but should be re-checked if custom headers are ever added.)

## 7. Cost to ARKlight's central claim

`WHAT-ARKLIGHT-IS.md` section 7 says ARKlight's bet is a tool that is
"provably incapable of running code it didn't itself generate, anywhere in
its pipeline." An AVM changes that sentence, and honest docs must change
with it:

> ARKlight runs third-party code only inside an opt-in, capability-less
> WebAssembly sandbox, on pinned and hash-verified bytes, and only for
> packages the site declared by name at build time.

That is a real, checkable, *narrower* promise, comparable to how
`Provider` and `script-extension` already qualify the original claim. It
should be listed as an escape-hatch-class feature in the register's section
P ("Security model caveats"), and the experimental banner below is meant to
make sure no site adopts it without seeing that.

Three concrete places where the current implementation bumps against it:

1. **CSP.** `_render_csp_meta_tag` emits `script-src 'self'` with no
   WebAssembly allowance. Compiling or instantiating a wasm module is blocked
   under that policy unless the policy includes `'wasm-unsafe-eval'` (or the
   much broader `'unsafe-eval'`). The AVM would need the narrower keyword
   *only on pages that declare an AVM package*. It permits wasm compilation,
   not JavaScript `eval`, and would be the first per-feature CSP loosening,
   so it needs its own entry in `csp.py`'s "what this module does and does not
   touch" record. Workers should be same-origin files (covered by
   `script-src 'self'` via the `worker-src` fallback), not `blob:` workers,
   which would need `worker-src blob:`.
2. **Trusted Types.** The policy includes `require-trusted-types-for
   'script'`. The `Worker` constructor's script URL is a Trusted Types sink,
   so creating workers under that policy likely needs a registered policy
   even though `csp.py` today registers none. The claim to verify in `A2`.
3. **`connect-src`.** Currently never set, on purpose. Only stage `A4`
   (live registry fetch) needs a network destination; if it lands it should
   add `connect-src` for the declared registry origin only, and never as a
   blanket allowance.

## 8. Targets

| Target | Expected behavior | Notes |
|---|---|---|
| Web (http/https) | Full single-worker-per-sandbox model | Baseline |
| Web with COOP/COEP headers | Optional shared-memory threads tier (`A5`) | Requires a deploy adapter that can send headers; verify against `DEPLOYMENT-CLI.md` |
| PWA | Same, with AVM assets in the service-worker precache | Interacts with issue #3 (PWA inline scripts vs CSP) |
| `.ark` bundle / air-gapped | Works **only** with vendored bytes (`source="bundled"`); live registry fetch is meaningless offline | Core reason bundled is the default |
| `file://` | Expected to be limited (worker and wasm loading from opaque origins are typically restricted) | Verify in `A2`, document like the existing `persist=True` `file://` caveat |
| Android (WebView) | Single-worker path only; threads tier unavailable | `WebViewAssetLoader` serves a stable origin, which helps workers |
| Desktop (WebKit2GTK) | Unverified | Open question Q7 |
| iOS | N/A | Already a documented non-target |

## 9. Explicitly out of scope

- **A Node.js runtime in the browser.** WebContainers is the prior art:
  it runs `npm install` and Node in the page, but needs cross-origin
  isolation, relies on hosted StackBlitz proxies, and requires a commercial
  license for for-profit production use. It contradicts "no server,
  works offline, closed vocabulary, MIT-friendly" and is not a foundation.
- **Emulating Node built-ins**, native addons, or packages that need a
  filesystem, sockets or a child process.
- **Author-typed package names or code at runtime.** Names come from build-time
  declarations only.
- **Floating versions.** No `latest`, no semver ranges reaching the browser.
- **Python in the browser.** Still a stated non-goal.
- **A general fetch primitive.** Stage `A4`'s registry access is scoped to
  package bytes for an already-pinned entry; it is not the
  JS-vocabulary proposal's "client-side data fetch" gap and does not solve it.
- **Compatibility promises.** The feature targets **pure-function packages**
  (formatting, parsing, text and number utilities). A compatibility corpus,
  not a guess, should define the supported set (Q5).

## 10. Staged ladder

Same rung discipline as `PROVIDER-SDK-ADDENDUM.md`: each rung is
independently shippable and the feature stays experimental throughout.

| Rung | What ships | Runtime cost | Done when |
|---|---|---|---|
| **A0** | Experimental gate `avm-sandbox` in `arklight/experimental.py`; `Avm.package`/`Avm.declare` in the IR; closed schema vocabulary; validation; build-time resolver that pins exact version + integrity into `avm.lock`; SBOM entries; lifecycle scripts recorded as *ignored* | None (emits nothing to the browser) | Bad pins and schema errors fail the build; `sbom.txt` lists packages; `avm.lock` is byte-reproducible |
| **A1** | Compile-time folding: a static-input `Derive.avm(...)` is evaluated during `arklight build` and baked in | None | A site with only static inputs ships zero AVM bytes |
| **A2** | Browser orchestrator, single sandbox, bundled source only, engine vendored under `arklight/backend/js/`, CSP `'wasm-unsafe-eval'` for AVM pages only, Trusted Types policy if required | Page-gated | Round-trip works under the real strict CSP; `file://` and Android behavior documented |
| **A3** | Sandbox pool: concurrent sandboxes, queueing, memory/deadline limits, purge on completion, async-derivation semantics (loading/error/stale states) | Page-gated | Limits proven by tests that hang and allocate on purpose |
| **A4** | `source="registry"`: live fetch of the pinned tarball, integrity-verified, scoped `connect-src` | Page-gated | Tampered bytes refused; offline failure is a clear runtime state |
| **A5** | Optional wasm-threads tier when `crossOriginIsolated`; deploy adapter emits isolation headers where the host supports it | Page-gated | Same outputs as the single-worker path, measurably faster; fallback proven |
| **A6** | Backend matrix (PWA precache, `.ark`, Android, Desktop) and docs graduation | None new | Matrix in section 8 is verified, not assumed |

## 11. Experimental-gate entry (draft)

Following the three-step process in `EXPERIMENTAL-APIS.md`:

- id: `avm-sandbox`
- inline note: *"This site runs third-party package code inside a WebAssembly
  sandbox. ARKlight does not audit the package or guarantee its output."*
- detail lines: what is pinned and hashed; what the sandbox withholds; that
  a poisoned pinned version can still return wrong data; that AVM pages relax
  CSP to allow WebAssembly compilation (not JavaScript `eval`).
- legacy note: n/a at first.
- `upstream_candidate=True`: heavy reliance suggests a missing ACC
  capability, which is exactly the "open a PR against ACC" nudge the
  heavy-reliance heuristic exists for.

## 12. Open questions

1. **Async in a synchronous reactive core.** `Computed`/`Derive.*` are
   synchronous today. An AVM call is not. Does the result flow through a new
   async-derivation primitive, a `Watch`-style action, or a `Show`-gated
   loading state? (Issue register #12/#13 already flag the rescan cost of
   state updates.)
2. **What does "per instance" mean?** Per call, per page load, or per
   package per session? This proposal assumes per call with purge after
   completion.
3. **Purge policy.** Purge every call (strongest isolation, re-instantiation
   cost) vs idle-timeout warm reuse (faster, weaker isolation). Should warm
   reuse exist at all?
4. **Engine choice and payload.** A JS-in-wasm interpreter versus a package's
   own wasm versus both. Measure size and startup in `A2` before committing.
5. **Compatibility corpus.** Which packages must work at `A2` for the
   feature to be worth shipping?
6. **Trusted Types and workers.** Confirm the `Worker` sink behavior and what
   default policy, if any, is acceptable.
7. **WebKit2GTK.** Does the Desktop backend's WebView support workers and
   wasm the way the model needs?
8. **`file://` and `.ark` viewers.** Confirm behavior in both.
9. **Naming.** "AVM" is already established shorthand elsewhere
   (the Algorand Virtual Machine, Adobe's ActionScript VM). Keep it, or pick
   something that will not collide in search? `Provider` was renamed away from
   "backend" for exactly this kind of reason.
10. **Where this sits in ACC's five-stage ladder.** Should the first real
    consumers be ACC capabilities only, with direct site-level `Avm.package`
    held back until a curated set exists?

## 13. Relationship to other proposals

- `PROVIDER-SDK-PROPOSAL.md`: external *services*; the AVM has no network.
  A5/A4's registry access does not make the AVM a Provider.
- `PLATFORM-API-IR-PROPOSAL.md`: device capabilities; the AVM has none by
  design. Both share the "compiler owns the interface, runtime owns the
  implementation" shape.
- `JS-VOCABULARY-EXPANSION-PROPOSAL.md`: adds vocabulary the compiler
  understands; the AVM is the deliberate alternative for logic that will never
  be vocabulary. Pure math/string derivations should stay `Derive.*`.
- `USER-DEFINED-ERROR-HANDLING-PROPOSAL.md`: an AVM failure (timeout, bad
  output, refused hash) should surface through the closed error vocabulary
  and the `0.06505` `arkReportError` sink, not a new channel.
- `APP-SHELL-CAPABILITY-PROPOSAL.md`: workers do not survive navigations;
  see `app_shell=True` before assuming warm sandboxes persist.

## 14. Filing checklist (per `docs/README.md`'s one-pass rule)

On acceptance or on filing, the same change should touch:

1. This file, `docs/Proposals/AVM-WASM-SANDBOX-PROPOSAL.md`, with its Status line.
2. Its row in `docs/Proposals/README.md`'s Index.
3. Its row in `docs/README.md`'s Folder Guide for `docs/Proposals/`.
4. If accepted: `docs/Implementation/AVM-ADDENDUM.md`, its rows in
   `docs/Implementation/README.md` and the Folder Guide, the
   `ARCHITECTURE.md` Milestones row, the `PROGRESS.md` Snapshot row, and the
   `EXPERIMENTAL-APIS.md` entry.

Suggested Index row text:

> | [`AVM-WASM-SANDBOX-PROPOSAL.md`](AVM-WASM-SANDBOX-PROPOSAL.md) | Proposal for the AVM, an experimental orchestrator that runs pinned, hash-verified third-party (npm) packages as pure input->output functions, one per WebAssembly sandbox, each purged after use. Closed-vocabulary at the authoring surface (`Avm.package`, `Derive.avm`), compile-time pinning into `avm.lock`, static-input calls folded at build time, no network/DOM/lifecycle scripts inside the sandbox. Shared-nothing parallelism via one worker per sandbox (no `SharedArrayBuffer` required); optional wasm-threads tier behind cross-origin isolation. A seven-rung ladder `A0`-`A6`. **Not accepted.** |

## 15. References

Primary sources consulted while writing this (external claims above rest on
these; repo claims rest on the files named inline):

- Cross-origin isolation, COOP/COEP and `SharedArrayBuffer`:
  https://web.dev/articles/coop-coep
- Chrome's Document Isolation Policy (per-frame isolation, Chrome 137):
  https://developer.chrome.com/blog/document-isolation-policy
- Chromium issue on `SharedArrayBuffer` in Android WebView:
  https://issues.chromium.org/issues/40914606
- WebAssembly CSP proposal (`wasm-unsafe-eval`):
  https://github.com/WebAssembly/content-security-policy/blob/main/proposals/CSP.md
- WebAssembly memory-control and `memory.discard`:
  https://github.com/WebAssembly/memory-control/blob/main/proposals/memory-control/Overview.md
  and `.../discard.md`
- `wasi-threads` (legacy status): https://github.com/WebAssembly/wasi-threads
- WASI 0.3 release notes: https://wasi.dev/releases/wasi-p3
- Wasmer JS SDK and cross-origin isolation:
  https://docs.wasmer.io/sdk/wasmer-js/explainers/troubleshooting
- WebContainers (isolation requirement, hosted proxies, licensing):
  https://www.npmjs.com/package/@webcontainer/api and
  https://developer.stackblitz.com/guides/user-guide/general-faqs
- `quickjs-emscripten` (JS-in-wasm sandbox, limits, audit disclaimer):
  https://github.com/justjake/quickjs-emscripten
- npm supply-chain incidents, 2026: Datadog Security Labs on the
  August 4, 2026 "ChainDrop" worm
  (https://securitylabs.datadoghq.com/articles/npm-worm-compromises-popular-npm-packages/),
  Aikido on the keyv compromise and provenance
  (https://www.aikido.dev/blog/keyv-and-friends-compromised-in-npm-supply-chain-attack),
  Snyk on the June 2026 node-gyp wave
  (https://snyk.io/blog/node-gyp-supply-chain-compromise-self-propagating-npm-worm-binding-gyp/).
- npm registry CORS and `dist.integrity`: verified directly against
  `registry.npmjs.org` while drafting; see section 6.
