"""
`notify` platform API fragment (`v0.065`, accepted from
`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`) -- the Web backend's own
implementation of the `notify` interface registered in
`arklight.ir.platform_api.PLATFORM_API_REGISTRY`. See
`arklight/backend/js/actions/geolocate.py` for the sibling shape this
mirrors: a per-capability module exporting `NAME` and `JS_FRAGMENT`,
only shipped when a site's IR actually uses it.

Deliberately asks for permission the first time it's needed rather
than assuming it's already granted (`Notification.permission ===
"granted"` is the only case that shows immediately), and falls back to
ARKlight's own in-page `arkNotify` banner if the `Notification`
constructor isn't available at all (Safari's aggressive restrictions,
an insecure/non-HTTPS context, or a browser that never implemented
it) -- the same "never a thrown error, always a visible fallback"
posture `Action.geolocate` already holds for its own missing-API case.
"""

from __future__ import annotations

NAME = "notify"

JS_FRAGMENT = """    notify: function (args) {
      var title = (args && args.title) || "";
      var body = (args && args.body) || "";
      if (typeof Notification === "undefined") {
        arkNotify(title || "Notification");
        return;
      }
      var show = function () {
        new Notification(title, { body: body });
      };
      if (Notification.permission === "granted") {
        show();
      } else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(function (permission) {
          if (permission === "granted") show();
        });
      }
    }"""
