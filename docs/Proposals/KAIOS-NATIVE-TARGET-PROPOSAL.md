# Proposal: KaiOS as a Target-Specialized Backend (Not a Packager)

## Status

**Proposed. Not accepted, not staged, not scheduled against a version.**
Filed against `alpha` @ `08f30f6` (`Working on v0.067`; `pyproject.toml`
still reads `0.066`).

Every claim about ARKlight below was read out of source at that commit.
Claims about KaiOS/Gecko come from
`docs/Far Future Concern/kaios-app-design-doc.md` plus browser
feature-shipping versions recalled from MDN/caniuse data, and are marked
**[verify]** where a decision depends on them. **Nothing was built or run
to produce this document** -- see "Method and limits".

If accepted, this supersedes the *packaging-only* framing in
`docs/Far Future Concern/KAIOS-BACKEND-IMPLEMENTATION.md` §§1-3 and §7.
It does **not** supersede that document's manifest design, its ZIP-reuse
prerequisite (§5), its staged CLI ladder, or its out-of-scope list (§6).

## TL;DR

- KaiOS needs no host shell. There is no WebView to write: Gecko *is* the
  app runtime, and a packaged app is a ZIP with a `manifest.webapp`. The
  existing doc is right about this.
- But the Web build cannot be zipped and shipped. Three independent
  things break it: the **input model** (D-pad and softkeys, no pointer),
  the **engine floor** (KaiOS 2.5 = Gecko 48), and **layout CSS** that
  assumes grid, flex `gap`, `min()` and `clamp()`.
- The vendored HTMX 2.0.10 contains `?.` and `??`. HTMX is concatenated
  into the same file as ARKlight's own runtime, so on Gecko 48 one
  unsupported token is a `SyntaxError` for the **entire** `arklight.js`.
  ARKlight's own templates are ES5 and are not the problem.
- Proposal: a **target profile**. HTML and assets carry over with a small
  mechanical delta; CSS is generated through a Gecko-48 profile; **JS is
  generated fresh from the IR** by a KaiOS JS backend that reuses the
  existing registry templates, ships no HTMX, and adds a compile-time
  focus table, a softkey table and a Back-key handler.
- Navigation stays **ordinary multi-page** (per
  `SYSTEM-DESIGN-AGREEMENTS.md` §3). A single-document shell is a gated
  option, earned only by on-device measurement.
- A CDN is a **distribution channel for the zip**, not a hosted
  `launch_path`.
- No Babel, no core-js, no polyfill layer: the code generator emits ES5
  directly.

## 1. What is being proposed

### 1.1 The split

| Artifact | KaiOS treatment |
| --- | --- |
| HTML pages | Carried over from `HTMLBackend` output with a mechanical delta: no `hx-*` attributes, softkey chrome (`#top-bar`/`#bottom-bar` regions), focus-order attributes. |
| Assets | Copied. |
| CSS | **Generated** through a Gecko-48 profile (token overrides and fallback rules). Not copied verbatim. |
| JS | **Generated fresh from the IR.** Registry templates reused; HTMX and app-shell wiring dropped; KaiOS input layer added. |
| `manifest.webapp` | Generated. Permissions derived from the IR (§3.7). |
| ZIP | Reuse of the `arklight.packer` ZIP path (prerequisite refactor already flagged in the existing doc §5). |

### 1.2 Why this is a backend, not a packer

The existing doc (§7) places KaiOS in `arklight/packer/kaios.py` because
it "only ever reads an already-built output directory and never touches
parser/ir/backend internals." That was coherent while the JS was
`arklight.js` reused as-is. Generating JS per target needs `WebsiteIR`,
which a packer never receives. Under `Backend`'s own contract
(`arklight/backend/base.py`), a target that consumes IR is a `Backend`
participating in `backends=[...]`.

The ZIP step stays a packager. The codegen does not.

## 2. Evidence

All rows read from source at `08f30f6`. Firefox versions are from memory
of compatibility data **[verify]**; Gecko 48 = KaiOS 2.5 per the design
doc §0.

### 2.1 What breaks if the Web build is zipped, on a Gecko 48 floor

