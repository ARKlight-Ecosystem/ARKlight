"""
`value_or` derivation fragment (`v0.068`, JS vocabulary addendum
stage 8/10 -- see `docs/version history/v0.068.md`). See `sum.py` for
the general shape.

One name plus a literal `fallback` (any JSON scalar -- a str, bool,
`None`, or finite number, same closed shape `list_includes.py`'s
`value` already validates): `Derive.value_or("nickname", fallback=
"Guest")` reads as Rust `Option::unwrap_or` -- the named state's own
value, unless it's `null`/`undefined`/an empty string, in which case
`fallback`. Unlike `Show`/`Watch`, this stays a plain scalar so it can
sit directly inside a `Text(Bind(...))` without a second node.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("value_or", ...)` case so a page's server-rendered `Bind(...)` text
never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "value_or"

JS_FRAGMENT = """    value_or: function (state, names, args) {
      var v = state[names[0]];
      if (v === null || v === undefined || v === "") return args.fallback;
      return v;
    }"""
