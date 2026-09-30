# What ARKlight Is

_A grounding document for `docs/Foundational/`. Written from the
project's own source, its own design docs, and hands-on verification --
not from the pitch alone. Current as of **v0.070** (latest closed
milestone on `alpha`; `v0.080`/`v0.100` -- the Android and Linux desktop
native backends -- are IN PROGRESS, and `v0.071`-`v0.079`, Project
Knowledge and the `arklight assistant` MVP, are PLANNED), **plus one
piece of code landed after `v0.070` closed**: `PlatformAPI.db`
(local key/value storage, Web + Android), shipped in source but still
`[Unreleased -- draft, version slot unconfirmed]` per `CHANGELOG.md` --
folded into this revision because it changes two "no" answers below
(offline key/value persistence beyond `localStorage`, and the first
real JS-to-native bridge in the Android backend), not because it closed
a milestone. Cross-check `PROGRESS.md`'s Snapshot table and
`CHANGELOG.md`'s `[Unreleased]` section before treating any
version-specific claim here as still accurate -- this document is a
snapshot, not a live view, and it has gone stale before (this revision
replaces one pinned to `v0.0644`, six milestones behind)._

## The Goal

ARKlight's goal is to give Python developers a web-development
experience comparable, in day-to-day ergonomics, to what a frontend
framework offers -- component calls, props, a reactive core, a real
dev loop -- while enforcing the philosophy the rest of this document
describes, not loosening it to get there faster. The DX bar is
"comparable to React/Vue/Svelte," not "acceptable for a compiled
language with a templating bolt-on" -- Section 5's comparison table
exists precisely so that bar can be checked against the real thing
rather than asserted. "Comparable ergonomics," not "equivalent
capability": where a frontend framework resolves something at runtime
with an expression evaluator, ARKlight resolves it at compile time
through a fixed, closed primitive, or doesn't offer it yet at all
(Section 6 lists what's still missing under that constraint). The DX
goal is real, but it never licenses relaxing Section 2's "Compiler
First, Runtime Last" agreement to get there.

ARKlight is being built for two specific, named audiences -- not
"developers" in the abstract:

- **The Python Community** -- people who already think in Python and
  are structurally unwilling, uninterested, or simply not equipped to
  reach for `npm`, a JS build chain, or a second language just to put
  a page on the web. Section 5's Astro comparison names this audience
  directly: Astro accepts any JS framework as an island and still
  expects JS/npm literacy for anything beyond bare content; ARKlight
  asks for neither.
- **The Education Community** -- classrooms, self-taught learners, and
  anyone teaching or learning "how to build a website," for whom every
  extra language, extra runtime, and extra failure mode between typing
  code and seeing a result is a teaching cost, not just a developer
  inconvenience. The closed vocabulary and the "fail loudly at build
  time, not silently in the browser" posture (`docs/README.md`'s
  Philosophy section) both cash out here specifically: a student's
  mistake should raise a Python exception during `arklight build`,
  never surface as silent broken behavior discovered only in a browser
  console after the fact.

Being a genuinely useful tool for both of those audiences, without
bending the design agreement in Section 2 to do it, is the whole
goal -- not "an SSG people happen to like," not "a frontend framework
for people who already know JS." ARKlight is only worth building if it
can be comparable-to-frontend-frameworks *and* philosophy-enforcing at
the same time, for an audience the rest of the field is not currently
building for. `docs/Foundational/V1-DEFINITION.md` picks up directly
from this goal to answer the next question it raises: what "stable"
and "just works" concretely mean, and exactly how far that promise is
meant to reach.

## 1. The one-sentence definition

**ARKlight is a compiler framework: you author in ordinary Python, it
compiles that authoring into a static site with its own
batteries-included developer workflow, and -- notably -- cross-platform
wrapped native targets are included, not bolted on.**

That wording is deliberate, and it replaces an earlier framing of this
document that leaned on "static-site compiler" as the load-bearing
noun. `PROGRESS.md`'s `v0.0642` entry records why: ARKlight's
*authoring* model -- a component-call vocabulary, a reactive core,
closed-vocabulary event handling -- is drawn from the same design
lineage as frontend/UI frameworks (React, Vue, Svelte). Its *compiled
output* is, in principle, SSG-shaped: `arklight build` runs once,
ahead of time, and emits plain files with no server at request time.
Neither label, on its own, describes the whole thing, and reaching for
either one flattens the project into a category it wasn't built to
fit.