| Feature | First in Firefox | Where it is in the repo | Failure on Gecko 48 |
| --- | --- | --- | --- |
| `?.` optional chaining | 74 | vendored HTMX 2.0.10 (`p?.swapDelay`), `arklight/backend/js/htmx.py` | `SyntaxError`: **whole bundle** fails to parse |
| `??` nullish coalescing | 72 | same file (`s.push??"true"`) | same |
| `Object.fromEntries` | 63 | same file (`toJSON` path) | `TypeError` at call, that path only |
| `trimStart()` / `trimEnd()` | 61 | `derivations/trim_start.py`, `trim_end.py` | `TypeError` at call, those derivations only |
| `display: grid` | 52 | `base_stylesheet.py` (grid layout primitive) | declaration dropped; falls back to block flow |
| `gap` on flex containers | 63 | `base_stylesheet.py` (cluster, sidebar, switcher, reel, others) | declaration dropped; spacing vanishes |
| `min()` / `clamp()` | 75 | `design_tokens.py` (`--ark-max-width: min(100% - 3rem, 75rem)`), `base_stylesheet.py` (fluid type, `max-width`) | `var()` value invalid at computed-value time; property becomes `unset` |

Two mechanisms are worth stating precisely, because they set the design.

**Parse failure is total.** `_build_runtime_js` in
`arklight/backend/js/render.py` appends `HTMX_JS` to `parts` ahead of
ARKlight's own code and emits one file (`SCRIPT_PATH`). SpiderMonkey
parses the whole script before running any of it. A single unsupported
token therefore removes ARKlight's own ES5 runtime along with HTMX, so
the failure mode is "the page is inert", not "one feature is missing".
HTMX is included whenever `needs_htmx = has_state or ir.app_shell`.

**`var()` has no fallback-by-cascade.** A declaration such as
`max-width: 75rem; max-width: var(--ark-max-width);` does not fall back
to `75rem` on an engine that cannot parse the resolved `min(...)`. Custom
property values are substituted at computed-value time and an invalid
result makes the property `unset`, not "use the previous declaration".
The profile must therefore substitute **token values** at compile time,
not just add fallback declarations.

### 2.2 What does not break

- ARKlight's own runtime templates are written in ES5 style (`var`,
  `function`; no arrow functions, no `async`/`await`, no classes, no
  optional chaining).
- The vendored snabbdom core (`arklight/backend/js/vdom.py`) is
  `var`-only.
- `IntersectionObserver` (Firefox 55) is behind an `in window` guard.
  See §3.6 for the one consequence.
- `padStart`/`padEnd` (Firefox 48) sit exactly at the floor **[verify]**.
- `base_stylesheet.py` has no `order:`, no `flex-direction`, and no
  `position: fixed|absolute`. That matters for the focus-order argument
  in §3.1. Author CSS in `custom_styles` can still reorder.

### 2.3 What "no choice" actually means

| Driver | Forced at which floor? |
| --- | --- |
| Input model (`keydown` on `event.key`: `SoftLeft`, `SoftRight`, `Enter`, arrows; no pointer) | **Every** floor. The Web build's delegated `click` wiring has no way to be reached. |
| ES5 / API allowlist | KaiOS 2.5 (Gecko 48) only. |
| CSS profile | KaiOS 2.5 only; also useful for the 240x320-class viewport at any floor. |

If the maintainer's floor is a newer KaiOS, the engine constraint mostly
disappears and the input layer alone still requires target-specific JS.

## 3. Design

Ordered by the Architecture Decision Rule in
`SYSTEM-DESIGN-AGREEMENTS.md` §16: compiler, then target platform, then
minimal generated bridge, then runtime abstraction.

### 3.1 Compiler first: a static focus table

Both reference apps in the design doc (§12) implement D-pad focus at
runtime. `sample-vanilla` walks `[nav-selectable]` nodes; `o.map` owns a
handler per screen. ARKlight knows more than either does at compile time.

For each page the compiler walks interactive components (links, buttons,
inputs, `Action.*` triggers) in **IR order** and emits:

- a per-element order attribute (e.g. `data-ark-nav="0..N-1"`), and
- a count `N` and, if needed, a row/column table for `Row`/`Cluster`
  primitives derived from the IR.

The runtime then holds a cursor index. `ArrowDown`/`ArrowUp` change one
integer and swap a class on two elements. There is **no
`getBoundingClientRect`, no geometry, no spatial search.**

