"""
JS Backend.

v0.003 milestone (extended in v0.003, then again in v0.0035). ARKlight
does not compile Python to JavaScript, and components do not accept
arbitrary JS strings -- both would break "the browser never executes
Python" in spirit and "one obvious way" in practice (every site
inventing its own inline-JS dialect). Instead, following the same model
as Alpine.js/htmx (describe behavior with HTML attributes; a small
shipped runtime does the rest, no build step), ARKlight ships one
static `arklight.js` implementing a fixed, documented vocabulary:

- `toggle`     -- toggles a CSS class on `target` element(s). Which
                  class is controlled by `toggle_class` (default
                  "is-open"). This is enough for menus, accordions,
                  and disclosure widgets without writing any JS.
- `scroll-to`  -- smooth-scrolls `target` into view.
- `copy`       -- copies `target`'s text content to the clipboard, and
                  briefly swaps the clicked element's own text to
                  confirm it worked (a "Copy" button next to a code
                  snippet or a share link).
- `dismiss`    -- adds `toggle_class` (default "hidden") to `target`
                  element(s) and leaves it there -- a one-way hide, for
                  closing a banner/alert/cookie-notice permanently
                  rather than toggling it back and forth.

A component opts in with `on_click="toggle"` (or `"scroll-to"`,
`"copy"`, `"dismiss"`) plus a `behavior_target="<css selector>"` prop --
validated against `arklight.ir.schema.KNOWN_BEHAVIORS` at the
Validation stage, so a typo in a behavior name is caught at build time,
not silently ignored in the browser.

v0.0035 adds a second, closed vocabulary on top of the above: reactive
page state. A page that declares `State("count", 0)` gets a small
reactive core (a `createState` store, a `data-ark-bind` re-render pass,
and an action dispatcher) plus only the `Action.*` fragments
(`arklight/backend/js/actions/`) that page's `on_click=` values
actually reference. Pages with no `State(...)` get none of this --
same "only ship what's used" discipline v0.0035 also brought to the
named-behavior runtime below. See docs/DESIGN-NOTES.md ("v0.0035:
stateful JS -- capability, not vocabulary") for the full design.

Every behavior/action fragment here is a small, statically-readable JS
function -- there is no `eval`, no `new Function`, no string ever
executed as code. The registries (`arklight.ir.schema.BEHAVIOR_REGISTRY`
/ `ACTION_REGISTRY`) are what's open to new *data*; the runtime itself
never becomes a general-purpose interpreter.

The runtime also auto-highlights the current page's nav link (any `<a>`
inside `.nav` whose resolved URL matches the current page) with an
`is-active` class -- zero wiring required, since every site with a
`nav()` gets this for free.

Stage 1 (staged reactive-core expansion, see
`arklight/backend/js/vdom.py`): pages with state now re-render their
`data-ark-bind` elements through a vendored snabbdom core (`init` +
`h`, no optional modules) instead of a raw `el.textContent = ...`
assignment. Behavior is unchanged from the outside -- this only swaps
the re-render mechanism for a real diff/patch algorithm, so later
stages (list rendering, conditional show/hide, attribute binding) have
a diffing engine to build on instead of each hand-rolling one.

Stage 2 adds reactive class binding: `bind_class=Bind.when("active",
"is-active")` toggles a class as `active`'s truthiness changes,
compiled to `data-ark-bind-class="<class>"` +
`data-ark-bind-class-state="<key>"`. This one deliberately does *not*
go through the vdom core -- the bare vendored core has no class
module, and re-deriving an element's vdom selector to add/remove a
class would make `patch()` treat it as a different vnode and remount
the element (dropping any already-wired listeners) -- so it's a
direct, one-line `classList.toggle` instead, run in its own pass
(`renderClassBindings`) alongside `renderBindings`.

Stage 3 adds event modifiers: `Action.set("saved", True).debounce(300)`
/ `Action.remove("items", 0).with_modifiers("prevent", "stop", "once")`
attach `prevent`/`stop`/`once`/`debounce:<ms>`/`throttle:<ms>` tokens
(`arklight.ir.schema.MODIFIER_REGISTRY`) to an `ActionRef`. At Stage 3
these compiled to `data-ark-modifiers="prevent,debounce:300"`, read by
one small shipped wrapper, `arkApplyModifiers`, that decided
*if*/*when* the underlying action actually ran. `htmx-2` (below)
replaced that attribute and wrapper with `hx-trigger` compiled at
build time. `prevent` is, and always was, honored by construction:
`wireActions`'s click listener unconditionally calls
`event.preventDefault()` regardless of any modifier, so there was
never a second effect for that particular token to add. Named
behaviors (`on_click="toggle"`, etc.) have no modifier-attaching API
yet -- deliberately left for a future addendum rather than
speculatively wired up now.

`htmx-1` (see `docs/Backends/HTMX-INTEGRATION.md` "Stage 1 --
Behaviors" / `docs/Backends/REFACTOR-INDEX.md` row 4) replaces the
named-behavior wiring pass with HTMX. `wireBehaviors()` and its
`_behaviors_block` are gone -- there is no more `DOMContentLoaded`
query/`addEventListener` loop over `[data-ark-on-click]` elements,
because `arklight/backend/html/attrs.py` now compiles a string
`on_click` straight to `hx-on:click="arkRunBehavior('<name>', this)"`
and HTMX's own attribute-processing pass (which runs on page load and
on any DOM HTMX subsequently swaps in, not just once at
`DOMContentLoaded`) does the wiring instead. What stays on the
ARKlight side is only what HTMX has no equivalent for: the closed
`behaviors` dispatch object itself (still just the four
`BEHAVIOR_FRAGMENTS` entries this site's IR actually references, same
"only ship what's used" discipline as before) and a one-line
`arkRunBehavior(name, el)` wrapper that looks a name up in it and
guards the call in `try`/`catch` -- the same guarantee
`wireBehaviors()`'s per-element `try`/`catch` used to give, just
scoped per-*call* instead of per-*wiring-pass* now that there is no
wiring pass to wrap. Both are attached to `window` because HTMX
evaluates `hx-on:click`'s value in the browser's normal (non-strict,
non-module) global scope, not inside this file's own IIFE closure --
see `arklight/backend/js/htmx.py`'s module docstring for why the two
scripts don't otherwise need to share scope.

Vendored HTMX itself (`arklight/backend/js/htmx.py`, upstream 2.0.10,
Zero-Clause BSD) ships whenever a page uses a named behavior *or*
declares state -- see `_build_runtime_js`'s `needs_htmx`. State-only
pages don't yet emit any `hx-*` attribute (that's `htmx-2`/`htmx-3`
territory: modifiers and `Action.*` dispatch still go through
`data-ark-modifiers`/`wireActions()` unchanged by this stage), but
`docs/Backends/REFACTOR-INDEX.md` row 4 scopes HTMX's inclusion to
"behaviors or state" rather than "behaviors only" so that landing
`htmx-2`/`htmx-3` later doesn't also have to touch this
already-shipped condition.

`htmx-2` (see `docs/Backends/HTMX-INTEGRATION.md` "Stage 2 --
Modifiers" / `docs/Backends/REFACTOR-INDEX.md` row 5) removes
`arkApplyModifiers` entirely -- `arklight/backend/html/attrs.py` now
compiles an `ActionRef`'s modifier tokens into an `hx-trigger`
attribute at build time instead of the `data-ark-modifiers` attribute
this runtime used to parse, so there is no attribute left for a
runtime parser to read. `wireActions` (`runtime/dispatch.py`) no
longer wraps its dispatch through that function -- it calls the action
directly on every click, same as before Stage 3 existed. This is a
deliberate, documented, temporary gap: `hx-trigger` is compiled into
the page's markup by this stage, but nothing reads it as a *trigger*
yet, so `debounce`/`throttle`/`once`/`stop` have no runtime effect at
this point. `prevent` is unaffected either way, per Stage 3's note
above. **This remained true through `htmx-5`** -- the delegated click
listener `htmx-3` built never grew modifier-timing enforcement either,
despite the design doc's original expectation that it would; see
`runtime/dispatch.py`'s module docstring, "Bug fix (post-`htmx-5`...)"
section, for where and how that gap was finally closed.

`htmx-3` (see `docs/Backends/HTMX-INTEGRATION.md` "Stage 3 -- Replace
`wireActions()` wiring loop" / `docs/Backends/REFACTOR-INDEX.md` row 6)
deletes `wireActions`'s `querySelectorAll('[data-ark-on-click^=
"action:"]')`/`forEach`/per-element-`addEventListener` loop entirely.
In its place, `runtime/dispatch.py`'s `ACTION_INTERCEPTOR_JS` registers
one delegated `click` listener on `document` (`wireActionInterceptor`)
that resolves the clicked element via `Element.closest()` -- a single
registration instead of a per-element wiring pass, matching the "audit
and remove hand-rolled plumbing" spirit `htmx-2` left for this stage.
See `runtime/dispatch.py`'s module docstring for why this is a
delegated native `click` listener rather than the literal
`htmx:beforeRequest` interceptor `HTMX-INTEGRATION.md` describes: that
event is only dispatched by HTMX's own request path, which requires a
request-verb attribute (`hx-get`/`hx-post`/etc) that `Action.*(...)`
buttons -- being client-local, not server requests -- deliberately
never carry, so wiring only through it would silently drop every
unmodified action button's click handling. `data-ark-on-click="action:
..."`/`data-ark-action-state`/`data-ark-action-args` are unchanged --
`REFACTOR-INDEX.md` row 6 scopes this stage to the JS backend only.
`initState()`/`renderBindings()`/`renderClassBindings()` are
untouched; only the `DOMContentLoaded` call site's `wireActions(store)`
becomes `wireActionInterceptor(store)` below.

`htmx-4` (see `docs/Backends/JS-BACKEND-REFACTOR-PLAN.md` "The
app-illusion problem, stated precisely" / `docs/Backends/
REFACTOR-INDEX.md` row 9) is app-shell navigation:
`Site(app_shell=True)` (see `arklight/backend/html/page_render.py`)
emits `hx-boost="true"` on `<body>`, so same-origin link clicks become
an in-place AJAX swap instead of a full document reload -- the fix for
packaging backends (Android/KaiOS/Desktop) wrapping ARKlight's
otherwise real multi-page output in a shell whose whole purpose is to
*not* look like a browser. This stage's audit surfaced two gaps a
boosted swap opens that the runtime as it stood through `htmx-3`
didn't handle:

1. **`needs_htmx` below now also ships HTMX for `ir.app_shell` alone**
   -- previously gated on "a named behavior or `State(...)` is used
   *anywhere on the site*" (see the `htmx-1` paragraph above), which
   left a real gap: `arklight.js` is one shared file across every page
   (`SCRIPT_PATH`), but a plain nav-only page in an `app_shell` site
   with no behaviors or state used *anywhere* would previously have
   shipped without HTMX loaded at all -- `hx-boost` requires HTMX's
   own click-interception to do anything, so clicking away from such a
   page would have silently fallen back to a real document navigation.
2. **`DOMContentLoaded` only ever fires once per real document
   load; a boosted swap doesn't refire it.** Nothing before this
   stage re-ran nav-link highlighting or (re-)hydrated a page's
   `State(...)` after navigating to a *different* page via a boosted
   link -- `highlightActiveNavLink()`/`initState()`/`renderBindings()`/
   `renderClassBindings()` all ran exactly once, at the very first
   page load, and never again. `arkInitPage()` below is the same init
   logic, just named and made re-callable: wired to `DOMContentLoaded`
   unconditionally (unchanged initial-load behavior) and, only for
   `app_shell` sites, to htmx's own `"htmx:afterSettle"` event too --
   the standard hook for "new content just settled into the DOM."
   `wireActionInterceptor` is registered exactly once regardless (see
   `runtime/dispatch.py`'s module docstring for why re-registering it
   on every boosted swap would be a bug, and how the getter-based
   signature avoids it).

Also see `arklight/backend/html/page_render.py`'s `_render_page`
docstring for a third gap this stage fixes on the HTML side: why a
state page's `data-ark-state` blob moves off `<body>` (whose own
attributes a boosted swap never updates) when `app_shell=True`.

`htmx-5` (see `docs/Backends/HTMX-INTEGRATION.md` "Stage 4 -- Audit
and remove remaining hand-rolled plumbing" / `docs/Backends/
REFACTOR-INDEX.md` row 10) is this project's own "audit and remove
hand-rolled plumbing that HTMX already duplicates" mandate cutting the
other way: `htmx-1`'s `hx-on:click="arkRunBehavior('<name>', this)"`
turned out to route every named-behavior click through HTMX's own
`Function`-from-string dispatch (see `runtime/dispatch.py`'s module
docstring for the precise mechanism) -- an eval-equivalent operation
this very docstring's opening paragraph already promises ARKlight
never does ("there is no eval, no new Function, no string ever
executed as code"), and the promise did not carve out an exception for
a vendored dependency's own optional attribute-processing feature.
This stage removes `hx-on:click` from ARKlight's output entirely: a
named behavior now compiles to `data-ark-on-click="behavior:<name>"`
(see `arklight/backend/html/attrs.py`), read by the same delegated
`click` listener `htmx-3` already built for `Action.*(...)` --
`wireActionInterceptor` is renamed `wireClickInterceptor` and gains a
`behavior:` branch alongside its existing `action:` one. `arkBehaviors`
/`arkRunBehavior` (window-attached, so HTMX's attribute evaluation
could reach them) are gone; the closed behavior-dispatch object is now
a plain local `behaviors` var, read by closure the same way `actions`
already was. A behavior-only page (no `State(...)`) now ships no HTMX
at all -- `hx-on:click` processing was the only reason it ever needed
to. As defense-in-depth, `_build_runtime_js` also sets
`htmx.config.allowEval = false` whenever HTMX does ship, closing the
handful of other vendored-HTMX code paths (`hx-vals`/`hx-vars`,
bracket-syntax `hx-trigger` filters) that construct a function from a
string -- paths ARKlight's compiler never emits into, but which this
line stops relying on "never emits" alone to guarantee.

`vdom-4` (see `docs/Backends/REFACTOR-INDEX.md` row 12) adds
computed/derived state: `Computed(name, deps=(...), derive=Derive.*(...))`
(`arklight.api`). A page that declares at least one `Computed(...)`
gets one more closed-vocabulary object alongside `actions`/
`behaviors` -- `derivations` (`arklight/backend/js/derivations/`,
only the `Derive.*` kinds that page's IR actually uses, same "only
ship what's used" discipline) -- and `createState`
(`runtime/state.py`) is extended to recompute every `Computed(...)`
value, in the dependency order `arklight.ir.build` already sorted at
build time, after every `set`/`reset` and once more at construction.
No new dispatch mechanism and no new markup pass: a `Computed(...)`
value lives in the exact same state object a `State(...)` value does,
so `Bind(...)`/`bind_class=` read it through the unmodified
`renderBindings`/`renderClassBindings` passes.

`vdom-5` (see `docs/Backends/REFACTOR-INDEX.md` row 13) adds watch
effects: `Watch(name, then=Action.*(...))` (`arklight.api.Watch`). A
page that declares at least one `Watch(...)` gets `wireWatchers`
(`arklight/backend/js/runtime/watch.py`) spliced in and called once
from `initState()`, registering one more `store.subscribe` listener
that re-dispatches the exact same `actions` object `on_click=
Action.*(...)` already uses, just triggered by a state-change
notification instead of a click. `_collect_usage` folds a `Watch(...)`
's `then.action` into the same `used_actions` set an `on_click=
Action.*(...)` reference would, so `actions` ships with exactly the
fragments a site's IR needs either way -- but a watch-only page (no
clickable `Action.*(...)`/named behavior anywhere) ships `actions`
without also shipping the click interceptor it would never use (see
`needs_actions_object` vs. `needs_click_interceptor` in
`_build_runtime_js`).

`v0.065` (`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`) adds Platform
APIs: `PlatformAPI.notify(...)`/`PlatformAPI.clipboard_write(...)`
(`arklight.api.PlatformAPI`), compiled to a `PlatformAPIRef` on
`on_click=` the same way `Action.*(...)` compiles to an `ActionRef`.
A page that references at least one gets one more closed-vocabulary
object alongside `actions`/`behaviors` -- `platformApis`
(`arklight/backend/js/platform_apis/`, only the capabilities that
page's IR actually uses, same "only ship what's used" discipline) --
dispatched by the same click interceptor's new `"platform:"` branch
(`runtime/dispatch.py`). Unlike `Action.*(...)`, a Platform API call
never targets `State(...)`, so it never touches `needs_actions_object`
the way a `Watch(...)` does -- it only ever affects
`needs_click_interceptor`, exactly like a named behavior. Before any
of this runtime is assembled, `check_backend_support` (`arklight.ir.
platform_api`) fails the build with a named-capability diagnostic if
this site references a capability the "web" backend (this module,
`arklight.backend.html`, `arklight.backend.css` together) doesn't yet
implement -- currently only relevant for a future `android`/`desktop`
backend, since "web" implements every capability the compiler-owned
registry currently knows about.
"""

