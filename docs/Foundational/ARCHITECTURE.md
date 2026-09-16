# ARKlight Architecture

## Vision

**ARKlight is a Python-first compiler for building static websites where
developers work with a structured component API, while the output remains
ordinary, dependency-free HTML.**

Write your site in Python. ARKlight compiles it to standard HTML with CSS and
vanilla JavaScript. The browser never executes Python — you get predictable,
inspectable, portable output that works anywhere static files are hosted.

Python ergonomics at authorship time. Clean web artifacts at deployment time.
No Python runtime in production. No framework bloat.

## Core Principles

- Flask-like simplicity.
- Functions over classes.
- One obvious way.
- Beginner friendly.
- AI-friendly API.
- Backend independent compiler.
- Configurable only where it needs to be -- an internal value gets a
  user-facing override (`Site(...)`/`Page(...)` kwarg, `arklight build`
  flag) only when a real site could want it different *and* nothing
  already reaches it; otherwise it stays a plain internal constant. See
  `docs/CONFIGURABILITY.md` for the full rule and worked examples.

## Compiler Pipeline

```
Python Source
    |
    v
Python AST
    |
    v
ARK AST
    |
    v
Normalization
    |
    v
Validation
    |
    v
Website IR
    |
    v
Backend Interface
    |
    v
HTML Backend
    |
    v
index.html
```

## Website IR

Each node contains:
- type
- props
- children

The IR models website intent rather than HTML.

## Backend Interface

Current:
- HTML (`arklight/backend/html/`) -- a service-oriented module split
  (mirroring the CSS backend below) is designed and Stages 1-2 of 6 are
  now implemented (`tag_map.py`, `routing.py`), see
  `docs/Backends/HTML-BACKEND-REFACTOR.md`.
- CSS (`arklight/backend/css/`) -- already split into
  `base_stylesheet.py`/`design_tokens.py`/`custom_styles.py`/
  `render.py`, see `docs/CSS-BACKEND-REFACTOR.md`.
- JavaScript (`arklight/backend/js/`)

Future:
- Vue
- Svelte
- Android (`arklight android` -- packaging backend, not a template/
  codegen backend like Vue/Svelte: wraps an existing `build-dir` into
  a native Android project via `androidx.webkit.WebViewAssetLoader`,
  same "reads already-built output, never touches the
  parser/ir/backend internals" shape as `arklight.packer`. Evolves the
  existing `ARKlight-Viewer-for-Android-Devices` app into this
  backend's runtime rather than generating an Android project from
  scratch. See `docs/DESIGN-NOTES.md` ("v0.0438: Android backend") for
  the design and `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md` for
  the staged implementation order -- Stage 0 in progress.)

## Public API

Everything is a function.

Children are positional arguments.

Properties are keyword arguments.

Components are Python functions.

```python
from arklight import *

site = Site()

@site.page("/")
def home():
    return Page(
        Heading("ARKlight"),
        Text("Build websites with Python."),
        Button("Get Started")
    )
```

## Repository

```
arklight-framework/
  arklight/
    compiler/
    parser/
    ast/
    ir/
    backend/
      html/
    cli/
    config.py         `arklight.config.py` project-config loader
  examples/
  tests/
  docs/
```

## Milestones

This is the canonical roadmap -- `README.md` and `PROGRESS.md` link
here rather than keeping their own copies. Status: DONE / PLANNED.

| Version | What | Status |
|---|---|---|
| v0.001 | Python → HTML | DONE |
| v0.002 | CSS (default stylesheet) | DONE |
| v0.003 | JavaScript helpers, incl. two vocabulary extension addenda (semantic layout, forms, tables, media, intrinsic responsive layout utilities, `copy`/`dismiss` behaviors) | DONE |
| v0.0035 | Stateful JS -- registry-driven behaviors + actions; `State`/`Bind`/`Action.*` | DONE |
| v0.004a | CLI scaffolding (`arklight new <name> --template simple\|production`) | DONE |
| v0.036 | ARK Bundle spec v1 -- single-file `.ark` packaging of a site's build output (`arklight pack`) | DONE |
| v0.037 | Sealed ARK Bundles -- archive half encrypted by default, `assets/` + all files carried over, `arklight unpack` | DONE |
| v0.041 | CLI/pipeline/JS runtime error-handling hardening + stateful JS vocabulary addenda I & II (`Action.decrement/reset/append/remove`) | DONE |
| v0.042 | Extra CSS features -- `Site.style(name, rules)` custom CSS class authoring, `arklight search <name>` component-schema lookup, `arklight --help`/bare `arklight` help text | DONE |
| v0.043 | Optional `<head>` metadata props (`description`/`favicon`/`og_*` on `Page(...)`) + `Backend.postprocess(...)` extension hook | DONE |
| v0.048 | CSS `@media` queries + structured `<head>`/`<header>` extension -- Stage A (`meta`/`links` on `Page(...)`, DONE) + Stage B (`responsive_style` + `@media` compilation, DONE); see `docs/DESIGN-NOTES.md` | DONE |
| v0.054 | JS backend capability expansion -- computed/derived state, watch effects, two-way input binding, per-item list rendering, conditional show/hide, event modifiers, reactive class binding, all via closed registries (no arbitrary JS/eval) -- design complete in `docs/DESIGN-NOTES.md`; all seven feeding capabilities landed as `vdom-1` through `vdom-7`, and `vdom-8` (the last stage, `localStorage` persistence) has now landed too | DONE |
| vdom-staging | Reactive-core vdom staging, 8 stages feeding `v0.054`, all DONE: vendored snabbdom bare core swapped into `State`'s re-render pass (Stage 1); reactive class binding via `Bind.when(...)`/`bind_class=` (Stage 2); event modifiers -- `.with_modifiers(...)`/`.debounce(...)`/`.throttle(...)` (Stage 3); computed/derived state -- `Computed`/`Derive.*` (Stage 4); watch effects -- `Watch(...)` (Stage 5); two-way input binding -- `bind_value=Bind.model(...)` (Stage 6); per-item list rendering (`Repeat`) + conditional show/hide (`Show`) (Stage 7); `localStorage` persistence for `State(..., persist=True)` (Stage 8) -- see `docs/DESIGN-NOTES.md` ("Reactive-core vdom staging") and `PROGRESS.md`'s Snapshot table for the per-stage implementation record | DONE |
| v0.060 | User-defined, reusable components | DONE |
| v0.080 | Android backend -- `arklight android` packages a `build-dir` into a native Android project via `androidx.webkit.WebViewAssetLoader`, evolving the existing `ARKlight-Viewer-for-Android-Devices` app into the backend's runtime (staged `scaffold` -> CI build (2) -> CI install/launch smoke test (3) -> CI release build (4) -> local `build` (5) -> `--install` (6) -> `--release` (7) CLI ladder); design complete in `docs/DESIGN-NOTES.md`, staged implementation tracked in `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`, Stages 0-4 (`arklight android scaffold`, including its generated GitHub Actions CI build + emulator smoke-test + release-build workflow) done | IN PROGRESS |
| v0.100 | Desktop backend -- `arklight desktop` packages a `build-dir` into a cross-platform desktop app (Tauri-based or similar); design pending | PLANNED |
| v1.0 | Stable compiler | PLANNED |