Why this matters mechanically: a runtime spatial-navigation pass reads
layout per candidate, and any layout read after a DOM or style mutation
forces a synchronous style-and-layout flush. On a Cortex-A7-class part
that is on the critical path of every keypress (design doc §1, §3). A
compile-time table makes the per-keypress cost O(1) and layout-free.

IR order is trustworthy as visual order only while nothing reorders
visually. `base_stylesheet.py` does not (§2.2). A page using author CSS
that reorders (`order:`, `*-reverse`) needs a compile-time diagnostic or a
documented caveat.

One accepted cost: when the newly focused element is off-screen, scrolling
it into view forces a layout. That is one flush per off-screen focus move,
not per keypress. Viewport-sized paging (no scrolling) is an option, not
assumed.

### 3.2 Target platform first: what Gecko already gives

- DOM focus, `focus()`/`blur()` on inputs, `keydown` with `event.key`.
- The manifest `csp` field. ARKlight's "no inline script, no eval" output
  already satisfies a strict CSP by construction (existing doc §3,
  first bullet, which remains correct).
- Session history, including `history.state`.

No platform-native D-pad traversal for web content in an app is described
in the design doc; both reference apps implement their own.

### 3.3 Minimal generated bridge

Three small pieces, all in the generated file, none a reusable framework:

1. **Key dispatcher.** One document-level `keydown` listener per page,
   switching on `event.key`: arrows move the cursor, `Enter` calls
   `el.click()` on the focused element, softkeys map to per-page handlers.
   Because `Enter` becomes a synthetic click, it reuses the existing
   delegated click dispatch (`runtime/dispatch.py`) unchanged, so
   `Action.*` and named behaviors need no KaiOS-specific wiring.
2. **Softkey painter.** A static table indexed by focus position,
   e.g. `SK[i] = ["Back", "Select", ""]`, written into three
   `textContent` slots. No allocation per key event.
3. **Back key.** The hardware Back key arrives as `Backspace` **[verify]**.
   Handler: `preventDefault`, then `history.back()`, or `window.close()` at
   the root. Do not intercept when an `<input>` holds text.

Default softkey policy is derived, not authored: left = "Back" on
non-root pages, center = the focused control's label, right = empty. An
author-facing override would be new IR vocabulary; see Open question 2.

### 3.4 JS profile: how the bundle is assembled

Today `_build_runtime_js(ir)` is one long assembler. This proposal
requires it to become `build_runtime_js(ir, profile)`, where the Web
profile output is **byte-identical to today** (same discipline as the
`refactor-0` "pure move, no JS output change" stage; existing tests lock
it).

The KaiOS profile differs as follows.

| Part | Web profile (unchanged) | KaiOS profile |
| --- | --- | --- |
| HTMX | when `has_state or app_shell` | **never** |
| `Site(app_shell=True)` | `hx-boost` | compile-time diagnostic; navigation is multi-page |
| `Action.*` modifiers (`debounce`, `throttle`, `once`, `stop`) | `hx-trigger` tokens | direct implementation or compile-time rejection (see Stage 0) |
| snabbdom | state pages | kept for now; ES5-safe. Replacing it with direct binding writes is an optimization to be earned by measurement, per the compiler-first rule. |
| `trimStart`/`trimEnd` | ES2019 methods | `replace(/^\s+/, "")` / `replace(/\s+$/, "")` |
| Input layer | click only | + key dispatcher, focus table, softkeys, Back key |
| Registry templates (actions, derivations, behaviors, state) | as-is | as-is, subject to the API lint below |

**Enforcement, not intent.** The KaiOS profile ships with a test that
fails the build when the emitted bundle contains any token or API outside
an allowlist: `=>`, `?.`, `??`, backticks, `class`, `async`, spread, and
banned API names (`trimStart`, `trimEnd`, `Object.fromEntries`,
`replaceAll`, `.at(`, `.flat(`, and so on). It is a lexical check in
Python, so it needs no Node toolchain. A real Gecko-era parser check is
Stage 0's job. There is no transpiler: the generator is the lowering.

**One open dependency.** After `htmx-5`, `runtime/dispatch.py` already
parses modifier tokens itself at dispatch time (`parseTriggerModifiers`).
It is unclear how much of HTMX remains load-bearing for a non-boosted
state page even on the Web target. Stage 0 answers it. If the answer is
"vestigial", dropping HTMX there is a separate Web-side win.

### 3.5 Navigation: multi-page by default

