"""
`list_any` derivation fragment (`v0.067`, JS vocabulary addendum stage
7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

`Array.prototype.some` over **one fixed comparison**, never a callback:
`args.op` is validated at build time against
`arklight.ir.schema.COMPARE_OPS` (mirroring `compare.py`), and
`args.value` is a literal. `eq`/`ne` are `===`/`!==` against the element
itself; `gt`/`lt`/`gte`/`lte` compare the element read as a number
(`Number(x) || 0`, numbers/strings/booleans only -- see `list_min.py`)
against a numeric literal. Returns a **boolean**; `false` for an empty
list or a value that is not a list. The `switch` is written out in each of
`list_any.py`/`list_all.py` because a fragment is one self-contained
object entry with no shared helper scope.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_any", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_any"

JS_FRAGMENT = """    list_any: function (state, names, args) {
      var list = state[names[0]];
      if (!Array.isArray(list)) { return false; }
      for (var i = 0; i < list.length; i += 1) {
        var item = list[i];
        var number = (typeof item === "number" || typeof item === "string" || typeof item === "boolean")
          ? (Number(item) || 0)
          : 0;
        var hit;
        switch (args.op) {
          case "eq": hit = item === args.value; break;
          case "ne": hit = item !== args.value; break;
          case "gt": hit = number > args.value; break;
          case "lt": hit = number < args.value; break;
          case "gte": hit = number >= args.value; break;
          case "lte": hit = number <= args.value; break;
          default: hit = false;
        }
        if (hit) { return true; }
      }
      return false;
    }"""