- **A compiler framework** -- the genuinely load-bearing noun. Not "a
  static-site generator," not "a frontend framework," not "a UI
  framework." Those three labels each describe one slice of what
  ARKlight does (respectively: what its output looks like, what its
  authoring ergonomics resemble, what its component vocabulary is
  shaped like) and none of them describe the compiler itself -- the
  thing that owns route resolution, validation, IR construction, and
  backend selection as compile-time decisions rather than runtime or
  build-tool behavior bolted onto an existing category. Section 4
  below states this directly rather than leaving it implied.
- **Python-authored** -- not templated, not a DSL with its own syntax.
  `Heading("Hi")` is a real Python function call; the site is a real
  Python module ARKlight's parser statically discovers
  (`arklight/parser/discover.py`) and then actually executes
  (`arklight/parser/loader.py`) to build a tree of `ARKNode` objects.
- **Closed-vocabulary** -- the single most distinctive, load-bearing
  property in the whole project, and the one every other design
  decision traces back to. There is no `eval`, no `new Function`, no
  string ever executed as code, anywhere in the compiler or the
  emitted runtime -- confirmed directly in `arklight/backend/js/
  render.py`, `runtime/dispatch.py`, and `attrs.py`. Interactivity is
  expressed through a fixed, closed menu of registered primitives
  (`Action.*`, `Derive.*`, `Predicate.*`, `Watch`), not arbitrary
  expressions. This is a security and predictability choice, not a
  performance one -- React, Vue, Svelte, and Solid are all
  general-purpose runtimes that don't make this trade.
- **Compiles to a static site** -- `arklight build` runs once, ahead
  of time, and produces plain files. No server exists at request time.
  This is the property every genuine differentiator (offline `.ark`
  bundles, air-gapped delivery, `file://` operation) depends on, and
  it's the property that makes ARKlight's *output* recognizable to
  anyone who has used an SSG before -- without that recognition
  extending to ARKlight itself as a category.
- **Its own batteries-included developer workflow** -- routing,
  component validation, CSS generation and unused-style elimination,
  a real file-watch dev loop (`arklight live-streaming`), bundling
  (`arklight pack`/`unpack`), and PWA manifest injection
  (`arklight pwa`) all live inside the same compiler and the same CLI,
  not spread across a build-tool-plus-plugin-ecosystem the way most
  SSG or frontend-framework toolchains are assembled.
- **Cross-platform wrapped targets are included** -- Android
  (`androidx.webkit.WebViewAssetLoader`, real AndroidX/Jetpack
  machinery) and Linux Desktop (GTK3 + WebKit2GTK, a system WebView,
  not a bundled Chromium) are backends of the same compiler, not a
  separate packaging product layered on afterward. Both wrap the
  compiler's *own* output under the same closed-vocabulary guarantee
  the web target already has -- there is no second, independently-
  trusted layer of arbitrary native code, because ARKlight has never
  built one and its own design agreement
  (`SYSTEM-DESIGN-AGREEMENTS.md`) says it isn't going to.

## 2. The design agreement everything else follows from

`docs/Foundational/SYSTEM-DESIGN-AGREEMENTS.md` states the whole
project's governing rule in one line:

> **"Compiler First, Runtime Last."**
>
> If the compiler can solve it correctly and completely, the runtime
> should not solve it again. If a behavior is inherently determined by
> the target runtime, ARKlight should delegate to it rather than
> recreate that runtime inside its own abstraction.

Concretely, this means: route resolution, internal-link resolution,
component validation, CSS generation, unused-style elimination, and
behavior selection are all compiler-time decisions -- none of them
exist as runtime mechanisms the way a client-side router or a CSS-in-
JS runtime would implement them elsewhere. Runtime code is reserved
for the specific, named cases where the browser (or the OS) is the
only thing that can possibly know the answer: user input, viewport
state, local storage, network responses, device capabilities.

Every distinctive property described below is a direct consequence of
this one rule, not an independent design choice. It's also the rule
that a Platform APIs layer has to fit into without bending: see
`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md` for how "the compiler
owns the semantic interface, the platform backend owns the
implementation" is this same agreement applied to device/OS
capabilities specifically.

## 3. What actually exists today, verified hands-on

This section reflects what was built and tested directly against the
`alpha` branch's real source -- not the roadmap, not the pitch.