from __future__ import annotations

from arklight.ast.nodes import ActionRef, ModelBindSpec, PlatformAPIRef
from arklight.backend.base import Backend
from arklight.backend.js.actions import ACTION_FRAGMENTS
from arklight.backend.js.behaviors import BEHAVIOR_FRAGMENTS
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.backend.js.htmx import HTMX_JS
from arklight.backend.js.platform_apis import PLATFORM_API_FRAGMENTS
from arklight.ir.platform_api import check_backend_support
from arklight.backend.js.runtime import CLICK_INTERCEPTOR_JS as _CLICK_INTERCEPTOR_JS
from arklight.backend.js.runtime import NAV_HIGHLIGHT_JS as _NAV_HIGHLIGHT_JS
from arklight.backend.js.runtime import NOTIFY_JS as _NOTIFY_JS
from arklight.backend.js.runtime import RENDER_MODEL_BINDINGS_JS as _RENDER_MODEL_BINDINGS_JS
from arklight.backend.js.runtime import RENDER_REPEAT_JS as _RENDER_REPEAT_JS
from arklight.backend.js.runtime import RENDER_SHOW_JS as _RENDER_SHOW_JS
from arklight.backend.js.runtime import STATE_CORE_JS as _STATE_CORE_JS
from arklight.backend.js.runtime import WIRE_MODEL_BINDING_JS as _WIRE_MODEL_BINDING_JS
from arklight.backend.js.runtime import WIRE_QUERY_SYNC_JS as _WIRE_QUERY_SYNC_JS
from arklight.backend.js.runtime import WIRE_REVEAL_JS as _WIRE_REVEAL_JS
from arklight.backend.js.runtime import WIRE_WATCHERS_JS as _WIRE_WATCHERS_JS
from arklight.backend.js.vdom import SNABBDOM_CORE_JS
from arklight.ir.build import IRNode, WebsiteIR

