"""
`renderShow`: `vdom-7` (docs/Backends/REFACTOR-INDEX.md row 15) --
the runtime half of `Show(predicate, ...)` (`arklight.api.Show`).

`docs/new js backend proposal/ARCHITECTURE-VDOM.md` SS6.3 proposes
`Show`/conditional rendering as a vnode swap between the real subtree
and a comment-node placeholder, through the vendored `patch()`
(`arklight/backend/js/vdom.py`) -- the same mechanism `vdom-7` gives
`Repeat` (see `repeat.py` in this package). This module deliberately
does *not* do that, and the reason is a real hydration bug, not a
style preference:

The vendored core is the *bare* snabbdom diff/patch algorithm with no
dedicated hydration pass -- `patch(realElement, vnode)` always starts
from `emptyNodeAt(realElement)`, which produces a synthetic vnode with
`children: []`, discarding any knowledge of the real DOM children
already there. Toggling the anchor's own `sel` between a real tag and
`"!"` (comment) -- literally what SS6.3 asks for -- means the *very
first* `renderShow` pass either (a) leaves stale server-rendered
content sitting next to a freshly created, empty vnode's-worth of
DOM (since nothing tells `patch()` to remove content it never knew
about), or (b) once a real toggle does happen, destroys the anchor
element itself (`removeVnodes` removes the *whole* old element when
`sel` differs), losing the one handle `querySelectorAll("[data-ark-
show]")` needs to find it again on the next state change. `repeat.py`
solves the equivalent problem for list items by manually adopting the
server-rendered DOM into a matching vnode tree before ever calling
`patch()` -- workable there because each item's shape is fully known
from `data-ark-repeat-template`. `Show`'s children can be *any*
arbitrary nested tree (including further `Bind(...)`/`Action.*(...)`),
so there is no equivalently cheap way to reconstruct "the real
subtree" as a vnode on demand.

Given that, `Show` uses the HTML `hidden` attribute instead -- a
content-visibility semantic (removes the subtree from the
accessibility tree), not a style declaration, so it doesn't reintroduce
the "smuggle a CSS decision into the JS backend" concern SS6.3 is
actually guarding against. The HTML backend
(`arklight/backend/html/page_render.py`'s `_render_show`) always
renders `Show`'s children (so there's real content to reveal even if a
page loads with the predicate false) and sets `hidden` up front when
the predicate is false against the page's *initial* state; this
function just keeps that attribute in sync with `predicate` afterward.
No diffing needed -- the subtree never changes shape, only whether
it's present to a visitor -- so nothing here touches `arkPatch`.

`renderShow(store)` is called once from `arkInitPage` right after
`initState()` (only on a page that actually uses `Show(...)` -- see
`arklight/backend/js/render.py`'s `has_show` gating) and again on every
`store.subscribe` notification (`arklight/backend/js/runtime/state.py`'s
`INIT_STATE_JS`, `typeof`-guarded the same way `renderModelBindings`/
`wireWatchers` already are).
"""

from __future__ import annotations

RENDER_SHOW_JS = """  function arkEvalPredicate(store, spec) {
    var names = spec.names;
    if (spec.kind === "equals") return store.get(names[0]) === store.get(names[1]);
    if (spec.kind === "gt") return store.get(names[0]) > store.get(names[1]);
    if (spec.kind === "lt") return store.get(names[0]) < store.get(names[1]);
    // 0.06517 (v0.066): the predicates catalog. Twins of
    // arklight/ir/js_predicate.py -- keep the two in step.
    if (spec.kind === "and") return names.every(function (n) { return !!store.get(n); });
    if (spec.kind === "or") return names.some(function (n) { return !!store.get(n); });
    if (spec.kind === "not") return !store.get(names[0]);
    if (spec.kind === "in_range") {
      var x = Number(store.get(names[0])) || 0;
      return (Number(store.get(names[1])) || 0) <= x && x <= (Number(store.get(names[2])) || 0);
    }
    if (spec.kind === "one_of") return spec.args.values.indexOf(store.get(names[0])) !== -1;
    if (spec.kind === "is_null") return store.get(names[0]) == null;
    if (spec.kind === "is_empty" || spec.kind === "is_not_empty") {
      var v = store.get(names[0]);
      var empty = v == null || ((typeof v === "string" || Array.isArray(v)) && v.length === 0);
      return spec.kind === "is_empty" ? empty : !empty;
    }
    var value = store.get(names[0]);
    return spec.kind === "falsy" ? !value : !!value;
  }

  function renderShow(store) {
    document.querySelectorAll("[data-ark-show]").forEach(function (el) {
      // 0.06505: per-element guard (RUNTIME-ERROR-HANDLING-PROPOSAL.md, 3a).
      try {
        var spec = JSON.parse(el.getAttribute("data-ark-show"));
        el.hidden = !arkEvalPredicate(store, spec);
      } catch (err) {
        arkReportError("A conditional section on this page couldn't be updated -- it may be showing stale content.", err);
      }
    });
  }

"""
