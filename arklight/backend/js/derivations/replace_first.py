"""
`replace_first` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

Replaces the first occurrence of a **literal** substring. Deliberately
not `String.prototype.replace(a, b)` as written: `search` is a plain
string (never a regex -- nothing here builds a `RegExp`, and a future
contributor should not add that), and `replacement` goes through a
function so `$&`, `$1`, `` $` `` and `$$` in it stay literal text
instead of being expanded. `search` must be non-empty (build-time
checked).

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("replace_first", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "replace_first"

JS_FRAGMENT = """    replace_first: function (state, names, args) {
      return String(state[names[0]]).replace(args.search, function () {
        return args.replacement;
      });
    }"""
