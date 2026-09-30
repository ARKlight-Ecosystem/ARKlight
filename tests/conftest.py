import os

import pytest


@pytest.fixture(autouse=True)
def _accept_arklight_license(monkeypatch):
    """
    The CLI's one-time license-acceptance gate (arklight.cli.license_gate)
    prompts interactively on first run. Tests run non-interactively, so
    set the documented CI/scripted-use bypass for every test -- this is
    exactly what a real CI pipeline would do after actually reading
    LICENSE once, not a way of skipping the gate's real behavior (which
    tests/test_license_gate.py exercises directly).
    """
    monkeypatch.setenv("ARKLIGHT_ACCEPT_LICENSE", "1")


@pytest.fixture(autouse=True)
def _isolate_component_registry():
    """
    `@component(...)` registrations are process-global
    (`arklight.ir.components.COMPONENT_REGISTRY`). The loader's own fix
    for register #2 (`unregister_components_under`, called before each
    load) only clears entries whose file lives under *that* load's own
    site_dir, so it's scoped to "rebuild the same project" -- it doesn't
    help two *different* temporary projects in the same test session
    that both happen to register a component with the same name (e.g.
    every scaffold test's "NavBar"). Without this, whichever such test
    runs second fails with "already registered" depending on run order.
    """
    from arklight.ir.components import COMPONENT_REGISTRY

    saved = dict(COMPONENT_REGISTRY)
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)
