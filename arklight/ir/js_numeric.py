"""
Python mirrors of the JavaScript numeric semantics the math derivation
catalog (`v0.064`, JS vocabulary addendum stage 4/10 -- see
`docs/version history/v0.064.md`) depends on.

Every function here exists for one reason: `arklight.ir.build`'s
`_evaluate_derivation` pre-renders a `Computed(...)`'s initial value
at build time, and the browser recomputes it with `Math.*` /
`Number.prototype.*` on the first state change. Python's `math` module
disagrees with JavaScript's in exactly the places that matter at the
edges -- it *raises* (`math.sqrt(-1)`, `math.log(0)`, `math.exp(1000)`,
`math.ceil(inf)`) where JavaScript returns `NaN`/`Infinity` -- so each
function below reproduces JavaScript's answer rather than Python's
exception, the same discipline `arklight/backend/js/derivations/
divide.py` already documents for division.

Nothing here is a general evaluator: each function is one fixed,
named operation a registry entry points at.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Context, Decimal
from fractions import Fraction

_NAN = math.nan
_INF = math.inf

# Wide enough for `Decimal.quantize` to hold any `toFixed` (up to 100
# fraction digits on a value below 1e21) or `toPrecision` result. Only
# used for `quantize`'s result-size check; `Decimal(float)` itself is
# always exact regardless of context.
_DECIMAL_CONTEXT = Context(prec=500)


def js_lerp(a: float, b: float, t: float) -> float:
    """`v0.068`: C++20 `std::lerp(a, b, t)` -- linear interpolation,
    `a + t * (b - a)`, with the two edge cases C++20 added a stdlib
    function specifically to get right: `t == 0` returns exactly `a`
    and `t == 1` returns exactly `b`, even where floating-point
    rounding would otherwise nudge `a + t * (b - a)` off by a bit."""
    if t == 0:
        return a
    if t == 1:
        return b
    return a + t * (b - a)


def js_midpoint(a: float, b: float) -> float:
    """`v0.068`: C++20 `std::midpoint(a, b)` -- `a + (b - a) / 2`
    rather than the naive `(a + b) / 2`, so a pair of very large
    same-sign floats never round through an intermediate that
    overflows before the division happens."""
    return a + (b - a) / 2


def js_divide(a: float, b: float) -> float:
    """`a / b` with JavaScript's float semantics (`x / 0` is
    `Infinity`/`-Infinity`/`NaN`, never a `ZeroDivisionError`)."""
    if b == 0:
        if a == 0 or math.isnan(a):
            return _NAN
        return math.copysign(_INF, a) * math.copysign(1.0, b)
    return a / b


def _with_sign_of_zero(result: float, original: float) -> float:
    # `Math.ceil(-0.5)`/`Math.trunc(-0.5)` are `-0` in JavaScript;
    # Python's `float(math.ceil(-0.5))` is `+0.0`. Keeps `1 / result`
    # agreeing on both sides.
    return math.copysign(result, original) if result == 0 else result


def js_ceil(x: float) -> float:
    if not math.isfinite(x):
        return x
    return _with_sign_of_zero(float(math.ceil(x)), x)


def js_floor(x: float) -> float:
    if not math.isfinite(x):
        return x
    return float(math.floor(x))


def js_trunc(x: float) -> float:
    if not math.isfinite(x):
        return x
    return _with_sign_of_zero(float(math.trunc(x)), x)


def js_sign(x: float) -> float:
    if math.isnan(x) or x == 0:
        return x
    return 1.0 if x > 0 else -1.0


def js_sqrt(x: float) -> float:
    if math.isnan(x) or x < 0:
        return _NAN
    return math.sqrt(x)


def js_cbrt(x: float) -> float:
    if not math.isfinite(x) or x == 0:
        return x
    cbrt = getattr(math, "cbrt", None)  # Python 3.11+
    if cbrt is not None:
        root = cbrt(x)
    else:
        root = math.copysign(abs(x) ** (1.0 / 3.0), x)
        root -= (root * root * root - x) / (3.0 * root * root)  # one Newton step
    # libm's `cbrt` is not correctly rounded (`cbrt(27.0)` can come back as
    # `3.0000000000000004`), while JavaScript's gives exactly `3`. Settle
    # on whichever of the neighbouring doubles cubes closest to `x`, so a
    # perfect cube always lands exactly and the result no longer depends
    # on the build machine's libm.
    exact_x = Fraction(x)
    best, best_error = root, abs(Fraction(root) ** 3 - exact_x)
    for candidate in (math.nextafter(root, _INF), math.nextafter(root, -_INF)):
        error = abs(Fraction(candidate) ** 3 - exact_x)
        if error < best_error:
            best, best_error = candidate, error
    return best


def js_exp(x: float) -> float:
    try:
        return math.exp(x)
    except OverflowError:
        return _INF


def _js_log(x: float, fn) -> float:
    if math.isnan(x) or x < 0:
        return _NAN
    if x == 0:
        return -_INF
    if math.isinf(x):
        return _INF
    return fn(x)


def js_log(x: float) -> float:
    return _js_log(x, math.log)


def js_log2(x: float) -> float:
    return _js_log(x, math.log2)


def js_log10(x: float) -> float:
    return _js_log(x, math.log10)


def _is_odd_integer(x: float) -> bool:
    return math.isfinite(x) and x == math.floor(x) and math.fmod(x, 2.0) != 0.0


def js_pow(base: float, exponent: float) -> float:
    """`Math.pow(base, exponent)`, including the two places JavaScript
    departs from C's `pow` (and so from `math.pow`): `pow(1, +-Infinity)`
    and `pow(-1, +-Infinity)` are `NaN`, not `1`."""
    if math.isnan(exponent):
        return _NAN
    if exponent == 0:
        return 1.0
    if math.isnan(base):
        return _NAN
    if abs(base) == 1.0 and math.isinf(exponent):
        return _NAN
    try:
        return math.pow(base, exponent)
    except OverflowError:
        return -_INF if (base < 0 and _is_odd_integer(exponent)) else _INF
    except ValueError:
        if base == 0:  # zero to a negative power
            negative_zero = math.copysign(1.0, base) < 0
            return -_INF if (negative_zero and _is_odd_integer(exponent)) else _INF
        return _NAN  # negative base, non-integer exponent


def js_hypot(values: list[float]) -> float:
    return math.hypot(*values)


def js_average(values: list[float]) -> float:
    # Explicit left-to-right loop, not `sum()`: since Python 3.12
    # `sum()` on floats is compensated (Neumaier) and would disagree
    # with JavaScript's plain `reduce` in the last digit.
    total = 0.0
    for value in values:
        total += value
    return total / len(values)


def js_median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _gcd2(a: float, b: float) -> float:
    while b:
        a, b = b, math.fmod(a, b)
    return a


def _integer_magnitudes(values: list[float]) -> list[float] | None:
    magnitudes = []
    for value in values:
        if not math.isfinite(value):
            return None
        magnitudes.append(abs(float(math.trunc(value))))
    return magnitudes


def js_gcd(values: list[float]) -> float:
    """Greatest common divisor of `|trunc(x)|` for each value; `NaN` if
    any value is non-finite. `gcd(0, 0)` is `0`."""
    magnitudes = _integer_magnitudes(values)
    if magnitudes is None:
        return _NAN
    result = magnitudes[0]
    for value in magnitudes[1:]:
        result = _gcd2(result, value)
    return result


def js_lcm(values: list[float]) -> float:
    """Least common multiple of `|trunc(x)|` for each value; `0` if any
    value is `0`, `NaN` if any value is non-finite."""
    magnitudes = _integer_magnitudes(values)
    if magnitudes is None:
        return _NAN
    result = magnitudes[0]
    for value in magnitudes[1:]:
        if result == 0 or value == 0:
            result = 0.0
        else:
            result = result / _gcd2(result, value) * value
    return result


def js_number_to_string(x: float) -> str:
    """`String(x)` for the range `toFixed` falls back to it for
    (`|x| >= 1e21`), where both languages use exponent notation and
    the shortest round-tripping digits (`1e+21`, `1.2345e+25`)."""
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    return repr(x)


def js_to_fixed(x: float, digits: int) -> str:
    """`Number.prototype.toFixed(digits)`. Rounds an exact tie away
    from zero (`(2.5).toFixed(0) === \"3\"`), which Python's own
    `format(2.5, \".0f\")` (half-to-even, `\"2\"`) does not."""
    if not math.isfinite(x) or abs(x) >= 1e21:
        return js_number_to_string(x)
    if x == 0:
        x = 0.0  # `(-0).toFixed(2)` is "0.00", no sign
    quantum = Decimal(1).scaleb(-digits)
    rounded = Decimal(x).quantize(quantum, rounding=ROUND_HALF_UP, context=_DECIMAL_CONTEXT)
    return format(rounded, "f")


def js_to_precision(x: float, digits: int) -> str:
    """`Number.prototype.toPrecision(digits)`: `digits` significant
    digits, in fixed notation unless the exponent is below -6 or at
    least `digits`, in which case exponent notation (`1.23e+5`)."""
    if not math.isfinite(x):
        return js_number_to_string(x)
    sign = "-" if x < 0 else ""
    if x == 0:
        return "0" if digits == 1 else "0." + "0" * (digits - 1)

    magnitude = Decimal(abs(x))
    exponent = magnitude.adjusted()
    rounded = magnitude.quantize(
        Decimal(1).scaleb(exponent - digits + 1), rounding=ROUND_HALF_UP, context=_DECIMAL_CONTEXT
    )
    if rounded.adjusted() > exponent:  # rounded up into the next power of ten
        exponent += 1
        rounded = magnitude.quantize(
            Decimal(1).scaleb(exponent - digits + 1), rounding=ROUND_HALF_UP, context=_DECIMAL_CONTEXT
        )
    # `scaleb` rounds to the *context's* precision (28 digits by default),
    # which would silently zero-pad a 100-digit request -- pass the wide one.
    digit_string = str(int(rounded.scaleb(-(exponent - digits + 1), context=_DECIMAL_CONTEXT)))

    if exponent < -6 or exponent >= digits:
        mantissa = digit_string[0] + ("." + digit_string[1:] if digits > 1 else "")
        return f"{sign}{mantissa}e{'+' if exponent >= 0 else '-'}{abs(exponent)}"
    if exponent == digits - 1:
        return sign + digit_string
    if exponent >= 0:
        return f"{sign}{digit_string[: exponent + 1]}.{digit_string[exponent + 1 :]}"
    return f"{sign}0.{'0' * (-(exponent + 1))}{digit_string}"
