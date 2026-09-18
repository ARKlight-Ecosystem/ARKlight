"""
`clipboard_write` platform API fragment (`v0.065`, accepted from
`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`) -- the Web backend's own
implementation of the `clipboard_write` interface registered in
`arklight.ir.platform_api.PLATFORM_API_REGISTRY`. See `notify.py` in
this same package for the sibling shape this mirrors: a per-capability
module exporting `NAME` and `JS_FRAGMENT`, only shipped when a site's
IR actually uses it.

**Not a duplicate of the existing `copy` behavior**
(`arklight/backend/js/behaviors/copy.py`), even though both end up
calling `navigator.clipboard.writeText`: `copy` is a DOM-target
behavior -- it reads whatever text is currently sitting in the
element `data-ark-target` points at (a `<textarea>`'s `.value`, or
another element's `.textContent`), decided at *click time*. This
fragment instead writes the literal string an author already supplied
at build time via `PlatformAPI.clipboard_write("some text")` --
there's no DOM element to read from, and no "Copied!" label swap on
the clicked element the way `copy` does, since a `PlatformAPIRef` on
`on_click` carries only a capability name and its own JSON args, not
a `data-ark-target`. An author who wants "copy whatever's in this
input" reaches for `on_click="copy"`; an author who wants "copy this
exact known string" reaches for `PlatformAPI.clipboard_write(...)`.
Same underlying browser API, two different authoring shapes for two
different needs -- the same relationship `Action.geolocate` (a
state-mutating write-back) has to a hypothetical read-only "where am
I" platform API that doesn't exist yet.

Falls back to `arkNotify` if the Clipboard API isn't available at all
(insecure/non-HTTPS context, or a browser that never implemented it)
-- the same "never a thrown error, always a visible fallback" posture
`notify.py` and `Action.geolocate` both already hold for their own
missing-API case.
"""

from __future__ import annotations

NAME = "clipboard_write"

JS_FRAGMENT = """    clipboard_write: function (args) {
      var text = (args && args.text) || "";
      if (!navigator.clipboard) {
        arkNotify("Copying to the clipboard isn't available in this browser or context.");
        return;
      }
      navigator.clipboard.writeText(text).catch(function () {
        arkNotify("Couldn't copy to clipboard -- try selecting and copying the text manually.");
      });
    }"""
