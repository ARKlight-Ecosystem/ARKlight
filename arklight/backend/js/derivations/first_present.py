"""
`first_present` derivation fragment (`v0.068`, JS vocabulary
addendum stage 8/10 -- see `docs/version history/v0.068.md`). See
`value_or.py` for the "present" test this generalizes.

Two or more names, in order: `Derive.first_present("nickname",
"first_name", "\\"Guest\\"")`-shaped reads generalize `value_or` to more
than one fallback -- Rust `Option::or` chains / SQL `COALESCE`. Reads
each named value in order and returns the first that isn't
`null`/`undefined`/an empty string; if every one is empty, returns the
last name's value (still empty) rather than throwing, so a `Bind(...)`
over this derivation is always a defined scalar.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("first_present", ...)` case so a page's server-rendered `Bind(...)`
text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "first_present"

JS_FRAGMENT = """    first_present: function (state, names, args) {
      for (var i = 0; i < names.length; i++) {
        var v = state[names[i]];
        if (v !== null && v !== undefined && v !== "") return v;
      }
      return state[names[names.length - 1]];
    }"""
