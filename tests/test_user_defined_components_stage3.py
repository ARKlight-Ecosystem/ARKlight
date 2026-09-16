"""
v0.060, Stage 3: per-backend render dispatch for user-defined
components -- Option B's real differentiator.

Covers `arklight.ir.components.register_backend_render`/
`ComponentSpec.backend_render_fns`/`ComponentOrigin`, the
`.register_backend(backend_name)` decorator `arklight.api.component`
attaches to a registered component, `arklight.ir.build`'s
`IRNode.component_origin` plumbing, and
`arklight.ir.component_dispatch.resolve_backend_dispatch` -- the pass
that actually swaps in a backend's own override, wired into
`arklight.backend.html.render.HTMLBackend.render`. See
`docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s Stage
3 row, and `tests/test_user_defined_components_stage0.py`/`stage1.py`/
`stage2.py` for the earlier stages this mirrors the conventions of.
"""

from __future__ import annotations

import textwrap

import pytest

from arklight.api import Container, Link, Page, Text, component
from arklight.backend.css.render import CSSBackend
from arklight.backend.html.render import HTMLBackend
from arklight.compiler.pipeline import compile_site_file
from arklight.ir.build import ark_node_to_ir_node
from arklight.ir.component_dispatch import resolve_backend_dispatch
from arklight.ir.components import (
    COMPONENT_REGISTRY,
    ComponentError,
    Prop,
    expand_ark_ast,
    register_backend_render,
    register_component,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Same isolation fixture Stage 0/1/2's test files already use."""
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# `register_backend_render` / `.register_backend(...)` registration
# ---------------------------------------------------------------------------


def test_register_backend_render_stores_on_the_spec():
    register_component("NavBar", lambda: None, mode="registry")
    register_backend_render("NavBar", "html", lambda: "html version")
    spec = COMPONENT_REGISTRY["NavBar"]
    assert set(spec.backend_render_fns) == {"html"}
    assert spec.backend_render_fns["html"]() == "html version"


def test_register_backend_render_rejects_unknown_component():
    with pytest.raises(ComponentError, match="no component with that name"):
        register_backend_render("Nope", "html", lambda: None)


def test_register_backend_render_rejects_macro_mode():
    register_component("Foo", lambda: None)  # mode="macro" (default)
    with pytest.raises(ComponentError, match='mode="registry"'):
        register_backend_render("Foo", "html", lambda: None)


def test_register_backend_render_last_registration_wins():
    register_component("NavBar", lambda: None, mode="registry")
    register_backend_render("NavBar", "html", lambda: "first")
    register_backend_render("NavBar", "html", lambda: "second")
    assert COMPONENT_REGISTRY["NavBar"].backend_render_fns["html"]() == "second"


def test_decorator_register_backend_wires_through():
    @component(mode="registry")
    def NavBar():  # noqa: N802
        return Container(Text("default"))

    @NavBar.register_backend("html")
    def _():
        return Container(Text("html-specific"))

    spec = COMPONENT_REGISTRY["NavBar"]
    assert "html" in spec.backend_render_fns
    rendered = spec.backend_render_fns["html"]()
    assert rendered.children == [Text("html-specific")]


def test_decorator_register_backend_rejects_macro_component():
    @component()
    def Plain():  # noqa: N802
        return Text("hi")

    with pytest.raises(ComponentError, match='mode="registry"'):

        @Plain.register_backend("html")
        def _():
            return Text("override")


# ---------------------------------------------------------------------------
# Expansion: only a registry component *with* an override gets tagged
# ---------------------------------------------------------------------------


def test_registry_component_without_override_is_untagged():
    @component(mode="registry")
    def NavBar():  # noqa: N802
        return Container(Text("default"))

    expanded = expand_ark_ast({"/": Page(NavBar())})["/"]
    root = expanded.children[0]
    ir_node = ark_node_to_ir_node(root)
    assert ir_node.component_origin is None


def test_registry_component_with_override_is_tagged():
    @component(mode="registry", props={"active": Prop(default=None)})
    def NavBar(active=None):  # noqa: N802
        return Container(Text("default"))

    @NavBar.register_backend("html")
    def _(active=None):
        return Container(Text("html"))

    expanded = expand_ark_ast({"/": Page(NavBar(active="home"))})["/"]
    root = expanded.children[0]
    ir_node = ark_node_to_ir_node(root)
    assert ir_node.component_origin is not None
    assert ir_node.component_origin.name == "NavBar"
    assert ir_node.component_origin.resolved_props == {"active": "home"}


def test_macro_component_is_never_tagged_even_with_same_name_registered_elsewhere():
    @component()  # mode="macro"
    def Plain():  # noqa: N802
        return Container(Text("hi"))

    expanded = expand_ark_ast({"/": Page(Plain())})["/"]
    root = expanded.children[0]
    ir_node = ark_node_to_ir_node(root)
    assert ir_node.component_origin is None


# ---------------------------------------------------------------------------
# `resolve_backend_dispatch`
# ---------------------------------------------------------------------------


def _compiled_ir(site_source: str, tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(textwrap.dedent(site_source))
    return compile_site_file(site_dir / "site.py")


def test_resolve_backend_dispatch_swaps_in_the_matching_override(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component(mode="registry")
        def NavBar():
            return Container(Text("default"))

        @NavBar.register_backend("html")
        def _():
            return Container(Text("html-only"))

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar())
        """,
        tmp_path,
    )
    resolved = resolve_backend_dispatch(ir, "html")
    root = resolved.pages[0].root
    navbar_container = root.children[0]
    assert navbar_container.children[0].children == ["html-only"]


def test_resolve_backend_dispatch_falls_back_when_no_override_for_backend(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component(mode="registry")
        def NavBar():
            return Container(Text("default"))

        @NavBar.register_backend("android")
        def _():
            return Container(Text("android-only"))

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar())
        """,
        tmp_path,
    )
    resolved = resolve_backend_dispatch(ir, "html")
    root = resolved.pages[0].root
    navbar_container = root.children[0]
    assert navbar_container.children[0].children == ["default"]


def test_resolve_backend_dispatch_clears_the_origin_marker(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component(mode="registry")
        def NavBar():
            return Container(Text("default"))

        @NavBar.register_backend("html")
        def _():
            return Container(Text("html-only"))

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar())
        """,
        tmp_path,
    )
    resolved = resolve_backend_dispatch(ir, "html")
    root = resolved.pages[0].root
    assert root.children[0].component_origin is None


def test_resolve_backend_dispatch_is_a_pure_function(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component(mode="registry")
        def NavBar():
            return Container(Text("default"))

        @NavBar.register_backend("html")
        def _():
            return Container(Text("html-only"))

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar())
        """,
        tmp_path,
    )
    resolve_backend_dispatch(ir, "html")
    # Calling it doesn't mutate `ir` itself -- a second call for a
    # different backend must see the same, still-tagged original.
    root = ir.pages[0].root
    assert root.children[0].component_origin is not None
    assert root.children[0].component_origin.name == "NavBar"


