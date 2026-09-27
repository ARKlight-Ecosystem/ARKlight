"""
`to_kebab_case` derivation fragment (v0.069, JS vocabulary addendum stage
9/10 -- see `docs/version history/v0.069.md`). See `sum.py` for the
general shape.

Same word split as `to_snake_case`, joined with `-`: `"HelloWorld"` -> `"hello-world"`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("to_kebab_case", ...)` case (via `js_to_kebab_case` in `arklight/ir/js_string.py`) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "to_kebab_case"

JS_FRAGMENT = r"""    to_kebab_case: function (state, names, args) {
      var words = String(state[names[0]])
        .replace(/([\p{Ll}\p{N}])(?=\p{Lu})/gu, "$1 ")
        .replace(/(\p{Lu})(?=\p{Lu}\p{Ll})/gu, "$1 ")
        .split(/[^\p{L}\p{N}]+/u)
        .filter(function (w) { return w.length > 0; });
      return words.map(function (w) { return w.toLowerCase(); }).join("-");
    }"""
