"""
`list_all` derivation fragment (`v0.067`, JS vocabulary addendum stage
7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

`Array.prototype.every` over one fixed comparison -- the same bounded
`op`/`value` contract as `list_any.py` (read that for how each is
checked and how an element is read). Returns a **boolean**. An empty
list is vacuously `true`, exactly like `[].every(...)`, and so is a value
that is not a list (it reads as an empty list); guard with
`Derive.list_length` if "no items yet" must not count as "all done".

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_all", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_all"

JS_FRAGMENT = """    list_all: function (state, names, args) {
      var list = state[names[0]];
      if (!Array.isArray(list)) { return true; }
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
        if (!hit) { return false; }
      }
      return true;
    }"""