**The compiler pipeline** (`arklight/compiler/pipeline.py`):

```
Python Source → Python AST → ARK AST → Normalization → Validation
→ Website IR → Backend (html / css / js / android / desktop)
```

**The reactive core** (closed vocabulary, no eval, all verified
working end-to-end): `State`, `Computed`/`Derive.*` (`sum`, `subtract`,
`multiply`, `divide`, `max`, `min`, `count`, `join`, `compare`,
`format`, `trim`, `uppercase`), `Watch`, `Show`/`Predicate.*`,
`Repeat`, two-way `bind_value`, and opt-in `localStorage` persistence
(`persist=True`) with a `file://`/opaque-origin caveat that the
Android backend's `WebViewAssetLoader` specifically exists to solve.
Two real hardware/OS-adjacent primitives exist beyond pure
computation: `geolocate`, wrapping `navigator.geolocation` with
permission-denial handling, and `State(..., query=..., history=...)`,
syncing a state key with a URL query parameter via
`history.replaceState`/`pushState`.

**User-defined components** (`v0.060`, Stage 0-1 shipped): a
`@component(props={...})` decorator that macro-expands a call into its
built-in subtree *before validation runs* -- the compiled output
contains zero trace of the component name, verified directly. Props
are schema-checked with compiler-quality errors (`Component 'X'
received unexpected prop(s) [...]`), not raw Python tracebacks. A
`mode="registry"` alternative also exists for per-backend dispatch.
This is architecturally closer to a macro or a template partial than
to a stateful framework component -- it has no runtime existence, no
encapsulated state at the Stage 0-1 level, and no lifecycle.

**A real dev loop**: `arklight live-streaming` does a genuine
file-watch-and-full-rebuild cycle (verified by editing a live site and
seeing the change on the next request), plus an explicit, dev-only
`--channel` flag that streams `State` over Server-Sent Events.

**Packaging**: sealed `.ark` bundles (`arklight pack`), PWA manifest
injection (`arklight pwa`), and the two native backends described
above -- both confirmed to use `hx-boost` (a real, vendored,
deliberately narrow use of htmx 2.0.10) for AJAX-style internal
navigation, avoiding the native-shell "white flash" between pages.

**A self-aware escape-hatch system** (`arklight/experimental.py`):
features that step outside ARKlight's own design philosophy (`@media`
queries, `raw-postprocess`, `css-import`) are not silently allowed --
every use prints an explicit warning naming what philosophy it steps
outside of and what to prefer instead.

**Doc-tree retrieval** (`v0.064`): `arklight search --retrieve-doc`
gives the CLI itself read-only, unsynthesized access to `docs/` --
exact file bytes, nothing invented or summarized -- the same primitive
`arklight assistant`'s planned Miko MVP (`v0.079`) is designed to wrap
rather than reimplement.

**Everything shipped between `v0.0644` and `v0.070`** (the gap this
revision closes -- see `PROGRESS.md`'s Snapshot table for the
version-by-version breakdown):

- **Preamble directives** (`v0.0650`-`v0.06502`): `# include
  <stdlib.ARKlight>` / `# include <acc.<dotted.module.path>>` and
  `# define <name> -> <text>`, reserved-shape comments ARKlight's own
  loader parses and resolves itself, replacing `from arklight import
  *` (retired, still works, now logs a build-time notice) as the way a
  site file's vocabulary gets bound. Two includes disagreeing on a
  name raises `PreambleCollisionError` rather than Python's star-import
  silently keeping whichever ran last. Full detail in
  `docs/Foundational/AUTHORING-GUIDE.md`.
- **`Provider`, all six stages** (`v0.06514`-`v0.06616`, spanning
  `v0.065`-`v0.070`): `Provider.declare(name=..., capabilities=[...])`
  and `Site(provider=...)` went from a bare, gated declaration to a
  fully wired, discoverable contract -- IR/validation integration, a
  read-only `window.ARKLIGHT_PROVIDER` runtime object, external
  script loading (`Page(scripts=[...])`), `arklight search
  <provider-name>` integration, and a finalized capability vocabulary
  (`auth`, `read`, `write`, `subscribe`, plus a namespaced `custom:`
  escape hatch). Settled design record:
  `docs/Foundational/PROVIDER-SDK.md`.
