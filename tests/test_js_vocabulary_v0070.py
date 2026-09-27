"""
Tests for `v0.070` -- JS vocabulary addendum, stage 10/10, the capstone
(see `docs/version history/v0.070.md`): `Derive.pluralize` and
`Derive.random_int`, the two entries the addendum's "Scope filter"
(`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`) flagged as
needing an explicit design exception before they could ship as
written.

Same shape as `tests/test_js_vocabulary_v0069.py` for `pluralize`
(API, registry, validation, build-time initial values, and a Node
parity sweep). `random_int` is not a pure function of its inputs by
design, so instead of a parity sweep it gets: arity/argument
validation (including the `min > max` check), the documented
build-time placeholder behavior, and a Node-side check that the
shipped fragment always lands in `[min, max]`.
"""

import json
import shutil
import subprocess

import pytest

from arklight.api import Computed, Derive, Page, State
from arklight.ast.nodes import DerivationRef
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.ir import js_string
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import DERIVATION_REGISTRY, LITERAL_ARG_RULES
from arklight.ir.validate import ValidationError, validate_ark_ast

NEW_KINDS = ("pluralize", "random_int")
_NODE = shutil.which("node")


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _initial(derive, **state):
    tree = Page(
        *(State(name, value) for name, value in state.items()),
        Computed("out", deps=tuple(state) or ("x",), derive=derive),
    )
    return _ir({"/": tree}).pages[0].computed_initial["out"]


def _validate(derive, deps=("x",)):
    tree = Page(State("x", 1), Computed("out", deps=deps, derive=derive))
    validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# API and registry
# ---------------------------------------------------------------------------


def test_derive_pluralize_returns_an_ordered_pair_derivation_ref():
    ref = Derive.pluralize("word", "count")
    assert ref == DerivationRef(kind="pluralize", names=("word", "count"))


def test_derive_random_int_returns_a_zero_name_derivation_ref():
    ref = Derive.random_int(min=1, max=6)
    assert ref == DerivationRef(kind="random_int", names=(), args={"min": 1, "max": 6})


def test_registry_and_fragments_cover_every_v0070_kind():
    for kind in NEW_KINDS:
        assert kind in DERIVATION_REGISTRY
        assert kind in DERIVATION_FRAGMENTS


def test_registry_and_fragment_keys_stay_in_lockstep():
    assert set(DERIVATION_REGISTRY) == set(DERIVATION_FRAGMENTS)


def test_pluralize_arity_is_exactly_two():
    spec = DERIVATION_REGISTRY["pluralize"]
    assert spec.min_names == 2
    assert spec.max_names == 2
    with pytest.raises(ValidationError):
        _validate(DerivationRef(kind="pluralize", names=("x",)))
    with pytest.raises(ValidationError):
        _validate(
            DerivationRef(kind="pluralize", names=("x", "x", "x")),
            deps=("x",),
        )


def test_pluralize_rejects_unexpected_arguments():
    with pytest.raises(ValidationError):
        _validate(
            DerivationRef(kind="pluralize", names=("x", "x"), args={"extra": 1}),
        )


def test_random_int_arity_is_exactly_zero():
    spec = DERIVATION_REGISTRY["random_int"]
    assert spec.min_names == 0
    assert spec.max_names == 0
    with pytest.raises(ValidationError):
        _validate(
            DerivationRef(kind="random_int", names=("x",), args={"min": 1, "max": 6}),
        )


def test_random_int_requires_min_and_max():
    with pytest.raises(ValidationError):
        _validate(DerivationRef(kind="random_int", names=(), args={"min": 1}))
    with pytest.raises(ValidationError):
        _validate(DerivationRef(kind="random_int", names=(), args={"max": 6}))


def test_random_int_rejects_min_above_max():
    with pytest.raises(ValidationError):
        _validate(DerivationRef(kind="random_int", names=(), args={"min": 6, "max": 1}))


def test_random_int_accepts_equal_min_and_max():
    # Degenerate but valid: always "rolls" the same number.
    _validate(DerivationRef(kind="random_int", names=(), args={"min": 4, "max": 4}))


def test_random_int_min_max_use_the_saturating_bound_literal_arg_rule():
    assert "random_int" in LITERAL_ARG_RULES
    assert set(LITERAL_ARG_RULES["random_int"]) == {"min", "max"}