`SYSTEM-DESIGN-AGREEMENTS.md` §3 says ARKlight does not need a
client-side router to decide which built HTML file matches a URL. A
KaiOS shell that mounts and unmounts screens is a client-side router. The
proposal therefore defaults to **ordinary multi-page navigation** between
the packaged HTML files.

Consequences, both directions:

- **Leak class removed by construction.** Design doc §4's central hazard
  (a `keydown` listener without symmetric teardown) exists only when one
  document outlives its screens. Under multi-page navigation the engine
  tears the document down, and the listener with it. The teardown
  discipline is done by the platform.
- **Cost accepted.** Each navigation re-parses HTML, CSS and JS and
  re-lays-out. Not measured; see Stage 0.
- **Focus persistence.** Before navigating, `history.replaceState` records
  the focus index in the current session-history entry; on load (including
  Back), the page reads `history.state` and restores it. No storage I/O,
  no `sessionStorage` write.

A single-document shell is **not** rejected forever. It is Stage 6, gated
on Stage 0/2 measurements failing a budget, and it must come as its own
proposal reconciling with agreements §3, not as an implementation detail
of this one.

### 3.6 CSS profile

- **Token overrides at compile time**, not fallback declarations (§2.1,
  `var()` mechanism): e.g. `--ark-max-width` resolves to a plain length or
  percentage in the Gecko-48 profile.
- **Primitive substitutions**: grid layout becomes wrapping flex with
  margin-based spacing (owl-selector style) in place of `gap`; fluid
  `clamp()` type becomes a fixed size chosen for the device profile.
- **Device scale**: base type and spacing tuned for a small fixed viewport
  (most 2.5-era devices are 240x320 **[verify]**). Values are measured on
  device, not guessed here.
- **Reveal fallback**: `wireReveal` intentionally leaves elements as
  authored when `IntersectionObserver` is absent. Depending on the
  author's CSS, an element that stays hidden until `is-visible` is added
  would never appear on 2.5. The KaiOS profile should add the class at
  load (scroll-triggered reveal has little value on a keypad device).
- **Enforcement**: a lexical lint of emitted CSS for post-Gecko-48
  constructs, mirroring the JS lint in §3.4.

### 3.7 Manifest and permissions are derived, not authored

The existing doc §4 ships `permissions: {}` as "the honest reflection" of
an IR with no permission vocabulary. Since `v0.065` that is no longer
true: `arklight/ir/platform_api.py` holds a capability registry with
per-capability permissions and a per-backend support table.
`BACKEND_PLATFORM_API_SUPPORT` currently lists `web` as non-empty and
`android`/`desktop` as empty "on purpose... native implementations are
earned".

Proposal:

- Register `"kaios"` in that table, **empty** at first, on the same rule.
- A KaiOS **capability -> manifest permission** mapping table lives with
  the KaiOS backend. Web permission names and KaiOS manifest names are not
  the same vocabulary.
- The compiler emits exactly the permissions the IR implies. `{}` when the
  IR implies none. The author never writes a permissions block.
- Two capabilities are natural first earners: `Action.geolocate` (already
  in `arklight/backend/js/actions/geolocate.py`, needs the geolocation
  permission) and a wake lock. Wake lock is **not** in the registry today
  and would need its own accepted capability proposal. The design doc §13
  documents the two-tier `requestWakeLock` / `mozPower` detection and that
  `power` and `wake-lock` permissions must be declared **[verify]**.

`type: "privileged"`, the 56/112 icon sizes, the generated `csp`, and the
"warn, do not silently omit" icon rule from the existing doc §4 are
retained. `Site` has no `icon=` prop today.

### 3.8 The CDN

"CDN hosts it and the phone runs it" can mean three different things.

1. **Hosted app (`launch_path` pointing at the CDN).** Not proposed as a
   default. In the B2G lineage a hosted app is unprivileged (`web` type)
   **[verify]**, so the permission set in §3.7 is unavailable. Every cold
   start pays DNS, TCP and TLS round trips on 2G/3G before first paint,
   where a packaged app reads local flash. It violates the offline-first
   rule in design doc §6b. Old firmware's frozen root-CA store is an
   additional risk worth checking **[verify]**.
2. **CDN as distribution and update channel for the packaged zip.**
   Proposed. Versioned, content-hashed filenames; update policy out of
   scope for Stage 1.
