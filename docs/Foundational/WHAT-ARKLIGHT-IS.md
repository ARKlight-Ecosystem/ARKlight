# What ARKlight Is

_A grounding document for `docs/Foundational/`. Written from the
project's own source, its own design docs, and hands-on verification --
not from the pitch alone. Current as of **v0.0642** (latest shipped
milestone on `alpha`); cross-check `PROGRESS.md`'s Snapshot table
before treating any version-specific claim here as still accurate._

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

ARKlight's authoring ideas come from frontend/UI-framework lineage;
its compiled artifacts are SSG-like in principle. That combination is
not itself a recognized category -- the table below compares ARKlight
against the *nearest* tool on each axis, not against a peer in its own
category, because by the definition in Section 1 there isn't one yet.

| Category | Closest relative | The real difference |
|---|---|---|
| Static-site generators | Astro (component-authored, JS only where needed) | Astro accepts any JS framework as an island and requires npm/JS knowledge for anything beyond bare content; ARKlight has exactly one, Python-only, closed vocabulary and serves an audience (Python-only developers, structurally unwilling to touch JS) that Astro doesn't attempt to serve at all. |
| Compiler-first UI frameworks | Svelte (reactivity resolved at compile time, not via a shipped runtime) | Svelte still ships a real, if small, named runtime (`svelte`'s own docs draw this line explicitly) and lets you write arbitrary JS inside a component. ARKlight's macro-expanded components ship *zero* bytes for the abstraction itself, and the vocabulary is closed by construction -- no expression evaluation exists anywhere in the pipeline. |
| Native-wrapper tooling | Tauri / Capacitor (system WebView, not bundled Chromium) | Tauri/Capacitor wrap an arbitrary, independently-trusted web app. ARKlight's native shells package the compiler's *own* closed-vocabulary output -- there's no second layer of arbitrary code to trust, because there isn't a mechanism to introduce one. |
| Python-to-native-app tools | Kivy / BeeWare | Both bundle an actual Python interpreter into the shipped artifact. ARKlight ships zero Python anywhere in any artifact, web or native -- Python exists only at build time, on the developer's machine. |

## 6. Honest, currently-unresolved gaps

- **No fetch/HTTP primitive anywhere in the closed vocabulary** -- a
  real, checkable wall (verified against `ACTION_REGISTRY` and
  `DERIVATION_REGISTRY` directly) that rules out a whole class of
  common beginner projects (weather apps, anything API-driven) until
  or unless a sanctioned, closed-vocabulary way to fetch data is
  designed. `Provider` (`docs/Proposals/PROVIDER-SDK-PROPOSAL.md`,
  accepted, staged `v0.065`-`v0.070`) is the accepted answer for
  *external services*; a Platform APIs layer
  (`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`, filed this revision,
  not yet accepted) is a related but distinct answer for *execution-
  platform* capabilities -- Section 25 of that proposal draws the
  line between the two explicitly.
- **No slot/children-passing model for user-defined components** --
  `Card(Text("content"))` forwarding `"content"` into `Card`'s render
  function the way React/Vue `children`/`<slot>` works does not exist
  yet.
- **`main`/PyPI lag `alpha` by a full generation.** The published
  package (`0.42.2` as of this writing) predates the entire reactive
  core, the component system, and both native backends. Nothing
  described in Section 3 is currently reachable via `pip install
  arklight`.
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
