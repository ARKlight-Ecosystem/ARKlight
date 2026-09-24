"""
`"overdrive": True` in arklight.config.py -- waives only the *unverifiable*
gate findings (unknown internal href, reference outside assets/ the build
can't supply), always prints what it let through, and leaves everything
provably broken fatal. See `arklight.compiler.overdrive`.
"""

from pathlib import Path

import pytest

from arklight.cli.main import main
from arklight.compiler.pipeline import CompileError, build
from arklight.config import ConfigError, overdrive_enabled

HEAD = "# include <stdlib.ARKlight>\nsite = Site()\n"


def write_site(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "site.py"
    path.write_text(HEAD + f'\n@site.page("/")\ndef home():\n    return Page({body}, title="Home")\n')
    return path


def write_config(tmp_path: Path, line: str) -> None:
    (tmp_path / "arklight.config.py").write_text(f"CONFIG = {{\n    {line}\n}}\n")


UNVERIFIABLE = 'Link("api", href="/api/login"), Image(src="/api/avatar", alt="a")'


# ---- the config accessor ---------------------------------------------------

def test_overdrive_defaults_to_false():
    assert overdrive_enabled({}) is False
    assert overdrive_enabled({"overdrive": False}) is False
    assert overdrive_enabled({"overdrive": True}) is True


@pytest.mark.parametrize("bad", ["yes", 1, 0, None, "true", []])
def test_overdrive_rejects_non_bool_values(bad):
    with pytest.raises(ConfigError, match="overdrive"):
        overdrive_enabled({"overdrive": bad})


# ---- default behavior is unchanged ------------------------------------------

def test_without_overdrive_unverifiable_references_still_halt(tmp_path):
    with pytest.raises(CompileError):
        build(write_site(tmp_path, UNVERIFIABLE), tmp_path / "dist")


# ---- overdrive on -----------------------------------------------------------

def test_config_line_lets_unverifiable_references_through_and_reports_them(tmp_path, capsys):
    write_config(tmp_path, '"overdrive": True,')
    out = tmp_path / "dist"
    build(write_site(tmp_path, UNVERIFIABLE), out)  # no kwarg: build() reads the config itself
    assert (out / "index.html").exists()
    err = capsys.readouterr().err
    assert "OVERDRIVE" in err and "UNVERIFIED" in err
    assert "/api/login" in err and "api/avatar" in err
    assert "2 reference(s)" in err


def test_the_report_prints_even_with_a_silent_on_stage(tmp_path, capsys):
    build(write_site(tmp_path, UNVERIFIABLE), tmp_path / "dist", overdrive=True, on_stage=lambda _m: None)
    assert "OVERDRIVE" in capsys.readouterr().err


def test_explicit_kwarg_beats_the_config_file(tmp_path):
    write_config(tmp_path, '"overdrive": True,')
    with pytest.raises(CompileError):
        build(write_site(tmp_path, UNVERIFIABLE), tmp_path / "dist", overdrive=False)


def test_a_typo_is_still_reported_with_its_hint_under_overdrive(tmp_path, capsys):
    path = tmp_path / "site.py"
    path.write_text(
        HEAD
        + '\n@site.page("/")\ndef home():\n    return Page(Link("x", href="/abuot"), title="H")\n'
        + '\n@site.page("/about")\ndef about():\n    return Page(Heading("A"), title="A")\n'
    )
    build(path, tmp_path / "dist", overdrive=True)
    assert "Did you mean '/about'?" in capsys.readouterr().err


def test_no_notice_when_nothing_was_waived(tmp_path, capsys):
    build(write_site(tmp_path, 'Heading("clean")'), tmp_path / "dist", overdrive=True)
    assert "OVERDRIVE" not in capsys.readouterr().err


# ---- what overdrive must NOT waive ------------------------------------------

def test_missing_file_inside_assets_is_still_fatal(tmp_path, capsys):
    (tmp_path / "assets").mkdir()
    site = write_site(tmp_path, 'Image(src="assets/gone.png", alt="g")')
    with pytest.raises(CompileError, match="Asset check failed"):
        build(site, tmp_path / "dist", overdrive=True)
    assert "assets/gone.png" in capsys.readouterr().err


def test_wrong_case_inside_assets_is_still_fatal(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "Logo.png").write_text("x")
    site = write_site(tmp_path, 'Image(src="assets/logo.png", alt="l")')
    with pytest.raises(CompileError):
        build(site, tmp_path / "dist", overdrive=True)


def test_dead_fragment_is_still_fatal(tmp_path):
    site = write_site(tmp_path, 'Link("x", href="#missing")')
    with pytest.raises(CompileError, match="Link check failed"):
        build(site, tmp_path / "dist", overdrive=True)


def test_fatal_and_waivable_together_still_halt_and_report_both(tmp_path, capsys):
    site = write_site(tmp_path, 'Link("api", href="/api/login"), Link("x", href="#missing")')
    with pytest.raises(CompileError):
        build(site, tmp_path / "dist", overdrive=True)
    err = capsys.readouterr().err
    assert "OVERDRIVE" in err and "LINK CHECK FAILED" in err


# ---- config / CLI plumbing --------------------------------------------------

def test_bad_config_value_fails_the_build_call(tmp_path):
    write_config(tmp_path, '"overdrive": "yes",')
    with pytest.raises(CompileError, match="overdrive"):
        build(write_site(tmp_path, 'Heading("h")'), tmp_path / "dist")


def test_cli_build_honors_the_config_line(tmp_path, capsys):
    write_config(tmp_path, '"overdrive": True,')
    site = write_site(tmp_path, UNVERIFIABLE)
    code = main(["build", str(site), "-o", str(tmp_path / "dist"), "--no-open"])
    assert code == 0
    assert "OVERDRIVE" in capsys.readouterr().err


def test_cli_build_fails_on_a_bad_overdrive_value(tmp_path, capsys):
    write_config(tmp_path, '"overdrive": 1,')
    site = write_site(tmp_path, 'Heading("h")')
    code = main(["build", str(site), "-o", str(tmp_path / "dist"), "--no-open"])
    assert code == 1
    assert "overdrive" in capsys.readouterr().err


def test_cli_build_without_config_still_halts(tmp_path):
    site = write_site(tmp_path, UNVERIFIABLE)
    assert main(["build", str(site), "-o", str(tmp_path / "dist"), "--no-open"]) == 1
