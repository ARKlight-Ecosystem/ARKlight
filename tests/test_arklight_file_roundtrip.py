"""
Tests for closing the "emit but never consume" .arklight gap --
`arklight.ir.binary.decoded_site_to_website_ir` and
`arklight.compiler.pipeline`'s `compile_arklight_file`/`build`
detecting a `.arklight` file as `entry` and rebuilding straight from
it, skipping the Python compiler pipeline entirely. See
`arklight/ir/binary.py`'s module docstring ("Uncharted territory, now
charted") for the full design rationale.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from arklight.api import Action, Bind, Button, Heading, Page, Site, State, Text
from arklight.compiler.pipeline import CompileError, build, compile_arklight_file
from arklight.ir.binary import (
    ArklightFormatError,
    decode_arklight,
    decoded_site_to_website_ir,
    encode_arklight,
)
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast

SIMPLE_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"), Text("hello"), title="Home")

@site.page("/about")
def about():
    return Page(Heading("About"), title="About")
"""


def write_site(tmp_path: Path, source: str = SIMPLE_SITE) -> Path:
    path = tmp_path / "site.py"
    path.write_text(source)
    return path


def _ir(pages: dict, **kwargs):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized, **kwargs)


# -- decoded_site_to_website_ir() directly -----------------------------------


def test_rebuilds_site_name_lang_app_shell():
    ir = _ir({"/": Page(Heading("Hi"), title="Home")}, lang="fr", app_shell=True)
    decoded = decode_arklight(encode_arklight(ir))
    rebuilt = decoded_site_to_website_ir(decoded)
    assert rebuilt.site_name == ir.site_name
    assert rebuilt.lang == "fr"
    assert rebuilt.app_shell is True


def test_rebuilds_page_routes_and_static_tree():
    ir = _ir(
        {
            "/": Page(Heading("Home"), title="Home"),
            "/about": Page(Heading("About"), Text("more"), title="About"),
        }
    )
    decoded = decode_arklight(encode_arklight(ir))
    rebuilt = decoded_site_to_website_ir(decoded)
    assert {p.route for p in rebuilt.pages} == {"/", "/about"}


def test_unset_fields_fall_back_to_websiteir_stock_defaults():
    ir = _ir({"/": Page(Heading("Hi"), title="Home")})
    decoded = decode_arklight(encode_arklight(ir))
    rebuilt = decoded_site_to_website_ir(decoded)
    # Not part of the v1 .arklight format -- come back at WebsiteIR's
    # own dataclass defaults, not an error.
    assert rebuilt.custom_styles == {}
    assert rebuilt.experimental_usages == []
    assert rebuilt.css_var_overrides == {}
    assert rebuilt.strict_csp is True
    assert rebuilt.devtools_console_reminder is True


def test_actionref_prop_reconstructed_as_live_dataclass():
    from arklight.ast.nodes import ActionRef

    ir = _ir(
        {
            "/": Page(
                State("count", 0),
                Heading(Bind("count")),
                Button("Inc", on_click=Action.increment("count")),
                title="Counter",
            )
        }
    )
    decoded = decode_arklight(encode_arklight(ir))
    rebuilt = decoded_site_to_website_ir(decoded)
    button = rebuilt.pages[0].root.children[1]
    assert isinstance(button.props["on_click"], ActionRef)
    assert button.props["on_click"].action == "increment"
    assert button.props["on_click"].state == "count"


def test_state_initial_value_preserved():
    ir = _ir({"/": Page(State("count", 5), Heading(Bind("count")), title="Counter")})
    decoded = decode_arklight(encode_arklight(ir))
    rebuilt = decoded_site_to_website_ir(decoded)
    assert rebuilt.pages[0].state == {"count": 5}


# -- End-to-end: rendering a rebuilt WebsiteIR ---------------------------------


def test_rebuilt_ir_renders_through_html_backend():
    from arklight.backend.html.render import HTMLBackend

    ir = _ir({"/": Page(Heading("Hi"), title="Home")})
    decoded = decode_arklight(encode_arklight(ir))
    rebuilt = decoded_site_to_website_ir(decoded)
    html = HTMLBackend().render(rebuilt)["index.html"]
    assert "<h1>Hi</h1>" in html


