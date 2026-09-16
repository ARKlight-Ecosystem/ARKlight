"""
Reactive state core: `createState` (the plain store: get/set/reset +
subscribe) and `initState` (reads `data-ark-state` off `<body>`, JSON
Notice-parses it, and wires the store's subscribers to the render
passes in `arklight.backend.js.runtime.bindings`).

Split out of `arklight/backend/js/render.py`'s old `_STATE_CORE_JS`
(`refactor-0`, see `docs/Backends/REFACTOR-INDEX.md`) -- pure move, no
JS output change. Mirrors the `actions/`/`behaviors/` per-file
pattern: `arklight.backend.js.runtime` reassembles these fragments in
the same order the monolithic string used to hold them.

`htmx-4` (docs/Backends/REFACTOR-INDEX.md row 9) changes where
`initState()` reads its JSON blob from. Per htmx's own docs, an
`hx-boost`ed swap replaces `<body>`'s *innerHTML* only, never the
`<body>` tag's own attributes -- so a `data-ark-state` attribute
placed directly on `<body>` would never update across an app-shell
boosted navigation to a different page. `arklight/backend/html/
page_render.py`'s `_render_page` accounts for this: on an
`app_shell=True` page with state, the JSON blob is instead emitted as
a `<div id="ark-state" data-ark-state="...">` marker that *is* part of
the swapped content. `initState()` below checks for that marker first
and falls back to the `<body>` attribute (the non-app_shell shape,
unchanged), so the same function handles both without needing to know
`app_shell` was set.

`vdom-4` (docs/Backends/REFACTOR-INDEX.md row 12): `createState` gains
a second, optional `computed` argument -- the same dependency-ordered
`(name, spec)` pairs `IRPage.computed` carries (see
`arklight/ir/build.py`), JSON-round-tripped as plain 2-element arrays
(`[["total", {"kind": "multiply", "names": [...], "args": {...}}],
...]`). A new `recomputeAll()` closure walks that list in order --
already a valid recompute order because `arklight.ir.build`'s
`_topological_order_computed` sorted it once at build time, so the
client never re-derives that ordering itself -- looking each entry's
`kind` up in the `derivations` object (`arklight/backend/js/
derivations/`, assembled into scope by `arklight/backend/js/
render.py`'s `_derivations_object_js`, the same "only ship what's
used" pattern `actions`/`behaviors` already follow) and writing the
result straight into `state` under that `Computed(...)`'s own `name`
-- so a `Computed(...)` value is readable through the exact same
`store.get(key)` every `Bind(...)`/`renderBindings` call already uses,
with no separate lookup path for computed vs. plain state.
`recomputeAll()` runs once at construction (so a value is already
present before the first render) and again at the end of every `set`/
`reset`, *before* that call's subscriber notification -- so a
subscriber (`renderBindings`/`renderClassBindings`) always sees
already-fresh computed values, never a stale one from before the
triggering mutation. `computed` defaults to an empty array on a page
with no `Computed(...)` declarations, in which case `recomputeAll()`
is a no-op and `derivations` (whose declaration is itself gated on
`has_computed` in `_build_runtime_js`) is never dereferenced.
`initState()` below reads the sibling `data-ark-computed` attribute
the same way it already reads `data-ark-state`, and passes it through.

`vdom-5` (docs/Backends/REFACTOR-INDEX.md row 13): `initState()` also
reads a sibling `data-ark-watch` attribute (`IRPage.watch`, the same
marker/`<body>`-attribute duality `data-ark-state`/`data-ark-computed`
already use) and, once the store is constructed, hands it to
`wireWatchers` (`arklight/backend/js/runtime/watch.py`) alongside the
existing `renderBindings`/`renderClassBindings` subscriber -- one more
kind of `store.subscribe` listener, per that module's docstring. The
call is guarded with `typeof wireWatchers === "function"` rather than
called unconditionally: `STATE_CORE_JS` (this fragment) ships on
*every* stateful page, but `WIRE_WATCHERS_JS` only ships on a page
that actually declares `Watch(...)` (see `arklight/backend/js/
render.py`'s `_build_runtime_js`) -- an unconditional call would throw
a `ReferenceError` on any stateful page with no watch effects at all,
`typeof` is the standard safe way to probe for a maybe-undeclared
identifier without that risk.

`vdom-6` (docs/Backends/REFACTOR-INDEX.md row 14): the `store.subscribe`
callback also calls `renderModelBindings(store)`
(`arklight/backend/js/runtime/model.py`), same `typeof`-guarded,
only-shipped-when-used pattern as `wireWatchers` just above -- a page
with no `bind_value=` anywhere never declares that function.

`vdom-7` (docs/Backends/REFACTOR-INDEX.md row 15): the same callback
also calls `renderRepeat(store)`/`renderShow(store)`
(`arklight/backend/js/runtime/repeat.py`/`show.py`), same
`typeof`-guarded, only-shipped-when-used pattern again -- a page with
no `Repeat(...)`/`Show(...)` never declares one or the other.

`vdom-8` (docs/Backends/REFACTOR-INDEX.md row 16): `initState()` also
reads a sibling `data-ark-persist` attribute (`IRPage.persist`, the
same marker/`<body>`-attribute duality every other `data-ark-*` piece
of hydration state already uses) -- a plain list of `State(...)` names
declared with `persist=True`. Unlike `computed`/`watch`, this doesn't
get passed into `createState` or a separate `runtime/*.py` module:
it's two small, self-contained steps, both scoped to their own
`try`/`catch` so a `localStorage` failure (private browsing, quota, a
hand-edited non-JSON value) degrades to "this key just doesn't
persist" rather than the page-wide "state couldn't be loaded" failure
the outer `try`/`catch` below produces.

1. *Read*, before `createState` is called: for each persisted key,
   look up `localStorage["ark:<location.pathname>:<key>"]` and, if
   present and JSON-parseable, use it to override that key's
   server-rendered initial value -- so a value survives a reload.
   `location.pathname` (not `page.route` from the build) is
   deliberate: this runtime file (`arklight.js`) is one shared file
   across every page (`SCRIPT_PATH`), so there is no page-specific
   build-time value to close over here -- the browser's own current
   URL is the only "which page is this" signal available at the point
   `initState()` runs, and it's already stable per page.
2. *Write*, as one more `store.subscribe` listener (registered only
   when `persist.length`, so a page with no persisted keys doesn't pay
   for an empty forEach on every state change): on every change,
   `JSON.stringify` each persisted key's current value back out to the
   same `localStorage` key the read step used.

Deliberately not plumbed through `createState`/a `derivations`-style
closed-vocabulary object, unlike `computed`: there's no dependency
graph, no derivation kind to look up, and no other module needs to
read `persist` -- it's purely "override on init, write on change,"
both of which `initState()` already touches every other piece of
hydration state at.

`v0.063` (JS vocabulary addendum, stage 3/10 -- see `docs/version
history/v0.063.md`): `initState()` also reads a sibling
`data-ark-media` attribute (`IRPage.media`, same marker/`<body>`-
attribute duality again) -- a list of `[name, query]` pairs for every
`State(..., media=...)` declared on the page. Same "override on init,
keep writing after that" shape `persist` above already establishes,
just sourced from `window.matchMedia` instead of `localStorage`:

1. *Override*, before `createState` is called: for each `[name,
   query]` pair, if `window.matchMedia` exists, override that key's
   server-rendered initial value with `matchMedia(query).matches` --
   so the very first render already reflects the *real* viewport,
   not just whatever guess `State(..., media=...)`'s own `initial=`
   argument server-rendered for a JS-disabled visitor.
2. *Listen*, once the store exists: attach one `"change"` listener per
   `MediaQueryList` (`mql.addEventListener`, falling back to the
   older `mql.addListener` for Safari versions that predate the
   standard event-target API) that calls `store.set(name, e.matches)`
   whenever the query's match state flips -- the live-updating half
   `persist` has no equivalent of (persisted state only ever changes
   through an explicit `Action.*(...)`/user input, never on its own).

Both steps are wrapped in their own `try`/`catch`, same degrade-
quietly discipline `persist`'s `localStorage` access already holds --
a media query the browser can't parse, or a very old browser lacking
`matchMedia` entirely, means this key just never updates on its own,
never a page-breaking error.
"""

