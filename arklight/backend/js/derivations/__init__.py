"""
Per-derivation JS runtime fragments (`vdom-4`, see
`REFACTOR-INDEX.md` [retired -- see CHANGELOG.md] row 12).

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
    capitalize,
    cbrt,
    ceiling,
    char_at,
    clamp,
    compare,
    count,
    divide,
    ends_with,
    exp,
    floor,
    format,
    gcd,
    hypot,
    includes_substring,
    is_empty,
    join,
    lcm,
    list_all,
    list_any,
    list_average,
    list_first,
    list_includes,
    list_last,
    list_length,
    list_max,
    list_min,
    log,
    log10,
    log2,
    max as max_,
    median,
    min as min_,
    multiply,
    pad_end,
    pad_start,
    percentage_of,
    power,
    repeat,
    replace_all,
    replace_first,
    reverse_string,
    sign,
    slice_string,
    split_count,
    sqrt,
    starts_with,
    string_length,
    subtract,
    sum,
    title_case,
    to_fixed,
    to_precision,
    trim,
    trim_end,
    trim_start,
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
    # `v0.065` (docs/version history/v0.065.md): JS vocabulary addendum
    # stage 5/10 -- the string derivations catalog.
    capitalize.NAME: capitalize,
    title_case.NAME: title_case,
    trim_start.NAME: trim_start,
    trim_end.NAME: trim_end,
    pad_start.NAME: pad_start,
    pad_end.NAME: pad_end,
    repeat.NAME: repeat,
    slice_string.NAME: slice_string,
    char_at.NAME: char_at,
    replace_first.NAME: replace_first,
    replace_all.NAME: replace_all,
    split_count.NAME: split_count,
    reverse_string.NAME: reverse_string,
    string_length.NAME: string_length,
    includes_substring.NAME: includes_substring,
    starts_with.NAME: starts_with,
    ends_with.NAME: ends_with,
    is_empty.NAME: is_empty,
    # `v0.067` (docs/version history/v0.067.md): JS vocabulary addendum
    # stage 7/10 -- the list-scalar derivations catalog (a list-valued
    # `State(...)` reduced to one scalar).
    list_length.NAME: list_length,
    list_min.NAME: list_min,
    list_max.NAME: list_max,
    list_average.NAME: list_average,
    list_first.NAME: list_first,
    list_last.NAME: list_last,
    list_includes.NAME: list_includes,
    list_any.NAME: list_any,
    list_all.NAME: list_all,
}

DERIVATION_FRAGMENTS: dict[str, str] = {
    name: module.JS_FRAGMENT for name, module in DERIVATION_MODULES.items()
}