# Where the HTML backend expects to find the generated runtime,
# relative to the output directory root.
SCRIPT_PATH = "arklight.js"

# _NOTIFY_JS / _NAV_HIGHLIGHT_JS / _STATE_CORE_JS used to be defined
# inline here as triple-quoted string constants. `refactor-0` (see
# docs/Backends/REFACTOR-INDEX.md) split them into
# arklight/backend/js/runtime/{state,bindings,modifiers,dispatch,nav,
# notify}.py, mirroring the actions/ and behaviors/ per-file pattern.
# The values imported above are byte-for-byte identical to the old
# inline constants -- pure refactor, no generated JS output change.


def _walk(node: IRNode):
    yield node
    for child in node.children:
        if isinstance(child, IRNode):
            yield from _walk(child)


def _collect_usage(
    ir: WebsiteIR,
) -> tuple[
    set[str], set[str], set[str], bool, set[str], bool, bool, bool, bool, bool, bool, bool, set[str]
]:
    """
    Inspect the site's IR for what the runtime actually needs to ship:
    which named behaviors are referenced, which actions are referenced
    by an `on_click=Action.*(...)` specifically (`used_on_click_actions`
    -- the click interceptor only ever needs to ship for *this* set,
    see `_build_runtime_js`), the full set of actions referenced by
    either `on_click=` or a `Watch(...)`'s `then=` (`used_actions`,
    `vdom-5` -- see below; this is what `_actions_object_js` reads),
    whether any page declares state at all, which derivation kinds are
    referenced by a `Computed(...)` (`vdom-4`, docs/Backends/
    REFACTOR-INDEX.md row 12), whether any page declares a
    `Computed(...)` at all, whether any page declares a `Watch(...)` at
    all (`vdom-5`, docs/Backends/REFACTOR-INDEX.md row 13), whether any
    node anywhere uses `bind_value=` (`vdom-6`, docs/Backends/
    REFACTOR-INDEX.md row 14), and whether any page uses `Repeat(...)`/
    `Show(...)` at all (`vdom-7`, docs/Backends/REFACTOR-INDEX.md row
    15) -- an `on_click=Action.*(...)` nested inside a `Repeat(...)`'s
    template is still a normal `IRNode` in the tree (it's the compiled
    template `IRNode`, not a separate declaration pulled out like
    `Computed`/`Watch` are), so the `_walk` loop below already picks it
    up into `used_on_click_actions`/`used_actions` without any special
    case. Also returns `has_reveal` (`v0.063`) -- whether any node
    anywhere carries `on_reveal=` -- gating `WIRE_REVEAL_JS`/
    `wireReveal()` the same "only ship what's used" way `has_repeat`/
    `has_show` gate their own runtime pieces, and independent of
    `has_state`: a reveal effect never reads or writes `State(...)`.
    Also returns `has_query` (`v0.064`) -- whether any page declares a
    query-tracked `State(..., query=...)` -- gating `WIRE_QUERY_SYNC_JS`/
    `wireQuerySync()` the same "only ship what's used" way. Unlike
    `has_reveal`, this one implies `has_state` (`query=` is only ever
    a prop on a `State(...)` node), but is still tracked separately:
    the read/write halves of this same feature are folded
    unconditionally into `STATE_CORE_JS` whenever `has_state` alone
    (see `arklight/backend/js/runtime/state.py`'s module docstring),
    while `wireQuerySync` -- the `popstate` listener -- is genuinely
    new runtime surface only worth shipping when at least one page
    actually uses it.

    Also returns `used_platform_apis` (`v0.065`) -- the set of
    `PlatformAPI.*(...)` capability names referenced by any
    `on_click=` anywhere, the `PlatformAPIRef` sibling of
    `used_on_click_actions`'s `ActionRef` handling. Folded into
    `needs_click_interceptor` in `_build_runtime_js` exactly like
    `used_behaviors`/`used_on_click_actions` are, since a
    `PlatformAPIRef` click is dispatched by that same interceptor
    (see `arklight/backend/js/runtime/dispatch.py`'s `"platform:"`
    branch) -- never folded into `used_actions`, since a Platform API
    call never targets `State(...)` the way `Action.*(...)`/`Watch(...)`
    do.
    """
    used_behaviors: set[str] = set()
    used_on_click_actions: set[str] = set()
    used_platform_apis: set[str] = set()
    has_state = any(page.state for page in ir.pages)
    used_derivations: set[str] = {
        spec["kind"] for page in ir.pages for _name, spec in page.computed
    }
    has_computed = any(page.computed for page in ir.pages)
    has_watch = any(page.watch for page in ir.pages)
    has_query = any(page.query for page in ir.pages)
    has_model_binding = False
    has_repeat = False
    has_show = False
    has_reveal = False

    for page in ir.pages:
        for node in _walk(page.root):
            on_click = node.props.get("on_click")
            if isinstance(on_click, str):
                used_behaviors.add(on_click)
            elif isinstance(on_click, ActionRef):
                used_on_click_actions.add(on_click.action)
            elif isinstance(on_click, PlatformAPIRef):
                used_platform_apis.add(on_click.capability)
            if isinstance(node.props.get("bind_value"), str) and node.props.get("bind_value"):
                has_model_binding = True
            elif isinstance(node.props.get("bind_value"), ModelBindSpec):
                has_model_binding = True
            if node.type == "Repeat":
                has_repeat = True
            elif node.type == "Show":
                has_show = True
            if node.props.get("on_reveal"):
                has_reveal = True

    # vdom-5: a Watch(...)'s `then=` reuses the exact same
    # ACTION_REGISTRY dispatcher an on_click=Action.*(...) does (see
    # arklight/backend/js/runtime/watch.py), so its action needs the
    # same "only ship what's used" fragment -- folded into the
    # broader `used_actions` set `_actions_object_js` reads, kept
    # separate from `used_on_click_actions` (which alone decides
    # whether the *click interceptor* is needed -- a watch effect
    # never involves a click).
    used_watch_actions: set[str] = {
        entry["then"]["action"] for page in ir.pages for entry in page.watch
    }
    used_actions = used_on_click_actions | used_watch_actions

    return (
        used_behaviors,
        used_on_click_actions,
        used_actions,
        has_state,
        used_derivations,
        has_computed,
        has_watch,
        has_model_binding,
        has_repeat,
        has_show,
        has_reveal,
        has_query,
        used_platform_apis,
    )


