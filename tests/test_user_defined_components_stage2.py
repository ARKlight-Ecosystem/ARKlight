"""
v0.060, Stage 2: default styling hook for user-defined components.

Covers `arklight.api.component(..., default_style=...)` /
`_validate_component_default_style`, `arklight.ir.components`'s
`_apply_default_class`/`collect_default_styles`, and the end-to-end
path this all exists for: a component registered with `default_style`
ships sane default styling -- folded into the site's stylesheet under
`.<ComponentName>` and onto the rendered subtree's own root
`class_name` -- without the caller having to pass `class_name=` by
hand. See
`USER-DEFINED-COMPONENTS-IMPLEMENTATION.md` [retired -- see CHANGELOG.md]'s Stage
2 row, and `tests/test_user_defined_components_stage0.py`/
`tests/test_user_defined_components_stage1.py` for the earlier stages
this mirrors the conventions of.
"""

from __future__ import annotations

import textwrap

import pytest

from arklight.api import CSSSyntaxError, Container, Link, Page, Text, component
from arklight.ast.nodes import ARKNode
from arklight.backend.css.render import CSSBackend
from arklight.backend.html.render import HTMLBackend
from arklight.compiler.pipeline import compile_site_file
from arklight.ir.components import (
    COMPONENT_REGISTRY,
    ComponentSpec,
    Prop,
    collect_default_styles,
    expand_ark_ast,
    register_component,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Same isolation fixture Stage 0/1's test files already use."""
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# `component(..., default_style=...)` registration + validation
# ---------------------------------------------------------------------------


def test_component_decorator_accepts_default_style():
    @component(default_style={"display": "flex", "gap": "1rem"})
    def NavBar():  # noqa: N802
        return Container(Link("Home", href="/"))

    spec = COMPONENT_REGISTRY["NavBar"]
    assert spec.default_style == {"display": "flex", "gap": "1rem"}


def test_component_without_default_style_is_unaffected():
    @component()
    def Widget():  # noqa: N802
        return Text("hi")

    assert COMPONENT_REGISTRY["Widget"].default_style is None


def test_default_style_rejects_empty_dict():
    with pytest.raises(ValueError, match="non-empty dict"):

        @component(default_style={})
        def Bad():  # noqa: N802
            return Text("hi")


def test_default_style_rejects_non_string_value():
    with pytest.raises(ValueError, match="non-empty string value"):

        @component(default_style={"color": 5})
        def Bad():  # noqa: N802
            return Text("hi")


def test_default_style_rejects_unsupported_pseudo_class():
    with pytest.raises(CSSSyntaxError, match="unsupported pseudo-class"):

        @component(default_style={":bogus:color": "red"})
        def Bad():  # noqa: N802
            return Text("hi")


def test_default_style_accepts_pseudo_class_shorthand():
    @component(default_style={"color": "blue", ":hover:color": "red"})
    def Link_(active=None):  # noqa: N802
        return Container(Text("hi"))

    assert COMPONENT_REGISTRY["Link_"].default_style == {
        "color": "blue",
        ":hover:color": "red",
    }


def test_default_style_rejects_injection_characters():
    with pytest.raises(CSSSyntaxError, match="break out of its declaration"):

        @component(default_style={"color": "red; } .evil { color"})
        def Bad():  # noqa: N802
            return Text("hi")


def test_register_component_stores_default_style_directly():
    # Lower-level entry point (bypasses `component(...)`'s validation,
    # same "validation is `arklight.api`'s job, not the registry's"
    # division of labor Stage 0/1 already established for `props`).
    spec = register_component(
        "Card", lambda: None, default_style={"padding": "1rem"}
    )
    assert spec.default_style == {"padding": "1rem"}
    assert isinstance(spec, ComponentSpec)


# ---------------------------------------------------------------------------
# `_apply_default_class` / expansion behavior
# ---------------------------------------------------------------------------


def test_expansion_adds_component_name_as_class():
    @component(default_style={"display": "flex"})
    def NavBar():  # noqa: N802
        return Container(Link("Home", href="/"))

    marker = NavBar()
    expanded = expand_ark_ast({"/": Page(marker)})["/"]
    root = expanded.children[0]
    assert root.props.get("class_name") == "NavBar"


def test_expansion_appends_to_an_existing_class_name():
    @component(default_style={"display": "flex"})
    def NavBar():  # noqa: N802
        return Container(Link("Home", href="/"), class_name="nav")

    expanded = expand_ark_ast({"/": Page(NavBar())})["/"]
    root = expanded.children[0]
    assert root.props.get("class_name") == "nav NavBar"


def test_expansion_does_not_duplicate_an_already_present_class():
    @component(default_style={"display": "flex"})
    def NavBar():  # noqa: N802
        return Container(Link("Home", href="/"), class_name="NavBar")

    expanded = expand_ark_ast({"/": Page(NavBar())})["/"]
    root = expanded.children[0]
    assert root.props.get("class_name") == "NavBar"


def test_component_without_default_style_gets_no_class():
    @component()
    def Plain():  # noqa: N802
        return Container(Link("Home", href="/"))

    expanded = expand_ark_ast({"/": Page(Plain())})["/"]
    root = expanded.children[0]
    assert "class_name" not in root.props or not root.props.get("class_name")


def test_default_style_is_a_no_op_on_a_non_arknode_render_result():
    # A component whose render function returns a bare list has no
    # single root to attach a class to -- `_apply_default_class` must
    # not raise, it just leaves the shape alone.
    @component(default_style={"color": "red"})
    def Siblings():  # noqa: N802
        return [Text("a"), Text("b")]

    expanded = expand_ark_ast({"/": Page(Siblings())})["/"]
    # Normalization (the next pipeline stage, not run here) is what
    # flattens a nested list into real siblings -- at this stage the
    # list survives exactly as `Siblings()` returned it, just with its
    # own children (if any) recursively expanded.
    nested = expanded.children[0]
    assert [c.children for c in nested] == [["a"], ["b"]]


# ---------------------------------------------------------------------------
# `collect_default_styles` -- usage-keyed, not registry-keyed
# ---------------------------------------------------------------------------


def test_collect_default_styles_only_returns_used_components():
    register_component("Used", lambda: None, default_style={"color": "red"})
    register_component("Unused", lambda: None, default_style={"color": "blue"})
    styles = collect_default_styles({"Used"})
    assert styles == {"Used": {"color": "red"}}


def test_collect_default_styles_skips_components_without_default_style():
    register_component("Plain", lambda: None)
    styles = collect_default_styles({"Plain"})
    assert styles == {}


def test_collect_default_styles_returns_independent_copies():
    register_component("Card", lambda: None, default_style={"padding": "1rem"})
    styles = collect_default_styles({"Card"})
    styles["Card"]["padding"] = "9999px"
    assert COMPONENT_REGISTRY["Card"].default_style == {"padding": "1rem"}


def test_expand_ark_ast_records_transitively_used_components():
    @component(default_style={"color": "red"})
    def Inner():  # noqa: N802
        return Text("inner")

    @component(default_style={"color": "blue"})
    def Outer():  # noqa: N802
        return Container(Inner())

    used: set[str] = set()
    expand_ark_ast({"/": Page(Outer())}, used=used)
    assert used == {"Outer", "Inner"}


# ---------------------------------------------------------------------------
# End-to-end: compiled CSS + HTML output
# ---------------------------------------------------------------------------


def test_end_to_end_default_style_appears_in_stylesheet_and_markup(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(
        textwrap.dedent(
            """
            from arklight import *

            @component(default_style={"display": "flex", "gap": "1rem"})
            def NavBar():
                return Container(
                    Link("Home", href="/"),
                    Link("About", href="/about"),
                )

            site = Site()

            @site.page("/")
            def home():
                return Page(NavBar())
            """
        )
    )

    ir = compile_site_file(site_dir / "site.py")
    css = CSSBackend().render(ir)["styles.css"]
    assert ".NavBar {" in css
    assert "display: flex;" in css
    assert "gap: 1rem;" in css

    html = HTMLBackend().render(ir)["index.html"]
    assert 'class="NavBar"' in html


def test_end_to_end_unused_component_default_style_is_not_emitted(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(
        textwrap.dedent(
            """
            from arklight import *

            @component(default_style={"padding": "2rem"})
            def UnusedCard():
                return Container(Text("never rendered"))

            site = Site()

            @site.page("/")
            def home():
                return Page(Text("hello"))
            """
        )
    )

    ir = compile_site_file(site_dir / "site.py")
    css = CSSBackend().render(ir)["styles.css"]
    assert ".UnusedCard" not in css


def test_end_to_end_explicit_site_style_wins_over_component_default(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(
        textwrap.dedent(
            """
            from arklight import *

            @component(default_style={"color": "blue"})
            def NavBar():
                return Container(Link("Home", href="/"))

            site = Site()
            site.style("NavBar", {"color": "red"})

            @site.page("/")
            def home():
                return Page(NavBar())
            """
        )
    )

    ir = compile_site_file(site_dir / "site.py")
    css = CSSBackend().render(ir)["styles.css"]
    idx = css.find(".NavBar {")
    block = css[idx : idx + 60]
    assert "color: red;" in block
    assert "color: blue;" not in block
