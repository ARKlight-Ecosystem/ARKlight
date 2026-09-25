"""
Python mirrors of the JavaScript string semantics the string derivation
catalog (`v0.065`, JS vocabulary addendum stage 5/10 -- see
`docs/version history/v0.065.md`) depends on.

Same reason `arklight/ir/js_numeric.py` exists for the math catalog:
`arklight.ir.build`'s `_evaluate_derivation` pre-renders a
`Computed(...)`'s initial value at build time, and the browser
recomputes it with `String.prototype.*` on the first state change. The
two must agree, and Python's `str` disagrees with JavaScript's in three
places that matter:

* **Indexing unit.** A JavaScript string is a sequence of UTF-16 code
  units, a Python `str` a sequence of code points. `"😀".length` is `2`
  in JavaScript and `1` in Python; `slice`, `charAt`, `padStart` and
  `replace` count in code units too. Every function below therefore
  works on a "unit string" -- a Python `str` in which each character is
  one UTF-16 code unit (an astral character becomes a surrogate pair of
  two characters) -- so `len`, slicing, `in` and `str.replace` behave
  exactly as their JavaScript counterparts do. `to_units`/`from_units`
  convert either way.
* **Coercion.** The fragments read `String(state[name])`. Python's
  `str()` spells booleans `True`/`False`, `None` as `None`, and
  integral floats `5.0`; `js_to_string` reproduces JavaScript's
  spelling.
* **Whitespace.** `String.prototype.trimStart`/`trimEnd` and the `\\s`
  class use JavaScript's own whitespace set (`JS_WHITESPACE`), which is
  not `str.strip()`'s: it includes `U+FEFF` and excludes `U+001C`-
  `U+001F` and `U+0085`.

Nothing here is a general evaluator or a regex engine: each function is
one fixed, named operation a registry entry points at, and the
`replace_*`/`split_count` mirrors are literal-substring operations only
(see `arklight/backend/js/derivations/replace_first.py`).
"""

from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal
from typing import Any

# `WhiteSpace` + `LineTerminator` from the ECMAScript spec -- exactly what
# `String.prototype.trim*` strips and what the `\s` regex class matches.
JS_WHITESPACE = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)

_ASTRAL = re.compile("[\U00010000-\U0010ffff]")
_SURROGATE_PAIR = re.compile("[\ud800-\udbff][\udc00-\udfff]")


def _split_astral(match: "re.Match[str]") -> str:
    offset = ord(match.group()) - 0x10000
    return chr(0xD800 + (offset >> 10)) + chr(0xDC00 + (offset & 0x3FF))


def _join_pair(match: "re.Match[str]") -> str:
    high, low = match.group()
    return chr(0x10000 + ((ord(high) - 0xD800) << 10) + (ord(low) - 0xDC00))


def to_units(text: str) -> str:
    """Expand every astral character into its UTF-16 surrogate pair, so
    each character of the result is one JavaScript code unit."""
    return _ASTRAL.sub(_split_astral, text)


def from_units(units: str) -> str:
    """Inverse of `to_units`: recombine every adjacent high/low
    surrogate pair. A *lone* surrogate (which JavaScript can produce,
    e.g. `charAt(0)` of an emoji) is left as it is."""
    return _SURROGATE_PAIR.sub(_join_pair, units)


def js_number_to_string(x: float) -> str:
    """`Number.prototype.toString()` (ECMAScript `Number::toString`):
    shortest round-tripping digits, no trailing `.0`, exponent notation
    only at `>= 1e21` or `< 1e-6`."""
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        return "0"  # also `-0`: `String(-0)` is "0"
    sign = "-" if x < 0 else ""
    _, digit_tuple, exponent = Decimal(repr(abs(x))).as_tuple()
    digits = list(digit_tuple)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    text = "".join(map(str, digits))
    k = len(text)
    n = exponent + k  # the value is 0.<text> * 10**n
    if k <= n <= 21:
        return sign + text + "0" * (n - k)
    if 0 < n <= 21:
        return sign + text[:n] + "." + text[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + text
    e = n - 1
    mantissa = text[0] + ("." + text[1:] if k > 1 else "")
    return f"{sign}{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"


def js_to_string(value: Any) -> str:
    """`String(value)` for the value types `State(...)` can hold."""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        if -(2**53) <= value <= 2**53:
            return str(value)
        try:
            return js_number_to_string(float(value))
        except OverflowError:
            return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, float):
        return js_number_to_string(value)
    if isinstance(value, (list, tuple)):
        # `Array.prototype.toString`: join(","), null -> "".
        return ",".join("" if item is None else js_to_string(item) for item in value)
    if isinstance(value, dict):
        return "[object Object]"
    return str(value)


# ---------------------------------------------------------------------------
# One function per catalog entry. Each takes/returns ordinary Python `str`
# (or `int`/`bool`); the unit-string conversion is internal.
# ---------------------------------------------------------------------------


def js_capitalize(text: str) -> str:
    """`s.charAt(0).toUpperCase() + s.slice(1)`."""
    units = to_units(text)
    return from_units(units[:1].upper() + units[1:])


def js_title_case(text: str) -> str:
    """`s.replace(/(^|\\s)(\\S)/g, (m, a, b) => a + b.toUpperCase())`:
    uppercase the first code unit of every whitespace-delimited word;
    the rest of each word is left as it is."""
    units = to_units(text)
    out: list[str] = []
    previous_is_boundary = True
    for char in units:
        is_space = char in JS_WHITESPACE
        out.append(char.upper() if (previous_is_boundary and not is_space) else char)
        previous_is_boundary = is_space
    return from_units("".join(out))