3. **CDN as a data/asset source fetched by a packaged app at runtime.**
   Deferred to Stage 5. It needs either permissive CORS on the CDN
   (`Access-Control-Allow-Origin`) or the `systemXHR` permission with
   `mozSystem` XHR; plain `fetch` does not bypass CORS. Fetches must be
   explicit and user-triggered, with a disk-backed cache, per design doc
   §6b and §2. This needs IR vocabulary that does not exist and is not
   invented here.

### 3.9 Where it lives

```
arklight/backend/kaios/
    __init__.py
    profile.py      # js_dialect, css profile, manifest schema, viewport
    js.py           # KaiOSJSBackend: build_runtime_js(ir, kaios_profile)
    css.py          # profile-aware token/primitive overrides
    manifest.py     # capability -> permission mapping, manifest.webapp
    input_layer.py  # key dispatcher / softkey / back-key templates
```

Pipeline for `arklight kaios build`:

```
build(entry, backends=[HTMLBackend(profile), CSSBackend(profile),
                       KaiOSJSBackend()])
  -> KaiOSBackend.postprocess()   # manifest + chrome
  -> packer ZIP step              # binary assets and icons
```

`Backend.render()` returns `dict[str, str]` and never touches the
filesystem, so binary assets and icons are copied by the packer step, not
by the backend.

## 4. Fit with the standing agreements

| Agreement (`SYSTEM-DESIGN-AGREEMENTS.md`) | How this proposal complies |
| --- | --- |
| §1 Compiler owns what it can know | Focus table, softkey table, permissions and token values all resolved at compile time. |
| §3 Do not reimplement the target runtime | Multi-page navigation; no router. The router is a separately-proposed, measurement-gated option. |
| §4 Compiler may specialize for the target | The premise of the proposal. |
| §6 One source model, multiple targets | Same authoring source; only generated output diverges. |
| §12-13 Targets may diverge; no lowest common denominator | Web output stays unchanged; KaiOS output is specialized. |
| §16 Decision rule | §3 is organized in that order. |
| §17 Anti-pattern: framework feature parity | The input layer is a table and a dispatcher, not a spatial-navigation library. |

## 5. Stage ladder

**Stage 0 -- Verify. No behavior change.**
Build `examples/hello_site`, a `State`/`Computed` site, and an
`app_shell=True` site on `alpha`. Run the emitted JS and CSS through an
ES5-era parser and the KaiOS simulator, then on at least one real 2.5
device. Record: does each bundle parse, does the CSS degrade as predicted
in §2.1, what is a page transition's cost, and app-process memory (the
simulator does not reproduce the memory ceiling, design doc §15).
Determine what HTMX still does for state pages after `htmx-5`.
*Exit:* §2.1 is replaced by measured facts; the floor is decided
(Open question 1).

**Stage 1 -- Profile plumbing; Web output byte-identical.**
Extract `build_runtime_js(ir, profile)`. Add the ES5 KaiOS bundle without
HTMX, the JS lint test, and `arklight kaios scaffold|build` producing a
valid ZIP with a manifest (after the ZIP-primitive refactor).
*Exit:* a static site, and a `State` + `Computed` site, run on Gecko 48.

**Stage 2 -- Input layer.**
Focus table, key dispatcher, `Enter` -> click, Back key, softkey chrome,
focus restore via `history.state`.
*Exit:* `hello_site` is fully drivable by D-pad on device; no
`getBoundingClientRect` in emitted JS; exactly one document-level
`keydown` listener per page.

**Stage 3 -- CSS profile.**
Token overrides, primitive substitutions, device scale, reveal fallback,
CSS lint.
*Exit:* every layout primitive renders acceptably on device.

**Stage 4 -- Earned capabilities.**
First `BACKEND_PLATFORM_API_SUPPORT["kaios"]` entries; capability ->
permission mapping; wake lock via its own capability proposal.

**Stage 5 -- gated: CDN runtime fetch.** Needs new IR vocabulary and its
own proposal.

**Stage 6 -- gated: single-document shell.** Only if Stage 0/2
measurements fail a budget; its own proposal reconciling with agreements
§3.

## 6. Non-goals

- Hosted-app mode as a default (§3.8).
- Babel, core-js, or any runtime polyfill layer. Codegen emits ES5.
- A general "profile system" for other targets. The profile exists for
  KaiOS and is deliberately small.
