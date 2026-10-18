"""
`fetch_json` action fragment -- EXPERIMENTAL
(docs/Proposals/FETCH-HTTP-AS-PRIMITIVE-PROPOSAL.md, stage 2 of that
proposal's own staged rollout; gated as
`arklight.experimental.FEATURES["fetch-json"]`).

Same "fire and forget" async shape `geolocate.py` already established
(see that module's docstring): `wireClickInterceptor`
(`arklight/backend/js/runtime/dispatch.py`) calls
`action(store, key, args)` and moves on without waiting for a return
value, so the `store.set(...)` call below happening inside a `.then()`
callback, after this function has already returned, is safe.

Two helpers this fragment calls but does not itself define --
`arkIsTrustedFetchURL` and `arkStripDangerousKeys` -- are emitted once,
ahead of the `actions` object, only when `"fetch_json"` is actually in
a build's `used_actions` (see `_fetch_trust_helpers_js` in
`arklight/backend/js/render.py`): the usual "only ship what's used"
discipline, and it keeps the two helpers in one place instead of
duplicated into every call site, since a future `State(..., fetch=...)`
(stage 3 of the proposal) would need the identical pair.

- **`arkIsTrustedFetchURL`** is the *runtime* half of the trust check.
  A literal `url=` string is already checked against
  `Site(trusted_fetch_origins=[...])` at build time
  (`arklight/ir/build.py`) -- this runtime check only matters for the
  `Bind(...)`-sourced case (`Action.fetch_json("r", url=Bind("q"))`),
  where the compiler cannot see the value ahead of time. Defense in
  depth, not the only check.
- **`arkStripDangerousKeys`** strips `__proto__`/`constructor`/
  `prototype` keys from the parsed JSON response, recursively, before
  it ever reaches `store.set`. See the proposal's \u00a73.1 for why: an
  inert `{"__proto__": {...}}` in the response becomes a real
  prototype-pollution path the moment any later `Derive`/`Bind`
  handling assigns fields from it into existing state without this
  check.
"""

from __future__ import annotations

NAME = "fetch_json"

JS_FRAGMENT = """    fetch_json: function (store, key, args) {
      var url = args.url;
      var method = args.method || "GET";
      if (typeof url !== "string" || !arkIsTrustedFetchURL(url)) {
        arkNotify("This fetch target isn't on the site's trusted-origin list.");
        return;
      }
      fetch(url, { method: method, headers: { "Accept": "application/json" } })
        .then(function (res) {
          if (!res.ok) { throw new Error("HTTP " + res.status); }
          return res.json();
        })
        .then(function (data) {
          store.set(key, arkStripDangerousKeys(data));
        })
        .catch(function () {
          arkNotify("Couldn't load that -- check your connection and try again.");
        });
    }"""
