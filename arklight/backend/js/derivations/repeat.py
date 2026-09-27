"""
`repeat` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.repeat(count)`, with `count` a literal `0`-`1000`
(build-time checked -- a negative count would be a `RangeError` on
every client recompute).

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("repeat", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "repeat"

JS_FRAGMENT = """    repeat: function (state, names, args) {
      return String(state[names[0]]).repeat(args.count);
    }"""
