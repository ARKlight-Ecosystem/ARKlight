"""
`split_count` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.split(sep).length` -- how many pieces a literal,
non-empty `sep` cuts the string into (`"a b c"` with `" "` -> `3`; an
empty string is `1` piece). A word counter is `sep=" "`, with the
usual caveat that runs of spaces count as empty pieces.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("split_count", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "split_count"

JS_FRAGMENT = """    split_count: function (state, names, args) {
      return String(state[names[0]]).split(args.sep).length;
    }"""
