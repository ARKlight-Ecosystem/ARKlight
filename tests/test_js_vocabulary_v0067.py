"""
Tests for `v0.067` -- JS vocabulary addendum, stage 7/10 (see
`docs/version history/v0.067.md`): the list-scalar derivations catalog
(`Derive.list_length` ... `Derive.list_all`, 9 kinds). Same shape as
`tests/test_js_vocabulary_v0065.py`: API, registry, validation,
build-time initial values, HTML pre-fill, JS shipping, and a Node parity
sweep -- the catalog's whole job is for the build-time mirror
(`arklight/ir/js_list.py`) to agree with the shipped JavaScript,
including where Python and JavaScript differ (`1 == True`, `Number("0x10")`,
`Math.min()` of nothing, UTF-16 strings).
"""

import json
import math
import re
import shutil
import subprocess

import pytest

from arklight.api import Bind, Computed, Derive, Page, Predicate, Show, State, Text
from arklight.ast.nodes import DerivationRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.backend.js.render import JSBackend
from arklight.ir import js_list, js_string
from arklight.ir.build import _evaluate_derivation, build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import DERIVATION_REGISTRY, LITERAL_ARG_RULES
from arklight.ir.validate import ValidationError, validate_ark_ast

NEW_KINDS = (
    "list_length", "list_min", "list_max", "list_average", "list_first",
    "list_last", "list_includes", "list_any", "list_all",
)
BOOLEAN_KINDS = ("list_includes", "list_any", "list_all")
UNARY_KINDS = ("list_length", "list_min", "list_max", "list_average", "list_first", "list_last")

# A valid literal-argument dict for every kind that takes any.
SAMPLE_ARGS = {
    "list_includes": {"value": "a"},
    "list_any": {"op": "gt", "value": 1},
    "list_all": {"op": "eq", "value": "a"},
}


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _initial(derive, value):
    """Build-time initial value of `Computed("out", derive=derive)` over one state `s`."""
    tree = Page(State("s", value), Computed("out", deps=("s",), derive=derive))
    return _ir({"/": tree}).pages[0].computed_initial["out"]


def _validate(derive):
    tree = Page(State("s", ["x"]), Computed("out", deps=("s",), derive=derive))
    validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ref,kind,args",
    [
        (Derive.list_length("a"), "list_length", {}),
        (Derive.list_min("a"), "list_min", {}),
        (Derive.list_max("a"), "list_max", {}),
        (Derive.list_average("a"), "list_average", {}),
        (Derive.list_first("a"), "list_first", {}),
        (Derive.list_last("a"), "list_last", {}),
        (Derive.list_includes("a", "x"), "list_includes", {"value": "x"}),
        (Derive.list_includes("a", None), "list_includes", {"value": None}),
        (Derive.list_any("a", "gt", 5), "list_any", {"op": "gt", "value": 5}),
        (Derive.list_all("a", "eq", True), "list_all", {"op": "eq", "value": True}),
    ],
)
def test_derive_returns_derivation_ref(ref, kind, args):
    assert ref == DerivationRef(kind=kind, names=("a",), args=args)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_and_fragments_cover_every_v0067_kind():
    for kind in NEW_KINDS:
        assert kind in DERIVATION_REGISTRY
        assert kind in DERIVATION_FRAGMENTS


def test_registry_and_fragment_keys_stay_in_lockstep():
    assert set(DERIVATION_REGISTRY) == set(DERIVATION_FRAGMENTS)


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_every_new_kind_reads_exactly_one_name(kind):
    spec = DERIVATION_REGISTRY[kind]
    assert (spec.min_names, spec.max_names) == (1, 1)


def test_the_literal_arguments_of_the_new_kinds_are_exactly_the_documented_ones():
    for kind in NEW_KINDS:
        assert set(DERIVATION_REGISTRY[kind].extra_args) == set(SAMPLE_ARGS.get(kind, {}))
    # These are checked by `_validate_list_derivation_args`, not by the
    # generic string/int `LITERAL_ARG_RULES` table.
    assert not set(NEW_KINDS) & set(LITERAL_ARG_RULES)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_sample_arguments_are_valid(kind):
    _validate(DerivationRef(kind=kind, names=("s",), args=SAMPLE_ARGS.get(kind, {})))


