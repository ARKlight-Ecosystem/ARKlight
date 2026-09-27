"""
DOM render passes for reactive state: `renderBindings` (text content,
routed through the vendored snabbdom core -- see
`arklight.backend.js.vdom`) and `renderClassBindings` (a direct
`classList.toggle`, deliberately *not* routed through the vdom core --
see the docstring on `renderClassBindings` itself for why).

Split out of `arklight/backend/js/render.py`'s old `_STATE_CORE_JS`
(`refactor-0`). Pure move, no JS output change.
"""

from __future__ import annotations

RENDER_BINDINGS_JS = """  function renderBindings(store) {
    document.querySelectorAll("[data-ark-bind]").forEach(function (el) {
      // 0.06505: per-element guard (RUNTIME-ERROR-HANDLING-PROPOSAL.md,
      // 3a) -- one bad binding must not stop the rest of this pass, or
      // the render passes after it in the store.subscribe callback.
      try {
        var key = el.getAttribute("data-ark-bind");
        var text = String(store.get(key));
        var next = snabbdom.h(arkSelectorFor(el), {}, text);
        arkPatch(el.__arkVnode || el, next);
        el.__arkVnode = next;
      } catch (err) {
        arkReportError("A displayed value couldn't be updated -- part of this page may be out of date.", err);
      }
    });
  }

"""

RENDER_CLASS_BINDINGS_JS = """  function renderClassBindings(store) {
    // Stage 2 ("Reactive-core vdom staging"): a direct classList
    // toggle, not routed through the vendored vdom -- the bare core
    // doesn't carry snabbdom's optional classModule, and re-deriving
    // the element's selector to include/exclude the class would make
    // patch() treat it as a different vnode (sameVnode compares `sel`)
    // and remount the element, dropping any listeners already wired to
    // it. A one-line classList.toggle has none of that risk.
    document.querySelectorAll("[data-ark-bind-class]").forEach(function (el) {
      // 0.06505: per-element guard, same reasoning as renderBindings.
      try {
        var className = el.getAttribute("data-ark-bind-class");
        var key = el.getAttribute("data-ark-bind-class-state");
        el.classList.toggle(className, !!store.get(key));
      } catch (err) {
        arkReportError("A displayed value couldn't be updated -- part of this page may be out of date.", err);
      }
    });
  }

"""
