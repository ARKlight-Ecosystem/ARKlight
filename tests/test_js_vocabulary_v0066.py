"""
Tests for `v0.066` -- JS vocabulary addendum, stage 6/10 (see
`docs/version history/v0.066.md`): the predicates catalog for `Show(...)`
-- `and`/`or`/`not`, `in_range`, `one_of`, `is_empty`/`is_not_empty`,
`is_null`. Mirrors `tests/test_js_vocabulary_v0062.py`.

The Node parity test at the bottom is the one that matters most: it runs
the *shipped* `arkEvalPredicate` (pulled straight out of
`RENDER_SHOW_JS`, not a copy) against the build-time evaluator over a
matrix of awkward values, because `Show`'s server-rendered `hidden`
attribute and the client's re-evaluation must never disagree.
"""

import json
import shutil
import subprocess

import pytest

from arklight.api import Page, Predicate, Show, State, Text
from arklight.ast.nodes import PredicateRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.render import JSBackend
from arklight.backend.js.runtime.show import RENDER_SHOW_JS
from arklight.cli.search import search_component
from arklight.ir.binary import decode_arklight, encode_arklight
from arklight.ir.build import build_website_ir
from arklight.ir.js_predicate import (
    PREDICATE_EVALUATORS,
    js_in_range,
    js_is_empty,
    js_one_of,
    js_truthy,
)
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import PREDICATE_REGISTRY
from arklight.ir.validate import ValidationError, validate_ark_ast

V0066_KINDS = ("and", "or", "not", "in_range", "one_of", "is_empty", "is_not_empty", "is_null")


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _validate(tree):
    validate_ark_ast(normalize_ark_ast({"/": tree}))


def _html(states: dict, predicate) -> str:
    tree = Page(*(State(k, v) for k, v in states.items()), Show(predicate, Text("body")))
    return HTMLBackend().render(_ir({"/": tree}))["index.html"]


def _hidden(html: str) -> bool:
    return " hidden>" in html


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_predicate_and_or_return_refs_with_any_number_of_names():
    assert Predicate.and_("a", "b") == PredicateRef(kind="and", names=("a", "b"))
    assert Predicate.and_("a", "b", "c").names == ("a", "b", "c")
    assert Predicate.or_("a", "b", "c") == PredicateRef(kind="or", names=("a", "b", "c"))


def test_predicate_unary_kinds_return_refs():
    assert Predicate.not_("a") == PredicateRef(kind="not", names=("a",))
    assert Predicate.is_empty("a") == PredicateRef(kind="is_empty", names=("a",))
    assert Predicate.is_not_empty("a") == PredicateRef(kind="is_not_empty", names=("a",))
    assert Predicate.is_null("a") == PredicateRef(kind="is_null", names=("a",))


def test_predicate_in_range_uses_clamp_argument_order():
    assert Predicate.in_range("x", "lo", "hi") == PredicateRef(
        kind="in_range", names=("x", "lo", "hi")
    )


def test_predicate_one_of_carries_values_in_args_as_a_list():
    ref = Predicate.one_of("tag", ("news", "sale"))
    assert ref == PredicateRef(kind="one_of", names=("tag",), args={"values": ["news", "sale"]})


@pytest.mark.parametrize("bad", ["abc", b"abc", 5, None, {"a": 1}])
def test_predicate_one_of_rejects_non_list_values(bad):
    with pytest.raises(TypeError, match="list or tuple"):
        Predicate.one_of("tag", bad)


def test_registry_covers_v0066_kinds():
    for kind in V0066_KINDS:
        assert kind in PREDICATE_REGISTRY
        assert kind in PREDICATE_EVALUATORS
    assert PREDICATE_REGISTRY["and"].variadic and PREDICATE_REGISTRY["or"].variadic
    assert PREDICATE_REGISTRY["in_range"].names == 3
    assert PREDICATE_REGISTRY["one_of"].extra_args == ("values",)


