"""
Per-action JS runtime fragments (v0.0035).

Mirrors `arklight.backend.js.behaviors`: each sibling module exports
`NAME` (matching a key in `arklight.ir.schema.ACTION_REGISTRY`) and
`JS_FRAGMENT` (that action's `name: function (store, key, args) {
... }` entry). `JSBackend.render()` includes the reactive core (and
only the action fragments actually used) for a build only when at
least one page declares `State(...)`.
"""

from __future__ import annotations

from arklight.backend.js.actions import (
    append,
    decrement,
    fetch_json,
    geolocate,
    increment,
    remove,
    reset,
    set,
    toggle_bool,
)

ACTION_MODULES = {
    set.NAME: set,
    increment.NAME: increment,
    decrement.NAME: decrement,
    toggle_bool.NAME: toggle_bool,
    reset.NAME: reset,
    append.NAME: append,
    remove.NAME: remove,
    # `v0.063` (docs/version history/v0.063.md): JS vocabulary
    # addendum stage 3/10 -- one-shot geolocation write-back.
    geolocate.NAME: geolocate,
    # EXPERIMENTAL (docs/Proposals/FETCH-HTTP-AS-PRIMITIVE-PROPOSAL.md,
    # stage 2): same-origin/trusted-origin JSON fetch, write-back into
    # State(...). See arklight/backend/js/actions/fetch_json.py.
    fetch_json.NAME: fetch_json,
}

ACTION_FRAGMENTS: dict[str, str] = {
    name: module.JS_FRAGMENT for name, module in ACTION_MODULES.items()
}
