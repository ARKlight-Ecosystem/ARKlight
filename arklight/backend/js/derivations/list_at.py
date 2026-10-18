"""
`list_at` derivation fragment (Tier 3, SS7.3 of
`docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md` -- a follow-up
addition after the `v0.061`-`v0.070` JS vocabulary addendum ladder, not
one of its ten stages). See `sum.py` for the general shape.

The list-side counterpart of `char_at` (`arklight/backend/js/
derivations/char_at.py`): the element at a literal, non-negative
`index`, or `null` past the end. Never wraps from the end -- `list_at`
with a negative index is not a feature here, same as `char_at`; use
`list_first`/`list_last` for the two fixed ends.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_at", ...)` case (via `arklight/ir/js_list.py`'s `js_list_at`) so
a page's server-rendered `Bind(...)` text never disagrees with what the
client recomputes.
"""

from __future__ import annotations

NAME = "list_at"

JS_FRAGMENT = """    list_at: function (state, names, args) {
      var list = state[names[0]];
      return Array.isArray(list) && args.index >= 0 && args.index < list.length
        ? list[args.index]
        : null;
    }"""
