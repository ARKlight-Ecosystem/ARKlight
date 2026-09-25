"""
Tests for `v0.068` -- JS vocabulary addendum, stage 8/10 (see
`docs/version history/v0.068.md`): the cross-language numeric
batteries catalog (`Derive.lerp`, `Derive.midpoint`,
`Derive.saturating_add`, `Derive.saturating_subtract`,
`Derive.value_or`, `Derive.first_present`). Same shape as
`tests/test_js_vocabulary_v0067.py`: API, registry, validation, and
build-time initial values -- the catalog's whole job is for the
build-time mirror (`arklight/ir/js_numeric.py`, `arklight/ir/build.py`)
to agree with the shipped JavaScript fragments.
"""

import math

import pytest

from arklight.api import Computed, Derive, Page, State
from arklight.ast.nodes import DerivationRef
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.ir.build import build_website_ir
from arklight.ir.js_numeric import js_lerp, js_midpoint
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import DERIVATION_REGISTRY, LITERAL_ARG_RULES
from arklight.ir.validate import ValidationError, validate_ark_ast

NEW_KINDS = (
    "lerp", "midpoint", "saturating_add", "saturating_subtract",
    "value_or", "first_present",
)


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _initial(derive, **state):
    """Build-time initial value of `Computed("out", derive=derive)`
    over the given named `State(...)` values."""
    tree = Page(
        *(State(name, value) for name, value in state.items()),
        Computed("out", deps=tuple(state), derive=derive),
    )
    return _ir({"/": tree}).pages[0].computed_initial["out"]


