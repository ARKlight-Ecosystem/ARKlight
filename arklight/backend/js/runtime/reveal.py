"""
`wireReveal`: `v0.063` (JS vocabulary addendum, stage 3/10 -- see
`docs/version history/v0.063.md`) -- the runtime half of
`on_reveal="reveal"` (`arklight.ir.schema.REVEAL_REGISTRY`).

Unlike every named `on_click=` behavior (wired through
`wireClickInterceptor`'s delegated `click` listener --
`arklight/backend/js/runtime/dispatch.py`), a reveal effect has no
click to hook: it needs to know when an element *enters the viewport*,
which only an `IntersectionObserver` -- not a DOM event -- can tell it.
So this is a small, separate mount-time wiring pass instead of one
more entry in the click-dispatched `behaviors` object, queried by its
own `data-ark-on-reveal` attribute (`arklight/backend/html/attrs.py`)
rather than `data-ark-on-click`.

`wireReveal()` finds every `[data-ark-on-reveal="reveal"]` element and
observes it with one shared `IntersectionObserver`. The first time an
observed element becomes intersecting, this adds its
`data-ark-toggle-class` (default `"is-visible"`, the same attribute/
default `toggle`/`dismiss` already use for their own toggle-class prop
-- see `arklight/backend/html/attrs.py`'s `BEHAVIOR_PROP_ATTRS`) and
immediately stops observing that element -- a one-shot reveal, not a
toggle that would remove the class again on scrolling away, matching
the common "fade/slide in once, on first reveal" pattern this exists
for. Browsers without `IntersectionObserver` support (a vanishingly
small, very old slice of the web -- every browser ARKlight otherwise
targets has shipped it for years) simply never add the class; the
guarded early return leaves the element exactly as authored (no
`is-visible`/etc. class), the same "degrade to inert, never throw"
discipline `copy`/`paste`/`geolocate` already hold for their own
missing-browser-API guards.

Called once from `arkInitPage()` (`arklight/backend/js/render.py`),
alongside `highlightActiveNavLink()` -- not just at first
`DOMContentLoaded` but also, on an `app_shell=True` site, after every
boosted navigation settles, so a reveal element newly swapped into the
page still gets observed. Re-running this on every `arkInitPage()`
call is safe/idempotent even for elements already on the page from a
prior call: `IntersectionObserver.observe()` on an already-observed
element is a documented no-op in the spec, not a duplicate
registration, so a plain (non-boosted) page's single `DOMContentLoaded`
call and a boosted site's repeated `arkInitPage()` calls behave
identically for elements that persist across a swap.
"""

from __future__ import annotations

WIRE_REVEAL_JS = """  function wireReveal() {
    if (typeof window === "undefined" || !("IntersectionObserver" in window)) return;
    var elements = document.querySelectorAll('[data-ark-on-reveal="reveal"]');
    if (!elements.length) return;
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        var className = el.getAttribute("data-ark-toggle-class") || "is-visible";
        el.classList.add(className);
        observer.unobserve(el);
      });
    });
    elements.forEach(function (el) { observer.observe(el); });
  }

"""
