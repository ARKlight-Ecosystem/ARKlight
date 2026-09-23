"""
`renderRepeat`: `vdom-7` (docs/Backends/REFACTOR-INDEX.md row 15) --
the runtime half of `Repeat(name, template=...)` (`arklight.api.Repeat`).

Per `docs/new js backend proposal/ARCHITECTURE-VDOM.md` SS6.2, list
items are reconciled by *value*, not by index: each item's vnode `key`
is `JSON.stringify(item)` itself. That's a deliberate, documented
simplification for this stage -- it assumes no duplicate values in a
given list, the least-bad default for a plain value list with no
separate identity field of its own (there's also no in-place "edit
item" action shipped yet -- only `Action.append`/`Action.remove` --
so an item's rendered content never needs to change once created; only
whether/where it appears does). Keying by *index* was deliberately
rejected -- see SS6.2 -- since `Action.remove(name, i)` removing index
`i` would then make the vendored `patch()` treat every later item as
"the same key, new content" and re-render them all, instead of
recognizing that exactly one item left and the rest just shifted.

**The hydration problem, and why `renderRepeat`'s first call is
special.** The vendored core has no dedicated hydration pass (see
`show.py`'s docstring in this package for the fuller version of this
same problem) -- `patch()` always starts a fresh diff from
`emptyNodeAt(realElement)`, i.e. "this element has zero known
children," discarding whatever the HTML backend already rendered
there. Patching against that on page load would duplicate every
server-rendered item (the diff sees an empty old list and a full new
one, so it *creates* everything again) rather than reconciling against
it. So the first time `renderRepeat` runs for a given container, it
doesn't call `arkPatch` at all: it builds the same vnode tree a real
patch would, walks it down in lockstep with the container's actual
DOM children (`arkAdoptVnode`), and manually stamps `.elm` onto each
vnode from the matching real element -- "adopting" the server-rendered
markup as the baseline instead of re-creating it. This is sound
specifically *because* every real element and its vnode came from the
exact same template + item list (`data-ark-repeat-template` and the
store's current value for `name` agree by construction on load, before
any `Action.*(...)` has run) -- a general-purpose hydration algorithm
would need to handle mismatches; this doesn't, because there aren't
any. Every later call -- always triggered by an actual
`Action.append(...)`/`Action.remove(...)`, via `store.subscribe` -- is
a genuine `arkPatch()` diff against that adopted baseline.

Deliberately scoped to a *single* dynamic value per item (see
`arklight.api.Repeat`'s docstring for what that means for authors) and,
for a template's static attributes, `class`/`id` plus one
`on_click=Action.*(...)` per node (`arkApplyRepeatAttrs`) -- other
props render correctly for the items the server already produced
(`arklight/backend/html/page_render.py`'s `_render_repeat` goes
through the full, unrestricted `_render_node`/`_attr_string` pipeline
for those), but won't be reproduced for an item added purely
client-side via `Action.append(...)`. Both are real, documented
limitations of this stage -- see docs/Backends/REFACTOR-INDEX.md row
15 for what's left for a future version.
"""

from __future__ import annotations

