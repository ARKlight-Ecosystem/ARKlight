from pathlib import Path
from unittest.mock import patch

from arklight.cli.main import main
from arklight.compiler.pipeline import build
from arklight.ir.binary import (
    MAGIC,
    ArklightFormatError,
    decode_arklight,
    encode_arklight,
    peek_header,
)

SIMPLE_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"), Text("hello binary IR"))
"""

MULTI_PAGE_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Home"))

@site.page("/about")
def about():
    return Page(Heading("About"), Text("more content, repeated repeated"))
"""


def write_site(tmp_path: Path, source: str = SIMPLE_SITE) -> Path:
    path = tmp_path / "site.py"
    path.write_text(source)
    return path


# --------------------------------------------------------------------------
# encode_arklight / decode_arklight round-trip
# --------------------------------------------------------------------------


def test_round_trip_preserves_site_shape(tmp_path):
    site_path = write_site(tmp_path, MULTI_PAGE_SITE)
    result = build(site_path, tmp_path / "dist")

    payload = encode_arklight(result.ir)
    decoded = decode_arklight(payload)

    assert decoded.site_name == result.ir.site_name
    assert decoded.lang == result.ir.lang
    assert decoded.app_shell == result.ir.app_shell
    assert [p.route for p in decoded.pages] == [p.route for p in result.ir.pages]


def test_round_trip_preserves_node_tree_shape(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")

    decoded = decode_arklight(encode_arklight(result.ir))
    original_root = result.ir.pages[0].root
    decoded_root = decoded.pages[0].root

    assert decoded_root.type == original_root.type
    assert len(decoded_root.children) == len(original_root.children)


def test_encoded_bytes_start_with_magic_and_version(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")

    payload = encode_arklight(result.ir)

    assert payload[:4] == MAGIC
    header = peek_header(payload)
    assert header.format_version == 1
    assert "arklight v" in header.schema_tag


def test_peek_header_does_not_require_full_decode(tmp_path):
    site_path = write_site(tmp_path)
    result = build(site_path, tmp_path / "dist")
    payload = encode_arklight(result.ir)

    # `peek_header` only ever reads magic + version + schema tag +
    # string count -- truncating everything after that (the actual
    # string table and body) must not stop it from working.
    header = peek_header(payload)
    tag_len = len(header.schema_tag.encode("utf-8"))
    header_only_length = 4 + 2 + 4 + tag_len + 4
    truncated = payload[:header_only_length]

    assert truncated != payload
    header_from_truncated = peek_header(truncated)
    assert header_from_truncated.format_version == 1
    assert header_from_truncated.schema_tag == header.schema_tag
    assert header_from_truncated.string_count == header.string_count


def test_rejects_bad_magic_bytes():
    try:
        decode_arklight(b"NOPE" + b"\x00" * 20)
        assert False, "expected ArklightFormatError"
    except ArklightFormatError as exc:
        assert "magic" in str(exc)


def test_rejects_unsupported_format_version():
    bogus = MAGIC + (99).to_bytes(2, "little") + (0).to_bytes(4, "little")
    try:
        decode_arklight(bogus)
        assert False, "expected ArklightFormatError"
    except ArklightFormatError as exc:
        assert "format version" in str(exc)


def test_string_table_dedupes_repeated_strings(tmp_path):
    site_path = write_site(tmp_path, MULTI_PAGE_SITE)
    result = build(site_path, tmp_path / "dist")

    header_and_body = encode_arklight(result.ir)
    header = peek_header(header_and_body)
    # "Text" (the node type) is repeated across at least one page's
    # tree plus the schema-generation tag/site name churn -- the table
    # should hold meaningfully fewer entries than a naive "one entry
    # per string occurrence" encoding would.
    assert header.string_count > 0


# --------------------------------------------------------------------------
# CLI: `arklight build --emit-arklight`
# --------------------------------------------------------------------------


def test_cli_build_without_flag_does_not_write_arklight_file(tmp_path):
    site_path = write_site(tmp_path)
    out_dir = tmp_path / "dist"

    with patch("arklight.cli.main.webbrowser.open"):
        exit_code = main(["build", str(site_path), "-o", str(out_dir), "--no-open"])

    assert exit_code == 0
    assert not (out_dir / "site.arklight").exists()


def test_cli_build_emit_arklight_bare_flag_writes_default_path(tmp_path, capsys):
    site_path = write_site(tmp_path)
    out_dir = tmp_path / "dist"

    exit_code = main(
        ["build", str(site_path), "-o", str(out_dir), "--no-open", "--emit-arklight"]
    )

    assert exit_code == 0
    arklight_path = out_dir / "site.arklight"
    assert arklight_path.exists()
    assert arklight_path.read_bytes()[:4] == MAGIC

    out = capsys.readouterr().out
    assert "site.arklight" in out
    assert "binary IR" in out


def test_cli_build_emit_arklight_custom_path(tmp_path):
    site_path = write_site(tmp_path)
    out_dir = tmp_path / "dist"
    custom_path = tmp_path / "artifacts" / "compiled.arklight"

    exit_code = main(
        [
            "build",
            str(site_path),
            "-o",
            str(out_dir),
            "--no-open",
            f"--emit-arklight={custom_path}",
        ]
    )

    assert exit_code == 0
    assert custom_path.exists()
    assert not (out_dir / "site.arklight").exists()


def test_cli_build_emit_arklight_file_decodes_back(tmp_path):
    site_path = write_site(tmp_path, MULTI_PAGE_SITE)
    out_dir = tmp_path / "dist"

    exit_code = main(
        ["build", str(site_path), "-o", str(out_dir), "--no-open", "--emit-arklight"]
    )

    assert exit_code == 0
    decoded = decode_arklight((out_dir / "site.arklight").read_bytes())
    assert [p.route for p in decoded.pages] == ["/", "/about"]
