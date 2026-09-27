"""
`saturating_add` derivation fragment (`v0.068`, JS vocabulary
addendum stage 8/10 -- see `docs/version history/v0.068.md`). See
`sum.py` for the general shape.

Exactly two names plus literal `min`/`max` bounds (`min <= max`,
checked at build time): `Derive.saturating_add("qty", "step", min=0,
max=100)` reads as Rust `i32::saturating_add`, adapted for a language
with no fixed integer width -- the sum is clamped to `[min, max]`
instead of over/underflowing. Complements `clamp` (`v0.064`), but a
quantity stepper that should stop at a boundary rather than run past
it reads more naturally through this than through
`Derive.clamp(Derive.sum(...), lo, hi)`'s two-step composition.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("saturating_add", ...)` case so a page's server-rendered `Bind(...)`
text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "saturating_add"

JS_FRAGMENT = """    saturating_add: function (state, names, args) {
      var sum = (Number(state[names[0]]) || 0) + (Number(state[names[1]]) || 0);
      return Math.min(Math.max(sum, args.min), args.max);
    }"""