def _behaviors_object_js(used_behaviors: set[str]) -> str:
    # htmx-5 (docs/Backends/REFACTOR-INDEX.md row 10; see
    # arklight/backend/js/runtime/dispatch.py's module docstring for
    # the full audit finding): this used to build `arkBehaviors` +
    # `arkRunBehavior`, both attached to `window` so vendored HTMX's
    # `hx-on:click="arkRunBehavior('<name>', this)"` attribute
    # processing could call them -- which meant every behavior click
    # ran through HTMX's `Function`-from-string dispatch, violating
    # this project's own "no eval, no new Function" invariant (see
    # this module's docstring). Now this just builds the closed
    # dispatch object itself, `behaviors` -- still only the fragments
    # this site's IR actually references, "only ship what's used"
    # unchanged -- as a plain local `var`, not attached to `window`.
    # `wireClickInterceptor` (`runtime/dispatch.py`) reads it directly
    # via closure, the same way it already reads `actions` below; the
    # per-call try/catch guard that used to live in the now-deleted
    # `arkRunBehavior` wrapper lives in that interceptor's behavior
    # branch instead.
    fragments = [
        BEHAVIOR_FRAGMENTS[name] for name in sorted(used_behaviors) if name in BEHAVIOR_FRAGMENTS
    ]
    if not fragments:
        return "  var behaviors = {};\n"
    entries = ",\n".join(fragments)
    return "  var behaviors = {\n" + entries + "\n  };\n"


