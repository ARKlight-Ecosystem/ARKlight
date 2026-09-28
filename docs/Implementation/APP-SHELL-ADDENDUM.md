# App Shell Addendum: Staged Order Toward SPA-Grade UX

**Status:** PLANNED. Six stages (`S1`-`S6`), none started, **no version
slots reserved** -- `v0.071`-`v0.078` belong to the Project Knowledge
ladder and `v0.081`-`v0.084` to the Rei ladder, so real numbers are
assigned when a stage is scheduled, not here. This file turns the
accepted
[`docs/Proposals/APP-SHELL-CAPABILITY-PROPOSAL.md`](../Proposals/APP-SHELL-CAPABILITY-PROPOSAL.md)
into a trackable landing order, the same role
[`PLATFORM-API-IR-ADDENDUM.md`](PLATFORM-API-IR-ADDENDUM.md) plays for
its proposal. It does not restate the proposal's reasoning; it fixes
the order, the touch points, and the exit test for each rung.

## Goal

Make an `app_shell` site indistinguishable, in use, from a Vue/Svelte
SPA -- no reload flash, persistent chrome, targeted reactive updates,
state that follows the visitor between pages, real shareable URLs --
**without** a client-side router, a general component tree, or any
string executed as code. Every stage follows the rule the project
already uses: the compiler decides, the runtime executes what the
compiler emitted, and anything that can be delegated to htmx or the
browser is.

## Ground truth this ladder starts from

Verified against source on `alpha`, not taken from the proposal text:

| Fact | Where |
| --- | --- |
| `Site(app_shell=True)` puts `hx-boost="true"` on `<body>`; navigation is htmx AJAX + swap, so the tab's JS context is never torn down | `arklight/backend/html/page_render.py`, vendored htmx `at()` |
| Vendored htmx is **2.0.10** and already contains `config.globalViewTransitions` and the per-swap `transition:` modifier (feature-detects `document.startViewTransition`) | `arklight/backend/js/htmx.py` |
| The runtime pins `htmx.config.allowEval = false` and `includeIndicatorStyles = false` from one place | `arklight/backend/js/render.py` (~L904-918) |
| `store.set`/`store.reset` call `listeners.forEach(fn => fn())` with **no key**, then `recomputeAll()` re-runs every `Computed` | `arklight/backend/js/runtime/state.py`, `createState` |
| Every subscriber notification runs `renderBindings`, `renderClassBindings`, `renderModelBindings`, `renderRepeat`, `renderShow`; the first three-plus-Show each do a full `querySelectorAll` and recompute **every** binding regardless of which key changed; `renderShow` also `JSON.parse`s each predicate on every pass | `runtime/bindings.py`, `runtime/show.py`, `state.py` (~L362) |
| `Show` toggles the `hidden` attribute on a server-rendered `<div data-ark-show>`; it does not mount/unmount | `runtime/show.py`, `page_render.py` (~L169) |
| `Repeat` already renders through the vendored snabbdom core (`init`/`h`/`vnode`/`htmldomapi` only, no optional modules) with a keyed diff and an 8-line lockstep adoption (`arkAdoptVnode`); key is `JSON.stringify(item)` | `runtime/repeat.py`, `backend/js/vdom.py` |
| `persist=True` keys are `"ark:" + pathname + ":" + key` -- **per page**, so the same key on two pages is two independent stores. `IRPage.persist` is a flat `list[str]` emitted as `data-ark-persist` | `state.py`, `ir/build.py` (~L107), `page_render.py` (~L491) |
| One `@page` function = one page; there are no dynamic route segments | `arklight/parser/discover.py` |
| The IR binary carries `app_shell` as a `u8`; `FORMAT_VERSION = 1` | `arklight/ir/binary.py` |

## Stage S1 -- View transitions

`Site(app_shell=True, transitions=True)` emits
`htmx.config.globalViewTransitions = true;` next to the existing
`allowEval` line. Nothing is written; htmx already implements it.

