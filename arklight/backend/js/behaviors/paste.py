"""
`paste` behavior fragment (`v0.063` -- see `docs/version history/
v0.063.md`). See `copy.py`, which this mirrors almost exactly (same
`data-ark-target` selector, same clipboard-availability guard), just
reading instead of writing: `navigator.clipboard.readText()` into
`target`'s `.value` (an `Input`/`Textarea`) or `.textContent`
otherwise.

Writing into `.value` also dispatches a real `input` event on the
target -- so if that element also carries `bind_value=Bind.model(...)`
(`vdom-6`), pasting picks up the two-way binding's own `wireModelBinding`
listener (`arklight/backend/js/runtime/model.py`) exactly as if the
visitor had typed the pasted text, writing it into `State(...)` too.
An element with no such binding is unaffected either way -- dispatching
an event nobody's listening for is a no-op.
"""

from __future__ import annotations

NAME = "paste"

JS_FRAGMENT = """    paste: function (el) {
      var selector = el.getAttribute("data-ark-target");
      if (!selector) return;
      var target = document.querySelector(selector);
      if (!target || !navigator.clipboard) {
        arkNotify("Paste isn't available in this browser or context.");
        return;
      }
      navigator.clipboard.readText().then(function (text) {
        if (target.tagName === "TEXTAREA" || target.tagName === "INPUT") {
          target.value = text;
          target.dispatchEvent(new Event("input", { bubbles: true }));
        } else {
          target.textContent = text;
        }
      }).catch(function () {
        arkNotify("Couldn't paste from clipboard -- check permissions and try again.");
      });
    }"""