RENDER_REPEAT_JS = """  function arkAdoptVnode(vnode, realElm) {
    vnode.elm = realElm;
    if (vnode.children && realElm) {
      for (var i = 0; i < vnode.children.length; i++) {
        arkAdoptVnode(vnode.children[i], realElm.children[i]);
      }
    }
  }

  function arkApplyRepeatAttrs(elm, spec, index) {
    var attrs = spec.attrs || {};
    Object.keys(attrs).forEach(function (name) { elm.setAttribute(name, attrs[name]); });
    if (spec.on_click) {
      elm.setAttribute("data-ark-on-click", "action:" + spec.on_click.action);
      elm.setAttribute("data-ark-action-state", spec.on_click.state);
      var args = {};
      var specArgs = spec.on_click.args || {};
      Object.keys(specArgs).forEach(function (key) {
        var value = specArgs[key];
        args[key] = (value && value.__item_index__) ? index : value;
      });
      elm.setAttribute("data-ark-action-args", JSON.stringify(args));
    }
  }

  function arkBuildRepeatVnode(spec, item, index) {
    var children;
    if (spec.text && spec.text.item_value) {
      children = String(item);
    } else if (typeof spec.text === "string") {
      children = spec.text;
    } else if (spec.children && spec.children.length) {
      children = spec.children.map(function (child) {
        return arkBuildRepeatVnode(child, item, index);
      });
    } else {
      children = [];
    }
    var data = {
      key: JSON.stringify(item),
      hook: {
        create: function (empty, vn) { arkApplyRepeatAttrs(vn.elm, spec, index); },
        update: function (old, vn) { arkApplyRepeatAttrs(vn.elm, spec, index); }
      }
    };
    return snabbdom.h(spec.tag, data, children);
  }

  function renderRepeat(store) {
    document.querySelectorAll("[data-ark-repeat]").forEach(function (container) {
      // 0.06505: per-container guard (RUNTIME-ERROR-HANDLING-PROPOSAL.md,
      // 3a) -- a malformed data-ark-repeat-template on one container must
      // not stop the other lists, or Show(...), from updating.
      try {
        var name = container.getAttribute("data-ark-repeat");
        var spec = JSON.parse(container.getAttribute("data-ark-repeat-template"));
        var list = store.get(name) || [];
        var vnodes = list.map(function (item, index) { return arkBuildRepeatVnode(spec, item, index); });
        if (!container.__arkRepeatInit) {
          // First call: the server already rendered exactly these items --
          // adopt the real DOM as the baseline vnode tree instead of
          // patching, so hydration never duplicates or discards
          // server-rendered content. Every later call (after a real
          // Action.append(...)/Action.remove(...)) patches for real.
          //
          // That "exactly these items" assumption can be false on the
          // very first call, though: `list`/`vnodes` come from the
          // store's *current* value for `name`, and `State(...,
          // persist=True)` overrides that value from localStorage
          // before this ever runs (see runtime/state.py's
          // `initState()`) -- so a returning visitor's stored list can
          // be a different length than what the server just rendered
          // for a fresh, unpersisted `initial=`. Adopting past the
          // shorter side only was leaving the mismatch as a silent
          // baseline: extra items the persisted list added were
          // recorded in `__arkVnode` as already on-screen (with no
          // real `.elm` behind them) without ever actually being
          // added to the DOM, and an item the persisted list dropped
          // was left rendered with nothing telling `__arkVnode` it was
          // still there -- either way, nothing visibly changed until
          // some later Action.*(...) triggered a real `arkPatch`
          // against that already-wrong baseline. Adopting only the
          // overlap, then patching for real when the lengths disagree,
          // makes the DOM match the store on this very first render
          // instead of waiting on a mutation that may never come.
          var real = container.children;
          var overlapLength = Math.min(vnodes.length, real.length);
          for (var i = 0; i < overlapLength; i++) {
            arkAdoptVnode(vnodes[i], real[i]);
          }
          var adopted = snabbdom.h(arkSelectorFor(container), {}, vnodes.slice(0, overlapLength));
          adopted.elm = container;
          container.__arkVnode = adopted;
          container.__arkRepeatInit = true;
          if (vnodes.length !== real.length) {
            var reconciled = snabbdom.h(arkSelectorFor(container), {}, vnodes);
            arkPatch(container.__arkVnode, reconciled);
            container.__arkVnode = reconciled;
          }
          return;
        }
        var next = snabbdom.h(arkSelectorFor(container), {}, vnodes);
        arkPatch(container.__arkVnode, next);
        container.__arkVnode = next;
      } catch (err) {
        arkReportError("A list on this page couldn't be updated -- it may be out of date.", err);
      }
    });
  }

"""
