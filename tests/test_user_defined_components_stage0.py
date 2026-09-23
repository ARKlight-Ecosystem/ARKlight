"""
v0.060, Stage 0: user-defined, reusable components.

Covers `arklight.api.component`/`Prop`, `arklight.ir.components`'s
expansion pass (Option A -- the default `mode="macro"`), its props
contract enforcement, its cycle/depth guards, and the experimental
`mode="registry"` (Option B) selector -- see
`USER-DEFINED-COMPONENTS-IMPLEMENTATION.md` [retired -- see CHANGELOG.md].
"""

import pytest

from arklight.api import Container, Link, Page, Text, component
from arklight.ast.nodes import ARKNode
from arklight.ir.components import (
    COMPONENT_REGISTRY,
    ComponentError,
    ComponentSpec,
    DuplicateComponentError,
    Prop,
    expand_ark_ast,
    expand_node,
    register_component,
)
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast


@pytest.fixture(autouse=True)
def _clean_registry():
    """Each test gets a fresh `COMPONENT_REGISTRY` -- real projects
    register components once at import time, but tests would otherwise
    leak registrations across each other (same reason `Site.style(...)`
    re-registration is last-call-wins rather than append-only)."""
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# `component(...)` decorator / registration
# ---------------------------------------------------------------------------


def test_component_decorator_registers_and_returns_marker_factory():
    @component(props={"active": Prop(default=None)})
    def NavBar(active=None):  # noqa: N802 -- component name convention
        return Container(Link("Home", href="/"))

    assert "NavBar" in COMPONENT_REGISTRY
    marker = NavBar(active="home")
    assert isinstance(marker, ARKNode)
    assert marker.type == "NavBar"
    assert marker.props == {"active": "home"}
    assert marker.children == []


def test_component_defaults_to_macro_mode():
    @component()
    def Widget():
        return Text("hi")

    assert COMPONENT_REGISTRY["Widget"].mode == "macro"


def test_component_registry_mode_is_selectable():
    @component(mode="registry")
    def Experimental():
        return Text("hi")

    assert COMPONENT_REGISTRY["Experimental"].mode == "registry"


def test_invalid_mode_rejected_at_registration_time():
    with pytest.raises(ValueError):
        ComponentSpec(name="Bad", render_fn=lambda: None, mode="not-a-real-mode")


def test_re_registering_a_name_raises_without_allow_redefine():
    register_component("Thing", lambda: Text("v1"))

    with pytest.raises(DuplicateComponentError, match="already registered"):
        register_component("Thing", lambda: Text("v2"))

    # The failed second call didn't touch the first registration.
    assert COMPONENT_REGISTRY["Thing"].render_fn() == Text("v1")


def test_re_registering_a_name_with_allow_redefine_overwrites():
    register_component("Thing", lambda: Text("v1"))
    register_component("Thing", lambda: Text("v2"), allow_redefine=True)
    assert COMPONENT_REGISTRY["Thing"].render_fn() == Text("v2")


def test_registering_a_builtin_name_raises_without_allow_redefine():
    """Regression: `expand_ark_ast` looks a node up in the user registry
    before the built-in schema, so a user component named `Button`
    silently replaced every `Button(...)` in the site, ARKlight's own
    included, with no diagnostic anywhere."""
    with pytest.raises(DuplicateComponentError, match="would shadow the built-in"):
        register_component("Button", lambda: Text("HIJACKED"))
    assert "Button" not in COMPONENT_REGISTRY


def test_component_decorator_raises_when_named_like_a_builtin():
    with pytest.raises(DuplicateComponentError, match="would shadow the built-in"):
        @component()
        def Button():  # noqa: N802 -- component name convention
            return Text("HIJACKED")


def test_registering_a_builtin_name_with_allow_redefine_is_the_explicit_opt_in():
    register_component("Button", lambda: Text("deliberate"), allow_redefine=True)
    assert "Button" in COMPONENT_REGISTRY


def test_component_decorator_marks_whether_redefinition_was_allowed():
    from arklight.ir.components import ALLOW_REDEFINE_MARKER

    @component()
    def Plain():  # noqa: N802 -- component name convention
        return Text("x")

    @component(allow_redefine=True)
    def Deliberate():  # noqa: N802 -- component name convention
        return Text("x")

    assert getattr(Plain, ALLOW_REDEFINE_MARKER) is False
    assert getattr(Deliberate, ALLOW_REDEFINE_MARKER) is True


def test_component_decorator_raises_on_redefinition_without_allow_redefine():
    @component()
    def Thing():  # noqa: N802 -- component name convention
        return Text("v1")

    with pytest.raises(DuplicateComponentError, match="already registered"):
        @component()
        def Thing():  # noqa: N802,F811
            return Text("v2")


def test_component_decorator_allow_redefine_overwrites():
    @component()
    def Thing():  # noqa: N802 -- component name convention
        return Text("v1")

    @component(allow_redefine=True)
    def Thing():  # noqa: N802,F811
        return Text("v2")

    assert COMPONENT_REGISTRY["Thing"].render_fn() == Text("v2")