def _actions_object_js(used_actions: set[str]) -> str:
    # htmx-5: split out of the old `_actions_block`, which bundled
    # this declaration together with `_STATE_CORE_JS` (createState/
    # bindings/initState) because both only ever shipped inside the
    # `if has_state:` branch below. That coupling no longer holds --
    # `wireClickInterceptor` needs an `actions` object declared
    # whenever it ships, and it now ships for behavior-only pages too
    # (no `State(...)` anywhere), where `_STATE_CORE_JS` correctly
    # still doesn't ship. The two are assembled independently in
    # `_build_runtime_js` now; `actions` stays an empty object on a
    # behavior-only page (the interceptor's action branch is simply
    # never reached there -- no element carries `data-ark-on-click=
    # "action:..."` without `State(...)` to act on, an existing,
    # unchanged invariant enforced by `arklight.ir.validate`).
    fragments = [
        ACTION_FRAGMENTS[name] for name in sorted(used_actions) if name in ACTION_FRAGMENTS
    ]
    if not fragments:
        return "  var actions = {};\n"
    entries = ",\n".join(fragments)
    return "  var actions = {\n" + entries + "\n  };\n"


def _platform_apis_object_js(used_platform_apis: set[str]) -> str:
    # `v0.065`: mirrors `_behaviors_object_js` exactly -- only the
    # `PlatformAPI.*(...)` capabilities this site's IR actually
    # references, assembled as a plain local `var` `wireClickInterceptor`
    # (`runtime/dispatch.py`'s `"platform:"` branch) reads by closure.
    # `check_backend_support` (called from `_build_runtime_js`) is
    # what actually enforces that every capability here is one the
    # "web" backend implements -- this function only ever emits
    # fragments for capabilities `PLATFORM_API_FRAGMENTS` has, same
    # "only ship what's used" discipline as its siblings.
    fragments = [
        PLATFORM_API_FRAGMENTS[name] for name in sorted(used_platform_apis) if name in PLATFORM_API_FRAGMENTS
    ]
    if not fragments:
        return "  var platformApis = {};\n"
    entries = ",\n".join(fragments)
    return "  var platformApis = {\n" + entries + "\n  };\n"


