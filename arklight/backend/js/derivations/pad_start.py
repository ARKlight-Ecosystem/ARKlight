"""
`pad_start` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.padStart(length, fill)` (ES2017), with `length` and
`fill` literal arguments. `length` is the target length in UTF-16 code
units (`0`-`1000`, build-time checked); a string already that long, or an
empty `fill`, is returned unchanged.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("pad_start", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "pad_start"

JS_FRAGMENT = """    pad_start: function (state, names, args) {
      return String(state[names[0]]).padStart(args.length, args.fill);
    }"""
