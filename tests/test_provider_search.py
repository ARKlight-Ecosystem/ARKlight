"""
Tests for `Provider`, stage 5 of 6 (`v0.069`, see `arklight/provider.py`
and `docs/version history/v0.069.md`): `arklight search <provider-name>`
prints a registered provider's declared contract.

Covers the registry (`PROVIDER_REGISTRY` / `register_provider` /
`resolve_provider`), the `Site(provider=...)` hook that fills it, and the
`arklight.cli.search` lookup path (`search_component` /
`_resolve_provider`).
"""

from __future__ import annotations

import pytest

from arklight import Provider, Site
from arklight.cli.search import search_component
from arklight.provider import (
    PROVIDER_REGISTRY,
    ProviderDeclaration,
    register_provider,
    resolve_provider,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    PROVIDER_REGISTRY.clear()
    yield
    PROVIDER_REGISTRY.clear()


def _declare(name="firebase", capabilities=("auth", "read")):
    return Provider.declare(name=name, capabilities=list(capabilities))


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------


def test_register_then_resolve_returns_the_declaration():
    decl = _declare()
    register_provider(decl)
    assert resolve_provider("firebase") == decl


def test_resolve_is_case_insensitive_and_returns_the_canonical_declaration():
    decl = _declare(name="Firebase")
    register_provider(decl)
    assert resolve_provider("FIREBASE") == decl
    assert resolve_provider("firebase") == decl


def test_resolve_returns_none_for_an_unregistered_name():
    assert resolve_provider("firebase") is None


def test_resolve_does_no_fuzzy_matching():
    register_provider(_declare(name="firebase"))
    assert resolve_provider("firebse") is None
    assert resolve_provider("fire") is None


def test_a_later_registration_with_the_same_name_replaces_the_earlier_one():
    register_provider(_declare(capabilities=("auth",)))
    newer = _declare(capabilities=("read", "write"))
    register_provider(newer)
    assert resolve_provider("firebase") == newer
    assert len(PROVIDER_REGISTRY) == 1


def test_register_rejects_a_non_declaration():
    with pytest.raises(ValueError):
        register_provider({"name": "firebase"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Site(provider=...) fills the registry
# ---------------------------------------------------------------------------


def test_constructing_a_site_with_a_provider_registers_it():
    decl = _declare()
    Site(provider=decl)
    assert resolve_provider("firebase") == decl


def test_constructing_a_site_without_a_provider_registers_nothing():
    Site()
    assert PROVIDER_REGISTRY == {}


# ---------------------------------------------------------------------------
# arklight search <provider-name>
# ---------------------------------------------------------------------------


def test_search_prints_the_declared_contract():
    register_provider(_declare(name="firebase", capabilities=("auth", "read")))
    result = search_component("firebase")
    assert result.splitlines()[0] == "firebase (declared provider, Site(provider=...))"
    assert "  capabilities   : auth, read" in result


def test_search_lists_capabilities_in_declared_order():
    register_provider(_declare(name="svc", capabilities=("write", "auth", "read")))
    result = search_component("svc")
    assert "  capabilities   : write, auth, read" in result


def test_search_names_the_runtime_config_object():
    register_provider(_declare())
    result = search_component("firebase")
    assert "window.ARKLIGHT_PROVIDER" in result


def test_search_provider_lookup_is_case_insensitive():
    register_provider(_declare(name="firebase"))
    assert "declared provider" in search_component("FireBase")


def test_search_reports_nothing_for_an_unregistered_provider_without_suggesting_it():
    register_provider(_declare(name="firebase"))
    result = search_component("supabase-nope")
    assert "declared provider" not in result
    assert "No component named 'supabase-nope' found" in result


def test_a_component_name_wins_over_a_provider_with_the_same_label():
    # A provider label is a free string; if it collides with a built-in
    # component name, the component keeps priority (as it does for every
    # other closed vocabulary lookup in this module).
    register_provider(_declare(name="Image", capabilities=("read",)))
    result = search_component("Image")
    assert "declared provider" not in result
    assert not result.startswith("Image (declared provider")


def test_search_provider_output_does_not_claim_dom_hooks_or_state_keys():
    register_provider(_declare())
    result = search_component("firebase")
    assert "DOM" not in result
    assert "state" not in result.lower()