**Renumbered.** v0.048 (CSS `@media` + `<head>` extension) is now
DONE -- both Stage A (`meta`/`links` on `Page(...)`) and Stage B
(`responsive_style` + `@media` compilation) have landed; see
`docs/DESIGN-NOTES.md` for both designs and `PROGRESS.md` for the
implementation record of each stage. With v0.048 out of the way, the
milestones behind it were renumbered to close the gap and, at the
time, make room for a dedicated KaiOS slot: JS backend capability
expansion moved `v0.044` -> `v0.054`; user-defined components moved
`v0.100` -> `v0.060`; the Desktop backend moved `v0.060` -> `v0.080`;
the Android backend moved `v0.080` -> `v0.100`; and the KaiOS
backend -- previously designed but unnumbered -- was given `v0.120`.
None of this reordering changed scope or design, only sequencing.

**Re-renumbered again.** The Desktop and Android backend slots have
since swapped a second time: Android is now `v0.080` and Desktop is
now `v0.100`. Reason: an existing external project,
`ARKlight-Viewer-for-Android-Devices`, is already most of the Android
backend's runtime (AndroidX `WebView`, offline `.ark`-bundle handling,
bundle/seal logic already split into its own files) -- see
`docs/DESIGN-NOTES.md` ("v0.0438: Android backend")'s "Updated
direction" note. The Android backend has a head start the Desktop
backend doesn't (Desktop's design is still pending, not complete), so
it moves ahead in sequence. Scope is unchanged for both; only order
moved. v0.054 (JS backend expansion) has since shipped in full --
all 8 vdom-staging stages feeding it are DONE; v0.060
(user-defined components -- staged ladder now DONE in full, Stages
0-4; see `docs/Foundational/USER-DEFINED-COMPONENTS.md` for the
reference), v0.080 (Android), and v0.100
(Desktop) are designed (Desktop excepted -- design pending); v0.080/
v0.100 implementation is still in progress or deferred. Alternate backends (Vue, Svelte) remain moved to unscheduled
future work, pending further development of the IR and state/event
semantics.

**Un-scheduled (amendment): KaiOS.** `v0.120` above was retired, not
reassigned -- KaiOS is pulled back out of the numbered roadmap
entirely and moved to unscheduled future work, the same tier Vue and
Svelte already sit at. This mirrors, deliberately, how a
hypothetical dedicated Windows-specific backend would be treated: the
project has no committed milestone for one, only a written, plausible
design sitting in `docs/Far Future Concern/WINDOWS-PHONE-BACKEND.md`
(a Windows Phone/UWP-era backend, in this case) with no version number
and no roadmap table entry at all -- an acknowledged possibility, not
a commitment. KaiOS's own design work isn't discarded by this change;
`docs/Far Future Concern/KAIOS-BACKEND-IMPLEMENTATION.md` (plus the
constraint-gathering doc alongside it, `kaios-app-design-doc.md`)
already lived in that same "Far Future Concern" directory even while
the milestone table above still scheduled it -- this amendment just
brings the roadmap's own bookkeeping into agreement with where the
design docs already sat. See `PROGRESS.md`'s "Planned, not yet
scheduled to a version" section for the equivalent snapshot-table
change.

## Non-goals

- Browser-side Python
- Virtual DOM
- Runtime Python
- Feature creep

---

See `PROGRESS.md` in the repo root for implementation status and
`CHANGELOG.md` for version history.
