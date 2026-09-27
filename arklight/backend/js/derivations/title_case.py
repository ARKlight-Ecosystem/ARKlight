"""
`title_case` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

Uppercases the first code unit of every whitespace-delimited word; the
rest of each word is left as it is (`"hello wORLD"` -> `"Hello WORLD"`).
The one regex here is a fixed literal -- no user data ever reaches a
regex engine.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("title_case", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "title_case"

JS_FRAGMENT = """    title_case: function (state, names, args) {
      return String(state[names[0]]).replace(/(^|\\s)(\\S)/g, function (m, boundary, letter) {
        return boundary + letter.toUpperCase();
      });
    }"""