@pytest.mark.parametrize(
    "derive,message",
    [
        (Derive.list_includes("s", [1]), r"value=\[1\].*isn't a str, bool, None"),
        (Derive.list_includes("s", {"a": 1}), r"isn't a str, bool, None"),
        (Derive.list_includes("s", float("nan")), r"isn't a str, bool, None"),
        (Derive.list_includes("s", float("inf")), r"isn't a str, bool, None"),
        (Derive.list_includes("s", 2**53 + 1), r"integer within \+/-2\*\*53"),
        (Derive.list_any("s", "contains", 1), r"unknown op 'contains'.*Known ops are"),
        (Derive.list_all("s", None, 1), r"unknown op None"),
        (Derive.list_any("s", ["gt"], 1), r"unknown op \['gt'\]"),
        (Derive.list_any("s", "eq", [1]), r"value=\[1\].*isn't a str, bool, None"),
        (Derive.list_all("s", "ne", float("nan")), r"isn't a str, bool, None"),
        (Derive.list_any("s", "gt", "5"), r"op='gt' and value='5'.*value must be a finite number"),
        (Derive.list_all("s", "lte", None), r"op='lte' and value=None.*must be a finite number"),
        (Derive.list_any("s", "lt", True), r"op='lt' and value=True.*must be a finite number"),
        (Derive.list_any("s", "gte", float("inf")), r"must be a finite number"),
        (Derive.list_all("s", "gt", 2**53 + 1), r"must be a finite number"),
    ],
)
def test_bad_literal_arguments_are_build_errors(derive, message):
    with pytest.raises(ValidationError, match=message):
        _validate(derive)


@pytest.mark.parametrize(
    "derive",
    [
        Derive.list_includes("s", None),
        Derive.list_includes("s", ""),
        Derive.list_includes("s", False),
        Derive.list_includes("s", 0),
        Derive.list_includes("s", 2**53),
        Derive.list_includes("s", -(2**53)),
        Derive.list_includes("s", 1.5),
        Derive.list_any("s", "eq", None),
        Derive.list_all("s", "ne", ""),
        Derive.list_any("s", "eq", True),
        Derive.list_any("s", "gt", 0),
        Derive.list_all("s", "gte", -1.5),
        Derive.list_all("s", "lte", 2**53),
    ],
)
def test_boundary_literal_arguments_are_accepted(derive):
    _validate(derive)


def test_every_compare_operator_is_accepted_by_list_any_and_list_all():
    for op in ("eq", "ne", "gt", "lt", "gte", "lte"):
        _validate(Derive.list_any("s", op, 1))
        _validate(Derive.list_all("s", op, 1))


def test_missing_and_unexpected_arguments_are_rejected():
    with pytest.raises(ValidationError, match="missing required argument"):
        _validate(DerivationRef(kind="list_any", names=("s",), args={"op": "gt"}))
    with pytest.raises(ValidationError, match="missing required argument"):
        _validate(DerivationRef(kind="list_includes", names=("s",), args={}))
    with pytest.raises(ValidationError, match="unexpected argument"):
        _validate(DerivationRef(kind="list_length", names=("s",), args={"x": 1}))
    with pytest.raises(ValidationError, match="unexpected argument"):
        _validate(DerivationRef(kind="list_includes", names=("s",), args={"value": 1, "op": "eq"}))


