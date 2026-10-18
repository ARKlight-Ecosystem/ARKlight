"""
Tests for `list_at` -- Tier 3, SS7.3 of
`docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md`: the list-side
counterpart of `char_at` (one arbitrary-index read into a list-valued
`State(...)`/`Computed(...)`, literal non-negative index, `null` past
the end). Not one of the ten `v0.061`-`v0.070` JS vocabulary addendum
stages -- a follow-up addition layered on top of that catalog, same
registry shape as `tests/test_js_vocabulary_v0065.py`'s `char_at`
coverage and `tests/test_js_vocabulary_v0067.py`'s list-scalar coverage.
"""

import json
import re
import shutil
import subprocess

import pytest

from arklight.api import Bind, Computed, Derive, Page, State, Text
from arklight.ast.nodes import DerivationRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.backend.js.render import JSBackend
from arklight.ir import js_list, js_string
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import DERIVATION_REGISTRY, LITERAL_ARG_RULES
from arklight.ir.validate import ValidationError, validate_ark_ast

KIND = "list_at"
_NODE = shutil.which("node")


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


def test_derive_list_at_returns_a_derivation_ref():
    assert Derive.list_at("a", 2) == DerivationRef(kind=KIND, names=("a",), args={"index": 2})


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_and_fragments_cover_list_at():
    assert KIND in DERIVATION_REGISTRY
    assert KIND in DERIVATION_FRAGMENTS
    assert set(DERIVATION_REGISTRY) == set(DERIVATION_FRAGMENTS)


def test_list_at_reads_exactly_one_name():
    spec = DERIVATION_REGISTRY[KIND]
    assert (spec.min_names, spec.max_names) == (1, 1)
    assert spec.extra_args == ("index",)


def test_list_at_is_checked_by_the_generic_literal_arg_rules_table():
    # Same path as `char_at`, not the special `list_includes`/`list_any`/
    # `list_all` validator -- see `arklight.ir.schema.LITERAL_ARG_RULES`.
    assert KIND in LITERAL_ARG_RULES
    assert set(LITERAL_ARG_RULES[KIND]) == {"index"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_sample_arguments_are_valid():
    _validate(DerivationRef(kind=KIND, names=("s",), args={"index": 0}))


@pytest.mark.parametrize(
    "derive,message",
    [
        (Derive.list_at("s", -1), r"index=-1.*from 0 to"),
        (Derive.list_at("s", 1.0), r"must be an integer\."),
        (Derive.list_at("s", True), r"must be an integer\."),
        (Derive.list_at("s", "1"), r"must be an integer\."),
    ],
)
def test_bad_literal_arguments_are_build_errors(derive, message):
    with pytest.raises(ValidationError, match=message):
        _validate(derive)


@pytest.mark.parametrize(
    "derive",
    [
        Derive.list_at("s", 0),
        Derive.list_at("s", 2**31 - 1),
    ],
)
def test_boundary_literal_arguments_are_accepted(derive):
    _validate(derive)


def test_missing_and_unexpected_arguments_are_rejected():
    with pytest.raises(ValidationError, match="missing required argument"):
        _validate(DerivationRef(kind=KIND, names=("s",), args={}))
    with pytest.raises(ValidationError, match="unexpected argument"):
        _validate(DerivationRef(kind=KIND, names=("s",), args={"index": 0, "extra": 1}))


def test_arity_is_enforced():
    with pytest.raises(ValidationError, match="needs exactly 1"):
        _validate(DerivationRef(kind=KIND, names=("s", "t"), args={"index": 0}))


# ---------------------------------------------------------------------------
# Build-time initial value (and its Python mirror, `js_list.js_list_at`)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,index,expected",
    [
        (["a", "b", "c"], 0, "a"),
        (["a", "b", "c"], 2, "c"),
        (["a", "b", "c"], 3, None),  # past the end -> null, never wraps
        ([], 0, None),
        ([7, 8], 1, 8),
        ([1.5, 2], 0, 1.5),
        ([True, False], 1, False),
        ([None, 1], 0, None),
        ("abc", 0, None),  # not a list -> reads as empty list
        ({"a": 1}, 0, None),
        (None, 0, None),
        ([[1, 2], [3]], 0, [1, 2]),  # a nested list, returned as itself
    ],
)
def test_ir_build_evaluates_initial_value(value, index, expected):
    assert _initial(Derive.list_at("s", index), value) == expected


