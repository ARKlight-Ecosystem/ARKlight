"""
Tests for `Provider`, stage 6 of 6 (`v0.070`, see `arklight/provider.py`
and `docs/version history/v0.070.md`): capability vocabulary
finalization plus the `custom:`-prefixed escape hatch.

`test_provider.py` covers the closed four (`PROVIDER_CAPABILITIES`) and
predates stage 6; this file is the dedicated pass for the part stage 6
actually added -- `CUSTOM_CAPABILITY_PREFIX`, `is_custom_capability`,
`is_known_capability`, `Provider.declare(...)` accepting a well-formed
`custom:`-prefixed name, and `arklight search <name>`'s `(custom)`
tagging (`arklight/cli/search.py`'s `_format_provider_spec`) -- rather
than folding it into that file's existing structure.
"""

from __future__ import annotations

import pytest

from arklight import Provider
from arklight.cli.search import search_component
from arklight.ir.validate import validate_provider
from arklight.provider import (
    CUSTOM_CAPABILITY_PREFIX,
    PROVIDER_CAPABILITIES,
    PROVIDER_REGISTRY,
    ProviderDeclaration,
    is_custom_capability,
    is_known_capability,
    register_provider,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    PROVIDER_REGISTRY.clear()
    yield
    PROVIDER_REGISTRY.clear()


def _declare(**overrides):
    kwargs = {"name": "firebase", "capabilities": ["auth", "read"]}
    kwargs.update(overrides)
    return Provider.declare(**kwargs)


# ---------------------------------------------------------------------------
# The prefix constant and the two predicates
# ---------------------------------------------------------------------------


def test_the_prefix_is_custom_colon():
    assert CUSTOM_CAPABILITY_PREFIX == "custom:"


def test_is_custom_capability_true_for_a_well_formed_label():
    assert is_custom_capability("custom:inventory-sync") is True


@pytest.mark.parametrize(
    "cap",
    ["auth", "read", "write", "subscribe", "raed", "", "customs:x", "Custom:x"],
)
def test_is_custom_capability_false_for_anything_unprefixed_or_misspelled(cap):
    assert is_custom_capability(cap) is False


@pytest.mark.parametrize(
    "cap",
    [
        "custom:",
        "custom:Auth",
        "custom:-x",
        "custom:x-",
        "custom:x_",
        "custom:1x",
        "custom:x--y",
        "custom:x__y",
        "custom:x-_y",
        "custom:x_-y",
    ],
)
def test_is_custom_capability_false_for_a_malformed_label(cap):
    # A malformed label after the prefix is not accepted as some new,
    # oddly-named custom capability -- it falls through to the
    # unknown-capability error instead (see the declare() tests below).
    assert is_custom_capability(cap) is False


@pytest.mark.parametrize(
    "cap",
    ["custom:x", "custom:inventory-sync", "custom:a1", "custom:a_b", "custom:a-b-c"],
)
def test_is_custom_capability_true_for_valid_shapes(cap):
    assert is_custom_capability(cap) is True


def test_is_known_capability_true_for_each_well_known_name():
    for cap in PROVIDER_CAPABILITIES:
        assert is_known_capability(cap) is True


def test_is_known_capability_true_for_a_well_formed_custom_name():
    assert is_known_capability("custom:inventory-sync") is True


def test_is_known_capability_false_for_a_typo_of_a_well_known_name():
    # The one behavior stage 6 must not change: an unprefixed typo still
    # fails as unknown, never silently accepted as a new custom word.
    assert is_known_capability("raed") is False


def test_is_known_capability_false_for_a_malformed_custom_name():
    assert is_known_capability("custom:") is False
    assert is_known_capability("custom:Auth") is False


# ---------------------------------------------------------------------------
# Provider.declare(...) accepting the escape hatch
# ---------------------------------------------------------------------------


def test_declare_accepts_a_well_known_name_alongside_a_custom_one():
    decl = _declare(capabilities=["auth", "custom:inventory-sync"])
    assert decl.capabilities == ("auth", "custom:inventory-sync")


def test_declare_accepts_a_declaration_made_only_of_custom_names():
    decl = _declare(capabilities=["custom:inventory-sync", "custom:loyalty-points"])
    assert decl.capabilities == ("custom:inventory-sync", "custom:loyalty-points")


def test_declare_still_rejects_an_unprefixed_typo():
    with pytest.raises(ValueError, match=r"unknown capabilit.*\['raed'\]"):
        _declare(capabilities=["raed"])


def test_declare_rejects_a_malformed_custom_label():
    with pytest.raises(ValueError, match=r"unknown capabilit"):
        _declare(capabilities=["custom:"])


def test_declare_rejects_reusing_a_well_known_name_under_the_prefix():
    with pytest.raises(ValueError, match=r"already a well-known capability"):
        _declare(capabilities=["custom:read"])


def test_the_reused_well_known_error_points_at_the_unprefixed_form():
    with pytest.raises(ValueError) as exc_info:
        _declare(capabilities=["custom:auth"])
    message = str(exc_info.value)
    assert "custom:auth" in message
    assert "declare it without the prefix instead" in message


def test_a_duplicated_custom_capability_still_fails_as_duplicated():
    with pytest.raises(ValueError, match=r"\['custom:inventory-sync'\]"):
        _declare(capabilities=["custom:inventory-sync", "custom:inventory-sync"])


def test_two_distinct_custom_capabilities_are_not_treated_as_duplicates():
    decl = _declare(capabilities=["custom:inventory-sync", "custom:loyalty-points"])
    assert len(decl.capabilities) == 2


def test_a_hand_built_declaration_with_a_custom_capability_is_validated_too():
    decl = ProviderDeclaration(name="svc", capabilities=["custom:inventory-sync"])
    assert decl.capabilities == ("custom:inventory-sync",)


def test_a_hand_built_declaration_with_a_malformed_custom_capability_still_fails():
    with pytest.raises(ValueError, match=r"unknown capabilit"):
        ProviderDeclaration(name="svc", capabilities=["custom:Bad"])


# ---------------------------------------------------------------------------
# validate_provider (the pipeline's own re-check)
# ---------------------------------------------------------------------------


def test_validate_provider_accepts_a_custom_capability():
    validate_provider(_declare(capabilities=["auth", "custom:inventory-sync"]))  # must not raise


def test_validate_provider_still_catches_a_bypassed_malformed_custom_value():
    decl = _declare()
    object.__setattr__(decl, "capabilities", ("custom:Bad",))
    from arklight.ir.validate import ValidationError

    with pytest.raises(ValidationError, match=r"unknown capabilit"):
        validate_provider(decl)


# ---------------------------------------------------------------------------
# arklight search <name> -- the (custom) tag
# ---------------------------------------------------------------------------


def test_search_tags_a_custom_capability_but_not_a_well_known_one():
    register_provider(_declare(name="svc", capabilities=["auth", "custom:inventory-sync"]))
    result = search_component("svc")
    assert "  capabilities   : auth, custom:inventory-sync (custom)" in result


def test_search_adds_no_custom_explanation_line_when_nothing_is_custom():
    register_provider(_declare(name="svc", capabilities=["auth", "read"]))
    result = search_component("svc")
    assert "custom" not in result.lower()


def test_search_adds_the_custom_explanation_line_when_something_is_custom():
    register_provider(_declare(name="svc", capabilities=["custom:inventory-sync"]))
    result = search_component("svc")
    assert "custom:'-prefixed name is this" in result or "custom:'-prefixed" in result


def test_search_tags_every_custom_capability_independently():
    register_provider(
        _declare(name="svc", capabilities=["custom:inventory-sync", "auth", "custom:loyalty-points"])
    )
    result = search_component("svc")
    line = next(line for line in result.splitlines() if "capabilities" in line)
    assert "custom:inventory-sync (custom)" in line
    assert "custom:loyalty-points (custom)" in line
    assert ", auth," in line or line.endswith("auth")
