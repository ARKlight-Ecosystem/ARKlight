"""
`wireQuerySync`: `v0.064` (docs/Proposals/URL-STATE-AS-PRIMITIVE-
PROPOSAL.md, `docs/version history/v0.064.md`) -- the back/forward
half of `State(..., query=...)` (`arklight.api.State`).

Per the proposal's §3.5: nothing in ARKlight's shipped runtime
listened for `popstate` before this -- there is no SPA router, so
there was never a reason to. This is genuinely new runtime surface,
not an extension of an existing mechanism (unlike the read/write
pieces in `arklight/backend/js/runtime/state.py`'s `initState()`,
which fall directly out of the `persist=True`/`media=` precedent), so
it gets its own file, the same way `watch.py` got its own file for
`Watch(...)` rather than being folded into `STATE_CORE_JS`.

`wireQuerySync(getter)` is registered exactly once, from
`arklight/backend/js/render.py`'s `DOMContentLoaded` handler --
`getter` is the same zero-argument `function () { return arkStore; }`
closure `wireClickInterceptor`/`wireModelBinding` already take, for
the same app_shell-boosted-navigation reason documented on
`runtime/dispatch.py`: `window` is never replaced by `hx-boost`, so a
`popstate` listener registered once, here, outlives any number of
later boosted swaps -- it just needs to keep reading whatever
`arkStore` most recently holds, not close over a store fixed at
registration time.

Unlike `wireWatchers(store, specs)`, this doesn't take the page's
`data-ark-query` manifest as an argument at registration time -- on an
`app_shell` site, a boosted navigation can swap in a *different* page
with a different (or empty) set of query-tracked keys, and the one
`window`-level listener registered here has to stay correct across
that swap without being re-registered. So each `popstate` event re-
reads whichever manifest is on the page *right now* (the state
marker/`<body>` attribute the currently-displayed page's own
`initState()` call already populated), the same "read fresh, don't
close over something that can go stale" reasoning `getter` itself
already follows for `arkStore`.

A key present in the URL's query string overrides that key's current
value via `store.set(...)`, coerced the same way `initState()`'s own
override step coerces it (`"int"`/`"bool"`/`"str"`); a key *not*
present in the query string (the visitor navigated back to a URL that
never had this param at all) falls back to that key's own server-
rendered default -- read from the same `data-ark-state` JSON blob
`initState()` already parsed, so "no `page` param" and "the page this
site shipped with no `page` param baked in" behave identically. Both
directions fail open per key, in their own `try`/`catch`, same
discipline every other read in this feature already holds -- a
malformed value, or a store with no matching key at all, degrades to
"this key doesn't update on this particular `popstate`", never a
page-breaking error.

Deliberately does *not* re-write the URL after applying these changes
-- `state.py`'s own write-back `store.subscribe` listener (registered
inside `initState()`) already fires from the `store.set(...)` calls
below, and its own before/after-URL equality check (see that file's
module docstring, "v0.064" section, step 2) already makes that a
no-op when the value it would write is the value the browser already
navigated to. No separate "am I currently handling a popstate" guard
needed here either, for the same reason.
"""

from __future__ import annotations

WIRE_QUERY_SYNC_JS = """  function wireQuerySync(getter) {
    window.addEventListener("popstate", function () {
      var store = getter();
      if (!store) return;
      var marker = document.getElementById("ark-state");
      var rawQuery = marker
        ? marker.getAttribute("data-ark-query")
        : document.body.getAttribute("data-ark-query");
      if (!rawQuery) return;
      var rawState = marker
        ? marker.getAttribute("data-ark-state")
        : document.body.getAttribute("data-ark-state");
      try {
        var query = JSON.parse(rawQuery);
        var defaults = rawState ? JSON.parse(rawState) : {};
        var searchParams = new URLSearchParams(location.search);
        query.forEach(function (entry) {
          var name = entry[0];
          var param = entry[1];
          var typeTag = entry[2];
          try {
            if (searchParams.has(param)) {
              var raw = searchParams.get(param);
              var value = raw;
              if (typeTag === "int") {
                value = parseInt(raw, 10);
                if (isNaN(value)) { throw new Error("not an int: " + raw); }
              } else if (typeTag === "bool") {
                if (raw === "true") { value = true; }
                else if (raw === "false") { value = false; }
                else { throw new Error("not a bool: " + raw); }
              }
              store.set(name, value);
            } else if (Object.prototype.hasOwnProperty.call(defaults, name)) {
              store.set(name, defaults[name]);
            }
          } catch (err) {
            // Malformed query value on this particular popstate: leave
            // this key's current value alone -- never a page-breaking
            // error, same fail-open discipline every other read in
            // this feature already holds.
          }
        });
      } catch (err) {
        // data-ark-query/data-ark-state couldn't be parsed at all:
        // this navigation just doesn't sync query state, same
        // degrade-quietly posture as initState()'s own outer catch.
      }
    });
  }

"""