def test_arity_and_deps_are_enforced():
    tree = Page(
        State("a", [1]), State("b", [2]),
        Computed("out", deps=("a", "b"), derive=DerivationRef(kind="list_max", names=("a", "b"))),
    )
    with pytest.raises(ValidationError, match="needs exactly 1"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))
    tree = Page(State("a", [1]), Computed("out", deps=("a",), derive=Derive.list_max("b")))
    with pytest.raises(ValidationError, match="isn't in this Computed"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_one_of_still_reports_its_own_error_after_sharing_the_scalar_check():
    tree = Page(State("a", 1), Show(Predicate.one_of("a", [1, [2]]), Text("x")))
    with pytest.raises(ValidationError, match=r"gives Predicate\.one_of\(\.\.\.\) the value \[2\]"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# Build-time initial values -- exact expected results
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "derive,value,expected",
    [
        # list_length -- lists only; a non-list reads as an empty list
        (Derive.list_length("s"), [], 0),
        (Derive.list_length("s"), ["a", "b", "c"], 3),
        (Derive.list_length("s"), [None, None], 2),
        (Derive.list_length("s"), [[1, 2], [3]], 2),
        (Derive.list_length("s"), "hello", 0),
        (Derive.list_length("s"), {"a": 1, "b": 2}, 0),
        (Derive.list_length("s"), 5, 0),
        (Derive.list_length("s"), None, 0),
        (Derive.list_length("s"), True, 0),
        # list_min / list_max -- elements read as `Number(x) || 0`
        (Derive.list_min("s"), [3, 1, 2], 1.0),
        (Derive.list_max("s"), [3, 1, 2], 3.0),
        (Derive.list_min("s"), [5], 5.0),
        (Derive.list_min("s"), [-1.5, -5.5, 2.5], -5.5),
        (Derive.list_max("s"), [-1.5, -5.5, -2.5], -1.5),
        (Derive.list_min("s"), ["10", "9", "100"], 9.0),  # numeric strings are numbers
        (Derive.list_max("s"), ["10", "9", "100"], 100.0),
        (Derive.list_max("s"), [" 12 ", "0x10", "1e1"], 16.0),
        (Derive.list_min("s"), ["abc", 5], 0.0),  # NaN becomes 0
        (Derive.list_max("s"), ["abc", -5], 0.0),
        (Derive.list_max("s"), [True, False, 0.5], 1.0),  # booleans are 1/0
        (Derive.list_min("s"), [None, 4], 0.0),  # null is 0
        (Derive.list_max("s"), [[9], {"a": 9}, 4], 4.0),  # nested values are 0
        (Derive.list_min("s"), [float("nan"), 3], 0.0),
        (Derive.list_max("s"), [-0.0, -1], 0.0),
        (Derive.list_min("s"), [], math.inf),
        (Derive.list_max("s"), [], -math.inf),
        (Derive.list_min("s"), "not a list", math.inf),
        (Derive.list_max("s"), None, -math.inf),
        (Derive.list_max("s"), [1, float("inf")], math.inf),
        # list_average
        (Derive.list_average("s"), [1, 2, 3], 2.0),
        (Derive.list_average("s"), [1, 2], 1.5),
        (Derive.list_average("s"), [4], 4.0),
        (Derive.list_average("s"), ["2", 4, None], 2.0),  # (2 + 4 + 0) / 3
        (Derive.list_average("s"), [0.1] * 10, 0.09999999999999999),  # plain `+=` (1.0 / 10 would be 0.1): not a compensated sum()
        (Derive.list_average("s"), [1, -1], 0.0),
        # list_first / list_last -- the element itself, `null` when there is none
        (Derive.list_first("s"), ["a", "b", "c"], "a"),
        (Derive.list_last("s"), ["a", "b", "c"], "c"),
        (Derive.list_first("s"), [7], 7),
        (Derive.list_last("s"), [7], 7),
        (Derive.list_first("s"), [1.5, 2], 1.5),
        (Derive.list_last("s"), [True, False], False),
        (Derive.list_first("s"), [None, 1], None),
        (Derive.list_last("s"), [1, None], None),
        (Derive.list_first("s"), [], None),
        (Derive.list_last("s"), [], None),
        (Derive.list_first("s"), "abc", None),
        (Derive.list_last("s"), {"a": 1}, None),
        (Derive.list_first("s"), None, None),
        (Derive.list_first("s"), [[1, 2], [3]], [1, 2]),
        # list_includes -- strict equality, a real boolean
        (Derive.list_includes("s", "b"), ["a", "b"], True),
        (Derive.list_includes("s", "z"), ["a", "b"], False),
        (Derive.list_includes("s", 2), [1, 2, 3], True),
        (Derive.list_includes("s", 2.0), [1, 2, 3], True),
        (Derive.list_includes("s", 2), [1, 2.0, 3], True),
        (Derive.list_includes("s", "2"), [1, 2, 3], False),  # no coercion
        (Derive.list_includes("s", 1), [True], False),  # `1 === true` is false
        (Derive.list_includes("s", True), [1], False),
        (Derive.list_includes("s", True), [True], True),
        (Derive.list_includes("s", False), [0, ""], False),
        (Derive.list_includes("s", 0), [False, ""], False),
        (Derive.list_includes("s", None), [None], True),
        (Derive.list_includes("s", None), [0, ""], False),
        (Derive.list_includes("s", ""), [""], True),
        (Derive.list_includes("s", "😀"), ["a", "😀"], True),
        (Derive.list_includes("s", "\ud83d\ude00"), ["😀"], True),  # the same string in JavaScript
        (Derive.list_includes("s", "x"), [], False),
        (Derive.list_includes("s", "x"), "xyz", False),  # a string is not a list
        (Derive.list_includes("s", "x"), None, False),
        (Derive.list_includes("s", 2**53), [2**53 + 1], True),  # both are the same double
        (Derive.list_includes("s", 1), [[1]], False),  # no deep search
        # list_any / list_all -- one fixed comparison
        (Derive.list_any("s", "gt", 90), [70, 95, 88], True),
        (Derive.list_any("s", "gt", 95), [70, 95, 88], False),
        (Derive.list_any("s", "gte", 95), [70, 95, 88], True),
        (Derive.list_any("s", "lt", 70), [70, 95, 88], False),
        (Derive.list_any("s", "lte", 70), [70, 95, 88], True),
        (Derive.list_all("s", "gte", 70), [70, 95, 88], True),
        (Derive.list_all("s", "gt", 70), [70, 95, 88], False),
        (Derive.list_all("s", "lt", 100), [70, 95, 88], True),
        (Derive.list_all("s", "lte", 88), [70, 95, 88], False),
        (Derive.list_any("s", "eq", "done"), ["todo", "done"], True),
        (Derive.list_any("s", "eq", "Done"), ["todo", "done"], False),
        (Derive.list_all("s", "eq", True), [True, True], True),
        (Derive.list_all("s", "eq", True), [True, 1], False),  # `1 === true` is false
        (Derive.list_all("s", "ne", "x"), ["a", "b"], True),
        (Derive.list_any("s", "ne", "a"), ["a", "a"], False),
        (Derive.list_any("s", "eq", None), [1, None], True),
        # relational operators read the element as a number, not as text
        (Derive.list_any("s", "gt", 5), ["10"], True),  # 10 > 5 (a text comparison would say no)
        (Derive.list_any("s", "gt", 5), ["abc"], False),  # NaN -> 0
        (Derive.list_any("s", "lt", 1), ["abc"], True),  # ... and 0 < 1
        (Derive.list_any("s", "gt", 0), [None, []], False),
        (Derive.list_any("s", "gte", 1), [True], True),
        (Derive.list_all("s", "lt", 0.5), [False, None], True),
        # empty and non-list values: `some` is false, `every` is vacuously true
        (Derive.list_any("s", "eq", 1), [], False),
        (Derive.list_all("s", "eq", 1), [], True),
        (Derive.list_any("s", "gt", 0), "abc", False),
        (Derive.list_all("s", "gt", 0), "abc", True),
        (Derive.list_any("s", "eq", None), None, False),
        (Derive.list_all("s", "eq", 1), None, True),
    ],
)
def test_ir_build_evaluates_initial_value(derive, value, expected):
    result = _initial(derive, value)
    if isinstance(expected, float) and math.isnan(expected):
        assert math.isnan(result)
        return
    assert result == expected
    assert type(result) is type(expected)


def test_average_of_nothing_is_nan_like_zero_over_zero():
    for value in ([], "abc", None, {}):
        assert math.isnan(_initial(Derive.list_average("s"), value))


def test_state_is_read_through_derived_values_too():
    tree = Page(
        State("scores", [70, 95, "88"]),
        Computed("best", deps=("scores",), derive=Derive.list_max("scores")),
        Computed("shown", deps=("best",), derive=Derive.to_fixed("best", 1)),
        Computed("has_top", deps=("scores",), derive=Derive.list_any("scores", "gte", 95)),
    )
    computed = _ir({"/": tree}).pages[0].computed_initial
    assert computed["best"] == 95.0
    assert computed["shown"] == "95.0"
    assert computed["has_top"] is True


def test_a_derivation_can_return_a_list_that_another_one_reads():
    # `list_first` of a list of lists is itself a list.
    tree = Page(
        State("rows", [[4, 8], [1]]),
        Computed("head", deps=("rows",), derive=Derive.list_first("rows")),
        Computed("n", deps=("head",), derive=Derive.list_length("head")),
        Computed("top", deps=("head",), derive=Derive.list_max("head")),
    )
    computed = _ir({"/": tree}).pages[0].computed_initial
    assert computed["head"] == [4, 8]
    assert (computed["n"], computed["top"]) == (2, 8.0)


# ---------------------------------------------------------------------------
# js_list helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (1, 1.0), (0, 0.0), (-3, -3.0), (2.5, 2.5), (-0.0, 0.0), (float("nan"), 0.0),
        (float("inf"), math.inf), (True, 1.0), (False, 0.0), (10**400, math.inf),
        (-(10**400), -math.inf), (2**53 + 1, 9007199254740992.0),
        # strings follow `Number(string)`, not Python's `float()`
        ("12", 12.0), (" 12 ", 12.0), ("\t12\n", 12.0), ("\u00a012\u2003", 12.0), ("\ufeff12", 12.0),
        ("", 0.0), ("   ", 0.0), ("-5", -5.0), ("+5", 5.0), (".5", 0.5), ("5.", 5.0),
        ("1e3", 1000.0), ("1E-2", 0.01), ("1e400", math.inf), ("Infinity", math.inf),
        ("-Infinity", -math.inf), ("+Infinity", math.inf),
        ("0x10", 16.0), ("0X1f", 31.0), ("0o17", 15.0), ("0b101", 5.0),
        ("abc", 0.0), ("12px", 0.0), ("1 2", 0.0), ("1_0", 0.0), ("1,5", 0.0), ("--1", 0.0),
        ("inf", 0.0), ("infinity", 0.0), ("nan", 0.0), ("NaN", 0.0), ("e5", 0.0), ("5e", 0.0),
        ("0x", 0.0), ("-0x10", 0.0), ("0b12", 0.0), ("0o8", 0.0), (".", 0.0), ("+", 0.0),
        ("\u0663", 0.0), ("\uff11", 0.0),  # non-ASCII digits are not digits
        # anything that isn't a number, string or boolean reads as 0
        (None, 0.0), ([], 0.0), ([5], 0.0), ({"a": 1}, 0.0),
    ],
)
def test_js_to_number_reads_an_element_like_number_or_zero(value, expected):
    result = js_list.js_to_number(value)
    assert result == expected
    assert math.copysign(1.0, result) == math.copysign(1.0, expected)  # never -0


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (1, 1, True), (1, 1.0, True), (1, 2, False), (0, -0.0, True), ("a", "a", True), ("a", "b", False),
        ("1", 1, False), (1, True, False), (True, 1, False), (True, True, True), (False, 0, False),
        (None, None, True), (None, 0, False), (None, "", False), (None, False, False),
        ([1], [1], False), ({}, {}, False),  # objects are never strictly equal to a literal
        ("😀", "\ud83d\ude00", True), ("\ud83d", "\ud83d", True), ("\ud83d", "😀", False),
        (2**53, 2**53 + 1, True), (10**25, 10**25, True), (float("nan"), float("nan"), False),
        (float("inf"), float("inf"), True),
    ],
)
def test_js_strict_equal_is_triple_equals(a, b, expected):
    assert js_list.js_strict_equal(a, b) is expected


