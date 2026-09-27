"""
`slice_string` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.slice(start, end)`, with `start`/`end` literal
integers. Negative indices count from the end; `end=None` (serialized
`null`) means "to the end" -- handled explicitly, because
`slice(0, null)` would coerce `null` to `0` and return `""`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("slice_string", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "slice_string"

JS_FRAGMENT = """    slice_string: function (state, names, args) {
      return String(state[names[0]]).slice(args.start, args.end === null ? undefined : args.end);
    }"""
