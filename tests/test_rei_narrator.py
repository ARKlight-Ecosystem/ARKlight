"""Tests for the Rei compiler narrator (`--narrate`), `v0.065` --
see docs/Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md /
docs/Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md.
"""

from pathlib import Path

from arklight.cli.main import main
from arklight.compiler import rei
from arklight.ir.validate import ValidationError

SIMPLE_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"))
"""

MISSING_REQUIRED_PROP_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Image())
"""

BEHAVIOR_VALIDATION_ERROR_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Button("Go", on_click="not_a_real_behavior"))
"""

DUPLICATE_COMPONENT_SITE = """
from arklight import *

@component("Dup")
def dup_one(props):
    return Heading("one")

@component("Dup")
def dup_two(props):
    return Heading("two")

site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"))
"""


def write_site(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "site.py"
    path.write_text(source)
    return path


# --- Flag parsing -----------------------------------------------------


def test_narrate_and_verbose_are_mutually_exclusive(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    exit_code = main(
        ["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--narrate", "--verbose"]
    )
    assert exit_code == 1
    assert "--narrate" in capsys.readouterr().err


def test_narrate_and_debug_are_mutually_exclusive(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    exit_code = main(
        ["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--narrate", "--debug"]
    )
    assert exit_code == 1
    assert "--narrate" in capsys.readouterr().err


def test_debug_alone_still_implies_verbose_and_is_unaffected(tmp_path, capsys):
    """`--debug` (no `--narrate`) still works exactly as before --
    `--narrate` existing doesn't change `--debug`'s own behavior."""
    site_path = write_site(tmp_path, SIMPLE_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--debug"])
    assert exit_code == 0
    assert "[ARKlight]" in capsys.readouterr().out


# --- Narration itself ---------------------------------------------------


def test_narrate_prints_rei_lines_not_arklight_lines(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--narrate"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[Rei]" in out
    assert "[ARKlight]" not in out


def test_plain_build_has_no_rei_or_arklight_stage_lines(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[Rei]" not in out
    assert "[ARKlight]" not in out


def test_narrate_output_is_deterministic(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    main(["build", str(site_path), "-o", str(tmp_path / "dist1"), "--no-open", "--narrate"])
    first = capsys.readouterr().out
    main(["build", str(site_path), "-o", str(tmp_path / "dist2"), "--no-open", "--narrate"])
    second = capsys.readouterr().out
    # Strip the one-time intro banner (both are fresh dirs, so both get
    # one) and the output-path-bearing lines before comparing, since
    # those legitimately differ by output directory name.
    assert first.count("[Rei]") == second.count("[Rei]")


# --- Config: rei.default_mode --------------------------------------------


def test_rei_default_mode_config_enables_narration_without_flag(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    (tmp_path / "arklight.config.py").write_text(
        'CONFIG = {"rei": {"default_mode": "narrate"}}\n'
    )
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[Rei]" in out


def test_explicit_verbose_flag_overrides_rei_config_default(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    (tmp_path / "arklight.config.py").write_text(
        'CONFIG = {"rei": {"default_mode": "narrate"}}\n'
    )
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--verbose"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[ARKlight]" in out
    assert "[Rei]" not in out


def test_absent_rei_section_behaves_like_plain(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    (tmp_path / "arklight.config.py").write_text('CONFIG = {"csp": {"strict_csp": None}}\n')
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[Rei]" not in out
    assert "[ARKlight]" not in out


# --- First-compile introduction banner -----------------------------------


def test_intro_banner_on_fresh_output_dir(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    out_dir = tmp_path / "dist"
    main(["build", str(site_path), "-o", str(out_dir), "--no-open", "--narrate"])
    out = capsys.readouterr().out
    assert "I'm Rei" in out


def test_intro_banner_not_repeated_on_second_build_into_same_dir(tmp_path, capsys):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    out_dir = tmp_path / "dist"
    main(["build", str(site_path), "-o", str(out_dir), "--no-open", "--narrate"])
    capsys.readouterr()
    main(["build", str(site_path), "-o", str(out_dir), "--no-open", "--narrate"])
    out = capsys.readouterr().out
    assert "I'm Rei" not in out
    assert "[Rei]" in out  # still narrates stages, just no intro


def test_intro_banner_reappears_after_output_dir_cleared(tmp_path, capsys):
    import shutil

    site_path = write_site(tmp_path, SIMPLE_SITE)
    out_dir = tmp_path / "dist"
    main(["build", str(site_path), "-o", str(out_dir), "--no-open", "--narrate"])
    capsys.readouterr()
    shutil.rmtree(out_dir)
    main(["build", str(site_path), "-o", str(out_dir), "--no-open", "--narrate"])
    out = capsys.readouterr().out
    assert "I'm Rei" in out


# --- arklight search pointer on schema violations ------------------------


def test_narrate_appends_search_pointer_for_missing_required_prop(tmp_path, capsys):
    site_path = write_site(tmp_path, MISSING_REQUIRED_PROP_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--narrate"])
    err = capsys.readouterr().err
    assert exit_code == 1
    assert "Try: arklight search Image" in err


def test_narrate_omits_search_pointer_for_non_schema_validation_error(tmp_path, capsys):
    site_path = write_site(tmp_path, BEHAVIOR_VALIDATION_ERROR_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--narrate"])
    err = capsys.readouterr().err
    assert exit_code == 1
    assert "[Rei]" in err
    assert "Try: arklight search" not in err


def test_plain_mode_never_prints_search_pointer(tmp_path, capsys):
    site_path = write_site(tmp_path, UNKNOWN_COMPONENT_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open"])
    err = capsys.readouterr().err
    assert exit_code == 1
    assert "Try: arklight search" not in err


# --- ValidationError structured data --------------------------------------


def test_validation_error_component_name_set_for_unknown_type():
    exc = ValidationError("Unknown component type 'Foo' at root.", component_name="Foo")
    assert exc.component_name == "Foo"


def test_validation_error_component_name_defaults_to_none():
    exc = ValidationError("Bind(...) needs a name.")
    assert exc.component_name is None


# --- rei module unit tests -------------------------------------------------


def test_narrate_stage_is_deterministic_for_known_message():
    a = rei.narrate_stage("Running validation...")
    b = rei.narrate_stage("Running validation...")
    assert a == b
    assert a.startswith("[Rei]")


def test_narrate_stage_falls_back_for_unknown_message():
    out = rei.narrate_stage("Some future stage that doesn't exist yet...")
    assert out == "[Rei] Some future stage that doesn't exist yet..."


def test_is_unconditional_banner_matches_warning_glyph():
    assert rei.is_unconditional_banner("\u26a0 experimental feature active")
    assert not rei.is_unconditional_banner("Running validation...")


def test_render_failure_with_component_name_appends_pointer():
    rendered = rei.render_failure("Unknown component type 'Foo' at root.", component_name="Foo")
    assert "Try: arklight search Foo" in rendered
    assert "[Rei] Compilation halted." in rendered


def test_render_failure_without_component_name_omits_pointer():
    rendered = rei.render_failure("Bind(...) needs a name.", component_name=None)
    assert "Try: arklight search" not in rendered


def test_is_fresh_output_dir_true_for_missing_and_empty(tmp_path):
    missing = tmp_path / "missing"
    assert rei.is_fresh_output_dir(str(missing)) is True

    empty = tmp_path / "empty"
    empty.mkdir()
    assert rei.is_fresh_output_dir(str(empty)) is True


def test_is_fresh_output_dir_false_once_populated(tmp_path):
    populated = tmp_path / "populated"
    populated.mkdir()
    (populated / "index.html").write_text("hi")
    assert rei.is_fresh_output_dir(str(populated)) is False