def test_rebuilt_stateful_ir_renders_working_action_wiring():
    from arklight.backend.html.render import HTMLBackend
    from arklight.backend.js.render import JSBackend

    ir = _ir(
        {
            "/": Page(
                State("count", 0),
                Heading(Bind("count")),
                Button("Inc", on_click=Action.increment("count")),
                title="Counter",
            )
        }
    )
    decoded = decode_arklight(encode_arklight(ir))
    rebuilt = decoded_site_to_website_ir(decoded)
    html = HTMLBackend().render(rebuilt)["index.html"]
    assert 'data-ark-on-click="action:increment"' in html
    js = JSBackend().render(rebuilt)["arklight.js"]
    assert "increment" in js


# -- compile_arklight_file() ---------------------------------------------------


def test_compile_arklight_file_rebuilds_ir(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")
    arklight_path = tmp_path / "site.arklight"
    arklight_path.write_bytes(encode_arklight(result.ir))

    ir = compile_arklight_file(arklight_path)
    assert {p.route for p in ir.pages} == {"/", "/about"}


def test_compile_arklight_file_applies_lang_override(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")
    arklight_path = tmp_path / "site.arklight"
    arklight_path.write_bytes(encode_arklight(result.ir))

    ir = compile_arklight_file(arklight_path, lang="ta")
    assert ir.lang == "ta"


def test_compile_arklight_file_applies_strict_csp_override(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")
    arklight_path = tmp_path / "site.arklight"
    arklight_path.write_bytes(encode_arklight(result.ir))

    ir = compile_arklight_file(arklight_path, strict_csp_override=False)
    assert ir.strict_csp is False


def test_compile_arklight_file_applies_devtools_console_reminder_override(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")
    arklight_path = tmp_path / "site.arklight"
    arklight_path.write_bytes(encode_arklight(result.ir))

    ir = compile_arklight_file(arklight_path, devtools_console_reminder=False)
    assert ir.devtools_console_reminder is False


def test_compile_arklight_file_raises_compile_error_on_corrupt_file(tmp_path):
    bad_path = tmp_path / "broken.arklight"
    bad_path.write_bytes(b"not a real arklight file")
    with pytest.raises(CompileError):
        compile_arklight_file(bad_path)


def test_compile_arklight_file_raises_compile_error_on_missing_file(tmp_path):
    with pytest.raises(CompileError):
        compile_arklight_file(tmp_path / "does-not-exist.arklight")


# -- build() detecting a .arklight entry end-to-end ----------------------------


def test_build_from_arklight_file_by_extension(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")
    arklight_path = tmp_path / "site.arklight"
    arklight_path.write_bytes(encode_arklight(result.ir))

    out_dir = tmp_path / "dist_from_arklight"
    rebuilt_result = build(arklight_path, out_dir)

    index_html = (out_dir / "index.html").read_text()
    about_html = (out_dir / "about.html").read_text()
    assert "<h1>Hi</h1>" in index_html
    assert "<h1>About</h1>" in about_html
    assert len(rebuilt_result.written_paths) == 4  # index, about, styles.css, arklight.js


def test_build_from_arklight_file_detected_by_magic_bytes_without_extension(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")
    # No ".arklight" suffix at all -- must be detected via magic bytes.
    snapshot_path = tmp_path / "site_snapshot"
    snapshot_path.write_bytes(encode_arklight(result.ir))

    out_dir = tmp_path / "dist_from_snapshot"
    build(snapshot_path, out_dir)
    assert (out_dir / "index.html").exists()


def test_build_from_arklight_file_still_copies_assets(tmp_path):
    site_path = write_site(tmp_path)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.svg").write_text("<svg></svg>")
    result = build(site_path, tmp_path / "dist")
    arklight_path = tmp_path / "site.arklight"
    arklight_path.write_bytes(encode_arklight(result.ir))

    out_dir = tmp_path / "dist_from_arklight"
    build(arklight_path, out_dir)
    assert (out_dir / "assets" / "logo.svg").exists()


def test_build_from_arklight_raises_compile_error_on_corrupt_file(tmp_path):
    bad_path = tmp_path / "broken.arklight"
    bad_path.write_bytes(b"definitely not valid")
    with pytest.raises(CompileError):
        build(bad_path, tmp_path / "dist")
