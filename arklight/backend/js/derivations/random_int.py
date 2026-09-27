"""
`random_int` derivation fragment (`v0.070`, JS vocabulary addendum
stage 10/10, the capstone -- see `docs/version history/v0.070.md`).
See `sum.py` for the general shape.

`Derive.random_int(min=1, max=6)` reads no state names at all (the
only `kind` in the whole catalog that doesn't) -- a whole-number roll
uniformly over `[min, max]` inclusive, composed from `Math.random()`.
The owning `Computed(...)`'s own `deps=(...)` (still required
non-empty, same as every `Computed(...)`) names whatever state should
trigger a re-roll; `derive.names` staying empty just means this
`kind` doesn't *read* any of those names' values, unlike every other
entry in the catalog.

**Design exception, documented per the addendum's "Scope filter":**
unlike every other derivation, this one is not a pure function of its
inputs, which cuts against the "server-rendered `Bind` text agrees
with the client recompute" invariant `sum.py`'s own docstring calls
out. It is therefore excluded from build-time pre-rendering entirely
(see `arklight.ir.build._evaluate_derivation`'s `"random_int"` case,
which pre-fills `min` as a deterministic placeholder rather than
attempting to reproduce `Math.random()`) and always resolves
client-side only -- `recomputeAll()` (`arklight/backend/js/runtime/
state.py`) already re-derives every `Computed(...)` at construction,
before the first paint, so the placeholder is overwritten with a real
roll immediately and is never actually seen by a visitor with
JavaScript enabled.
"""

from __future__ import annotations

NAME = "random_int"

JS_FRAGMENT = """    random_int: function (state, names, args) {
      var lo = args.min, hi = args.max;
      return lo + Math.floor(Math.random() * (hi - lo + 1));
    }"""
