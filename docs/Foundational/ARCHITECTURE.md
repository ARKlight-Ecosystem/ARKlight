# ARKlight Architecture

_Current as of **v0.063** (latest shipped milestone). This file is
updated in place as new milestones land, but a fact here can still
lag a merge — cross-check the Milestones table below and
[`PROGRESS.md`](../../PROGRESS.md)'s Snapshot table (the fastest
DONE/IN PROGRESS/PLANNED read) before treating anything version-
specific as current._

## Vision

The project pitch (what ARKlight is, the Python-in/HTML-out model, why
the browser never executes Python) lives in exactly one place: the
opening of the root [`README.md`](../../README.md). Kept there, not
copied here, because it's landing-page copy first and an architecture
fact second -- see `docs/README.md`'s "Adding a new doc" section for
the rule this follows.

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
  [`CONFIGURABILITY.md`](CONFIGURABILITY.md) for the full rule and worked
  examples.

## Compiler Pipeline

This is the canonical copy of the pipeline diagram -- `README.md`
links here rather than keeping its own copy (see "Why this file is
short" at the bottom for the rule).

```
Python Source
    |
    v
Python AST            arklight/parser/discover.py
    |                  (static analysis via the stdlib `ast` module:
    |                   finds Site()/@site.page(...) without executing
    |                   user code)
    v
ARK AST               arklight/parser/loader.py + arklight/api.py
    |                  (the module is executed; calling Heading(...),
    |                   Text(...), etc. builds a tree of ARKNode objects
    |                   -- that tree IS the ARK AST)
    v
Normalization         arklight/ir/normalize.py
    |                  (flattens nested lists, drops None/False,
    |                   wraps bare strings as Text nodes where needed)
    v
Validation            arklight/ir/validate.py
    |                  (schema check: known component types, required
    |                   props, valid text-only nesting)
    v
Website IR            arklight/ir/build.py
    |                  (backend-independent IRNode tree: type/props/children
    |                   -- models website *intent*, not HTML)
    v
Backend Interface     arklight/backend/base.py
    |                  (abstract `Backend.render(ir) -> {path: contents}`)
    v
HTML Backend          arklight/backend/html/render.py
    |                  (maps IR node types to HTML tags, rewrites internal
    |                   Link/Image hrefs to relative file paths, links the
    |                   generated stylesheet and behavior runtime)
    v
CSS Backend           arklight/backend/css/render.py
    |                  (v0.002: generates a global default stylesheet)
    v
JS Backend            arklight/backend/js/render.py
    |                  (v0.003: generates a tiny fixed behavior runtime;
    |                   all three backends run over the same IR and their
    |                   outputs are merged)
    v
index.html, about.html, styles.css, arklight.js, ...
```

`arklight/compiler/pipeline.py` orchestrates all of the above into a
single `build(entry_path, output_dir)` call, which is what the CLI
uses. By default it runs `[HTMLBackend(), CSSBackend(), JSBackend()]`
-- pass your own `backends=[...]` list to customize which backends run.

Each backend can also implement `postprocess(output_files) ->
output_files`, called once per backend (same order as `backends=[...]`)
*after* every backend's `render()` has run, over the combined
`{path: contents}` dict from all of them. The default `Backend`
implementation is a no-op identity, so existing backends need no
changes. This is the extension point for adding a new backend that
depends on what other backends already produced (analytics snippets,
build stamps, sitemap generation, ...) without editing that backend's
source -- see `tests/test_pipeline_end_to_end.py` for a worked example.

## Website IR

Each node contains:
- type
- props
- children

The IR models website intent rather than HTML.

## Binary IR (`.arklight`)

`arklight/ir/binary.py` defines `.arklight`: a small, portable,
versioned binary encoding of the Website IR, separate from the
in-memory `WebsiteIR`/`IRNode` tree above. Where `WebsiteIR` is "IR for
humans" (the legible, in-process form every backend consumes), a
`.arklight` file is "IR for machines" -- a build-once, ship-anywhere
snapshot that can be read back without re-running the Python compiler
pipeline.

Produced optionally, alongside the normal backend outputs, via
`arklight build --emit-arklight[=PATH]` (see
[`CLI-REFERENCE.md`](CLI-REFERENCE.md)); nothing about a plain
`arklight build` changes if the flag is never passed.

Format (little-endian, hand-rolled and zero-dependency -- the same
house style `arklight.packer`'s `.ark` bundle format follows, rather
than reaching for protobuf/flatbuffers/etc.):

```
magic bytes           4   b"ARKL"
format version        u16 FORMAT_VERSION (independent of ARKlight's
                           own __version__)
schema generation tag str "arklight v{__version__} ({CHANNEL})" --
                           self-declares which ARKlight build produced
                           the file, so a reader can tell
                           "older/newer schema" apart from "corrupt
                           file"
string table           u32 count, then `count` length-prefixed UTF-8
                           strings -- every string used anywhere below
                           (site name, routes, node types, JSON-encoded
                           props/state blobs, text content) is stored
                           once and referenced everywhere else by u32
                           index
body                       site_name, lang, app_shell flag, then page
                           count and each page's IR tree
```

`encode_arklight(ir) -> bytes` and `decode_arklight(data) ->
DecodedSite` are the round-trip pair; `peek_header(data) ->
ArklightHeader` reads just the magic/version/schema-tag prefix without
decoding the full body. Malformed or wrong-version input raises
`ArklightFormatError` rather than failing silently or guessing.

Scope note (v1): covers the structural IR tree (site/page/node shape)
plus each page's route, `state`, and `computed_initial` -- enough to
rebuild what a backend actually renders from. The long tail of
page-level bookkeeping on `WebsiteIR`/`IRPage` (watch/persist/media/
query specs, site-wide style registrations, raw postprocessors, ...)
is not yet round-tripped; a follow-up once this format has soaked, same
staged-rollout discipline the rest of the schema-generation model
already uses. See `tests/test_binary_ir.py` for the current coverage.

## Backend Interface

Current:
- HTML (`arklight/backend/html/`) -- fully split into a
  service-oriented set of modules (`tag_map.py`, `routing.py`,
  `attrs.py`, `head_meta.py`, `page_render.py`, `render.py`), the
  same shape the CSS backend below already used. All 6 staged rungs
  of this refactor shipped; the staging doc that tracked them,
  `docs/Backends/HTML-BACKEND-REFACTOR.md`, was removed once it
  finished -- see `CHANGELOG.md` for the per-stage record.
- CSS (`arklight/backend/css/`) -- split into
  `base_stylesheet.py`/`design_tokens.py`/`custom_styles.py`/
  `at_rules.py`/`selectors.py`/`render.py`. Same removed-once-done
  staging doc pattern as the HTML backend above -- see `CHANGELOG.md`
  for the record.
- JavaScript (`arklight/backend/js/`)

Future:
- Android (`arklight android` -- packaging backend, not a template/
  codegen backend: wraps an existing `build-dir` into
  a native Android project via `androidx.webkit.WebViewAssetLoader`,
  same "reads already-built output, never touches the
  parser/ir/backend internals" shape as `arklight.packer`. Evolves the
  existing `ARKlight-Viewer-for-Android-Devices` app into this
  backend's runtime rather than generating an Android project from
  scratch. See `DESIGN-NOTES.md` ("v0.0438: Android backend") for
  the design and `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md` for
  the staged implementation order -- Stages 0-4 done, see the Milestones
  table below for current status.)

## Public API

Everything is a function. Children are positional arguments,
properties are keyword arguments, components are Python functions --
no classes to subclass, no JSX-like syntax. The quickstart example
lives in the root [`README.md`](../../README.md), kept there as the
single canonical copy since it's the first thing a newcomer reads; the
full public component/behavior/state API reference lives in
[`AUTHORING-GUIDE.md`](AUTHORING-GUIDE.md).

## Repository

The annotated repository layout is
[`GETTING-STARTED.md`](GETTING-STARTED.md#repository-layout)'s
"Repository layout" section, kept there as the single canonical copy
rather than duplicated (and drifting out of sync) here.

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
| v0.048 | CSS `@media` queries + structured `<head>`/`<header>` extension -- Stage A (`meta`/`links` on `Page(...)`, DONE) + Stage B (`responsive_style` + `@media` compilation, DONE); see `DESIGN-NOTES.md` | DONE |
| v0.054 | JS backend capability expansion -- computed/derived state, watch effects, two-way input binding, per-item list rendering, conditional show/hide, event modifiers, reactive class binding, all via closed registries (no arbitrary JS/eval) -- design complete in `DESIGN-NOTES.md`; all seven feeding capabilities landed as `vdom-1` through `vdom-7`, and `vdom-8` (the last stage, `localStorage` persistence) has now landed too | DONE |
| vdom-staging | Reactive-core vdom staging, 8 stages feeding `v0.054`, all DONE: vendored snabbdom bare core swapped into `State`'s re-render pass (Stage 1); reactive class binding via `Bind.when(...)`/`bind_class=` (Stage 2); event modifiers -- `.with_modifiers(...)`/`.debounce(...)`/`.throttle(...)` (Stage 3); computed/derived state -- `Computed`/`Derive.*` (Stage 4); watch effects -- `Watch(...)` (Stage 5); two-way input binding -- `bind_value=Bind.model(...)` (Stage 6); per-item list rendering (`Repeat`) + conditional show/hide (`Show`) (Stage 7); `localStorage` persistence for `State(..., persist=True)` (Stage 8) -- see `DESIGN-NOTES.md` ("Reactive-core vdom staging") and `PROGRESS.md`'s Snapshot table for the per-stage implementation record | DONE |
| v0.060 | User-defined, reusable components | DONE |
| v0.061-v0.063 | JS vocabulary addendum, stages 1-3 of 10 (math derivation siblings; string-casing siblings + comparison `Show` predicates; small new runtime primitives -- `Action.geolocate`, clipboard `paste`, `matchMedia`-driven state, `reveal`/`lazy`, debounced/throttled two-way binding) -- staged in `docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`, see `docs/version history/v0.061.md`-`v0.063.md` for the per-stage user-facing summaries | DONE |
| v0.064 | `arklight search --retrieve-doc`, a doc-tree retrieval mode added to the existing `search` subcommand (root/folder index printing, `--file NAME` full-file retrieval) -- accepted, shipped ahead of its own planned `docs/Implementation/SEARCH-RETRIEVE-DOC-ADDENDUM.md` staging writeup (never actually filed); see `docs/version history/v0.064.md`. **Plus** JS vocabulary addendum, stage 4 of 10 (math derivations catalog, 21 `Derive.*` kinds) -- staged in `docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`, **shipped** out-of-band as `0.06509` after the capability fixes that paused it; see `docs/version history/v0.064.md`. Two independent pieces of work sharing one milestone slot, same precedent as `v0.041` (CLI/pipeline hardening + JS vocabulary addenda I & II) -- unlike `v0.041`, this slot's two pieces landed at different times, retrieve-doc at `v0.064` and JS vocab stage 4 later, as `0.06509` | DONE |
| v0.065-v0.070 | JS vocabulary addendum, stages 5-10 of 10 (string/list-scalar derivation catalogs, predicates catalog, cross-language "batteries included" numeric/formatting idioms, capstone `pluralize`/`random_int`) -- staged in `docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`; **stage 5 (string derivations catalog, 18 `Derive.*` kinds) and stage 6 (predicates catalog, 8 new `Predicate.*` kinds) have shipped** out-of-band as `0.06513` and `0.06517`, stages 7-10 remain PLANNED; **the `v0.066` slot is closed** (predicates catalog + `Provider` stage 2, package version `0.066`), and `Provider` stage 3 (`0.06518`) has already shipped ahead of the `v0.067` slot's other piece -- **interleaved with** `Provider`, an experimental, barebones interface for a site to declare it talks to an external service at runtime (contract + experimental gating, IR/validation, JS config emission, external-script loading, capability-enum finalization), accepted and staged as a six-rung ladder (stages 1-6, one per version in this range) in `docs/Implementation/PROVIDER-SDK-ADDENDUM.md` -- **and, at `v0.065` specifically, a third interleaved piece:** Rei, the compiler narrator (`--narrate` flag on `arklight build` + a `rei` config section), accepted from `docs/Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md` and shipped as `0.06510`, one version, no ladder; each stage's `docs/version history/vX.md` is a marked **PLANNED** preview until its stage actually lands, see that directory's own README for the convention | PLANNED |
| v0.071-v0.078 | Project Knowledge, stages 1-8 of 8 (compiler-owned `.arklight/` project-local knowledge directory: foundation, internal providers/facts/observations abstraction, Git as first provider, persistent project context, compiler build history, diagnostics integration, historical observations, future-provider open slot) -- staged in `docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md`; same marked-**PLANNED**-until-shipped convention as the row above | PLANNED |
| v0.080   | Android backend -- `arklight android` packages a `build-dir` into a native Android project via `androidx.webkit.WebViewAssetLoader`, evolving the existing `ARKlight-Viewer-for-Android-Devices` app into the backend's runtime (staged `scaffold` -> CI build (2) -> CI install/launch smoke test (3) -> CI release build (4) -> local `build` (5) -> `--install` (6) -> `--release` (7) CLI ladder); design complete in `DESIGN-NOTES.md`, staged implementation tracked in `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`, Stages 0-4 (`arklight android scaffold`, including its generated GitHub Actions CI build + emulator smoke-test + release-build workflow) done | IN PROGRESS |
| v0.100 | Desktop backend -- `arklight desktop` packages a `build-dir` into a native Linux desktop app via a purpose-built GTK3 + WebKit2GTK host (superseding an earlier, now-removed Neutralino.js plan; see `docs/Backends/ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md`); design complete, staged implementation tracked in `docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`, Stages 1-4 (`arklight desktop scaffold`, including its generated GitHub Actions CI build + headless-Xvfb smoke-test workflow, and `arklight desktop build`) done, Stages 5-7 (the local-toolchain counterparts) not started | IN PROGRESS |
| v1.0 | Stable compiler -- scope, "reliable" defined concretely, and the explicit exclusions (native backends, experimental features, ARKlight Component Collections) all live in [`V1-DEFINITION.md`](V1-DEFINITION.md), kept there as the single canonical copy rather than restated here | PLANNED |

## Non-goals (v0.001 and for the foreseeable future)

The canonical list -- `README.md` links here rather than keeping its
own copy:

- Browser-side Python
- Runtime Python execution in the browser
- **A user-facing/authored Virtual DOM.** ARKlight never asks a site
  author to write against a vdom concept, and a page with no
  `State(...)` ships zero vdom code. Internally, since `v0.054`
  (`vdom-staging`, all 8 stages DONE), the `State`/`Bind`/`Action.*`
  runtime is powered by a vendored bare [snabbdom](https://github.com/snabbdom/snabbdom)
  core (`init`/`h`/`vnode`/`htmlDomApi` only) as an implementation
  detail of the diff/patch mechanism -- see `DESIGN-NOTES.md`'s
  "Reactive-core vdom staging". No page-facing API changed when it
  landed. The vendored htmx runtime (`hx-boost`/`hx-preserve` for
  app-shell navigation) is the same kind of thing: an internal
  mechanism the compiler emits when needed, not an authoring surface
  a site author writes `hx-` attributes against directly.
- Feature creep beyond the milestone roadmap above

---

See `PROGRESS.md` in the repo root for implementation status and
`CHANGELOG.md` for version history.

## Why this file is short on prose, long on links

This file is the permanent architecture record (see
`docs/Foundational/README.md`'s "not deletable" note), so it's tempting
to make it self-contained by re-explaining everything here. Deliberately
not done: a fact that's also landing-page copy (the project pitch,
the quickstart example) lives in `README.md`, and this file links to
it rather than keeping a second, independently-editable copy that can
drift -- exactly the "single source of truth per kind of record" rule
`README.md`'s own "Status" section already follows for `CHANGELOG.md`/
`PROGRESS.md`. What stays here instead: the parts that are genuinely
*architecture*, not onboarding -- the pipeline's canonical diagram, the
Backend Interface's current/future split, the Milestones table, and
the Non-goals list above.
