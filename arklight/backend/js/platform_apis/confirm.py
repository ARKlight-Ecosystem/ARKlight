"""
`confirm` platform API fragment (Stage 6 of `docs/Implementation/
INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md`) -- the Web
backend's own implementation of the `confirm` interface registered in
`arklight.ir.platform_api.PLATFORM_API_REGISTRY`. See `notify.py` in
this same package for the sibling shape this mirrors: a per-capability
module exporting `NAME` and `JS_FRAGMENT`, only shipped when a site's
IR actually uses it.

A one-shot read, same shape as `db.py`'s `get`/`keys` ops and
`Action.geolocate`: the boolean result is written into the
`State(...)` named by `into` rather than returned to any caller (there
is no return value in a compiled page). `window.confirm` is
synchronous, unlike `db`'s IndexedDB/bridge round-trip, so the write
happens immediately rather than inside a `.then(...)`.

Falls back to `arkNotify` if `window.confirm` isn't callable at all
(a sandboxed iframe that disables it, or an embedding context that
deleted the global) -- the same "never a thrown error, always a
visible fallback" posture `notify.py`/`clipboard_write.py`/`db.py` all
already hold for their own missing-API case.
"""

from __future__ import annotations

NAME = "confirm"

JS_FRAGMENT = """    confirm: function (args, store) {
      if (!store) return;
      var message = (args && args.message) || "";
      if (typeof window.confirm !== "function") {
        arkNotify("A confirmation prompt isn't available in this browser or context.");
        return;
      }
      var result;
      try {
        result = window.confirm(message);
      } catch (err) {
        arkNotify("Couldn't show the confirmation prompt -- try again.");
        return;
      }
      store.set(args.into, !!result);
    }"""
