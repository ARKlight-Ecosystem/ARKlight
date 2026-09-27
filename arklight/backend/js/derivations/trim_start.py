"""
`trim_start` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.trimStart()` (ES2019) -- strips leading whitespace only.
JavaScript's whitespace set, not Python's `str.strip()`: see
`arklight/ir/js_string.py`'s `JS_WHITESPACE`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("trim_start", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "trim_start"

JS_FRAGMENT = """    trim_start: function (state, names, args) {
      return String(state[names[0]]).trimStart();
    }"""
