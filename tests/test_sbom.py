"""
Tests for `arklight.compiler.sbom` -- the per-build manifest
(`<output_dir>/sbom.txt`) `arklight.compiler.pipeline.build` writes
alongside every build's other output files.
"""

from __future__ import annotations

from pathlib import Path

from arklight.compiler.pipeline import build

SIMPLE_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"), Text("Hello from ARKlight."))
"""

INTERACTIVE_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(
        State("count", 0),
        Computed("doubled", deps=("count",), derive=Derive.sum("count", "count")),
        Heading("Hi", id="hi"),
        Text(Bind("doubled")),
        Button("Increment", on_click=Action.increment("count", 1)),
        Button("Copy", on_click="copy", behavior_target="#hi"),
    )
"""


def write_site(tmp_path: Path, source: str = SIMPLE_SITE) -> Path:
    path = tmp_path / "site.py"
    path.write_text(source)
    return path


def build_and_read_sbom(tmp_path: Path, source: str = SIMPLE_SITE) -> str:
    out_dir = tmp_path / "ARK"
    build(write_site(tmp_path, source), out_dir)
    return (out_dir / "sbom.txt").read_text()


def test_build_writes_sbom_txt_alongside_other_output(tmp_path):
    out_dir = tmp_path / "ARK"
    result = build(write_site(tmp_path), out_dir)

    assert (out_dir / "sbom.txt").exists()
    assert "sbom.txt" in result.output_files


def test_sbom_header_declares_itself_non_conformant(tmp_path):
    """The whole point of the informal-tag-value framing is that it
    never gets mistaken for a real, auditable SPDX document -- the
    header comment has to say so explicitly."""
    text = build_and_read_sbom(tmp_path)
    assert "NOT a validated/spec-conformant SPDX document" in text


def test_sbom_names_arklight_itself_with_real_version(tmp_path):
    text = build_and_read_sbom(tmp_path)
    assert "PackageName: ARKlight" in text
    assert "PackageLicenseDeclared: GPL-3.0-or-later" in text
    # Whatever's actually installed, not a hardcoded string -- this
    # asserts the field is populated at all, not a specific value,
    # since __version__ legitimately varies across environments.
    assert "PackageVersion: " in text


def test_plain_site_lists_no_first_party_runtime_pieces(tmp_path):
    """A site with no State/Computed/named behavior/Platform API
    usage gets the explicit "none" note, not an empty section that
    looks like something went wrong."""
    text = build_and_read_sbom(tmp_path, SIMPLE_SITE)
    assert "references no optional first-party runtime pieces" in text
    assert "PackageName: copy" not in text
    assert "PackageName: increment" not in text


def test_interactive_site_lists_only_what_it_actually_uses(tmp_path):
    """Never a static registry dump -- only named behaviors/actions/
    derivations this specific site's IR references."""
    text = build_and_read_sbom(tmp_path, INTERACTIVE_SITE)

    assert "PackageName: copy" in text
    assert "PackageName: increment" in text
    assert "PackageName: sum" in text
    assert "shipped as part of ARKlight's own runtime" in text

    # A behavior/action ARKlight supports but this site never
    # references must not show up.
    assert "PackageName: dismiss" not in text
    assert "PackageName: toggle" not in text


# ACC (ARKlight Component Collections) package-listing tests are
# deliberately not carried over here: `arklight/capabilities.py`, the
# entry-point-based capability-discovery module ACC is built on, is an
# feature not included on this branch (same standing
# exclusion policy as the Android/Desktop backends) -- see
# `arklight/compiler/sbom.py`'s module docstring.