- **Platform API IR, stage 1 of 2** (interleaved into `v0.065`):
  `PlatformAPI.notify(...)` / `PlatformAPI.clipboard_write(...)` on
  `on_click=`, backed by a compiler-owned interface registry
  (`arklight.ir.platform_api`) with the Web reference implementation
  shipped end-to-end.
- **Platform API IR, stage 2 of 2 -- first slice, `db`** (landed after
  `v0.070`, `[Unreleased]` per `CHANGELOG.md`): stage 2 is no longer
  purely unscheduled -- `PlatformAPI.db.set/get/delete/keys(...)` is a
  fourth-and-fifth-backend capability (local key/value storage) with
  real, distinct engines per platform: IndexedDB on Web, and a new
  generated `ArkDb.kt` (SQLite) on Android, registered through
  `WebViewCompat.addWebMessageListener` and restricted to the app's own
  asset origin -- the first JS-to-native bridge anywhere in the Android
  backend, previously an explicit non-goal. `notify`/`clipboard_write`
  remain Web-only; Desktop implements nothing yet. See
  `docs/Foundational/PLATFORM-APIS.md`'s "`db`: one interface, a
  different engine per backend" for the full contract.
- **The closed reactive vocabulary grew substantially**: the ~90-entry
  `Derive.*`/`Predicate.*` catalog referenced in `docs/Implementation/
  JS-VOCABULARY-ADDENDUM-v0.070.md` is now fully shipped end to end
  (math, string, list-scalar, cross-language-numeric, formatting/case,
  and predicate kinds), not just the handful that existed at
  `v0.0644`. Every kind still has a build-time Python mirror alongside
  its JS fragment, so server-rendered `Bind(...)` text and the client
  recompute agree -- the "no `eval`, closed vocabulary" property in
  Section 1 hasn't loosened as the catalog grew.
- **Rei, the compiler narrator** (`v0.06510`): `arklight build
  --narrate` narrates the compiler pipeline's own stages as
  deterministic `[Rei] ...` sentences, sibling to `--verbose`/
  `--debug`.
- **`arklight deploy`** (`v0.06515`): builds, then shells out to a
  locally-installed `wrangler` for a one-command Cloudflare Workers
  deploy. Never installs Wrangler itself, never touches credentials.
