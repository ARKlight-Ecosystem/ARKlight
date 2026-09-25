"""
`to_title_case` derivation fragment (v0.069, JS vocabulary addendum stage
9/10 -- see `docs/version history/v0.069.md`). See `sum.py` for the
general shape.

Same word split as `to_snake_case`, each word capitalized (first letter upper,
rest lower) and joined with single spaces: `"hello_WORLD"` -> `"Hello World"`.
Unlike `title_case` (which leaves the rest of each word alone), this lowercases
everything after the first letter.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("to_title_case", ...)` case (via `js_to_title_case` in `arklight/ir/js_string.py`) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "to_title_case"

JS_FRAGMENT = r"""    to_title_case: function (state, names, args) {
      var words = String(state[names[0]])
        .replace(/([\p{Ll}\p{N}])(?=\p{Lu})/gu, "$1 ")
        .replace(/(\p{Lu})(?=\p{Lu}\p{Ll})/gu, "$1 ")
        .split(/[^\p{L}\p{N}]+/u)
        .filter(function (w) { return w.length > 0; });
      return words.map(function (w) {
        return w.toLowerCase().replace(/^./u, function (c) { return c.toUpperCase(); });
      }).join(" ");
    }"""
