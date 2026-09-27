"""
`replace_all` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

Replaces every occurrence of a **literal** substring, left to right,
non-overlapping. Written as `split(search).join(replacement)` rather
than `replaceAll` (ES2021, and its string form still expands `$&`-style
patterns in the replacement): the result is identical for a non-empty
literal `search` and the method is universally available. Never a
regex -- see `replace_first.py`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("replace_all", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "replace_all"

JS_FRAGMENT = """    replace_all: function (state, names, args) {
      return String(state[names[0]]).split(args.search).join(args.replacement);
    }"""
