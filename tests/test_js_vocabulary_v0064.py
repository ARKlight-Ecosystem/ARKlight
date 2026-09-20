"""
Tests for `v0.064` -- JS vocabulary addendum, stage 4/10 (see
`docs/version history/v0.064.md`): the math derivations catalog
(`Derive.absolute` ... `Derive.to_precision`, 21 kinds). Mirrors the
registry-driven shape of `tests/test_js_vocabulary_v0061.py`/`v0062.py`,
plus a Node parity sweep -- the catalog's whole job is for the build-time
mirror (`arklight/ir/js_numeric.py`) to agree with the shipped JS.
"""

import json
import math
import re
import shutil
import subprocess

import pytest

from arklight.api import Bind, Computed, Derive, Page, State, Text
from arklight.ast.nodes import DerivationRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.backend.js.render import JSBackend
from arklight.ir import js_numeric
from arklight.ir.build import _evaluate_derivation, build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import DERIVATION_REGISTRY, DIGITS_RANGES
from arklight.ir.validate import ValidationError, validate_ark_ast

NEW_KINDS = (
    "absolute", "ceiling", "floor", "truncate_number", "sign", "sqrt", "cbrt",
    "power", "exp", "log", "log2", "log10", "hypot", "clamp", "average",
    "median", "gcd", "lcm", "percentage_of", "to_fixed", "to_precision",
)
ALL_KINDS = (
    "sum", "multiply", "join", "count", "format", "compare", "subtract",
    "divide", "min", "max", "uppercase", "trim",
) + NEW_KINDS


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _initial(derive, **state):
    """Build-time initial value of `Computed("out", derive=derive)` over `state`."""
    tree = Page(
        *(State(name, value) for name, value in state.items()),
        Computed("out", deps=tuple(state), derive=derive),
    )
    return _ir({"/": tree}).pages[0].computed_initial["out"]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ref,kind,names",
    [
        (Derive.absolute("a"), "absolute", ("a",)),
        (Derive.ceiling("a"), "ceiling", ("a",)),
        (Derive.floor("a"), "floor", ("a",)),
        (Derive.truncate_number("a"), "truncate_number", ("a",)),
        (Derive.sign("a"), "sign", ("a",)),
        (Derive.sqrt("a"), "sqrt", ("a",)),
        (Derive.cbrt("a"), "cbrt", ("a",)),
        (Derive.power("a", "b"), "power", ("a", "b")),
        (Derive.exp("a"), "exp", ("a",)),
        (Derive.log("a"), "log", ("a",)),
        (Derive.log2("a"), "log2", ("a",)),
        (Derive.log10("a"), "log10", ("a",)),
        (Derive.hypot("a", "b", "c"), "hypot", ("a", "b", "c")),
        (Derive.clamp("a", "b", "c"), "clamp", ("a", "b", "c")),
        (Derive.average("a", "b"), "average", ("a", "b")),
        (Derive.median("a", "b", "c"), "median", ("a", "b", "c")),
        (Derive.gcd("a", "b"), "gcd", ("a", "b")),
        (Derive.lcm("a", "b"), "lcm", ("a", "b")),
        (Derive.percentage_of("a", "b"), "percentage_of", ("a", "b")),
    ],
)
def test_derive_returns_derivation_ref(ref, kind, names):
    assert ref == DerivationRef(kind=kind, names=names)


def test_derive_mean_is_an_alias_for_average():
    assert Derive.mean("a", "b") == Derive.average("a", "b")


def test_derive_to_fixed_and_to_precision_carry_digits():
    assert Derive.to_fixed("a", 2) == DerivationRef(kind="to_fixed", names=("a",), args={"digits": 2})
    assert Derive.to_precision("a", 4) == DerivationRef(
        kind="to_precision", names=("a",), args={"digits": 4}
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_and_fragments_cover_every_v0064_kind():
    for kind in NEW_KINDS:
        assert kind in DERIVATION_REGISTRY
        assert kind in DERIVATION_FRAGMENTS


def test_registry_and_fragment_keys_stay_in_lockstep():
    assert set(DERIVATION_REGISTRY) == set(DERIVATION_FRAGMENTS)


@pytest.mark.parametrize(
    "kind,low,high",
    [
        ("absolute", 1, 1), ("power", 2, 2), ("clamp", 3, 3),
        ("percentage_of", 2, 2), ("hypot", 1, None), ("median", 1, None),
        ("to_fixed", 1, 1), ("to_precision", 1, 1),
    ],
)
def test_registry_arity(kind, low, high):
    spec = DERIVATION_REGISTRY[kind]
    assert (spec.min_names, spec.max_names) == (low, high)


def test_digits_ranges_match_javascript():
    assert DIGITS_RANGES == {"to_fixed": (0, 100), "to_precision": (1, 100)}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "derive,message",
    [
        (DerivationRef(kind="power", names=("a",)), "needs exactly 2"),
        (DerivationRef(kind="clamp", names=("a", "b")), "needs exactly 3"),
        (DerivationRef(kind="sqrt", names=("a", "b")), "needs exactly 1"),
        (DerivationRef(kind="percentage_of", names=("a", "b", "c")), "needs exactly 2"),
    ],
)
def test_arity_is_enforced(derive, message):
    tree = Page(
        State("a", 1.0), State("b", 2.0), State("c", 3.0),
        Computed("out", deps=("a", "b", "c"), derive=derive),
    )
    with pytest.raises(ValidationError, match=message):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


