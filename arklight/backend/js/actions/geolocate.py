"""
`geolocate` action fragment (`v0.063`, JS vocabulary addendum stage
3/10 -- see `docs/version history/v0.063.md`). See `set.py` for the
general shape.

Unlike every other action fragment, this one is asynchronous:
`navigator.geolocation.getCurrentPosition` is callback-based, so
`store.set(key, ...)` happens once the browser's location prompt
resolves, not before this function returns. That's safe here --
`wireClickInterceptor` (`arklight/backend/js/runtime/dispatch.py`)
calls `action(store, key, args)` and moves on without waiting for a
return value, the same "fire and forget" shape a debounced action's
deferred `setTimeout` callback already relies on. Writes a plain
`{lat, lng}` object into `key` -- a `Computed(...)`/`Bind(...)` can
read `key` as a whole (e.g. via `Derive.format`), but this doesn't
introduce per-field access into that object; that stays out of scope,
same as `Derive.count`'s "no per-field list-of-records access" note.
"""

from __future__ import annotations

NAME = "geolocate"

JS_FRAGMENT = """    geolocate: function (store, key, args) {
      if (!navigator.geolocation) {
        arkNotify("Geolocation isn't available in this browser or context.");
        return;
      }
      navigator.geolocation.getCurrentPosition(function (position) {
        store.set(key, { lat: position.coords.latitude, lng: position.coords.longitude });
      }, function () {
        arkNotify("Couldn't get your location -- check permissions and try again.");
      });
    }"""