- **Validation:** `transitions=True` without `app_shell=True` is a
  compile error (same shape as `_validate_shell_persistent`).
- **Reduced motion:** emit the assignment behind
  `!matchMedia("(prefers-reduced-motion: reduce)").matches` so the
  default respects the user setting. Not optional.
- **Plumbing cost to decide here:** a new `Site` field must cross
  `api.py` -> `ir/build.py` -> `ir/binary.py`. Either bump
  `FORMAT_VERSION` (decoder keeps accepting 1) or pack booleans into a
  flags byte. This stage settles the convention S5 reuses.
- **Exit test:** flag off leaves output byte-identical (existing
  snapshot tests unchanged); flag on emits the guarded config line;
  binary round-trip covers the new field.
- **Open check:** confirm a `hx-preserve` element (`shell_persistent`)
  survives inside a view transition without flicker.

## Stage S2 -- Key-scoped state -> DOM updates

The largest stage, and the one that makes the docs' "reactivity
resolved at compile time" claim literally true. The fix is to stop
*searching* for what to update, not to touch how updates are applied
(the vendored core `patch` keeps doing every mutation).

1. **Changed-key contract.** `set(key, ...)`/`reset(key)` call
   `fn(key)`. Existing listeners ignore the argument, so this is
   backward compatible.
2. **Compile-time dependents map.** `Computed` already arrives in
   dependency order (`_topological_order_computed`). Emit
   `key -> [transitive dependent computed names]` per page, and turn
   `recomputeAll()` into a recompute of only the dependents of the
   changed key.
3. **Binding index, built once per `arkInitPage()`** (so it rebuilds
   after every boosted swap): `key -> [elements]` for
   `data-ark-bind`, `data-ark-bind-class`, and `data-ark-show`
   (indexed by every name in the predicate; the parsed predicate is
   cached on the entry, killing the per-mutation `JSON.parse`).
4. **Targeted render.** The subscriber receives the changed key,
   resolves `{key} ∪ dependents(key)`, and refreshes only those index
   entries. Model bindings and `Watch` are audited for the same
   treatment but not required to change in this stage.

- **`Show` is not moved onto the vdom path.** The `hidden` toggle is
  already O(1) and preserves inner state (form values, focus); a spec
  table would add cost for no gain. `Show` only needs the index.
- **Gating:** ship behind a `Site` flag (name provisional,
  e.g. `indexed_bindings=True`) so sites that don't opt in stay
  byte-identical. Promoting it to the default is a separate,
  measurement-backed decision, not part of this stage.
- **Invariant to verify:** `Repeat` item templates contain no
  `State`-bound nodes (the documented single-`item_value` limitation),
  so nodes created by `Repeat` never need to enter the index.
- **Exit test:** a **differential test** -- for generated sequences
  of `set`/`reset` calls, the indexed path and the current full-scan
  path leave identical DOM. Plus a counter test that a single-key
  mutation touches only that key's entries. Closes register #12/#13.

## Stage S3 -- `Repeat` item identity