def test_backend_override_returning_siblings_list_raises():
    @component(mode="registry")
    def Siblings():  # noqa: N802
        return Container(Text("default"))

    @Siblings.register_backend("html")
    def _():
        return [Text("a"), Text("b")]

    expanded = expand_ark_ast({"/": Page(Siblings())})["/"]
    root = expanded.children[0]
    ir_node = ark_node_to_ir_node(root)
    from arklight.ir.build import IRPage, WebsiteIR

    ir = WebsiteIR(site_name="t", pages=[IRPage(route="/", root=ir_node)])
    with pytest.raises(ComponentError, match="single root node"):
        resolve_backend_dispatch(ir, "html")


def test_backend_override_returning_non_arknode_raises():
    @component(mode="registry")
    def Bad():  # noqa: N802
        return Container(Text("default"))

    @Bad.register_backend("html")
    def _():
        return "not a node"

    expanded = expand_ark_ast({"/": Page(Bad())})["/"]
    root = expanded.children[0]
    ir_node = ark_node_to_ir_node(root)
    from arklight.ir.build import IRPage, WebsiteIR

    ir = WebsiteIR(site_name="t", pages=[IRPage(route="/", root=ir_node)])
    with pytest.raises(ComponentError, match="must return an ARKNode"):
        resolve_backend_dispatch(ir, "html")


