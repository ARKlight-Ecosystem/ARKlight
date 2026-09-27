"""
v0.06506: component call-site diagnostics (issue-register #5 and #32).

Covers the two Python-level boundaries that used to leak a raw
`TypeError` for user-defined-component misuse:

1. A positional call, `Stat("a", "b")`. The call-site marker now raises
   `ComponentError` (message from `positional_call_message`) instead of
   Python's own "takes 0 positional arguments but 2 were given".
2. A `props=` contract that disagrees with the render function's
   signature -- `call_render_fn` checks argument binding (never runs
   the function) and raises `ComponentError` naming both sides.

Conventions mirror `tests/test_user_defined_components_stage0.py`.
"""

from __future__ import annotations

import textwrap

import pytest

from arklight.api import Container, Page, Text, component
from arklight.compiler.pipeline import CompileError, compile_site_file
from arklight.ir.build import ark_node_to_ir_node  # noqa: F401 -- imported for parity with stage3
from arklight.ir.component_dispatch import resolve_backend_dispatch
from arklight.ir.components import (
    COMPONENT_REGISTRY,
    ComponentError,
    Prop,
    call_render_fn,
    expand_ark_ast,
    expand_node,
    positional_call_message,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


def _stat():
    @component(props={"label": Prop(), "value": Prop(default=0)})
    def Stat(label, value=0):  # noqa: N802
        return Text(f"{label}: {value}")

    return Stat


# ---------------------------------------------------------------------------
# 1. Positional call sites
# ---------------------------------------------------------------------------


def test_positional_call_raises_component_error_not_type_error():
    Stat = _stat()
    with pytest.raises(ComponentError) as excinfo:
        Stat("a", "b")
    assert not isinstance(excinfo.value, TypeError)
    assert "takes 0 positional arguments" not in str(excinfo.value)


def test_positional_message_names_component_count_and_declared_props():
    Stat = _stat()
    with pytest.raises(ComponentError) as excinfo:
        Stat("a", "b")
    message = str(excinfo.value)
    assert "'Stat'" in message
    assert "2 positional arguments" in message
    assert "keyword props only" in message
    assert "['label', 'value']" in message
    assert "Stat(label=..., value=...)" in message


def test_positional_message_uses_singular_for_one_argument():
    Stat = _stat()
    with pytest.raises(ComponentError) as excinfo:
        Stat("a")
    message = str(excinfo.value)
    assert "1 positional argument," in message
    assert "Stat(label=...)" in message


def test_positional_message_reports_the_call_site_location():
    Stat = _stat()
    with pytest.raises(ComponentError) as excinfo:
        Stat("a")  # this line's file:line must appear in the message
    message = str(excinfo.value)
    assert "called at" in message
    assert "test_component_call_diagnostics.py:" in message


def test_positional_call_on_component_with_no_props():
    @component()
    def Bare():  # noqa: N802
        return Text("x")

    with pytest.raises(ComponentError, match=r"declares no props.*Bare\(\)"):
        Bare(1)


def test_positional_call_with_more_arguments_than_props():
    Stat = _stat()
    with pytest.raises(ComponentError, match=r"declares only 2 prop"):
        Stat("a", "b", "c")


def test_positional_message_mentions_children_are_unsupported():
    Stat = _stat()
    with pytest.raises(ComponentError, match="Positional children are not supported"):
        Stat(Text("hi"))


def test_keyword_call_is_unchanged():
    Stat = _stat()
    marker = Stat(label="a", value=3)
    assert marker.type == "Stat"
    assert marker.props == {"label": "a", "value": 3}
    assert marker.children == []


def test_keyword_call_still_expands():
    Stat = _stat()
    expanded = expand_ark_ast({"/": Page(Stat(label="a", value=3))})["/"]
    assert expanded.children[0].children == ["a: 3"]


def test_positional_call_message_helper_omits_location_when_not_given():
    message = positional_call_message("Foo", ("x",), ["a"])
    assert "called at" not in message


def test_positional_call_through_compile_site_file(tmp_path):
    site_dir = tmp_path / "proj"
    site_dir.mkdir()
    source = textwrap.dedent(
        """
        # include <stdlib.ARKlight>

        @component(props={"label": Prop(), "value": Prop(default=0)})
        def Stat(label, value=0):
            return Text(f"{label}: {value}")

        site = Site()

        @site.page("/")
        def home():
            return Page(Heading("Hi"), Stat("a", "b"))
        """
    )
    (site_dir / "site.py").write_text(source)
    bad_line = next(
        n for n, line in enumerate(source.splitlines(), start=1) if 'Stat("a", "b")' in line
    )
    with pytest.raises(CompileError) as excinfo:
        compile_site_file(site_dir / "site.py")
    message = str(excinfo.value)
    assert "Component 'Stat' was called with 2 positional arguments" in message
    assert "takes 0 positional arguments" not in message
    # The location points at the offending call in the *user's* file.
    assert f"site.py:{bad_line}" in message


# ---------------------------------------------------------------------------
# 2. props= vs. render-function signature
# ---------------------------------------------------------------------------


def test_declared_prop_missing_from_signature_is_a_component_error():
    @component(props={"label": Prop(), "extra": Prop(default=1)})
    def Mismatch(label):  # noqa: N802
        return Text(label)

    with pytest.raises(ComponentError) as excinfo:
        expand_node(Mismatch(label="x"))
    message = str(excinfo.value)
    assert "'Mismatch'" in message
    assert "signature disagree" in message
    assert "unexpected keyword argument 'extra'" in message
    assert "['extra', 'label']" in message
    assert "['label']" in message


def test_required_parameter_not_declared_in_props_is_a_component_error():
    @component(props={"label": Prop()})
    def Wants(label, other):  # noqa: N802
        return Text(label)

    with pytest.raises(ComponentError, match="missing a required argument: 'other'"):
        expand_node(Wants(label="x"))


def test_var_keyword_render_function_is_accepted():
    @component(props={"label": Prop(), "extra": Prop(default=1)})
    def Loose(label, **rest):  # noqa: N802
        return Text(f"{label}{rest['extra']}")

    expanded = expand_node(Loose(label="x"))
    assert expanded.children == ["x1"]


def test_defaulted_undeclared_parameter_is_accepted():
    @component(props={"label": Prop()})
    def Fine(label, spare="s"):  # noqa: N802
        return Text(label + spare)

    assert expand_node(Fine(label="x")).children == ["xs"]


def test_type_error_raised_inside_the_render_function_is_not_rewritten():
    @component(props={"label": Prop()})
    def Boom(label):  # noqa: N802
        return Text(label + 1)  # str + int -> TypeError from the body

    with pytest.raises(TypeError) as excinfo:
        expand_node(Boom(label="x"))
    assert not isinstance(excinfo.value, ComponentError)


def test_mismatch_in_registry_mode_component_is_a_component_error():
    @component(mode="registry", props={"a": Prop(default=None)})
    def Reg():  # noqa: N802
        return Container(Text("x"))

    with pytest.raises(ComponentError, match="signature disagree"):
        expand_node(Reg())


def test_backend_override_signature_mismatch_is_a_component_error(tmp_path):
    site_dir = tmp_path / "proj"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(
        textwrap.dedent(
            """
            # include <stdlib.ARKlight>

            @component(mode="registry", props={"active": Prop(default=None)})
            def NavBar(active=None):
                return Container(Text("default"))

            @NavBar.register_backend("html")
            def _():
                return Container(Text("html-only"))

            site = Site()

            @site.page("/")
            def home():
                return Page(NavBar())
            """
        )
    )
    ir = compile_site_file(site_dir / "site.py")
    with pytest.raises(ComponentError) as excinfo:
        resolve_backend_dispatch(ir, "html")
    message = str(excinfo.value)
    assert "'NavBar'" in message
    assert "'html' backend override" in message
    assert "unexpected keyword argument 'active'" in message


def test_call_render_fn_calls_uninspectable_callables_unchecked():
    # A callable `inspect.signature` can't introspect must behave
    # exactly as it did before v0.06506 -- called, not rejected.
    assert call_render_fn("Builtinish", dict, {"a": 1}) == {"a": 1}