# ---------------------------------------------------------------------------
# Expansion (Option A -- macro), the pipeline's new stage between ARK-AST
# construction and Normalization.
# ---------------------------------------------------------------------------


def test_expand_replaces_marker_with_rendered_subtree():
    register_component(
        "NavBar",
        lambda active=None: Container(
            Link("Home", href="/", class_name="active" if active == "home" else None),
            class_name="nav",
        ),
        props={"active": Prop(default=None)},
    )

    page = Page(ARKNode(type="NavBar", props={"active": "home"}, children=[]))
    expanded = expand_node(page)

    assert expanded.type == "Page"
    navbar_expansion = expanded.children[0]
    assert navbar_expansion.type == "Container"
    assert navbar_expansion.props["class_name"] == "nav"
    assert navbar_expansion.children[0].props["class_name"] == "active"


def test_expand_is_a_noop_for_a_tree_with_no_component_calls():
    page = Page(Text("just plain text, no components anywhere"))
    expanded = expand_node(page)
    assert expanded == page


def test_expanded_tree_passes_normalize_and_validate_unchanged_downstream():
    """The whole point of Option A: by the time Normalization/Validation
    run, nothing in the tree is a user component anymore."""
    register_component(
        "Card",
        lambda title="": Container(Text(title)),
        props={"title": Prop(type=str, default="")},
    )
    ark_ast = {"/": Page(ARKNode(type="Card", props={"title": "Hi"}, children=[]))}
    expanded = expand_ark_ast(ark_ast)
    normalized = normalize_ark_ast(expanded)
    validate_ark_ast(normalized)  # must not raise


def test_expansion_recurses_into_nested_user_components():
    register_component("Inner", lambda: Text("inner"))
    register_component("Outer", lambda: Container(ARKNode(type="Inner", props={}, children=[])))

    page = Page(ARKNode(type="Outer", props={}, children=[]))
    expanded = expand_node(page)
    assert expanded.children[0].type == "Container"
    assert expanded.children[0].children[0].type == "Text"
    assert expanded.children[0].children[0].children == ["inner"]


def test_expansion_reaches_components_nested_inside_ordinary_children():
    register_component("Badge", lambda: Text("new"))
    page = Page(Container(ARKNode(type="Badge", props={}, children=[])))
    expanded = expand_node(page)
    assert expanded.children[0].children[0].type == "Text"


# ---------------------------------------------------------------------------
# Props contract
# ---------------------------------------------------------------------------


def test_missing_required_prop_raises_component_error():
    register_component("Needs", lambda thing: Text(thing), props={"thing": Prop()})
    page = Page(ARKNode(type="Needs", props={}, children=[]))
    with pytest.raises(ComponentError, match="missing required prop 'thing'"):
        expand_node(page)


def test_unknown_prop_raises_component_error():
    register_component("Simple", lambda: Text("x"), props={})
    page = Page(ARKNode(type="Simple", props={"oops": 1}, children=[]))
    with pytest.raises(ComponentError, match="unexpected prop"):
        expand_node(page)


def test_prop_type_mismatch_raises_component_error():
    register_component("Typed", lambda n: Text(str(n)), props={"n": Prop(type=int)})
    page = Page(ARKNode(type="Typed", props={"n": "not an int"}, children=[]))
    with pytest.raises(ComponentError, match="expected"):
        expand_node(page)


def test_optional_prop_falls_back_to_default():
    register_component("Opt", lambda label="fallback": Text(label), props={"label": Prop(default="fallback")})
    page = Page(ARKNode(type="Opt", props={}, children=[]))
    expanded = expand_node(page)
    assert expanded.children[0].children == ["fallback"]


# ---------------------------------------------------------------------------
# Cycle / depth guards
# ---------------------------------------------------------------------------


def test_direct_self_reference_raises_component_error():
    register_component("Loop", lambda: ARKNode(type="Loop", props={}, children=[]))
    page = Page(ARKNode(type="Loop", props={}, children=[]))
    with pytest.raises(ComponentError, match="Cyclical component expansion"):
        expand_node(page)


def test_indirect_mutual_reference_raises_component_error():
    register_component("A", lambda: ARKNode(type="B", props={}, children=[]))
    register_component("B", lambda: ARKNode(type="A", props={}, children=[]))
    page = Page(ARKNode(type="A", props={}, children=[]))
    with pytest.raises(ComponentError, match="Cyclical component expansion"):
        expand_node(page)


def test_non_cyclical_deep_nesting_is_fine():
    # A chain of 10 distinct components, each expanding into the next --
    # not a cycle, should expand cleanly.
    for i in range(10):
        next_type = f"Chain{i + 1}" if i < 9 else None
        if next_type:
            register_component(f"Chain{i}", (lambda nt: (lambda: ARKNode(type=nt, props={}, children=[])))(next_type))
        else:
            register_component(f"Chain{i}", lambda: Text("end"))
    page = Page(ARKNode(type="Chain0", props={}, children=[]))
    expanded = expand_node(page)
    assert expanded.children[0].type == "Text"