@pytest.mark.parametrize(
    "derive",
    [
        Derive.to_fixed("a", -1),
        Derive.to_fixed("a", 101),
        Derive.to_fixed("a", 2.5),
        Derive.to_fixed("a", True),
        Derive.to_fixed("a", "2"),
        Derive.to_precision("a", 0),
        Derive.to_precision("a", 101),
    ],
)
def test_digits_out_of_range_or_wrong_type_is_a_build_error(derive):
    tree = Page(State("a", 1.0), Computed("out", deps=("a",), derive=derive))
    with pytest.raises(ValidationError, match="digits must be an integer from"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


@pytest.mark.parametrize(
    "derive",
    [Derive.to_fixed("a", 0), Derive.to_fixed("a", 100), Derive.to_precision("a", 1), Derive.to_precision("a", 100)],
)
def test_digits_at_the_javascript_limits_are_accepted(derive):
    tree = Page(State("a", 1.0), Computed("out", deps=("a",), derive=derive))
    validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_to_fixed_without_digits_is_rejected():
    tree = Page(
        State("a", 1.0),
        Computed("out", deps=("a",), derive=DerivationRef(kind="to_fixed", names=("a",))),
    )
    with pytest.raises(ValidationError, match="missing required argument"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_deps_must_list_every_name_a_new_derivation_reads():
    tree = Page(State("a", 1.0), State("b", 2.0), Computed("out", deps=("a",), derive=Derive.power("a", "b")))
    with pytest.raises(ValidationError, match="isn't in this Computed"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# Build-time initial values -- exact expected results
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "derive,state,expected",
    [
        (Derive.absolute("a"), {"a": -4.5}, 4.5),
        (Derive.ceiling("a"), {"a": 1.2}, 2.0),
        (Derive.ceiling("a"), {"a": -1.8}, -1.0),
        (Derive.floor("a"), {"a": 1.8}, 1.0),
        (Derive.floor("a"), {"a": -1.2}, -2.0),
        (Derive.truncate_number("a"), {"a": -2.7}, -2.0),
        (Derive.truncate_number("a"), {"a": 2.7}, 2.0),
        (Derive.sign("a"), {"a": -9}, -1.0),
        (Derive.sign("a"), {"a": 0}, 0.0),
        (Derive.sign("a"), {"a": 12}, 1.0),
        (Derive.sqrt("a"), {"a": 81}, 9.0),
        (Derive.cbrt("a"), {"a": 27}, 3.0),
        (Derive.cbrt("a"), {"a": -8}, -2.0),
        (Derive.power("a", "b"), {"a": 2, "b": 10}, 1024.0),
        (Derive.power("a", "b"), {"a": 9, "b": 0.5}, 3.0),
        (Derive.exp("a"), {"a": 0}, 1.0),
        (Derive.log("a"), {"a": 1}, 0.0),
        (Derive.log2("a"), {"a": 8}, 3.0),
        (Derive.log10("a"), {"a": 1000}, 3.0),
        (Derive.hypot("a", "b"), {"a": 3, "b": 4}, 5.0),
        (Derive.hypot("a"), {"a": -7}, 7.0),
        (Derive.clamp("x", "lo", "hi"), {"x": 15, "lo": 0, "hi": 10}, 10.0),
        (Derive.clamp("x", "lo", "hi"), {"x": -3, "lo": 0, "hi": 10}, 0.0),
        (Derive.clamp("x", "lo", "hi"), {"x": 4, "lo": 0, "hi": 10}, 4.0),
        (Derive.clamp("x", "lo", "hi"), {"x": 4, "lo": 8, "hi": 2}, 2.0),
        (Derive.average("a", "b", "c"), {"a": 1, "b": 2, "c": 6}, 3.0),
        (Derive.mean("a", "b"), {"a": 1, "b": 2}, 1.5),
        (Derive.median("a", "b", "c"), {"a": 9, "b": 1, "c": 5}, 5.0),
        (Derive.median("a", "b", "c", "d"), {"a": 4, "b": 1, "c": 3, "d": 2}, 2.5),
        (Derive.median("a"), {"a": 7}, 7.0),
        (Derive.gcd("a", "b"), {"a": 12, "b": 18}, 6.0),
        (Derive.gcd("a", "b", "c"), {"a": 12, "b": 18, "c": 30}, 6.0),
        (Derive.gcd("a", "b"), {"a": -12, "b": 18.9}, 6.0),
        (Derive.gcd("a", "b"), {"a": 0, "b": 0}, 0.0),
        (Derive.gcd("a", "b"), {"a": 0, "b": 5}, 5.0),
        (Derive.lcm("a", "b"), {"a": 4, "b": 6}, 12.0),
        (Derive.lcm("a", "b", "c"), {"a": 2, "b": 3, "c": 4}, 12.0),
        (Derive.lcm("a", "b"), {"a": 0, "b": 5}, 0.0),
        (Derive.percentage_of("a", "b"), {"a": 1, "b": 4}, 25.0),
        (Derive.percentage_of("a", "b"), {"a": 3, "b": 2}, 150.0),
        (Derive.to_fixed("a", 2), {"a": 9.5}, "9.50"),
        (Derive.to_fixed("a", 0), {"a": 2.5}, "3"),
        (Derive.to_fixed("a", 0), {"a": -2.5}, "-3"),
        (Derive.to_fixed("a", 2), {"a": 1.005}, "1.00"),  # 1.005 is really 1.00499999...
        (Derive.to_fixed("a", 1), {"a": -0.04}, "-0.0"),
        (Derive.to_fixed("a", 2), {"a": 0}, "0.00"),
        (Derive.to_precision("a", 3), {"a": 123.456}, "123"),
        (Derive.to_precision("a", 4), {"a": 0.000123456}, "0.0001235"),
        (Derive.to_precision("a", 2), {"a": 123456}, "1.2e+5"),
        (Derive.to_precision("a", 2), {"a": 9.96}, "10"),
        (Derive.to_precision("a", 3), {"a": 0}, "0.00"),
        (Derive.to_precision("a", 3), {"a": 1e-7}, "1.00e-7"),
    ],
)
def test_ir_build_evaluates_initial_value(derive, state, expected):
    result = _initial(derive, **state)
    assert result == expected
    assert type(result) is type(expected)


def test_non_numeric_state_reads_as_zero_like_sum_does():
    assert _initial(Derive.absolute("a"), a="not a number") == 0.0
    assert _initial(Derive.average("a", "b"), a="x", b=10) == 5.0


# ---------------------------------------------------------------------------
# Edge semantics: JavaScript's answer, never Python's exception
# ---------------------------------------------------------------------------


def test_out_of_domain_results_are_nan_or_infinity_not_errors():
    assert math.isnan(_initial(Derive.sqrt("a"), a=-1))
    assert math.isnan(_initial(Derive.log("a"), a=-1))
    assert _initial(Derive.log("a"), a=0) == -math.inf
    assert _initial(Derive.log2("a"), a=0) == -math.inf
    assert _initial(Derive.log10("a"), a=0) == -math.inf
    assert _initial(Derive.exp("a"), a=1000) == math.inf
    assert _initial(Derive.power("a", "b"), a=10, b=400) == math.inf
    assert _initial(Derive.power("a", "b"), a=-10, b=401) == -math.inf
    assert _initial(Derive.power("a", "b"), a=0, b=-1) == math.inf
    assert math.isnan(_initial(Derive.power("a", "b"), a=-8, b=0.5))
    assert _initial(Derive.percentage_of("a", "b"), a=5, b=0) == math.inf
    assert math.isnan(_initial(Derive.percentage_of("a", "b"), a=0, b=0))


def test_power_zero_exponent_is_one_and_one_to_infinity_is_nan_like_javascript():
    assert js_numeric.js_pow(5.0, 0.0) == 1.0
    assert js_numeric.js_pow(math.nan, 0.0) == 1.0
    assert math.isnan(js_numeric.js_pow(1.0, math.inf))  # C says 1.0; JavaScript says NaN
    assert math.isnan(js_numeric.js_pow(-1.0, -math.inf))
    assert math.isnan(js_numeric.js_pow(2.0, math.nan))


def test_ceil_and_trunc_of_small_negatives_keep_javascripts_negative_zero():
    assert math.copysign(1.0, js_numeric.js_ceil(-0.5)) == -1.0
    assert math.copysign(1.0, js_numeric.js_trunc(-0.5)) == -1.0
    assert math.copysign(1.0, js_numeric.js_floor(0.5)) == 1.0


def test_rounding_functions_pass_non_finite_values_through():
    for fn in (js_numeric.js_ceil, js_numeric.js_floor, js_numeric.js_trunc):
        assert fn(math.inf) == math.inf
        assert math.isnan(fn(math.nan))


def test_gcd_and_lcm_of_non_finite_input_are_nan():
    assert math.isnan(js_numeric.js_gcd([math.inf, 4.0]))
    assert math.isnan(js_numeric.js_lcm([4.0, -math.inf]))


def test_cbrt_is_exact_on_perfect_cubes_and_odd():
    for root in (1, 2, 3, 4, 5, 9, 10, 11, 100):
        assert js_numeric.js_cbrt(float(root**3)) == float(root)
        assert js_numeric.js_cbrt(-float(root**3)) == -float(root)


def test_to_fixed_large_and_non_finite_values_use_string_conversion():
    assert js_numeric.js_to_fixed(1e21, 2) == "1e+21"
    assert js_numeric.js_to_fixed(math.inf, 2) == "Infinity"
    assert js_numeric.js_to_fixed(-math.inf, 2) == "-Infinity"
    assert js_numeric.js_to_fixed(math.nan, 2) == "NaN"


def test_to_precision_exposes_exact_binary_digits_at_100():
    # 0.1 is 0.1000000000000000055511151231257827... -- all digits, no
    # zero-padding after Decimal's default 28-digit context.
    assert js_numeric.js_to_precision(0.1, 60).startswith("0.10000000000000000555111512312578270211815834045410156")


# ---------------------------------------------------------------------------
# Parity fixes found while adding this catalog
# ---------------------------------------------------------------------------


def test_nan_result_reads_as_zero_in_a_dependent_computed_like_the_client_does():
    # Client: `Number(NaN) || 0` === 0. Build time must agree.
    tree = Page(
        State("a", -4.0),
        Computed("root", deps=("a",), derive=Derive.sqrt("a")),  # NaN
        Computed("next", deps=("root",), derive=Derive.sum("root")),
    )
    ir = _ir({"/": tree})
    assert math.isnan(ir.pages[0].computed_initial["root"])
    assert ir.pages[0].computed_initial["next"] == 0.0


def test_sum_matches_javascripts_left_to_right_reduce_not_pythons_compensated_sum():
    names = [f"n{i}" for i in range(10)]
    tree = Page(
        *(State(n, 0.1) for n in names),
        Computed("total", deps=tuple(names), derive=Derive.sum(*names)),
    )
    assert _ir({"/": tree}).pages[0].computed_initial["total"] == 0.9999999999999999


def test_html_prefill_spells_non_finite_values_the_javascript_way():
    tree = Page(
        State("a", -1.0),
        State("z", 0.0),
        Computed("root", deps=("a",), derive=Derive.sqrt("a")),
        Computed("low", deps=("z",), derive=Derive.log("z")),
        Computed("high", deps=("z",), derive=Derive.exp("z")),
        Computed("inf", deps=("a", "z"), derive=Derive.percentage_of("a", "z")),
        Text(Bind("root")),
        Text(Bind("low")),
        Text(Bind("inf")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-bind="root">NaN<' in html
    assert 'data-ark-bind="low">-Infinity<' in html
    assert 'data-ark-bind="inf">-Infinity<' in html


def test_html_render_prefills_bind_text_with_a_new_derivation():
    tree = Page(
        State("price", 9.5),
        Computed("label", deps=("price",), derive=Derive.to_fixed("price", 2)),
        Text(Bind("label")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-bind="label">9.50<' in html


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_js_render_ships_only_the_used_new_derivation_kind(kind):
    arity = DERIVATION_REGISTRY[kind]
    names = ("a", "b", "c")[: max(arity.min_names, 1)]
    args = {"digits": 2} if kind in DIGITS_RANGES else {}
    tree = Page(
        State("a", 4.0), State("b", 2.0), State("c", 1.0),
        Computed("result", deps=names, derive=DerivationRef(kind=kind, names=names, args=args)),
        Text(Bind("result")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert re.search(rf"\b{kind}: function", js)
    for other in ALL_KINDS:
        if other != kind:
            assert not re.search(rf"\b{other}: function", js), other


def test_new_fragments_use_no_eval_or_new_function():
    for kind in NEW_KINDS:
        fragment = DERIVATION_FRAGMENTS[kind]
        assert "eval(" not in fragment
        assert "new Function" not in fragment
        assert "RegExp" not in fragment


# ---------------------------------------------------------------------------
# Node parity: the build-time mirror agrees with the shipped fragments
# ---------------------------------------------------------------------------

_NODE = shutil.which("node")

_UNARY_INPUTS = [0, 1, -1, 0.5, -0.5, 2.5, -2.5, 3, -8, 8, 27, 100, 123456.789, 1e21, 0.1, 7.9, -7.9, 1e300, 1e-7]
_PAIR_INPUTS = [0, 1, -1, 2, -2, 0.5, 10, -8, 3, 4, 1000]


def _parity_cases():
    cases = []
    for kind in ("absolute", "ceiling", "floor", "truncate_number", "sign", "sqrt", "cbrt", "exp", "log", "log2", "log10"):
        cases += [(kind, [v], {}) for v in _UNARY_INPUTS]
    for a in _PAIR_INPUTS:
        for b in _PAIR_INPUTS:
            for kind in ("power", "percentage_of", "gcd", "lcm", "average", "median", "hypot"):
                cases.append((kind, [a, b], {}))
    for lo in (-5, 0):
        for x in (-9, -5, 2.5, 20):
            for hi in (1, 8):
                cases.append(("clamp", [x, lo, hi], {}))
    for values in ([3, 1, 2], [4, 1, 3, 2], [0.1] * 10, [12, 18, 30], [7]):
        cases += [(kind, values, {}) for kind in ("average", "median", "gcd", "lcm")]
    for v in _UNARY_INPUTS + [2.675, 1.45, 0.045, 5.5, 999.9999, 0.00001, 123.456]:
        cases += [("to_fixed", [v], {"digits": d}) for d in (0, 1, 2, 10, 100)]
        cases += [("to_precision", [v], {"digits": d}) for d in (1, 2, 4, 21, 100)]
    return cases


def _same_number(a, b):
    """Bit-for-bit: same value, both NaN, or the same signed zero."""
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return a == b and math.copysign(1.0, a) == math.copysign(1.0, b)


def _parse_js(text):
    if text in ("NaN", "Infinity", "-Infinity"):
        return float(text.replace("Infinity", "inf").replace("NaN", "nan"))
    return float("-0.0" if text == "-0" else text)


@pytest.mark.skipif(_NODE is None, reason="node not available in this environment")
def test_node_recompute_matches_build_time_initial_value_across_the_catalog():
    cases = _parity_cases()
    fragments = ",\n".join(DERIVATION_FRAGMENTS[kind] for kind in NEW_KINDS)
    script = f"""
    var derivations = {{
{fragments}
    }};
    var cases = {json.dumps(cases)};
    console.log(JSON.stringify(cases.map(function (c) {{
      var names = c[1].map(function (_, i) {{ return "n" + i; }});
      var state = {{}};
      names.forEach(function (n, i) {{ state[n] = c[1][i]; }});
      var r = derivations[c[0]](state, names, c[2]);
      if (typeof r === "string") return r;
      return Object.is(r, -0) ? "-0" : String(r);
    }})));
    """
    node_out = json.loads(subprocess.run([_NODE, "-e", script], capture_output=True, text=True, check=True).stdout)

    # Kinds built from correctly-rounded operations (arithmetic, `fmod`,
    # rounding, sort, string formatting) must match to the last digit.
    # `exp`/`log*`/`cbrt`/`power`/`hypot` go through each platform's libm
    # (glibc here, V8's fdlibm port in the browser) and may differ in the
    # final binary digit -- see docs/version history/v0.064.md.
    libm_kinds = {"exp", "log", "log2", "log10", "cbrt", "power", "hypot"}
    mismatches = []
    for (kind, values, args), from_js in zip(cases, node_out):
        names = [f"n{i}" for i in range(len(values))]
        state = dict(zip(names, values))
        built = _evaluate_derivation(
            {"kind": kind, "names": names, "args": args}, get=state.__getitem__
        )
        if isinstance(built, str):
            if built != from_js:
                mismatches.append((kind, values, args, built, from_js))
            continue
        expected = _parse_js(from_js)
        if _same_number(built, expected):
            continue
        if kind in libm_kinds and abs(built - expected) <= 4.5e-16 * max(abs(built), abs(expected)):
            continue
        mismatches.append((kind, values, args, built, from_js))
    assert not mismatches, mismatches[:10]
