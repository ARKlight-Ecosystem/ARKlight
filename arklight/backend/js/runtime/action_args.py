"""
`resolveActionArgs`: the runtime half of the live-input -> action-value
capability fix (`Action.append("tasks", Bind("draft"))`, see
`arklight.api.Action`, `arklight.ast.nodes.STATE_REF_KEY`,
`docs/Proposals/ACTION-VALUE-FROM-STATE-PROPOSAL.md`).

An `ActionRef`'s args reach the browser as JSON -- in
`data-ark-action-args` for an `on_click=`, in the `data-ark-watch` blob
for a `Watch(...)`'s `then=`. A literal arg is just its value. An arg
that reads state is the marker object `{"__state__": "<name>"}`;
this function swaps each such marker for `store.get(<name>)` and hands
the resulting plain args object to the action fragment, which never
learns a marker existed -- so `set`/`append` (and any future action
that opts an argument into `ActionSpec.state_args`) are unchanged.

Resolved at *dispatch time*, not render time -- "the value at the
moment the action runs". For a click that means after any
`.debounce(...)` delay, which is what a debounced Add button should
read. Always returns a fresh object; the parsed args of a `Watch(...)`
live for the whole page, so mutating them in place would bake the
first resolved value in permanently.

No eval, no `new Function`: `name` is only ever used as a key into the
store, and `store.get` of an unknown key is simply `undefined`
(Validation has already refused a name that isn't declared, so that
only happens for a hand-built IR).

Unlike `WIRE_WATCHERS_JS`'s and `CLICK_INTERCEPTOR_JS`'s other
helpers this is not a top-level function of its own: it's declared
*inside* each of the two functions that dispatch actions, from this one
shared source string (a plain `for` loop, not `forEach`, so
`tests/test_htmx_3.py`'s "no per-element loop in the interceptor"
assertion keeps meaning what it says), so each of those fragments stays a
self-contained unit (the existing Node-driven tests evaluate
`WIRE_WATCHERS_JS` on its own, with only `actions`/`createState`
stubbed around it) and neither grows a new cross-fragment dependency
`render.py` would have to assemble in the right order.
"""

from __future__ import annotations

RESOLVE_ACTION_ARGS_JS = """    function resolveActionArgs(store, args) {
      var resolved = {};
      var keys = Object.keys(args);
      for (var k = 0; k < keys.length; k++) {
        var value = args[keys[k]];
        var isStateRef = value !== null && typeof value === "object" &&
          !Array.isArray(value) && typeof value.__state__ === "string";
        resolved[keys[k]] = isStateRef ? store.get(value.__state__) : value;
      }
      return resolved;
    }
"""