- **ACC capability discovery** (`arklight/capabilities.py`, documented
  at `v0.0645`): the one piece of **ARKlight Component Collections**
  (a separate repository,
  [`Rae-ARK/ARKlight-Component-Collections`](https://github.com/Rae-ARK/ARKlight-Component-Collections))
  that has to live in `alpha` itself, since it's the compiler's own
  side of discovering capabilities an installed ACC package
  advertises, without the compiler depending on ACC to exist. See
  `docs/Foundational/ACC-CAPABILITIES.md`.
- **Bracket-nesting indentation is now a checked compiler diagnostic**
  (`v0.06603`-`v0.06611`): a continuation line inside an open bracket
  must indent further than its opener, a closing-only line must sit
  flush with it, and nesting past 8 levels fails the build --
  `BracketIndentationError` (see `docs/Foundational/
  AUTHORING-GUIDE.md`).
- **Android native-shell hardening, first slice** (`v0.06507`):
  external links routed to the device instead of loading inside the
  app's own WebView, an `android.allow_navigation` allow-list,
  predictive-back support, and WebView state restoration across
  rotation.

## 4. What ARKlight deliberately is not

Stated as plainly as the project states it about itself -- and, as of
this revision, stated as an explicit list rather than left to be
inferred from Section 1's wording:

- **Not a static-site generator**, in the sense that term is usually
  used. ARKlight's *compiled output* is SSG-shaped -- files emitted
  once, ahead of time, no server at request time -- and comparing it
  to Astro or Eleventy on that axis is fair (Section 5 does exactly
  that). But "SSG" describes an output shape, not a project. ARKlight
  is the compiler that produces that shape, plus an authoring model,
  plus a closed reactive vocabulary, plus native packaging, all owned
  by the same tool. Calling the whole project "an SSG" describes the
  least distinctive third of it.
- **Not a frontend framework**, in the React/Vue/Svelte sense. Those
  ship a runtime (however small) that evaluates author-written
  expressions or components at render time. ARKlight ships nothing
  equivalent: its "frontend-framework-flavored" authoring ergonomics
  (component calls, props, a reactive core) exist entirely so that the
  *compiler* can resolve everything ahead of time into a fixed,
  closed vocabulary -- there is no expression evaluator anywhere in
  the emitted output for a frontend framework's runtime to be
  compared against in the first place.
- **Not a UI framework**, in the component-library sense either. There
  is no persistent widget tree, no client-side instance lifecycle
  outside a page's own reactive `State`, and (at the Stage 0-1 level
  shipped today) no component-owned state independent of the page
  that macro-expanded it in.
- **Not a general-purpose native-app framework.** No native plugin
  API, no camera/Bluetooth/sensor bridge, by explicit design choice --
  confirmed in the Desktop backend proposal, which rejects an
  embedded-runtime approach in favor of a plain WebView wrapper. (This
  is the one boundary a Platform APIs layer is deliberately designed
  to approach without crossing -- see
  `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md` Section 15's "No
  Generic Native Escape Hatch.")
- **Not a client-side application framework.** No persistent
  application state across page navigations by default, no dynamic
  client-side router, no component instances that survive a
  navigation -- every "page" is still an independently compiled
  document. `app_shell=True` makes navigation *feel* smoother; it does
  not make ARKlight's output an SPA in the technical sense.
- **Not iOS-capable, and not by oversight.** Android's
  `shouldInterceptRequest()`-based interception has no iOS equivalent
  for real `http(s)://` URLs -- `WKURLSchemeHandler` only handles
  custom, non-standard schemes, and the underlying WebKit capability
  gap (bug 138169) has been open, and explicitly declined, for a
  decade. This is a platform wall, not a scheduling gap.

None of these are hedges. Each one is a place a reader would land if
they reached for the nearest familiar label instead of the actual
one -- and each one is wrong in a specific, checkable way, not just
"not quite right in spirit."

## 5. Where it sits against the rest of the field

ARKlight's authoring ideas come from frontend/UI-framework lineage; its compiled artifacts are SSG-like in principle. That combination is not itself a recognized category -- the table below compares ARKlight against the *nearest* tool on each axis, not against a peer in its own category, because by the definition in Section 1 there isn't one yet.

| Category | Closest relative | The real difference |
|---|---|---|
| Static-site generators | Astro (component-authored, JS only where needed) | Astro accepts any JS framework as an island and requires npm/JS knowledge for anything beyond bare content; ARKlight has exactly one, Python-only, closed vocabulary and serves an audience (Python-only developers, structurally unwilling to touch JS) that Astro doesn't attempt to serve at all. |
| Compiler-first UI frameworks | Svelte (reactivity resolved at compile time, not via a shipped runtime) | Svelte still ships a real, if small, named runtime (`svelte`'s own docs draw this line explicitly) and lets you write arbitrary JS inside a component. ARKlight's macro-expanded components ship *zero* bytes for the abstraction itself, and the vocabulary is closed by construction -- no expression evaluation exists anywhere in the pipeline. |
| Native-wrapper tooling | Tauri / Capacitor (system WebView, not bundled Chromium) | Tauri/Capacitor wrap an arbitrary, independently-trusted web app. ARKlight's native shells package the compiler's *own* closed-vocabulary output -- there's no second layer of arbitrary code to trust, because there isn't a mechanism to introduce one. |
| Python-to-native-app tools | Kivy / BeeWare | Both bundle an actual Python interpreter into the shipped artifact. ARKlight ships zero Python anywhere in any artifact, web or native -- Python exists only at build time, on the developer's machine. |

### What can you build with ARKlight?

The following is the practical capability boundary for the current alpha. These categories describe what ARKlight can reasonably produce today, rather than what may exist on the roadmap.

#### Content, marketing, and documentation

| Client need | Feasible today? | Why / mechanism |
|---|---|---|
| Marketing site, landing page, portfolio | Yes | Full HTML vocabulary including `Section`, `Article`, `Table`, `Form`, `Picture`, and other built-in components. |
| Documentation site | Yes | Static routes and structured content compile directly to deployable HTML/CSS/JS. |
| Blog or publication-style site | Yes | Independently compiled pages, reusable components, styling, routing, and static output fit the content-oriented model. |
| Responsive content pages | Yes | Responsive state and CSS generation can adapt the output without requiring handwritten `@media` rules in ordinary use. |

#### Interactive websites and widgets

| Client need | Feasible today? | Why / mechanism |
|---|---|---|
| Accordions, toggles, tabs, dismissible UI | Yes | Closed `BEHAVIOR_REGISTRY` primitives such as `toggle`, `scroll-to`, `copy`, and `dismiss`. |
| Copy-to-clipboard interactions | Yes | `copy` behavior is represented through the compiler's registered behavior vocabulary. |
| Local reactive UI | Yes | `State`, `Computed`/`Derive.*`, `Watch`, `Show`, and related primitives provide synchronous in-memory reactivity. |
| Interactive forms with local state | Yes | Form elements can bind values to state and participate in the supported action/derivation vocabulary. |
| Deep-linkable UI state | Yes | `State(..., query=..., history=...)` synchronizes state with URL query parameters and browser history. |
| Persisted user preferences | Yes | `State(..., persist=True)` uses `localStorage` for supported client-side persistence -- one state key, one fixed slot. |
| General-purpose local key/value storage | Yes (Unreleased) | `PlatformAPI.db.set/get/delete/keys(...)` -- an arbitrary number of named keys, JSON-serializable values, read back into any declared `State(...)`. Distinct from `persist=`: this is a store an author addresses directly, not a state-level convenience. Web uses IndexedDB; ships in source but still `[Unreleased -- draft, version slot unconfirmed]`. |
| Viewport-responsive behavior | Yes | `State(..., media="...")` can expose media-query state to the closed reactive vocabulary. |
| Lists rendered from data | Yes | `Repeat`/`RepeatItem` provides data-driven repeated rendering. |

#### Packaged and offline experiences

| Client need | Feasible today? | Why / mechanism |
|---|---|---|
| Installable PWA | Yes | `arklight pwa` adds the manifest and service-worker machinery to an existing build. |
| Single-file website artifact | Yes | `arklight pack` produces a sealed `.ark` bundle containing the website and its package data. |
| Website that can be distributed without a web server | Yes | The compiled output is static, and `.ark` bundles are designed to be opened by the corresponding viewer tooling. |
| Air-gapped or offline content delivery | Yes | Static output and packaged `.ark` artifacts do not require a server at request time. |

#### Native-wrapped applications

| Client need | Feasible today? | Why / mechanism |
|---|---|---|
| Android wrapper around an ARKlight site | Alpha | Android backend uses AndroidX/WebView infrastructure and `WebViewAssetLoader` to provide the packaged site through a stable HTTPS-style asset origin. |
| App that persists data through real native storage, not just the WebView's own | Alpha (Unreleased) | `PlatformAPI.db` gives the Android build a generated `ArkDb.kt` (SQLite) reached through a narrow, own-origin-only `WebViewCompat` message bridge; the same author-facing calls fall back to IndexedDB on Web. Still `[Unreleased]`, on-click-triggered only (no on-load read, no `clear`), and Desktop has no `db` implementation. |
| Linux desktop wrapper | Alpha | Desktop backend uses GTK3 + WebKit2GTK and packages the compiled web output in a native shell. |
| Cross-platform native distribution | Partially | Android and Linux desktop backends exist, but the native target surface is still alpha and does not provide a general native plugin/API ecosystem. |
| iOS application | No | There is no iOS backend, and the current native-shell architecture does not provide an equivalent implementation. |

#### Applications ARKlight does not currently target

| Client need | Feasible today? | Why / mechanism |
|---|---|---|
| Backend-driven application with authentication | No | ARKlight has no server runtime, authentication system, or account model. |
| Database-backed application | No | There is no database/server integration in the current closed vocabulary. |
| Checkout or payment application | No | No sanctioned backend/payment-service integration exists in the current compiler vocabulary. |
| API-driven application requiring arbitrary HTTP requests | No | There is no `fetch`/HTTP primitive anywhere in ARKlight's closed vocabulary, and `PlatformAPI.db` does not change that -- it is local storage, not a network call. `Provider` (`Site(provider=Provider.declare(...))`) is the accepted, gated *boundary* for a site to declare it talks to an external service; the actual request -- "your own `fetch` calls" against a vendor SDK loaded via `Page(scripts=[...])`, in the maintainer's own words (`arklight/provider.py`) -- is the site author's hand-written JavaScript, never something ARKlight authors, generates, or validates. |
| Large SPA-shaped application | No | ARKlight does not provide a persistent application-level component tree, general client-side router, or fine-grained reactive dependency graph. |
| Complex multi-view client application | Not currently targeted | Pages remain independently compiled documents; `app_shell=True` improves navigation behavior but does not turn the output into a conventional SPA. |
| Arbitrary custom JavaScript | No | Client behavior is intentionally restricted to the closed vocabulary. There is no general JavaScript escape hatch in the normal authoring model. |

### Practical fit

The current capability boundary can therefore be summarized as:

**Strong fit:** static/content sites, marketing sites, documentation, portfolios, responsive pages, interactive widgets, locally reactive interfaces, URL-addressable state, persisted preferences, PWAs, and packaged/offline websites.

**Possible but alpha:** Android and Linux desktop wrappers.

**Outside the current model:** backend-heavy applications, authentication/account systems, database-backed applications, arbitrary API-driven applications, large SPA-shaped systems, and projects whose development model depends on unrestricted client-side JavaScript.

The purpose of this boundary is not to imply that the unsupported categories are inherently undesirable or impossible to implement. They require capabilities that ARKlight's current closed-vocabulary and compiler-first design does not provide.

For evaluation purposes, the important question is therefore not simply whether ARKlight can produce a website. It is whether the application's requirements fall inside the capability boundary that the current compiler, runtime vocabulary, and available targets actually support.

## 6. Honest, currently-unresolved gaps

- **No fetch/HTTP primitive anywhere in the closed vocabulary** -- a
  real, checkable wall (verified against `ACTION_REGISTRY` and
  `DERIVATION_REGISTRY` directly, and still true after `PlatformAPI.db`
  landed -- `db` is local storage, not a network call) that rules out a
  whole class of common beginner projects (weather apps, anything
  API-driven) until or unless a sanctioned, closed-vocabulary way to
  fetch data is designed. `Provider` (`docs/Foundational/
  PROVIDER-SDK.md`, six-rung `v0.065`-`v0.070` ladder fully shipped) is
  the accepted *boundary* for external services -- it declares that a
  site talks to one and can load its vendor script
  (`Page(scripts=[...])`), but the actual request is the site author's
  own hand-written code, never something ARKlight authors or
  validates; `arklight/provider.py`'s own docstring names this
  directly ("the real Firebase SDK, your own fetch calls"). A Platform
  APIs layer (`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`, accepted
  and staged in `docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`) is
  a related but distinct answer for *execution-platform* capabilities
  -- stage 1 of 2 (Web reference implementation, `notify`/
  `clipboard_write`) shipped as of `v0.065`, and stage 2's first slice
  (`db`, local key/value storage on Web + Android) has now landed in
  source (`[Unreleased]` per `CHANGELOG.md`), narrowing but not closing
  this gap: `db` reads and writes bytes a site already has, it still
  doesn't put a byte on the wire. Section 25 of the Platform API
  proposal draws the line between the two layers explicitly.
- **No slot/children-passing model for user-defined components** --
  `Card(Text("content"))` forwarding `"content"` into `Card`'s render
  function the way React/Vue `children`/`<slot>` works does not exist
  yet.
- **`main`/PyPI still lag `alpha` significantly, though the gap is
  narrower than it once was.** The published package (`0.54.1` as of
  this check against PyPI, not the `0.42.2` an earlier revision of
  this document reported) does now carry a real reactive core (`State`,
  a smaller `Action.*`/`Derive.*` vocabulary, named click behaviors)
  and the `.ark` bundle packager. It still has, confirmed directly
  against `main`'s own source: no `@component` user-defined-component
  system, no `Provider`, no preamble directives, no Rei narrator, and
  no native backends (Android/Desktop). Nothing in Section 3 beyond
  the reactive core basics and bundling is currently reachable via
  `pip install arklight`.
- **Zero independent adoption signal.** No stars, forks, or community
  discussion found under the project's own name at any point this was
  checked.

## 7. One line to leave this document on

ARKlight's real bet is not "a faster Jekyll" or "a smaller Vue" -- it's
a specific, narrower claim: **that a tool can be Python-only,
closed-vocabulary, and provably incapable of running code it didn't
itself generate, anywhere in its pipeline, on the web or packaged
native -- and that this constraint is worth more to the right audience
than the flexibility it gives up.** That claim doesn't fit neatly
under "SSG," "frontend framework," or "UI framework" -- it was never
going to, since it borrows the authoring habits of the second and
third categories to produce output shaped like the first, without
being reducible to any of them. Whether the audience for that specific
claim is large enough to matter is still an open, unanswered question;
whether the constraint itself is real and consistently honored is
not -- it has been checked, directly, against the source, repeatedly,
and it has held.