def test_tuples_are_lists_because_json_makes_them_arrays():
    assert js_list.js_list_length((1, 2, 3)) == 3
    assert js_list.js_list_max((1, 5)) == 5.0
    assert js_list.js_list_first(("a", "b")) == "a"


# ---------------------------------------------------------------------------
# HTML pre-fill
# ---------------------------------------------------------------------------


def _binds(tree):
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    return dict(re.findall(r'<span data-ark-bind="([^"]+)">([^<]*)</span>', html))


def test_html_prefill_spells_null_and_booleans_the_javascript_way():
    tree = Page(
        State("empty", []), State("todos", ["a", "b"]), State("scores", [70, 95]),
        Computed("head", deps=("empty",), derive=Derive.list_first("empty")),
        Computed("tail", deps=("todos",), derive=Derive.list_last("todos")),
        Computed("has_b", deps=("todos",), derive=Derive.list_includes("todos", "b")),
        Computed("has_z", deps=("todos",), derive=Derive.list_includes("todos", "z")),
        Computed("n", deps=("todos",), derive=Derive.list_length("todos")),
        Computed("hi", deps=("scores",), derive=Derive.list_max("scores")),
        Computed("nothing", deps=("empty",), derive=Derive.list_min("empty")),
        Computed("mean", deps=("empty",), derive=Derive.list_average("empty")),
        *[Text(Bind(name)) for name in ("head", "tail", "has_b", "has_z", "n", "hi", "nothing", "mean")],
    )
    binds = _binds(tree)
    assert binds["head"] == "null"  # not Python's "None"
    assert binds["tail"] == "b"
    assert binds["has_b"] == "true"
    assert binds["has_z"] == "false"
    assert binds["n"] == "2"
    assert binds["hi"] == "95.0"  # same spelling every numeric derivation already has
    assert binds["nothing"] == "Infinity"
    assert binds["mean"] == "NaN"