def js_trim_start(text: str) -> str:
    return text.lstrip(JS_WHITESPACE)


def js_trim_end(text: str) -> str:
    return text.rstrip(JS_WHITESPACE)


def js_pad_start(text: str, length: int, fill: str) -> str:
    """`s.padStart(length, fill)`."""
    units = to_units(text)
    return from_units(_pad(units, length, to_units(fill)) + units)


def js_pad_end(text: str, length: int, fill: str) -> str:
    """`s.padEnd(length, fill)`."""
    units = to_units(text)
    return from_units(units + _pad(units, length, to_units(fill)))


def _pad(units: str, length: int, fill: str) -> str:
    missing = length - len(units)
    if missing <= 0 or not fill:
        return ""
    return (fill * (missing // len(fill) + 1))[:missing]


def js_repeat(text: str, count: int) -> str:
    """`s.repeat(count)`."""
    return from_units(to_units(text) * count)


def js_slice(text: str, start: int, end: int | None) -> str:
    """`s.slice(start, end)` (negative indices count from the end)."""
    return from_units(to_units(text)[start:end])


def js_char_at(text: str, index: int) -> str:
    """`s.charAt(index)` -- `""` when out of range. May return a lone
    surrogate, exactly like JavaScript."""
    units = to_units(text)
    return units[index] if 0 <= index < len(units) else ""


def js_replace_first(text: str, search: str, replacement: str) -> str:
    """`s.replace(search, () => replacement)` -- literal `search`
    (non-empty, validated at build time), literal `replacement` (no
    `$&`/`$1` patterns)."""
    return from_units(to_units(text).replace(to_units(search), to_units(replacement), 1))


def js_replace_all(text: str, search: str, replacement: str) -> str:
    """`s.split(search).join(replacement)` -- literal, non-empty `search`."""
    return from_units(to_units(text).replace(to_units(search), to_units(replacement)))


def js_split_count(text: str, sep: str) -> int:
    """`s.split(sep).length` for a non-empty `sep`."""
    return to_units(text).count(to_units(sep)) + 1


def js_reverse(text: str) -> str:
    """`Array.from(s).reverse().join("")` -- reversed by code point, so
    an emoji's surrogate pair survives (combining marks and joined emoji
    sequences do not: this is not grapheme-aware)."""
    return from_units(to_units(text))[::-1]


def js_length(text: str) -> int:
    """`s.length` -- UTF-16 code units."""
    return len(to_units(text))


def js_includes(text: str, substring: str) -> bool:
    return to_units(substring) in to_units(text)


def js_starts_with(text: str, substring: str) -> bool:
    return to_units(text).startswith(to_units(substring))


def js_ends_with(text: str, substring: str) -> bool:
    return to_units(text).endswith(to_units(substring))


def js_is_empty(text: str) -> bool:
    return text == ""


# ---------------------------------------------------------------------------
# `v0.069` (JS vocabulary addendum stage 9/10): the case converters. The word
# split mirrors the client's regex chain in
# `arklight/backend/js/derivations/to_snake_case.py` exactly: the two
# case-boundary passes are lookahead-based, so each is computed against the
# string as it stood before that pass, and `\p{L}`/`\p{N}`/`\p{Lu}`/`\p{Ll}`
# are Unicode general categories on code points (the `u` flag), which Python's
# `unicodedata` reproduces.
# ---------------------------------------------------------------------------


def _category(ch: str) -> str:
    return unicodedata.category(ch)


def _is_lower_or_digit(ch: str) -> bool:
    return _category(ch) == "Ll" or _category(ch).startswith("N")


def _is_word_char(ch: str) -> bool:
    return _category(ch).startswith(("L", "N"))


def js_split_words(text: str) -> list[str]:
    """Split `text` into words the way the case converters do."""
    chars = list(text)
    # Pass 1: `/([\p{Ll}\p{N}])(?=\p{Lu})/gu` -> `"$1 "`.
    spaced: list[str] = []
    for i, ch in enumerate(chars):
        spaced.append(ch)
        if _is_lower_or_digit(ch) and i + 1 < len(chars) and _category(chars[i + 1]) == "Lu":
            spaced.append(" ")
    # Pass 2: `/(\p{Lu})(?=\p{Lu}\p{Ll})/gu` -> `"$1 "`.
    stage = spaced
    spaced2: list[str] = []
    for i, ch in enumerate(stage):
        spaced2.append(ch)
        if (
            _category(ch) == "Lu"
            and i + 2 < len(stage)
            and _category(stage[i + 1]) == "Lu"
            and _category(stage[i + 2]) == "Ll"
        ):
            spaced2.append(" ")
    # Split on runs of anything that isn't a letter or number.
    words: list[str] = []
    current: list[str] = []
    for ch in spaced2:
        if _is_word_char(ch):
            current.append(ch)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words


def _capitalize_word(word: str) -> str:
    """`w.replace(/^./u, c => c.toUpperCase())`, on an already-lowercased word."""
    return word[:1].upper() + word[1:]


def js_to_snake_case(text: str) -> str:
    return "_".join(word.lower() for word in js_split_words(text))


def js_to_kebab_case(text: str) -> str:
    return "-".join(word.lower() for word in js_split_words(text))


def js_to_camel_case(text: str) -> str:
    lowered = [word.lower() for word in js_split_words(text)]
    return "".join(word if i == 0 else _capitalize_word(word) for i, word in enumerate(lowered))


def js_to_title_case(text: str) -> str:
    return " ".join(_capitalize_word(word.lower()) for word in js_split_words(text))