# ---------------------------------------------------------------------------
# `pluralize` documented examples (build-time mirror)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word, count, expected",
    [
        ("item", 0, "items"),
        ("item", 1, "item"),
        ("item", 2, "items"),
        ("item", 1.0, "item"),
        ("box", 2, "boxes"),
        ("buzz", 2, "buzzes"),
        ("wish", 2, "wishes"),
        ("church", 2, "churches"),
        ("city", 2, "cities"),
        ("day", 2, "days"),  # vowel + y: regular +s, not +ies
        ("person", 2, "people"),
        ("child", 5, "children"),
        ("octopus", 2, "octopi"),
        ("leaf", 3, "leaves"),
        ("Person", 2, "Persons"),  # exact-match only, no case-folding
    ],
)
def test_pluralize_examples(word, count, expected):
    assert js_string.js_pluralize(word, count) == expected


def test_build_time_initial_value_uses_the_mirror():
    assert _initial(Derive.pluralize("noun", "qty"), noun="item", qty=3) == "items"
    assert _initial(Derive.pluralize("noun", "qty"), noun="item", qty=1) == "item"


def test_build_time_random_int_prefills_with_min_as_a_placeholder():
    # Documented design exception: not a pure function of its inputs, so
    # build time never tries to reproduce `Math.random()` -- it pre-fills
    # `min` and leaves the real roll to the client's `recomputeAll()`.
    assert _initial(Derive.random_int(min=3, max=9), x=1) == 3
    assert _initial(Derive.random_int(min=-5, max=-1), x=1) == -5
    assert _initial(Derive.random_int(min=4, max=4), x=1) == 4


# ---------------------------------------------------------------------------
# Node parity: run the shipped JS fragments and the Python mirror side by side
# ---------------------------------------------------------------------------

_PLURALIZE_CASES = [
    ("item", 0), ("item", 1), ("item", 2), ("item", -1), ("item", 1.5),
    ("box", 3), ("buzz", 2), ("wish", 4), ("church", 2), ("city", 5),
    ("day", 2), ("key", 3), ("person", 2), ("child", 0), ("man", 2),
    ("woman", 3), ("tooth", 2), ("foot", 2), ("mouse", 2), ("goose", 2),
    ("ox", 2), ("octopus", 2), ("cactus", 2), ("index", 2), ("matrix", 2),
    ("vertex", 2), ("criterion", 2), ("phenomenon", 2), ("die", 2),
    ("leaf", 2), ("life", 2), ("knife", 2), ("wife", 2), ("half", 2),
    ("loaf", 2), ("shelf", 2), ("wolf", 2), ("elf", 2), ("calf", 2),
    ("self", 2), ("sheep", 2), ("Person", 2), ("dog", 0), ("dog", 1),
]


def _node_pluralize_results(cases):
    frag = DERIVATION_FRAGMENTS["pluralize"]
    script = (
        "const D = {\n" + frag + "\n};\n"
        f"const inputs = {json.dumps(cases)};\n"
        "console.log(JSON.stringify(inputs.map("
        "(pair) => D.pluralize({w: pair[0], c: pair[1]}, ['w', 'c'], {}))));\n"
    )
    out = subprocess.run([_NODE, "-"], input=script, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(_NODE is None, reason="node is not installed")
def test_python_mirror_matches_the_shipped_javascript_for_pluralize():
    js_out = _node_pluralize_results(_PLURALIZE_CASES)
    py_out = [js_string.js_pluralize(word, count) for word, count in _PLURALIZE_CASES]
    assert py_out == js_out, [
        (case, py, js)
        for case, py, js in zip(_PLURALIZE_CASES, py_out, js_out)
        if py != js
    ]


@pytest.mark.skipif(_NODE is None, reason="node is not installed")
def test_random_int_javascript_always_lands_in_bounds():
    frag = DERIVATION_FRAGMENTS["random_int"]
    script = (
        "const D = {\n" + frag + "\n};\n"
        "const rolls = [];\n"
        "for (let i = 0; i < 500; i++) {\n"
        "  rolls.push(D.random_int({}, [], {min: 1, max: 6}));\n"
        "}\n"
        "console.log(JSON.stringify(rolls));\n"
    )
    out = subprocess.run([_NODE, "-"], input=script, capture_output=True, text=True, check=True)
    rolls = json.loads(out.stdout)
    assert all(isinstance(r, int) and 1 <= r <= 6 for r in rolls)
    # Not a hard guarantee, but with 500 rolls over 6 buckets this would
    # only fail by extraordinary bad luck -- catches an off-by-one that
    # silently narrows the range instead.
    assert len(set(rolls)) > 1


@pytest.mark.skipif(_NODE is None, reason="node is not installed")
def test_a_page_with_a_v0070_kind_ships_a_working_recompute_pass():
    from arklight.backend.js.render import JSBackend

    tree = Page(
        State("noun", "item"),
        State("qty", 3),
        Computed("label", deps=("noun", "qty"), derive=Derive.pluralize("noun", "qty")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "pluralize: function" in js
