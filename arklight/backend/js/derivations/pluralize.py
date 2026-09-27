"""
`pluralize` derivation fragment (`v0.070`, JS vocabulary addendum stage
10/10, the capstone -- see `docs/version history/v0.070.md`). See
`sum.py` for the general shape.

Reads two names -- a word and a count -- and returns the word,
pluralized for that count: `Derive.pluralize("noun", "qty")` with
`noun="item"`, `qty=3` -> `"items"`; `qty=1` -> `"item"` unchanged.
One of the two entries the addendum's "Scope filter" (see
`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`) flagged as
needing an explicit design exception before it could ship as written:
this ships with a small irregular-noun table (`person` -> `people`,
`octopus` -> `octopi`, ...) plus a documented regular-plural-only
fallback (`+s`/`+es`/consonant-`y` -> `ies`), not a claim of
exhaustive English pluralization -- an irregular noun outside the
table falls through to the regular rule and comes out wrong, same
limitation every other pluralization library documents rather than
solves.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("pluralize", ...)` case (via `js_pluralize` in
`arklight/ir/js_string.py`) so a page's server-rendered `Bind(...)`
text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "pluralize"

JS_FRAGMENT = r"""    pluralize: function (state, names, args) {
      var word = String(state[names[0]]);
      var count = Number(state[names[1]]) || 0;
      if (count === 1) return word;
      var irregular = {
        person: "people", child: "children", man: "men", woman: "women",
        tooth: "teeth", foot: "feet", mouse: "mice", goose: "geese",
        ox: "oxen", octopus: "octopi", cactus: "cacti", index: "indices",
        matrix: "matrices", vertex: "vertices", criterion: "criteria",
        phenomenon: "phenomena", die: "dice", leaf: "leaves", life: "lives",
        knife: "knives", wife: "wives", half: "halves", loaf: "loaves",
        shelf: "shelves", wolf: "wolves", elf: "elves", calf: "calves",
        self: "selves"
      };
      if (Object.prototype.hasOwnProperty.call(irregular, word)) {
        return irregular[word];
      }
      if (/[sxz]$/.test(word) || /[cs]h$/.test(word)) return word + "es";
      if (/[^aeiou]y$/.test(word)) return word.slice(0, -1) + "ies";
      return word + "s";
    }"""