def _derivations_object_js(used_derivations: set[str]) -> str:
    # vdom-4 (docs/Backends/REFACTOR-INDEX.md row 12): mirrors
    # `_actions_object_js`/`_behaviors_object_js` exactly -- only the
    # `Derive.*` kinds this site's IR actually references, assembled
    # as a plain local `var`, read by `createState`'s `recomputeAll()`
    # closure (`runtime/state.py`) the same way that function already
    # reads nothing else external. Only ever called when
    # `has_computed` is true (see `_build_runtime_js` below), which
    # itself implies `has_state` (every `Computed(...)` dependency
    # chain bottoms out at a real `State(...)`, enforced by
    # Validation) -- so this always lands inside the `if has_state:`
    # branch, alongside `STATE_CORE_JS`.
    fragments = [
        DERIVATION_FRAGMENTS[name] for name in sorted(used_derivations) if name in DERIVATION_FRAGMENTS
    ]
    if not fragments:
        return "  var derivations = {};\n"
    entries = ",\n".join(fragments)
    return "  var derivations = {\n" + entries + "\n  };\n"


def _build_runtime_js(ir: WebsiteIR) -> str:
    (
        used_behaviors,
        used_on_click_actions,
        used_actions,
        has_state,
        used_derivations,
        has_computed,
        has_watch,
        has_model_binding,
        has_repeat,
        has_show,
        has_reveal,
        has_query,
        used_platform_apis,
    ) = _collect_usage(ir)

    # `v0.065`: every `PlatformAPI.*(...)` capability this site's IR
    # references must be one the "web" backend (this JS backend, plus
    # its HTML/CSS siblings -- see `arklight.ir.platform_api`'s module
    # docstring for that naming) actually implements. Raises
    # `PlatformAPIError` -- a `CompileError`-wrapping failure, per
    # `arklight.compiler.pipeline.build` -- naming every unsupported
    # capability at once rather than silently dropping the request or
    # deferring the failure to runtime (Section 11 of the proposal).
    # Deliberately run unconditionally, even when `used_platform_apis`
    # is empty: `check_backend_support` is a no-op in that case, so
    # this costs nothing on the common site that uses no Platform API
    # at all.
    check_backend_support(used_platform_apis, backend_name="web")

    # htmx-5 (docs/Backends/REFACTOR-INDEX.md row 10): the click
    # interceptor now dispatches both actions and behaviors, and needs
    # shipping whenever either is used -- independent of has_state
    # (a behavior-only page has no State(...) at all; see
    # runtime/dispatch.py's module docstring). `vdom-5`: deliberately
    # keyed off `used_on_click_actions`, not the broader `used_actions`
    # -- a page with only `Watch(...)` effects and no `on_click=
    # Action.*(...)`/named behavior anywhere needs the `actions`
    # object (see `needs_actions_object` below) but never the click
    # interceptor itself, since a watch effect never involves a click.
    # `v0.065`: `used_platform_apis` joins `used_behaviors`/
    # `used_on_click_actions` here -- a `PlatformAPI.*(...)` click is
    # dispatched by this same interceptor's `"platform:"` branch (see
    # `runtime/dispatch.py`), never involves `State(...)`, and so
    # never needs `needs_actions_object` the way a `Watch(...)` does.
    needs_click_interceptor = bool(used_behaviors) or bool(used_on_click_actions) or bool(used_platform_apis)

    # vdom-5: `actions` is needed whenever the click interceptor is
    # (unchanged) *or* whenever any page declares a `Watch(...)` --
    # `wireWatchers` (`runtime/watch.py`) reads the same closed
    # dispatch object by closure. Split out from
    # `needs_click_interceptor` so a watch-only page (no clickable
    # Action.*(...)/behavior anywhere) ships `actions` without also
    # shipping the click interceptor it would never use.
    needs_actions_object = needs_click_interceptor or has_watch

    # htmx-1 (docs/Backends/REFACTOR-INDEX.md row 4) originally shipped
    # vendored HTMX whenever a page used a named behavior or declared
    # state, because named behaviors wired through HTMX's own
    # hx-on:click attribute processing. htmx-5 removes that wiring
    # (see runtime/dispatch.py's module docstring for why: hx-on:click
    # constructs a function from a string internally, which this
    # project's own "no eval, no new Function" invariant doesn't
    # permit) -- named behaviors no longer touch any hx-* attribute at
    # all, so they're dropped from this condition. What's left: state
    # (hx-trigger on Action.* modifiers, htmx-2) and ir.app_shell alone
    # (hx-boost/hx-preserve, htmx-4 -- see this module's docstring,
    # htmx-4 paragraph, point 1, for why a plain nav-only page in an
    # app_shell site still needs HTMX loaded even with no
    # behaviors/state used anywhere). A behavior-only page -- the
    # common "toggle a menu, nothing else" case -- now ships no HTMX at
    # all.
    needs_htmx = has_state or ir.app_shell

    parts: list[str] = [
        "// Generated by ARKlight -- v0.0035 runtime + Stage 1-2 of the",
        "// reactive-core vdom staging (vdom core, class binding), plus",
        "// htmx-2 (Action.* event modifiers compile to hx-trigger",
        "// instead of a shipped modifier-parsing runtime function),",
        "// htmx-4 (Site(app_shell=True) boosts navigation via",
        "// hx-boost; page init re-runs after a boosted swap, not just",
        "// at first load), and htmx-5 (one delegated click listener",
        "// dispatches both Action.*(...) and named behaviors -- see",
        "// arklight/backend/js/runtime/dispatch.py -- instead of",
        "// behaviors routing through vendored HTMX's own hx-on:click",
        "// attribute processing).",
        "// Implements only the named behaviors and Action.*(...)",
        "// references this site actually uses -- see",
        "// arklight.ir.schema.BEHAVIOR_REGISTRY / ACTION_REGISTRY /",
        "// MODIFIER_REGISTRY. No other JavaScript runs on this site.",
        "// Pages with state also carry a vendored snabbdom core",
        "// (init + h, no optional modules) -- see",
        "// arklight/backend/js/vdom.py. Pages with Computed(...)",
        "// (vdom-4) also carry only the Derive.*(...) kinds that",
        "// page's IR actually uses -- see",
        "// arklight/backend/js/derivations/.",
    ]

    if needs_htmx:
        parts.append("")
        parts.append(HTMX_JS)
        parts.append("")
        # htmx-5, defense-in-depth: ARKlight's compiler never emits
        # hx-vals/hx-vars or bracket-syntax hx-trigger event filters --
        # the other paths inside vendored HTMX that construct a
        # function from a string (see runtime/dispatch.py's module
        # docstring) -- so this has no effect on anything ARKlight
        # itself generates. It closes those paths at the source rather
        # than relying solely on "the compiler just never emits that"
        # as the only guarantee, matching this project's "no string is
        # ever executed as code" invariant even for optional vendored-
        # dependency features ARKlight doesn't use.
        parts.append("htmx.config.allowEval = false;")
        # Runtime policy enforcement (arklight/backend/html/csp.py):
        # vendored HTMX's core swap path already avoids Trusted-Types-
        # gated sinks (it parses via DOMParser, not `innerHTML=`), with
        # one exception -- `Wn()`'s indicator-style injection calls
        # `head.insertAdjacentHTML(...)`, which `require-trusted-types-
        # for 'script'` (the CSP directive `csp.py` always sets) would
        # otherwise block outright. ARKlight already ships its own
        # generated stylesheet (`STYLESHEET_PATH`) that this feature's
        # indicator CSS is redundant with, so disabling it here removes
        # the one remaining incompatible sink instead of registering a
        # Trusted Types policy to permit it -- same "close the path
        # instead of trusting it" choice `allowEval = false` above
        # already made for htmx's other optional features.
        parts.append("htmx.config.includeIndicatorStyles = false;")

    parts.append("")
    parts.append("(function () {")
    parts.append('  "use strict";')
    parts.append("")

    needs_notify = needs_click_interceptor or has_state
    if needs_notify:
        parts.append(_NOTIFY_JS)
        parts.append("")

    if has_state:
        parts.append(SNABBDOM_CORE_JS)
        parts.append("")
        if has_computed:
            parts.append(_derivations_object_js(used_derivations))
        parts.append(_STATE_CORE_JS)
        parts.append("")
        if has_model_binding:
            # vdom-6: `renderModelBindings` is only ever meaningful on
            # a stateful page (bind_value= is validated against
            # State(...) names -- see arklight.ir.validate), and only
            # shipped when at least one node actually uses it, same
            # "only ship what's used" discipline as WIRE_WATCHERS_JS.
            parts.append(_RENDER_MODEL_BINDINGS_JS)
        if has_repeat:
            # vdom-7: `renderRepeat` is only ever meaningful on a
            # stateful page (`Repeat(...)`'s `name` is validated
            # against a `State(...)`/`Computed(...)` name), and only
            # shipped when at least one page actually uses it, same
            # "only ship what's used" discipline as the two above.
            parts.append(_RENDER_REPEAT_JS)
        if has_show:
            # vdom-7: same reasoning as has_repeat above, for
            # `Show(...)`/`renderShow`.
            parts.append(_RENDER_SHOW_JS)

    # vdom-5: `actions` ships whenever the click interceptor needs it
    # (unchanged) or whenever any page declares a `Watch(...)` --
    # `needs_actions_object` covers both; `behaviors`/the interceptor
    # itself stay gated on `needs_click_interceptor` alone, since a
    # watch effect never dispatches a named behavior or needs a click
    # listener.
    if needs_actions_object:
        parts.append(_actions_object_js(used_actions))
    if needs_click_interceptor:
        parts.append(_behaviors_object_js(used_behaviors))
        parts.append(_platform_apis_object_js(used_platform_apis))
        parts.append(_CLICK_INTERCEPTOR_JS)
        parts.append("")
    if has_watch:
        parts.append(_WIRE_WATCHERS_JS)

    if has_model_binding:
        # vdom-6: `wireModelBinding` is the input-side counterpart to
        # `wireClickInterceptor` -- one delegated `input` listener,
        # registered once (see the getter/ready_calls handling below
        # for why), rather than a per-element wiring pass.
        parts.append(_WIRE_MODEL_BINDING_JS)
        parts.append("")

    if has_reveal:
        # `v0.063`: independent of `has_state` -- a reveal effect
        # never reads or writes `State(...)`, it just needs
        # `wireReveal()` itself declared before `arkInitPage()` calls
        # it below.
        parts.append(_WIRE_REVEAL_JS)

    if has_query:
        # `v0.064`: `wireQuerySync` needs declaring before
        # `DOMContentLoaded` registers it below (see `ready_calls`) --
        # same "declare, then register once" shape `has_model_binding`
        # above already follows.
        parts.append(_WIRE_QUERY_SYNC_JS)

    parts.append(_NAV_HIGHLIGHT_JS)
    parts.append("")

    # htmx-4: DOMContentLoaded only ever fires once per real document
    # load, but a boosted navigation (app_shell's hx-boost) swaps
    # <body>'s content in place with no new DOMContentLoaded event --
    # so nothing would otherwise re-run for the page just swapped in.
    # arkInitPage() is the same init logic prior stages ran directly
    # inside the DOMContentLoaded handler, just named and made
    # re-callable, so it can also run after a boosted swap settles.
    if has_state:
        parts.append("  var arkStore = null;")
        parts.append("")

    init_body = ["    highlightActiveNavLink();"]
    if has_reveal:
        # `v0.063`: called every time `arkInitPage()` runs -- first
        # load and, on an app_shell site, every boosted swap after
        # that -- so an element newly brought in by a boosted
        # navigation still gets observed. See `wireReveal`'s own
        # docstring for why re-observing an already-observed element
        # on a later call is safe.
        init_body.append("    wireReveal();")
    if has_state:
        init_body.append("    arkStore = initState();")
        render_calls = "renderBindings(arkStore); renderClassBindings(arkStore);"
        if has_model_binding:
            render_calls += " renderModelBindings(arkStore);"
        if has_repeat:
            render_calls += " renderRepeat(arkStore);"
        if has_show:
            render_calls += " renderShow(arkStore);"
        init_body.append(f"    if (arkStore) {{ {render_calls} }}")

    parts.append("  function arkInitPage() {")
    parts.extend(init_body)
    parts.append("  }")
    parts.append("")

    # `getter` is shared by wireClickInterceptor and (vdom-6)
    # wireModelBinding below -- both take a zero-argument getter
    # rather than a fixed store value, for the same app_shell-boosted-
    # navigation reason documented on runtime/dispatch.py's
    # wireClickInterceptor: registered exactly once, must keep reading
    # whatever arkStore most recently holds without re-registering a
    # second, stale-closure listener on every boosted swap.
    getter = "function () { return arkStore; }" if has_state else "function () { return null; }"

    ready_calls = ["    arkInitPage();"]
    if needs_click_interceptor:
        # Registered exactly once, here -- never from inside
        # arkInitPage() itself, and never again on a later boosted
        # swap. document is never replaced by hx-boost, so a second
        # registration would stack a second listener closing over a
        # now-stale store, double-firing every click. The getter
        # closure (see runtime/dispatch.py) always reads whatever
        # arkStore currently holds, so one registration is enough for
        # the lifetime of the page, boosted navigation or not. A
        # behavior-only page (no has_state) has no arkStore at all --
        # its getter always returns null, which the interceptor's
        # action branch's existing `if (!store) return;` guard already
        # handles (that branch is unreachable on such a page anyway:
        # no element carries data-ark-on-click="action:..." without
        # State(...) to act on).
        ready_calls.append(f"    wireClickInterceptor({getter});")
    if has_model_binding:
        # Same "register exactly once, getter closure" contract as
        # wireClickInterceptor above -- has_model_binding implies
        # has_state (bind_value= is only ever validated against a
        # State(...) name), so this getter is never the always-null
        # variant in practice, but shares the same expression either
        # way for consistency.
        ready_calls.append(f"    wireModelBinding({getter});")
    if has_query:
        # Same "register exactly once, getter closure" contract as
        # wireClickInterceptor/wireModelBinding above -- has_query
        # implies has_state (query= is only ever a prop on a
        # State(...) node), so this getter is never the always-null
        # variant in practice either. `wireQuerySync` (`arklight/
        # backend/js/runtime/query.py`) re-reads the current page's
        # own data-ark-query/data-ark-state attributes fresh on every
        # popstate event rather than closing over them at registration
        # -- the getter closure alone is enough for it to stay correct
        # across an app_shell boosted swap to a different page.
        ready_calls.append(f"    wireQuerySync({getter});")

    parts.append('  document.addEventListener("DOMContentLoaded", function () {')
    parts.extend(ready_calls)
    parts.append("  });")

    if ir.app_shell:
        # "htmx:afterSettle" is htmx's own post-swap-and-settle
        # lifecycle event -- the app-shell equivalent of
        # DOMContentLoaded for content a boosted navigation just
        # brought in. Only registered for app_shell sites: on a plain
        # site hx-boost is never active, so this event never fires and
        # the extra listener would be dead weight.
        parts.append("")
        parts.append('  document.body.addEventListener("htmx:afterSettle", arkInitPage);')

    parts.append("})();")
    parts.append("")

    return "\n".join(parts)


class JSBackend(Backend):
    name = "js"

    def render(self, ir: WebsiteIR) -> dict[str, str]:
        return {SCRIPT_PATH: _build_runtime_js(ir)}
