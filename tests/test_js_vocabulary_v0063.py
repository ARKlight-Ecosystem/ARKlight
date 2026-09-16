"""
Tests for `v0.063` -- JS vocabulary addendum, stage 3/10 (see
`docs/version history/v0.063.md`): five small runtime primitives --
`reveal`/`lazy` (`on_reveal="reveal"`, `IntersectionObserver`),
debounced/throttled two-way binding (`Bind.model(..., debounce=...)`),
clipboard `paste` (mirrors `copy`), `Action.geolocate(name)`, and
`matchMedia`-driven boolean state (`State(..., media=...)`). Mirrors
the style of `tests/test_js_vocabulary_v0062.py`.
"""

import pytest

from arklight.api import (
    Action,
    Bind,
    Button,
    Container,
    Input,
    Page,
    Predicate,
    Show,
    State,
    Text,
)
from arklight.ast.nodes import ActionRef, ModelBindSpec
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.behaviors import BEHAVIOR_MODULES
from arklight.backend.js.render import JSBackend
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import ACTION_REGISTRY, BEHAVIOR_REGISTRY, KNOWN_REVEAL_BEHAVIORS
from arklight.ir.validate import ValidationError, validate_ark_ast


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


# ---------------------------------------------------------------------------
# Action.geolocate
# ---------------------------------------------------------------------------


def test_action_geolocate_returns_action_ref():
    ref = Action.geolocate("here")
    assert ref == ActionRef(action="geolocate", state="here", args={})


def test_action_registry_covers_geolocate():
    assert "geolocate" in ACTION_REGISTRY
    assert ACTION_REGISTRY["geolocate"].args == ()


