"""
Per-platform-API JS runtime fragments (`v0.065`).

Mirrors `arklight.backend.js.actions`/`arklight.backend.js.behaviors`:
each sibling module exports `NAME` (matching a key in
`arklight.ir.platform_api.PLATFORM_API_REGISTRY`) and `JS_FRAGMENT`
(that capability's `name: function (args) { ... }` dispatch-object
entry). This package is the Web backend's own implementation of the
platform interfaces the compiler-owned registry only *describes* --
see `arklight.ir.platform_api`'s module docstring for that split.
`JSBackend.render()` (`arklight/backend/js/render.py`) concatenates
only the fragments a given site's IR actually references into the
`platformApis` dispatch object, the same "only ship what's used"
discipline `ACTION_FRAGMENTS`/`BEHAVIOR_FRAGMENTS` already follow.

Adding a new platform API capability later is: one new module here
(`NAME` + `JS_FRAGMENT`), one new `PLATFORM_API_REGISTRY` entry (and a
`BACKEND_PLATFORM_API_SUPPORT["web"]` addition once this backend's
implementation actually exists), and a line in `PLATFORM_API_MODULES`
below -- never a change to `JSBackend`'s generation logic itself.
"""

from __future__ import annotations

from arklight.backend.js.platform_apis import clipboard_write, notify

PLATFORM_API_MODULES = {
    notify.NAME: notify,
    clipboard_write.NAME: clipboard_write,
}

# capability name -> that capability's JS dispatch-object entry (source text).
PLATFORM_API_FRAGMENTS: dict[str, str] = {
    name: module.JS_FRAGMENT for name, module in PLATFORM_API_MODULES.items()
}