def test_preexisting_kinds_keep_their_fixed_arity_and_no_extra_args():
    for kind, names in (("truthy", 1), ("falsy", 1), ("equals", 2), ("gt", 2), ("lt", 2)):
        spec = PREDICATE_REGISTRY[kind]
        assert (spec.names, spec.variadic, spec.extra_args) == (names, False, ())


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_and_or_accept_two_or_more_declared_names():
    _validate(Page(State("a", True), State("b", 1), State("c", "x"),
                   Show(Predicate.and_("a", "b", "c"), Text("x")),
                   Show(Predicate.or_("a", "b"), Text("y"))))


@pytest.mark.parametrize("kind", ["and", "or"])
def test_and_or_reject_fewer_than_two_names(kind):
    tree = Page(State("a", True), Show(PredicateRef(kind=kind, names=("a",)), Text("x")))
    with pytest.raises(ValidationError, match="takes at least 2"):
        _validate(tree)


@pytest.mark.parametrize(
    "kind,names",
    [("not", ("a", "b")), ("is_empty", ()), ("is_null", ("a", "b")), ("in_range", ("a", "b"))],
)
def test_fixed_arity_kinds_reject_the_wrong_number_of_names(kind, names):
    tree = Page(State("a", 1), State("b", 2), Show(PredicateRef(kind=kind, names=names), Text("x")))
    with pytest.raises(ValidationError, match="takes exactly"):
        _validate(tree)


def test_new_kinds_reject_undeclared_state():
    tree = Page(State("a", 1), Show(Predicate.and_("a", "ghost"), Text("x")))
    with pytest.raises(ValidationError, match="'ghost'.*isn't declared"):
        _validate(tree)


def test_one_of_requires_its_values_argument():
    tree = Page(State("a", 1), Show(PredicateRef(kind="one_of", names=("a",)), Text("x")))
    with pytest.raises(ValidationError, match="missing required argument"):
        _validate(tree)


def test_kinds_without_extra_args_reject_unexpected_arguments():
    ref = PredicateRef(kind="is_null", names=("a",), args={"values": [1]})
    with pytest.raises(ValidationError, match="unexpected argument"):
        _validate(Page(State("a", 1), Show(ref, Text("x"))))


@pytest.mark.parametrize(
    "values,match",
    [
        ([], "non-empty list"),
        ("abc", "non-empty list"),
        ([float("nan")], "isn't a str"),
        ([float("inf")], "isn't a str"),
        ([2**53 + 1], "isn't a str"),
        ([[1]], "isn't a str"),
        ([{"a": 1}], "isn't a str"),
        (list(range(1001)), "limit is 1000"),
    ],
)
def test_one_of_rejects_bad_values(values, match):
    ref = PredicateRef(kind="one_of", names=("a",), args={"values": values})
    with pytest.raises(ValidationError, match=match):
        _validate(Page(State("a", 1), Show(ref, Text("x"))))


def test_one_of_accepts_every_json_scalar():
    ref = Predicate.one_of("a", ["s", 1, 2.5, True, None, -(2**53)])
    _validate(Page(State("a", 1), Show(ref, Text("x"))))


def test_unknown_predicate_error_lists_the_new_kinds():
    tree = Page(State("a", 1), Show(PredicateRef(kind="nope", names=("a",)), Text("x")))
    with pytest.raises(ValidationError, match="in_range"):
        _validate(tree)


# ---------------------------------------------------------------------------
# Build-time evaluators (arklight.ir.js_predicate)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, False), (False, False), (True, True), (0, False), (0.0, False),
        (float("nan"), False), (1, True), (-1, True), ("", False), ("0", True),
        ("false", True), ([], True), ([0], True), ({}, True),
    ],
)
def test_js_truthy_follows_javascript_not_python(value, expected):
    assert js_truthy(value) is expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, True), ("", True), ([], True), ((), True),
        (" ", False), ("0", False), (0, False), (False, False),
        ([None], False), ({}, False), (float("nan"), False),
    ],
)
def test_js_is_empty_covers_null_string_and_array_only(value, expected):
    assert js_is_empty(value) is expected