from __future__ import annotations

CREATE_STATE_JS = """  function createState(initial, computed) {
    var state = Object.assign({}, initial);
    var listeners = [];
    function recomputeAll() {
      (computed || []).forEach(function (entry) {
        var name = entry[0];
        var spec = entry[1];
        var derive = derivations[spec.kind];
        if (derive) { state[name] = derive(state, spec.names, spec.args); }
      });
    }
    recomputeAll();
    return {
      get: function (key) { return state[key]; },
      set: function (key, value) {
        state[key] = value;
        recomputeAll();
        listeners.forEach(function (fn) { fn(); });
      },
      reset: function (key) {
        state[key] = initial[key];
        recomputeAll();
        listeners.forEach(function (fn) { fn(); });
      },
      subscribe: function (fn) { listeners.push(fn); }
    };
  }

"""

INIT_STATE_JS = """  function initState() {
    var marker = document.getElementById("ark-state");
    var raw = marker
      ? marker.getAttribute("data-ark-state")
      : document.body.getAttribute("data-ark-state");
    if (!raw) return null;
    var rawComputed = marker
      ? marker.getAttribute("data-ark-computed")
      : document.body.getAttribute("data-ark-computed");
    var rawWatch = marker
      ? marker.getAttribute("data-ark-watch")
      : document.body.getAttribute("data-ark-watch");
    var rawPersist = marker
      ? marker.getAttribute("data-ark-persist")
      : document.body.getAttribute("data-ark-persist");
    var rawMedia = marker
      ? marker.getAttribute("data-ark-media")
      : document.body.getAttribute("data-ark-media");
    try {
      var computed = rawComputed ? JSON.parse(rawComputed) : [];
      var watch = rawWatch ? JSON.parse(rawWatch) : [];
      var persist = rawPersist ? JSON.parse(rawPersist) : [];
      var media = rawMedia ? JSON.parse(rawMedia) : [];
      var initial = JSON.parse(raw);
      persist.forEach(function (key) {
        try {
          var saved = localStorage.getItem("ark:" + location.pathname + ":" + key);
          if (saved !== null) { initial[key] = JSON.parse(saved); }
        } catch (err) {
          // Private browsing, quota, or a hand-edited non-JSON value:
          // fall back to the server-rendered initial value for this
          // key alone -- never a page-wide failure.
        }
      });
      media.forEach(function (entry) {
        try {
          if (typeof window !== "undefined" && window.matchMedia) {
            initial[entry[0]] = matchMedia(entry[1]).matches;
          }
        } catch (err) {
          // A media query string the browser can't parse, or no
          // matchMedia support at all: keep the server-rendered guess
          // for this key alone -- never a page-wide failure.
        }
      });
      var store = createState(initial, computed);
      if (typeof window !== "undefined" && window.matchMedia) {
        media.forEach(function (entry) {
          try {
            var name = entry[0];
            var mql = matchMedia(entry[1]);
            var handler = function (e) { store.set(name, e.matches); };
            if (mql.addEventListener) { mql.addEventListener("change", handler); }
            else if (mql.addListener) { mql.addListener(handler); }
          } catch (err) {
            // Same degrade-quietly discipline as the override step
            // above -- this key just never updates live.
          }
        });
      }
      store.subscribe(function () {
        renderBindings(store);
        renderClassBindings(store);
        if (typeof renderModelBindings === "function") { renderModelBindings(store); }
        if (typeof renderRepeat === "function") { renderRepeat(store); }
        if (typeof renderShow === "function") { renderShow(store); }
      });
      if (persist.length) {
        store.subscribe(function () {
          persist.forEach(function (key) {
            try {
              localStorage.setItem("ark:" + location.pathname + ":" + key, JSON.stringify(store.get(key)));
            } catch (err) {
              // Private browsing or quota exceeded: this key just
              // doesn't persist, same degrade-quietly discipline as
              // the read side above.
            }
          });
        });
      }
      if (typeof wireWatchers === "function") { wireWatchers(store, watch); }
      return store;
    } catch (err) {
      arkNotify("This page's saved state couldn't be loaded -- interactive features on this page may not work.");
      return null;
    }
  }

"""