def _validate(derive, *names):
    tree = Page(
        *(State(name, 1) for name in names),
        Computed("out", deps=tuple(names), derive=derive),
    )
    validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_derive_returns_derivation_refs():
    assert Derive.lerp("a", "b", "t") == DerivationRef(kind="lerp", names=("a", "b", "t"))
    assert Derive.midpoint("a", "b") == DerivationRef(kind="midpoint", names=("a", "b"))
    assert Derive.saturating_add("a", "b", min=0, max=10) == DerivationRef(
        kind="saturating_add", names=("a", "b"), args={"min": 0, "max": 10}
    )
    assert Derive.saturating_subtract("a", "b", min=0, max=10) == DerivationRef(
        kind="saturating_subtract", names=("a", "b"), args={"min": 0, "max": 10}
    )
    assert Derive.value_or("a", "fallback") == DerivationRef(
        kind="value_or", names=("a",), args={"fallback": "fallback"}
    )
    assert Derive.first_present("a", "b", "c") == DerivationRef(
        kind="first_present", names=("a", "b", "c")
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_and_fragments_cover_every_v0068_kind():
    for kind in NEW_KINDS:
        assert kind in DERIVATION_REGISTRY
        assert kind in DERIVATION_FRAGMENTS


def test_registry_and_fragment_keys_stay_in_lockstep():
    assert set(DERIVATION_REGISTRY) == set(DERIVATION_FRAGMENTS)


def test_arities():
    assert (DERIVATION_REGISTRY["lerp"].min_names, DERIVATION_REGISTRY["lerp"].max_names) == (3, 3)
    assert (DERIVATION_REGISTRY["midpoint"].min_names, DERIVATION_REGISTRY["midpoint"].max_names) == (2, 2)
    assert (DERIVATION_REGISTRY["saturating_add"].min_names, DERIVATION_REGISTRY["saturating_add"].max_names) == (2, 2)
    assert (DERIVATION_REGISTRY["value_or"].min_names, DERIVATION_REGISTRY["value_or"].max_names) == (1, 1)
    assert (DERIVATION_REGISTRY["first_present"].min_names, DERIVATION_REGISTRY["first_present"].max_names) == (2, None)


def test_saturating_bounds_are_in_the_literal_arg_rules_table():
    assert set(LITERAL_ARG_RULES["saturating_add"]) == {"min", "max"}
    assert set(LITERAL_ARG_RULES["saturating_subtract"]) == {"min", "max"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_first_present_needs_at_least_two_names():
    with pytest.raises(ValidationError, match="needs at least 2"):
        _validate(DerivationRef(kind="first_present", names=("a",)), "a")


def test_value_or_fallback_must_be_a_json_scalar_literal():
    with pytest.raises(ValidationError, match="isn't a str, bool, None"):
        _validate(Derive.value_or("a", [1, 2]), "a")
    _validate(Derive.value_or("a", None), "a")
    _validate(Derive.value_or("a", "x"), "a")
    _validate(Derive.value_or("a", 5), "a")
    _validate(Derive.value_or("a", True), "a")


def test_saturating_min_must_not_be_above_max():
    with pytest.raises(ValidationError, match="min=10.*above max=0"):
        _validate(Derive.saturating_add("a", "b", min=10, max=0), "a", "b")
    with pytest.raises(ValidationError, match="min=10.*above max=0"):
        _validate(Derive.saturating_subtract("a", "b", min=10, max=0), "a", "b")
    _validate(Derive.saturating_add("a", "b", min=0, max=0), "a", "b")


def test_saturating_bounds_must_be_integers():
    with pytest.raises(ValidationError, match="min must be an integer"):
        _validate(DerivationRef(kind="saturating_add", names=("a", "b"), args={"min": "0", "max": 10}), "a", "b")


def test_missing_and_unexpected_arguments_are_rejected():
    with pytest.raises(ValidationError, match="missing required argument"):
        _validate(DerivationRef(kind="value_or", names=("a",), args={}), "a")
    with pytest.raises(ValidationError, match="unexpected argument"):
        _validate(DerivationRef(kind="lerp", names=("a", "b", "c"), args={"x": 1}), "a", "b", "c")


# ---------------------------------------------------------------------------
# Build-time initial values
# ---------------------------------------------------------------------------


def test_lerp_matches_std_lerp_edge_cases():
    assert _initial(Derive.lerp("a", "b", "t"), a=0.0, b=10.0, t=0.0) == 0.0
    assert _initial(Derive.lerp("a", "b", "t"), a=0.0, b=10.0, t=1.0) == 10.0
    assert _initial(Derive.lerp("a", "b", "t"), a=0.0, b=10.0, t=0.5) == 5.0
    assert _initial(Derive.lerp("a", "b", "t"), a=10.0, b=0.0, t=0.25) == 7.5


def test_midpoint_is_overflow_safe_average():
    assert _initial(Derive.midpoint("a", "b"), a=4.0, b=8.0) == 6.0
    assert _initial(Derive.midpoint("a", "b"), a=-4.0, b=4.0) == 0.0


def test_saturating_add_clamps_both_directions():
    assert _initial(Derive.saturating_add("a", "b", min=0, max=10), a=8.0, b=5.0) == 10
    assert _initial(Derive.saturating_add("a", "b", min=0, max=10), a=2.0, b=3.0) == 5.0
    assert _initial(Derive.saturating_add("a", "b", min=0, max=10), a=-8.0, b=-5.0) == 0


def test_saturating_subtract_clamps_at_the_floor():
    assert _initial(Derive.saturating_subtract("a", "b", min=0, max=10), a=2.0, b=5.0) == 0
    assert _initial(Derive.saturating_subtract("a", "b", min=0, max=10), a=8.0, b=3.0) == 5.0


def test_value_or_falls_back_on_null_undefined_and_empty_string():
    assert _initial(Derive.value_or("a", "fallback"), a="hi") == "hi"
    assert _initial(Derive.value_or("a", "fallback"), a="") == "fallback"
    assert _initial(Derive.value_or("a", "fallback"), a=None) == "fallback"
    assert _initial(Derive.value_or("a", "fallback"), a=0) == 0  # 0 is present, not empty
    assert _initial(Derive.value_or("a", "fallback"), a=False) is False


def test_first_present_returns_first_non_empty_in_order():
    assert _initial(Derive.first_present("a", "b", "c"), a=None, b="", c="third") == "third"
    assert _initial(Derive.first_present("a", "b"), a="first", b="second") == "first"
    assert _initial(Derive.first_present("a", "b"), a=None, b=None) is None
    assert _initial(Derive.first_present("a", "b"), a="", b="") == ""


def test_python_and_documented_semantics_agree_on_edge_cases():
    assert js_lerp(0.0, 10.0, 0.0) == 0.0
    assert js_lerp(0.0, 10.0, 1.0) == 10.0
    assert js_midpoint(1.0, 3.0) == 2.0
    assert math.isclose(js_lerp(1.0, 2.0, 0.5), 1.5)