def test_js_one_of_is_strict_about_types():
    assert js_one_of("a", ["a", "b"]) is True
    assert js_one_of(1, [True]) is False       # Python: 1 == True
    assert js_one_of(True, [1]) is False
    assert js_one_of("1", [1]) is False
    assert js_one_of(1, [1.0]) is True         # both are the number 1 in JS
    assert js_one_of(None, [None]) is True
    assert js_one_of(None, [0, ""]) is False
    assert js_one_of([1], [1]) is False


def test_js_in_range_is_inclusive_and_coerces_like_clamp():
    assert js_in_range(5, 5, 10) and js_in_range(10, 5, 10)
    assert not js_in_range(4.99, 5, 10) and not js_in_range(10.01, 5, 10)
    assert js_in_range("7", 5, 10)            # Number("7")
    assert js_in_range("abc", -1, 1)          # Number("abc") || 0 -> 0
    assert js_in_range(None, 0, 0)
    assert not js_in_range(5, 10, 5)          # inverted bounds match nothing


# ---------------------------------------------------------------------------
# HTML backend -- hidden attribute against the initial state
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "states,predicate,visible",
    [
        ({"a": True, "b": 1}, Predicate.and_("a", "b"), True),
        ({"a": True, "b": 0}, Predicate.and_("a", "b"), False),
        ({"a": False, "b": 0, "c": "x"}, Predicate.or_("a", "b", "c"), True),
        ({"a": False, "b": 0}, Predicate.or_("a", "b"), False),
        ({"a": False}, Predicate.not_("a"), True),
        ({"a": "x"}, Predicate.not_("a"), False),
        ({"x": 5, "lo": 1, "hi": 9}, Predicate.in_range("x", "lo", "hi"), True),
        ({"x": 12, "lo": 1, "hi": 9}, Predicate.in_range("x", "lo", "hi"), False),
        ({"t": "sale"}, Predicate.one_of("t", ["news", "sale"]), True),
        ({"t": "other"}, Predicate.one_of("t", ["news", "sale"]), False),
        ({"q": ""}, Predicate.is_empty("q"), True),
        ({"q": "hi"}, Predicate.is_empty("q"), False),
        ({"q": []}, Predicate.is_empty("q"), True),
        ({"q": ""}, Predicate.is_not_empty("q"), False),
        ({"q": "hi"}, Predicate.is_not_empty("q"), True),
        ({"q": None}, Predicate.is_null("q"), True),
        ({"q": ""}, Predicate.is_null("q"), False),
    ],
)
def test_html_render_show_sets_hidden_against_initial_state(states, predicate, visible):
    assert _hidden(_html(states, predicate)) is (not visible)


def test_html_render_and_treats_an_empty_list_as_truthy_like_the_browser():
    # Python's bool([]) is False; the client's !![] is true.
    assert not _hidden(_html({"a": True, "items": []}, Predicate.and_("a", "items")))


def test_data_ark_show_carries_args_only_for_one_of():
    one_of = _html({"t": "a"}, Predicate.one_of("t", ["a", "b"]))
    assert "&quot;args&quot;: {&quot;values&quot;: [&quot;a&quot;, &quot;b&quot;]}" in one_of
    assert "&quot;args&quot;" not in _html({"a": 1}, Predicate.is_null("a"))
    assert "&quot;args&quot;" not in _html({"a": 1}, Predicate.truthy("a"))


# ---------------------------------------------------------------------------
# JS backend + search + binary
# ---------------------------------------------------------------------------


def test_js_render_ships_every_new_predicate_case_when_show_is_used():
    tree = Page(State("a", True), State("b", True), Show(Predicate.and_("a", "b"), Text("x")))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    for kind in V0066_KINDS:
        assert f'spec.kind === "{kind}"' in js
    # The pre-existing cases are untouched.
    for kind in ("equals", "gt", "lt", "falsy"):
        assert f'spec.kind === "{kind}"' in js


