"""
`saturating_subtract` derivation fragment (`v0.068`, JS vocabulary
addendum stage 8/10 -- see `docs/version history/v0.068.md`). See
`saturating_add.py` for the general shape -- same clamp-to-bounds
idea (Rust `i32::saturating_sub`), subtraction instead of addition:
`Derive.saturating_subtract("qty", "step", min=0, max=100)` never
drops below `min`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("saturating_subtract", ...)` case so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "saturating_subtract"

JS_FRAGMENT = """    saturating_subtract: function (state, names, args) {
      var diff = (Number(state[names[0]]) || 0) - (Number(state[names[1]]) || 0);
      return Math.min(Math.max(diff, args.min), args.max);
    }"""