def test_backend_override_gets_default_style_class_too(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component(mode="registry", default_style={"display": "flex"})
        def NavBar():
            return Container(Text("default"))

        @NavBar.register_backend("html")
        def _():
            return Container(Text("html-only"))

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar())
        """,
        tmp_path,
    )
    resolved = resolve_backend_dispatch(ir, "html")
    navbar_container = resolved.pages[0].root.children[0]
    assert navbar_container.props.get("class_name") == "NavBar"


def test_backend_override_may_nest_other_components(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component()
        def Inner():
            return Text("inner-macro")

        @component(mode="registry")
        def NavBar():
            return Container(Text("default"))

        @NavBar.register_backend("html")
        def _():
            return Container(Inner())

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar())
        """,
        tmp_path,
    )
    resolved = resolve_backend_dispatch(ir, "html")
    navbar_container = resolved.pages[0].root.children[0]
    assert navbar_container.children[0].children == ["inner-macro"]


# ---------------------------------------------------------------------------
# End-to-end: HTMLBackend actually uses the override; CSSBackend/output
# never leaks the internal marker.
# ---------------------------------------------------------------------------


def test_end_to_end_html_backend_uses_registered_override(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component(mode="registry", default_style={"display": "flex"}, props={"active": Prop(default=None)})
        def NavBar(active=None):
            return Container(Link("Home", href="/"))

        @NavBar.register_backend("html")
        def _(active=None):
            return Container(
                Link("Home (HTML)", href="/"), class_name="html-navbar"
            )

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar(active="home"))
        """,
        tmp_path,
    )
    html = HTMLBackend().render(ir)["index.html"]
    assert "Home (HTML)" in html
    assert "html-navbar" in html
    # default_style's own class still folds onto the override's root.
    assert "NavBar" in html
    # The internal dispatch marker never leaks into output.
    assert "__arklight_component_origin__" not in html


def test_end_to_end_no_override_behaves_like_stage_0(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component(mode="registry")
        def NavBar():
            return Container(Link("Home", href="/"))

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar())
        """,
        tmp_path,
    )
    html = HTMLBackend().render(ir)["index.html"]
    assert "Home" in html
    assert "__arklight_component_origin__" not in html


def test_end_to_end_css_backend_is_unaffected_by_backend_overrides(tmp_path):
    ir = _compiled_ir(
        """
        from arklight import *

        @component(mode="registry", default_style={"color": "red"})
        def NavBar():
            return Container(Link("Home", href="/"))

        @NavBar.register_backend("html")
        def _():
            return Container(Link("Home (HTML)", href="/"))

        site = Site()

        @site.page("/")
        def home():
            return Page(NavBar())
        """,
        tmp_path,
    )
    css = CSSBackend().render(ir)["styles.css"]
    assert ".NavBar {" in css
    assert "color: red;" in css


def test_end_to_end_build_pipeline_resolves_per_backend(tmp_path):
    from arklight.compiler.pipeline import build

    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(
        textwrap.dedent(
            """
            from arklight import *

            @component(mode="registry")
            def NavBar():
                return Container(Link("Home", href="/"))

            @NavBar.register_backend("html")
            def _():
                return Container(Link("Home (HTML)", href="/"))

            site = Site()

            @site.page("/")
            def home():
                return Page(NavBar())
            """
        )
    )
    out_dir = tmp_path / "out"
    result = build(site_dir / "site.py", out_dir)
    html = (out_dir / "index.html").read_text()
    assert "Home (HTML)" in html
    assert result.ir is not None