def test_search_reports_variadic_arity_and_extra_args():
    assert "at least 2 names" in search_component("Predicate.and")
    assert "exactly 3 names" in search_component("predicate.in_range")
    one_of = search_component("Predicate.one_of")
    assert "exactly 1 name" in one_of and "extra args     : values" in one_of


def test_one_of_values_survive_an_arklight_binary_round_trip():
    # The decoder currently leaves a `Show`'s `predicate` as the tagged
    # dict rather than a live `PredicateRef` -- true of `truthy` too, so
    # not something this stage introduced. Either form is fine here; what
    # matters is that `one_of`'s literal `values` make the trip intact.
    tree = Page(State("t", "a"), Show(Predicate.one_of("t", ["a", 2, None]), Text("x")))
    decoded = decode_arklight(encode_arklight(_ir({"/": tree})))
    show = next(c for c in decoded.pages[0].root.children if c.type == "Show")
    ref = show.props["predicate"]
    fields = ref if isinstance(ref, dict) else {"kind": ref.kind, "args": ref.args}
    assert fields["kind"] == "one_of"
    assert fields["args"] == {"values": ["a", 2, None]}


# ---------------------------------------------------------------------------
# Node parity: shipped arkEvalPredicate vs. the build-time evaluator
# ---------------------------------------------------------------------------

_VALUES = [None, True, False, 0, 1, -3, 2.5, float("nan"), "", "0", "a", "7", " ", [], [0]]


def _cases():
    """(kind, names, args, state) tuples covering awkward values."""
    cases = []
    for v in _VALUES:
        for kind in ("not", "is_empty", "is_not_empty", "is_null"):
            cases.append((kind, ["x"], {}, {"x": v}))
        cases.append(("one_of", ["x"], {"values": ["a", 1, True, None, "", 2.5, 0]}, {"x": v}))
    for a in _VALUES:
        for b in _VALUES:
            for kind in ("and", "or"):
                cases.append((kind, ["x", "y"], {}, {"x": a, "y": b}))
                cases.append((kind, ["x", "y", "z"], {}, {"x": a, "y": b, "z": True}))
    numeric = [None, True, False, 0, 1, -3, 2.5, float("nan"), "", "abc", "7", " 5 "]
    for x in numeric:
        for lo in (-3, 0, "abc"):
            for hi in (0, 5, 2.5):
                cases.append(("in_range", ["x", "lo", "hi"], {}, {"x": x, "lo": lo, "hi": hi}))
    return cases


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_node_arkevalpredicate_matches_build_time_evaluator_for_every_new_kind():
    cases = _cases()
    assert len(cases) > 1000
    payload = json.dumps(
        [{"kind": k, "names": n, "args": a, "state": s} for k, n, a, s in cases],
        allow_nan=True,  # emits the bare JS literal NaN, valid inside a JS array
    )
    script = f"""
    function arkReportError() {{}}
    {RENDER_SHOW_JS}
    var cases = {payload};
    var out = cases.map(function (c) {{
      var store = {{ get: function (name) {{ return c.state[name]; }} }};
      var spec = {{ kind: c.kind, names: c.names }};
      if (Object.keys(c.args).length) spec.args = c.args;
      return arkEvalPredicate(store, spec);
    }});
    console.log(JSON.stringify(out));
    """
    node = subprocess.run(
        [shutil.which("node"), "-e", script], capture_output=True, text=True, check=True
    )
    js_results = json.loads(node.stdout)
    mismatches = []
    for (kind, names, args, state), js_result in zip(cases, js_results):
        py_result = PREDICATE_EVALUATORS[kind](names, args, state.get)
        if py_result != js_result:
            mismatches.append((kind, state, args, py_result, js_result))
    assert not mismatches, mismatches[:5]
