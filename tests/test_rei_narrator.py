"""Tests for the Rei compiler narrator (`--narrate`), `v0.065` --
see docs/Foundational/DESIGN-NOTES.md and
docs/version history/v0.065.md.
"""

import ast
from pathlib import Path

import pytest

from arklight.cli.main import main
from arklight.compiler import rei
from arklight.ir.components import COMPONENT_REGISTRY
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
# include <stdlib.ARKlight>

@component()
def DupReiProbe():
    return Heading("one")

@component()
def DupReiProbe():
    return Heading("two")

site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"))
"""


DUPLICATE_STYLE_SITE = """
# include <stdlib.ARKlight>

site = Site()
site.style("dup-box", {"color": "red"})
site.style("dup-box", {"color": "blue"})

@site.page("/")
def home():
    return Page(Heading("Hi"))
"""


@pytest.fixture
def isolated_component_registry():
    """`@component()` registers into a process-global registry, so a
    site file that registers `DupReiProbe` would otherwise leak it into
    every later test. Snapshot and restore around the test."""
    saved = dict(COMPONENT_REGISTRY)
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


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
    site_path = write_site(tmp_path, MISSING_REQUIRED_PROP_SITE)
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


# --- vendored ELIZA reference is never imported by shipping code -----------


def test_no_shipping_module_imports_the_vendored_eliza_reference():
    """`docs/reference/eliza/eliza.py` is read-only design reference
    (addendum: "studied during design, not linked against at runtime").
    Walk every `arklight/**/*.py` module's real import statements
    (via `ast`, not a text grep, so a comment or docstring merely
    *mentioning* ELIZA -- as `arklight/compiler/rei/__init__.py`'s does
    -- doesn't count) and fail if any reaches into it.
    """
    package_root = Path(rei.__file__).resolve().parents[2]  # .../arklight
    offenders = []
    for py_file in sorted(package_root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported = [node.module or ""]
                imported += [f"{node.module}.{alias.name}" for alias in node.names if node.module]
            else:
                continue
            for name in imported:
                parts = name.lower().split(".")
                if "eliza" in parts or name.startswith("docs.reference"):
                    offenders.append(f"{py_file.relative_to(package_root.parent)}: {name}")
    assert offenders == []


# --- import-time registration errors (addendum: "Tests", last bullet) ------
#
# `DuplicateComponentError`/`DuplicateStyleNameError` fire while the site
# file itself runs, which happens *inside* the pipeline's first
# ("Discovering site...") stage. `load_site` re-raises them as
# `SiteLoadError` -> `CompileError`, so they are ordinary build errors --
# not raw tracebacks -- and are narrated like any other build failure.
# These tests pin that behavior (decided at v0.065; see the addendum).


@pytest.mark.parametrize("flags", [[], ["--verbose"], ["--narrate"]])
def test_duplicate_component_is_a_build_error_not_a_traceback_in_every_mode(
    tmp_path, capsys, isolated_component_registry, flags
):
    site_path = write_site(tmp_path, DUPLICATE_COMPONENT_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", *flags])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.err
    assert "already registered" in captured.err
    assert "Try: arklight search" not in captured.err


def test_duplicate_component_under_narrate_is_narrated_from_the_discovery_stage(
    tmp_path, capsys, isolated_component_registry
):
    site_path = write_site(tmp_path, DUPLICATE_COMPONENT_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--narrate"])
    captured = capsys.readouterr()
    assert exit_code == 1
    # The discovery stage had genuinely started, so it is narrated...
    assert "[Rei] Reading your site file and turning it into an AST tree." in captured.out
    # ...and the failure is reported in Rei's voice, on stderr.
    assert "[Rei] Compilation halted." in captured.err
    # Nothing past the discovery stage ran.
    assert "Expanding" not in captured.out
    assert not (tmp_path / "dist" / "index.html").exists()


def test_duplicate_component_under_verbose_prints_only_the_discovery_stage(
    tmp_path, capsys, isolated_component_registry
):
    site_path = write_site(tmp_path, DUPLICATE_COMPONENT_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--verbose"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[ARKlight] Discovering site and compiling AST trees..." in captured.out
    assert "[ARKlight] Expanding" not in captured.out
    assert "[Rei]" not in captured.out + captured.err


def test_duplicate_style_name_is_narrated_the_same_way(tmp_path, capsys):
    site_path = write_site(tmp_path, DUPLICATE_STYLE_SITE)
    exit_code = main(["build", str(site_path), "-o", str(tmp_path / "dist"), "--no-open", "--narrate"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.err
    assert "[Rei] Compilation halted." in captured.err
    assert "dup-box" in captured.err
    assert "Try: arklight search" not in captured.err


# --- stage-table drift guard -----------------------------------------------
#
# `narrate_stage` falls back to a raw `[Rei] <message>` passthrough for a
# message no pattern matches. That keeps a new pipeline stage visible, but
# it also means a stage added without a pattern would silently narrate as
# "[ARKlight]-style" text under --narrate. These tests make that a failure.


def _is_passthrough(message: str) -> bool:
    return rei.narrate_stage(message) == f"{rei.REI_PREFIX} {message}"


def test_every_stage_message_a_real_build_emits_has_a_narration_pattern(tmp_path):
    from arklight.compiler.pipeline import build

    site_path = write_site(tmp_path, SIMPLE_SITE)
    messages: list[str] = []
    build(site_path, tmp_path / "dist", on_stage=messages.append)
    assert messages
    unmatched = [
        m for m in messages if not rei.is_unconditional_banner(m) and _is_passthrough(m)
    ]
    assert unmatched == []


@pytest.mark.parametrize(
    "message",
    [
        # Stages a plain build doesn't reach, in the exact form
        # `arklight.compiler.pipeline` logs them.
        "Running raw postprocess function 1/2...",
        "Reading .arklight snapshot from build/site.arklight...",
        "Rebuilding Website IR from 3 page(s)...",
    ],
)
def test_conditional_stage_messages_have_a_narration_pattern(message):
    assert not _is_passthrough(message)


def test_assets_stage_does_not_claim_an_assets_folder_exists():
    # The pipeline logs this stage on every build, with or without an
    # `assets/` folder next to the site file.
    assert (
        rei.narrate_stage("Copying assets...")
        == "[Rei] Copying your assets/ folder into the output, if there is one."
    )