`JSON.stringify(item)` as the key means `["Deploy", "Deploy"]` are not
independently identifiable (register #11).

- **Proposed default:** suffix the key with an occurrence counter
  (`stringify(item) + "#" + n`, n = how many equal items precede it),
  so duplicates get stable, distinct keys with no authoring change.
  Object items with a natural id are left for a follow-up.
- **Exit test:** append/remove/reorder over lists containing
  duplicates against the vendored core, asserting DOM order and no
  dropped or duplicated nodes. If the occurrence scheme proves
  unstable under reorder, this stage stops at documenting the limit
  rather than shipping a scheme that looks correct and isn't.

## Stage S4 -- Global-scope persistence

`State("cart", persist=True, scope="global")` stores under
`"ark:global:" + key` instead of the path-prefixed key, so the value
follows the visitor across every page. Default stays per-page.

- **Data shape:** do **not** change `data-ark-persist` (flat
  `list[str]`). Add a sibling `data-ark-persist-global`, emitted only
  when non-empty, and a second read/write loop. Existing sites stay
  byte-identical and no existing parser sees a new shape.
- **Compile-time collision check:** the compiler sees every page, so
  it can require that a key declared global on more than one page has
  the *same initial value* everywhere, and fail the build otherwise.
  This turns the obvious hazard (two pages meaning different things by
  one name) into a build error.
- **Validation:** `scope=` without `persist=True` is a compile error;
  `scope` accepts only `"page"` and `"global"`.
- **Same failure discipline as `persist`:** quota/private-browsing
  errors fall back to the initial value for that key only; `file://`
  caveat documented alongside the existing one.
- **Open check:** define precedence when a key is both
  `persist(scope="global")` and `query=` -- follow whatever the
  current `persist` vs `query` order is and pin it with a test.
- **Exit test:** value written on page A is read on page B (boosted
  and full-load); two-page conflicting initials fail the build.

## Stage S5 -- Prefetch

On hover/focus/touchstart of a same-origin boosted link, prefetch the
target once so the swap resolves from cache.

- **Decision to make first:** vendor htmx's separate preload
  extension (a second in-tree dependency, normally CDN-loaded) versus
  a small ARKlight-owned listener that injects one
  `<link rel="prefetch">` per URL. The addendum's recommendation is
  the small listener: narrower surface, no second vendored file.
- **Guards:** skip when `navigator.connection.saveData`; one prefetch
  per URL; only links htmx would boost.
- **Gating:** `Site(prefetch=True)`, requires `app_shell=True`.
- **Open check:** confirm prefetch requests are permitted by the CSP
  `csp.py` emits, and record the result in that module's docs.

## Stage S6 -- Static-params routes (design first)

A finite, build-time-known set of pages generated from one route
definition (the Astro `getStaticPaths` shape): the author enumerates
the values, the compiler emits one real static page per value. No
runtime matcher.

- This stage begins as a **short design note**, not code. The open
  questions are authoring surface (decorator argument vs. a
  helper), how each generated page gets its own `<title>`/state
  defaults, and how `discover.py`'s one-function-one-page assumption
  changes.
- No implementation commitment until that note is accepted.

## Order and why

`S1` first: it is nearly free and forces the `Site`-field plumbing
convention once. `S2` next because it carries the architectural weight
and closes real register items, and every later stage benefits from
the changed-key contract. `S3` and `S4` are small and independent.
`S5` is optional polish. `S6` is last because it is the only stage
that changes what a route *is*.

## Not in this ladder

- **Live external data / BaaS.** `Provider` stays a declaration; the
  code that talks to a backend is author-written JS outside the closed
  vocabulary, by design. Adding a backend does not change any stage
  above.
- **WASM / worker-pool compute.** Covered by
  `AVM-WASM-SANDBOX-PROPOSAL.md` and
  `REI-DYNAMIC-CLASS-WASM-PROPOSAL.md`, both unaccepted. One recorded
  interaction: AVM already notes workers do not survive app-shell
  navigations. Unresolved and not blocked on by this ladder.
- **Permanently out, unchanged from the proposal:** a general route
  table, a persistent client-side component tree, live non-serializable
  object identity across a page boundary, and any arbitrary-expression
  navigation.

## Status tracking

| Stage | What | Status |
| --- | --- | --- |
| S1 | View transitions (`Site(transitions=True)`), reduced-motion guard | PLANNED |
| S2 | Changed-key contract, dependents map, per-page binding index | PLANNED |
| S3 | `Repeat` occurrence-suffixed keys | PLANNED |
| S4 | `State(scope="global")` persistence | PLANNED |
| S5 | Link prefetch (`Site(prefetch=True)`) | PLANNED |
| S6 | Static-params routes | DESIGN NOTE FIRST |

## Definition of done (per stage)

Re-check the proposal's philosophy-fit checklist before merge; tests
under `tests/`; a line in the docs the stage changes; and once every
stage has shipped, roll up into `docs/version history/` and trim this
file per `docs/Implementation/README.md`.