def test_an_unset_state_now_prefills_null_like_the_client_spells_it():
    tree = Page(State("nothing"), Text(Bind("nothing")))
    assert _binds(tree)["nothing"] == "null"


def test_html_prefill_of_a_boolean_derivation_drives_a_show_guard():
    def hidden(todos):
        tree = Page(
            State("todos", todos),
            Computed("any_left", deps=("todos",), derive=Derive.list_any("todos", "eq", "todo")),
            Show(Predicate.truthy("any_left"), Text("Keep going")),
        )
        html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
        i = html.index("data-ark-show")
        return " hidden" in html[i : i + 200]

    assert hidden(["todo", "done"]) is False
    assert hidden(["done", "done"]) is True
    assert hidden([]) is True


def test_a_non_empty_guard_built_from_list_length_matches_its_prefill():
    def hidden(items):
        tree = Page(
            State("items", items),
            Computed("n", deps=("items",), derive=Derive.list_length("items")),
            Show(Predicate.truthy("n"), Text("Cart")),
        )
        html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
        i = html.index("data-ark-show")
        return " hidden" in html[i : i + 200]

    assert hidden(["a"]) is False
    assert hidden([]) is True


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_js_render_ships_only_the_used_new_derivation_kind(kind):
    tree = Page(
        State("a", ["x", "y"]),
        Computed(
            "result", deps=("a",),
            derive=DerivationRef(kind=kind, names=("a",), args=SAMPLE_ARGS.get(kind, {})),
        ),
        Text(Bind("result")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert re.search(rf"\b{kind}: function", js)
    for other in DERIVATION_REGISTRY:
        if other != kind:
            assert not re.search(rf"\b{other}: function", js), other


def test_new_fragments_use_no_eval_or_new_function_or_regexp():
    for kind in NEW_KINDS:
        fragment = DERIVATION_FRAGMENTS[kind]
        assert "eval(" not in fragment
        assert "new Function" not in fragment
        assert "RegExp" not in fragment


def test_no_fragment_spreads_the_list_into_a_call_or_needs_a_modern_browser():
    # `Math.min(...list)` throws a RangeError past ~100k items, and `.at()`
    # is missing from browsers that predate 2022 -- loops and indexing
    # behave identically everywhere.
    for kind in NEW_KINDS:
        fragment = DERIVATION_FRAGMENTS[kind]
        assert "..." not in fragment, kind
        assert "Math.min" not in fragment and "Math.max" not in fragment, kind
        assert ".at(" not in fragment, kind


def test_a_very_long_list_does_not_overflow_the_call_stack():
    if _NODE is None:
        pytest.skip("node not available in this environment")
    fragments = ",\n".join(DERIVATION_FRAGMENTS[k] for k in ("list_min", "list_max", "list_average"))
    script = f"""
    var derivations = {{
{fragments}
    }};
    var big = [];
    for (var i = 0; i < 500000; i += 1) {{ big.push(i); }}
    var state = {{ n0: big }};
    console.log(JSON.stringify([
      derivations.list_min(state, ["n0"], {{}}),
      derivations.list_max(state, ["n0"], {{}}),
      derivations.list_average(state, ["n0"], {{}})
    ]));
    """
    out = json.loads(
        subprocess.run([_NODE, "-"], input=script, capture_output=True, text=True, check=True).stdout
    )
    assert out == [0, 499999, 249999.5]
    n = 500000
    assert js_list.js_list_average(list(range(n))) == 249999.5


def test_the_comparison_operator_is_only_ever_data_never_code():
    for kind in ("list_any", "list_all"):
        fragment = DERIVATION_FRAGMENTS[kind]
        assert "args.op" in fragment
        assert re.findall(r"case \"(\w+)\"", fragment) == ["eq", "ne", "gt", "lt", "gte", "lte"]


def test_a_page_with_only_a_list_derivation_ships_a_working_recompute_pass():
    tree = Page(
        State("todos", ["a"]),
        Computed("n", deps=("todos",), derive=Derive.list_length("todos")),
        Text(Bind("n")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "list_length: function" in js
    assert "recomputeAll" in js


# ---------------------------------------------------------------------------
# Node parity: the build-time mirror agrees with the shipped fragments
# ---------------------------------------------------------------------------

_NODE = shutil.which("node")

_NUMERIC_STRINGS = [
    "", " ", "0", "1", "-1", "+1", "12", " 12 ", "\t7\n", "\u00a07\u2003", "\ufeff7", "3.5", ".5", "5.", "-.5",
    "1e3", "1E3", "1e-2", "1e+2", "1e400", "-1e400", "5e", "e5", "1e", "Infinity", "-Infinity", "+Infinity",
    "infinity", "inf", "NaN", "nan", "0x10", "0X1F", "0xg", "0x", "-0x10", "0o17", "0O7", "0o8", "0b101",
    "0B11", "0b12", "1_0", "1,5", "12px", "px12", "1 2", "--1", "+-1", "0.0.1", ".", "+", "-", "abc",
    "\u0663", "\uff11", "\u2003", "\u180e5", "\u200b5", "00012", "-0", "0e0", "9007199254740993",
    "123456789012345678901234567890", "0x" + "f" * 30, "1" + "0" * 30,
]
_ODD_ELEMENTS = [
    None, True, False, 0, 1, -1, 2.5, -0.0, 1e21, 1e-7, 2**53, 2**53 + 1, -(2**53) - 1, 10**25,
    float("inf"), float("-inf"), float("nan"), "", "a", "😀", "\ud83d", "\ude00", [], [5], ["7"], [1, 2], {}, {"a": 1},
]
_LISTS = (
    [[], [0], [1], [-1], [1, 2, 3], [3, 1, 2], [2, 2], [-1, -5.5, 2.5], [0.1] * 10, [0.1, 0.2, 0.3]]
    + [[s] for s in _NUMERIC_STRINGS]
    + [[a, b] for a, b in zip(_NUMERIC_STRINGS, _NUMERIC_STRINGS[7:] + _NUMERIC_STRINGS[:7])]
    + [_NUMERIC_STRINGS]
    + [[e] for e in _ODD_ELEMENTS]
    + [[a, b] for a in _ODD_ELEMENTS[:14] for b in _ODD_ELEMENTS[14:20]]
    + [_ODD_ELEMENTS, list(reversed(_ODD_ELEMENTS))]
    + [["a", "b", "a"], ["todo", "done", "todo"], [True, True], [False, True], [1, "1", True, None, ""]]
    + [["😀", "a"], ["\ud83d", "\ude00"], ["\ud83d\ude00"], [[1, 2], [3]], [[["deep"]]], [{"a": 1}, {"b": 2}]]
    + [[1e308, 1e308], [1e308, -1e308], [float("inf"), float("-inf")], [2**53, 1], [5e-324, 5e-324]]
)
_NON_LISTS = [None, 0, 1, -1, 2.5, True, False, "", "abc", "12", {}, {"length": 3, "0": 1}, float("nan"), float("inf")]
_EQ_LITERALS = [
    None, True, False, 0, 1, 2, -1, 1.5, 2.5, 0.1, "", "a", "1", "0", "todo", "😀", "\ud83d\ude00", "\ud83d",
    1e21, 1e-7, 2**53, -(2**53), 100.0,
]
_REL_LITERALS = [0, 1, 2, 3, -1, 1.5, -0.5, 10, 100, 1e21, 1e-7, 2**53, -(2**53), 0.30000000000000004, 12, 16]
_OPS = ("eq", "ne", "gt", "lt", "gte", "lte")


def _parity_cases():
    values = _LISTS + _NON_LISTS
    cases = []
    for kind in UNARY_KINDS:
        cases += [(kind, value, {}) for value in values]
    for value in values:
        for literal in _EQ_LITERALS:
            cases.append(("list_includes", value, {"value": literal}))
    for value in values:
        for op in _OPS:
            literals = _EQ_LITERALS if op in ("eq", "ne") else _REL_LITERALS
            for literal in literals:
                cases.append(("list_any", value, {"op": op, "value": literal}))
                cases.append(("list_all", value, {"op": op, "value": literal}))
    return cases


def _canon_from_python(result):
    """The same `[type, text]` shape the Node script reports."""
    if result is None:
        return ["null", ""]
    if isinstance(result, bool):
        return ["boolean", "true" if result else "false"]
    if isinstance(result, (int, float)):
        number = float(result)
        text = "-0" if (number == 0 and math.copysign(1.0, number) < 0) else js_string.js_number_to_string(number)
        return ["number", text]
    if isinstance(result, str):
        return ["string", js_string.to_units(result)]
    return ["object", json.dumps(result, separators=(",", ":"))]


@pytest.mark.skipif(_NODE is None, reason="node not available in this environment")
def test_node_recompute_matches_build_time_initial_value_across_the_catalog():
    cases = _parity_cases()
    assert len(cases) > 15000
    fragments = ",\n".join(DERIVATION_FRAGMENTS[kind] for kind in NEW_KINDS)
    script = f"""
    var derivations = {{
{fragments}
    }};
    var cases = {json.dumps(cases)};
    function canon(r) {{
      if (r === undefined) return ["undefined", ""];
      if (r === null) return ["null", ""];
      if (typeof r === "boolean") return ["boolean", String(r)];
      if (typeof r === "number") return ["number", Object.is(r, -0) ? "-0" : String(r)];
      if (typeof r === "string") return ["string", r];
      return ["object", JSON.stringify(r)];
    }}
    console.log(JSON.stringify(cases.map(function (c) {{
      var state = {{ n0: c[1] }};
      return canon(derivations[c[0]](state, ["n0"], c[2]));
    }})));
    """
    # Via stdin: the case list is far past the command-line length limit.
    node_out = json.loads(
        subprocess.run(
            [_NODE, "-"], input=script, capture_output=True, text=True, encoding="utf-8", check=True
        ).stdout
    )
    assert len(node_out) == len(cases)

    mismatches = []
    for (kind, value, args), from_js in zip(cases, node_out):
        built = _evaluate_derivation(
            {"kind": kind, "names": ["n0"], "args": args}, get={"n0": value}.__getitem__
        )
        expected = _canon_from_python(built)
        if from_js[0] == "string":
            from_js = ["string", js_string.to_units(from_js[1])]
        if expected != from_js:
            mismatches.append((kind, value, args, built, from_js))
    assert not mismatches, mismatches[:10]
