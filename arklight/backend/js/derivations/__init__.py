"""
Per-derivation JS runtime fragments (`vdom-4`, see
`docs/Backends/REFACTOR-INDEX.md` row 12).

Mirrors `arklight.backend.js.actions`: each sibling module exports
`NAME` (matching a key in `arklight.ir.schema.DERIVATION_REGISTRY`)
and `JS_FRAGMENT` (that derivation's `name: function (state, names,
args) { ... }` entry). `createState`'s recompute pass
(`arklight/backend/js/runtime/state.py`) looks a `Computed(...)`'s
`kind` up in the `derivations` object these fragments assemble into,
and calls it with the store's plain state object plus that
`Computed(...)`'s `names`/`args` (both already parsed from the
`data-ark-computed` JSON blob -- see
`arklight/backend/html/page_render.py`). `JSBackend.render()` ships
the `derivations` object -- and only the fragments actually used --
for a build only when at least one page declares `Computed(...)`,
same "only ship what's used" discipline `ACTION_FRAGMENTS`/
`BEHAVIOR_FRAGMENTS` already apply.
"""

from __future__ import annotations

from arklight.backend.js.derivations import (
    absolute,
    average,
    cbrt,
    ceiling,
    clamp,
    compare,
    count,
    divide,
    exp,
    floor,
    format,
    gcd,
    hypot,
    join,
    lcm,
    log,
    log10,
    log2,
    max as max_,
    median,
    min as min_,
    multiply,
    percentage_of,
    power,
    sign,
    sqrt,
    subtract,
    sum,
    to_fixed,
    to_precision,
    trim,
    truncate_number,
    uppercase,
)

DERIVATION_MODULES = {
    sum.NAME: sum,
    multiply.NAME: multiply,
    join.NAME: join,
    count.NAME: count,
    format.NAME: format,
    compare.NAME: compare,
    subtract.NAME: subtract,
    divide.NAME: divide,
    min_.NAME: min_,
    max_.NAME: max_,
    # `v0.062` (docs/version history/v0.062.md): JS vocabulary
    # addendum stage 2/10 -- string-casing siblings of `join`/`format`.
    uppercase.NAME: uppercase,
    trim.NAME: trim,
    # `v0.064` (docs/version history/v0.064.md): JS vocabulary addendum
    # stage 4/10 -- the math derivations catalog.
    absolute.NAME: absolute,
    ceiling.NAME: ceiling,
    floor.NAME: floor,
    truncate_number.NAME: truncate_number,
    sign.NAME: sign,
    sqrt.NAME: sqrt,
    cbrt.NAME: cbrt,
    power.NAME: power,
    exp.NAME: exp,
    log.NAME: log,
    log2.NAME: log2,
    log10.NAME: log10,
    hypot.NAME: hypot,
    clamp.NAME: clamp,
    average.NAME: average,
    median.NAME: median,
    gcd.NAME: gcd,
    lcm.NAME: lcm,
    percentage_of.NAME: percentage_of,
    to_fixed.NAME: to_fixed,
    to_precision.NAME: to_precision,
}

DERIVATION_FRAGMENTS: dict[str, str] = {
    name: module.JS_FRAGMENT for name, module in DERIVATION_MODULES.items()
}