def test_js_list_at_matches_the_ir_build_mirror_directly():
    assert js_list.js_list_at(["a", "b", "c"], 1) == "b"
    assert js_list.js_list_at(["a", "b", "c"], 10) is None
    assert js_list.js_list_at([], 0) is None
    assert js_list.js_list_at("not-a-list", 0) is None


def test_tuples_are_lists_because_json_makes_them_arrays():
    assert js_list.js_list_at(("a", "b"), 1) == "b"


# ---------------------------------------------------------------------------
# HTML pre-fill
# ---------------------------------------------------------------------------


def test_html_prefill_spells_an_out_of_range_result_null():
    tree = Page(
        State("items", ["x"]),
        Computed("mid", deps=("items",), derive=Derive.list_at("items", 5)),
        Text(Bind("mid")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert "null" in html


def test_a_derivation_can_feed_another_one():
    # `list_at` of a list of lists is itself a list -- same precedent
    # `list_first`/`list_last` already establish.
    tree = Page(
        State("rows", [["a", "b"], ["c", "d"]]),
        Computed("row0", deps=("rows",), derive=Derive.list_at("rows", 0)),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial["row0"] == ["a", "b"]


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


def test_js_render_ships_only_list_at_when_only_list_at_is_used():
    tree = Page(
        State("a", ["x", "y"]),
        Computed("result", deps=("a",), derive=Derive.list_at("a", 0)),
        Text(Bind("result")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert re.search(rf"\b{KIND}: function", js)
    for other in DERIVATION_REGISTRY:
        if other != KIND:
            assert not re.search(rf"\b{other}: function", js), other


def test_list_at_fragment_uses_no_eval_or_new_function_or_regexp_or_spread():
    fragment = DERIVATION_FRAGMENTS[KIND]
    assert "eval(" not in fragment
    assert "new Function" not in fragment
    assert "RegExp" not in fragment
    assert "..." not in fragment
    assert ".at(" not in fragment


# ---------------------------------------------------------------------------
# Node parity sweep
# ---------------------------------------------------------------------------

_LISTS = [
    [], ["a"], ["a", "b", "c"], [0, 1, 2], [True, False, None], [[1, 2], [3]],
    [1.5, -0.5, 2**53, 2**53 + 1], ["😀", "a"], [{"a": 1}, {"b": 2}],
]
_INDICES = [0, 1, 2, 3, 10, 2**31 - 1]
_NON_LISTS = [None, 0, 1, True, "", "abc", {}, {"length": 2, "0": "a"}]


def _parity_cases():
    cases = []
    for value in _LISTS + _NON_LISTS:
        for index in _INDICES:
            cases.append((KIND, value, {"index": index}))
    return cases


def _canon_from_python(result):
    if result is None:
        return ["null", ""]
    if isinstance(result, bool):
        return ["boolean", "true" if result else "false"]
    if isinstance(result, (int, float)):
        return ["number", js_string.js_number_to_string(float(result))]
    if isinstance(result, str):
        return ["string", result]
    return ["object", json.dumps(result, separators=(",", ":"))]


@pytest.mark.skipif(_NODE is None, reason="node not available in this environment")
def test_node_recompute_matches_build_time_initial_value():
    cases = _parity_cases()
    fragment = DERIVATION_FRAGMENTS[KIND]
    script = f"""
    var derivations = {{
{fragment}
    }};
    var cases = {json.dumps(cases)};
    function canon(r) {{
      if (r === undefined) return ["undefined", ""];
      if (r === null) return ["null", ""];
      if (typeof r === "boolean") return ["boolean", String(r)];
      if (typeof r === "number") return ["number", String(r)];
      if (typeof r === "string") return ["string", r];
      return ["object", JSON.stringify(r)];
    }}
    var out = [];
    for (var i = 0; i < cases.length; i++) {{
      var kind = cases[i][0], value = cases[i][1], args = cases[i][2];
      var state = {{s: value}};
      out.push(canon(derivations[kind](state, ["s"], args)));
    }}
    console.log(JSON.stringify(out));
    """
    result = subprocess.run([_NODE, "-e", script], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    node_results = json.loads(result.stdout)
    assert len(node_results) == len(cases)
    for (kind, value, args), node_result in zip(cases, node_results):
        python_result = js_list.js_list_at(value, args["index"])
        assert node_result == _canon_from_python(python_result), (kind, value, args)
