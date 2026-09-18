"""
Tests for `arklight.capabilities` (ACC's Stage 1 discovery hook).

These construct `importlib.metadata.EntryPoint` objects directly and
monkeypatch `entry_points()` rather than actually installing a package,
so the test suite doesn't need a real ACC distribution on disk -- the
same "exercised through direct calls rather than through the real
discovery path" allowance `IMPLEMENTATION-LADDER.md` Stage 1's own
acceptance note anticipates for anything built before an end-to-end
package exists.
"""

from __future__ import annotations

from importlib.metadata import EntryPoint

import pytest

from arklight.capabilities import (
    CAPABILITY_ENTRY_POINT_GROUP,
    CapabilityError,
    discover_capabilities,
    require_capability,
)


class _FakeCapability:
    def __init__(self, identity: str):
        self.identity = identity


def _entry_point(name: str, target, *, dist_name: str = "acc-fake") -> EntryPoint:
    """Build a real EntryPoint whose `.load()` returns `target` directly,
    without needing an installed distribution on disk."""
    ep = EntryPoint(name=name, value=f"{__name__}:_unused", group=CAPABILITY_ENTRY_POINT_GROUP)
    # EntryPoint.load() normally imports `value`; patch just this
    # instance's `load` so tests don't need real importable targets.
    object.__setattr__(ep, "load", lambda: target)
    object.__setattr__(ep, "dist", type("Dist", (), {"name": dist_name})())
    return ep


def _patch_entry_points(monkeypatch, entry_points: list[EntryPoint]) -> None:
    def fake_entry_points(*, group: str):
        assert group == CAPABILITY_ENTRY_POINT_GROUP
        return entry_points

    monkeypatch.setattr("arklight.capabilities.importlib_metadata.entry_points", fake_entry_points)


def test_no_capabilities_installed_returns_empty_dict(monkeypatch):
    _patch_entry_points(monkeypatch, [])
    assert discover_capabilities() == {}


def test_discovers_a_single_capability(monkeypatch):
    ep = _entry_point("prism", lambda: _FakeCapability("code.highlight"))
    _patch_entry_points(monkeypatch, [ep])

    found = discover_capabilities()

    assert set(found) == {"code.highlight"}
    assert found["code.highlight"].provider == "acc-fake"
    assert found["code.highlight"].identity == "code.highlight"


def test_non_callable_entry_point_raises_capability_error(monkeypatch):
    ep = _entry_point("prism", "not-a-callable")
    _patch_entry_points(monkeypatch, [ep])

    with pytest.raises(CapabilityError, match="not a valid|does not point at a callable"):
        discover_capabilities()


def test_registration_function_raising_is_wrapped(monkeypatch):
    def boom():
        raise RuntimeError("pygments not installed")

    ep = _entry_point("prism", boom)
    _patch_entry_points(monkeypatch, [ep])

    with pytest.raises(CapabilityError, match="raised while registering"):
        discover_capabilities()


def test_missing_identity_raises_capability_error(monkeypatch):
    ep = _entry_point("prism", lambda: object())
    _patch_entry_points(monkeypatch, [ep])

    with pytest.raises(CapabilityError, match="valid capability identity"):
        discover_capabilities()


def test_duplicate_capability_raises_capability_error(monkeypatch):
    ep1 = _entry_point("prism-a", lambda: _FakeCapability("code.highlight"), dist_name="acc-a")
    ep2 = _entry_point("prism-b", lambda: _FakeCapability("code.highlight"), dist_name="acc-b")
    _patch_entry_points(monkeypatch, [ep1, ep2])

    with pytest.raises(CapabilityError, match="Duplicate capability"):
        discover_capabilities()


def test_duplicate_capability_allowed_when_declared_multi(monkeypatch):
    ep1 = _entry_point("prism-a", lambda: _FakeCapability("code.highlight"), dist_name="acc-a")
    ep2 = _entry_point("prism-b", lambda: _FakeCapability("code.highlight"), dist_name="acc-b")
    _patch_entry_points(monkeypatch, [ep1, ep2])

    found = discover_capabilities(allow_multi=frozenset({"code.highlight"}))

    assert found["code.highlight"].provider == "acc-b"  # last one wins the dict slot


def test_require_capability_found():
    capabilities = {"code.highlight": object()}
    # require_capability only cares that the key is present; use a real
    # Capability-shaped stand-in via discover_capabilities' own type.
    from arklight.capabilities import Capability

    cap = Capability(identity="code.highlight", provider="acc-prism", value=42)
    assert require_capability("code.highlight", {"code.highlight": cap}) is cap


def test_require_capability_missing_raises():
    with pytest.raises(CapabilityError, match="was not found"):
        require_capability("code.highlight", {})