- A spatial-navigation library or any runtime geometry.
- `mozActivity`, certified-app signing, store submission, carrier tooling
  (unchanged from the existing doc §6).
- Changing Web output in any way.
- Windows Phone (separate doc).

## 7. Risks

- **Assembler fork drift.** Two JS assemblers would diverge. Mitigation:
  one assembler with a profile parameter, and byte-identical Web output
  locked by tests.
- **Static order vs. visual order.** Reordering author CSS breaks the
  focus table. Mitigation: diagnostic (§3.1).
- **Dynamic lists.** A page with `Repeat` changes its focusable count at
  runtime; the static count is then wrong. Mitigation: re-index only on
  pages that contain `Repeat`, scoped to that change.
- **Text entry.** Multitap/T9 input and Back-key semantics with a
  non-empty `<input>` need on-device testing.
- **Version-number error.** The Firefox versions in §2.1 are from memory.
  Mitigation: Stage 0 uses a real parser, not a table.
- **Floor fragmentation.** 2.5 and 3.x differ in manifest schema
  (`manifest.webapp` vs `manifest.webmanifest` with `b2g_features`); the
  existing doc's "maintain both, do not unify" advice stands.
- **Memory.** Only real hardware shows it (design doc §2, §15).

## 8. Open questions

1. **Floor.** KaiOS 2.5 only, 3.x only, or both via a profile? This
   decides whether the ES5 and CSS work is needed at all.
2. **Softkey authoring.** Derive only, or add optional props? A prop is
   new IR vocabulary and must justify itself against agreements §8.
3. **Transition budget.** What page-transition time makes multi-page
   navigation unacceptable, and therefore triggers Stage 6? Suggest
   measuring against the device's own app-open time as the reference.
4. **HTMX after `htmx-5`.** Is it still load-bearing for non-boosted state
   pages? If not, drop it on Web too (separate change).
5. **`trimStart`/`trimEnd` globally.** Switching the templates to
   `replace(...)` costs nothing but changes Web output, which this
   proposal otherwise forbids.
6. **`Site(icon=)` and a version prop.** Needed for a non-warning
   manifest.
7. **`app_shell=True` under the KaiOS target.** Error or warning?
8. **Launcher name.** Truncation rule for `Site.title` (existing doc §4
   cites a ~20-character launcher limit **[verify]**).

## 9. Corrections required elsewhere if this is accepted

| Document | Correction |
| --- | --- |
| `KAIOS-BACKEND-IMPLEMENTATION.md` §3, first and third bullets | "Already runs on Gecko 48 without transformation" is false for any build that includes HTMX (state or `app_shell`). |
| same, §2 and §7 | The "easy, packager-only" framing and the `arklight/packer/` placement no longer hold for generated JS. |
| same, §4 | The `permissions: {}` default predates the platform API registry. |
| `JS-BACKEND-REFACTOR-PLAN.md`, "Cross-cutting risk" | HTMX 2.0.10 vs Gecko 48 is an open item there; Stage 0 closes it, and the token scan already indicates incompatibility. |
| `PROGRESS.md` (KaiOS entry), `docs/README.md`, `Far Future Concern/README.md` | Index and status lines. |

## 10. Method and limits

This is read-only static analysis of a clone of `alpha` @ `08f30f6`:
grep over the JS/CSS backend sources, and a regex scan of the `HTMX_JS`
constant in `arklight/backend/js/htmx.py`. Specifically:

- **Not built or executed.** `pip install -e .` runs a PEP 517 backend
  that gates source builds on license acceptance; that acceptance was not
  made on the maintainer's behalf, so no site was compiled and no emitted
  file was inspected. Findings about the *generated* output are inferred
  from the templates.
- **Feature versions** (§2.1) are recalled, not re-fetched.
- **KaiOS 3.x/4.x Gecko versions** are not asserted; the design doc gives
  Gecko 123 for KaiOS 4.0 and only "newer" for 3.0.
- **A grep miss is not proof of absence.** Templates are assembled from
  Python strings; Stage 0 replaces inference with parsing.

## 11. Removal and graduation

Deleting this proposal is a supported outcome. If accepted, Stage 0's
measured results replace §2.1 in place, the doc graduates out of
`docs/Proposals/` into an implementation doc beside the Android and
Desktop ones, and the KaiOS entries in `docs/Far Future Concern/` are
cleared per that folder's own rule.