def test_validate_accepts_geolocate_against_declared_state():
    tree = Page(
        State("here", None),
        Button("Find me", on_click=Action.geolocate("here")),
    )
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_validate_rejects_geolocate_against_undeclared_state():
    tree = Page(
        Button("Find me", on_click=Action.geolocate("nowhere")),
    )
    with pytest.raises(ValidationError):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_js_render_ships_geolocate_action_when_used():
    tree = Page(
        State("here", None),
        Button("Find me", on_click=Action.geolocate("here")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "geolocate: function" in js


def test_js_render_omits_geolocate_action_when_unused():
    tree = Page(State("count", 0), Button("+", on_click=Action.set("count", 1)))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "geolocate: function" not in js


# ---------------------------------------------------------------------------
# Clipboard paste
# ---------------------------------------------------------------------------


def test_behavior_registry_covers_paste():
    assert "paste" in BEHAVIOR_REGISTRY
    assert "paste" in BEHAVIOR_MODULES


def test_validate_accepts_paste_with_behavior_target():
    tree = Page(
        Button("Paste", on_click="paste", behavior_target="#target"),
        Input(id="target"),
    )
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_validate_rejects_paste_without_behavior_target():
    tree = Page(Button("Paste", on_click="paste"))
    with pytest.raises(ValidationError, match="behavior_target"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_html_render_compiles_paste_behavior_attrs():
    tree = Page(
        Button("Paste", on_click="paste", behavior_target="#target"),
        Input(id="target"),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-on-click="behavior:paste"' in html
    assert 'data-ark-target="#target"' in html


def test_js_render_ships_paste_behavior_when_used():
    tree = Page(
        Button("Paste", on_click="paste", behavior_target="#target"),
        Input(id="target"),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "paste: function" in js


def test_js_render_omits_paste_behavior_when_unused():
    tree = Page(Button("Copy", on_click="copy", behavior_target="#target"), Text(id="target"))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "paste: function" not in js
    assert "copy: function" in js


# ---------------------------------------------------------------------------
# matchMedia-driven boolean state
# ---------------------------------------------------------------------------


def test_state_media_prop_round_trips_through_ir():
    tree = Page(
        State("is_wide", False, media="(min-width: 768px)"),
        Show(Predicate.truthy("is_wide"), Text("Desktop layout")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].media == [("is_wide", "(min-width: 768px)")]
    assert ir.pages[0].state == {"is_wide": False}


def test_state_without_media_leaves_media_list_empty():
    tree = Page(State("count", 0))
    ir = _ir({"/": tree})
    assert ir.pages[0].media == []


def test_validate_rejects_non_string_media():
    tree = Page(State("bad", False, media=123))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="media"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_validate_rejects_empty_media():
    tree = Page(State("bad", False, media="   "))
    with pytest.raises(ValidationError, match="media"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_html_render_emits_data_ark_media_attribute():
    tree = Page(State("is_wide", False, media="(min-width: 768px)"))
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert "data-ark-media=" in html
    assert "is_wide" in html
    assert "(min-width: 768px)" in html


def test_html_render_omits_data_ark_media_when_no_media_state():
    tree = Page(State("count", 0))
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert "data-ark-media=" not in html


def test_js_render_reads_data_ark_media_attribute_in_init_state():
    tree = Page(State("is_wide", False, media="(min-width: 768px)"))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "data-ark-media" in js
    assert "matchMedia" in js


# ---------------------------------------------------------------------------
# reveal / lazy (IntersectionObserver)
# ---------------------------------------------------------------------------


def test_reveal_registry_has_reveal_kind():
    assert "reveal" in KNOWN_REVEAL_BEHAVIORS


def test_validate_accepts_known_reveal_behavior():
    tree = Page(Container(on_reveal="reveal", toggle_class="fade-in"))
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_validate_rejects_unknown_reveal_behavior():
    tree = Page(Container(on_reveal="not-a-thing"))
    with pytest.raises(ValidationError, match="on_reveal"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_reveal_does_not_require_behavior_target():
    # Unlike on_click, on_reveal observes the element itself.
    tree = Page(Container(on_reveal="reveal"))
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_html_render_compiles_on_reveal_attribute():
    tree = Page(Container(on_reveal="reveal", toggle_class="fade-in"))
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-on-reveal="reveal"' in html
    assert 'data-ark-toggle-class="fade-in"' in html


def test_js_render_ships_wire_reveal_when_used():
    tree = Page(Container(on_reveal="reveal"))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "function wireReveal" in js
    assert "wireReveal();" in js
    assert "IntersectionObserver" in js


def test_js_render_omits_wire_reveal_when_unused():
    tree = Page(Container(Text("hi")))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "function wireReveal" not in js


def test_reveal_works_without_any_state_declared():
    # has_reveal is independent of has_state.
    tree = Page(Container(on_reveal="reveal"))
    ir = _ir({"/": tree})
    assert ir.pages[0].state == {}
    js = JSBackend().render(ir)["arklight.js"]
    assert "function wireReveal" in js


# ---------------------------------------------------------------------------
# Debounced / throttled two-way binding (Bind.model)
# ---------------------------------------------------------------------------


def test_bind_model_without_modifier_returns_plain_string():
    assert Bind.model("query") == "query"


def test_bind_model_with_debounce_returns_model_bind_spec():
    spec = Bind.model("query", debounce=300)
    assert spec == ModelBindSpec(state="query", modifiers=("debounce:300",))


def test_bind_model_with_throttle_returns_model_bind_spec():
    spec = Bind.model("query", throttle=200)
    assert spec == ModelBindSpec(state="query", modifiers=("throttle:200",))


def test_html_render_compiles_model_bind_spec_modifiers():
    tree = Page(
        State("query", ""),
        Input(bind_value=Bind.model("query", debounce=300)),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-model="query"' in html
    assert 'data-ark-model-modifiers="debounce:300"' in html


# ---------------------------------------------------------------------------
# `from arklight import *` -- package export coverage
# ---------------------------------------------------------------------------


def test_wildcard_import_reaches_previously_missing_vocabulary():
    # Regression test for the gap test_package_exports.py already
    # found and fixed once before: Computed/Watch/Derive/
    # DerivationRef/Repeat/RepeatItem/Show/Predicate/PredicateRef/
    # ItemIndexRef/ClassBindSpec/ModelBindSpec were all definable via
    # `arklight.api`/`arklight.ast.nodes` but unreachable through
    # `from arklight import *`.
    namespace: dict = {}
    exec("from arklight import *", namespace)
    for name in (
        "Computed",
        "Watch",
        "Derive",
        "DerivationRef",
        "Repeat",
        "RepeatItem",
        "Show",
        "Predicate",
        "PredicateRef",
        "ItemIndexRef",
        "ClassBindSpec",
        "ModelBindSpec",
        "Action",
        "ActionRef",
        "State",
        "Bind",
    ):
        assert name in namespace, f"{name} unreachable via `from arklight import *`"


def test_api_wildcard_import_reaches_previously_missing_vocabulary():
    namespace: dict = {}
    exec("from arklight.api import *", namespace)
    for name in (
        "Repeat",
        "RepeatItem",
        "Show",
        "Predicate",
        "PredicateRef",
        "ItemIndexRef",
        "ClassBindSpec",
        "ModelBindSpec",
    ):
        assert name in namespace, f"{name} unreachable via `from arklight.api import *`"


def test_action_geolocate_reachable_after_wildcard_import():
    namespace: dict = {}
    exec("from arklight import *", namespace)
    ref = namespace["Action"].geolocate("here")
    assert ref == ActionRef(action="geolocate", state="here", args={})


# ---------------------------------------------------------------------------
# End-to-end: a page combining all five v0.063 primitives at once builds
# and renders cleanly, and a Node.js check that the shipped wireReveal
# fragment's default toggle-class behaves as documented.
# ---------------------------------------------------------------------------


def test_all_five_v0063_primitives_together():
    tree = Page(
        State("here", None),
        State("query", ""),
        State("is_wide", False, media="(min-width: 768px)"),
        Button("Find me", on_click=Action.geolocate("here")),
        Button("Paste", on_click="paste", behavior_target="#target"),
        Input(id="target", bind_value=Bind.model("query", debounce=300)),
        Container(on_reveal="reveal", toggle_class="fade-in"),
        Show(Predicate.truthy("is_wide"), Text("Desktop layout")),
    )
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    js = JSBackend().render(ir)["arklight.js"]

    assert "geolocate: function" in js
    assert "paste: function" in js
    assert "function wireReveal" in js
    assert "matchMedia" in js
    assert 'data-ark-model-modifiers="debounce:300"' in html
    assert 'data-ark-on-reveal="reveal"' in html
    assert "data-ark-media=" in html


def test_node_runtime_reveal_default_toggle_class_matches_docs():
    node = pytest.importorskip("shutil").which("node")
    if not node:
        pytest.skip("node not available in this environment")

    import subprocess

    from arklight.backend.js.runtime.reveal import WIRE_REVEAL_JS

    # A minimal DOM-free re-check that the fragment's fallback default
    # class name literal is exactly "is-visible", matching the module
    # docstring/PROGRESS.md/CHANGELOG.md documented default.
    script = f"""
    var src = {WIRE_REVEAL_JS!r};
    console.log(src.indexOf('"is-visible"') !== -1);
    """
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "true"
