from pathlib import Path

import pytest

from arklight.backend.desktop import runtime
from arklight.cli.desktop import DesktopError, scaffold_project
from arklight.cli.main import main
from arklight.compiler.pipeline import build

SIMPLE_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"), Text("Hello from ARKlight."))

@site.page("/about")
def about():
    return Page(Heading("About"))
"""


def write_site(tmp_path: Path) -> Path:
    path = tmp_path / "site.py"
    path.write_text(SIMPLE_SITE)
    return path


def build_dir(tmp_path: Path) -> Path:
    site_path = write_site(tmp_path)
    out_dir = tmp_path / "ARK"
    build(site_path, out_dir)
    return out_dir


def write_config(tmp_path: Path, desktop_section: str) -> None:
    (tmp_path / "arklight.config.py").write_text(
        f'CONFIG = {{\n    "desktop": {desktop_section},\n}}\n'
    )


# --------------------------------------------------------------------
# Defaults (no arklight.config.py at all)
# --------------------------------------------------------------------


def test_scaffold_with_no_config_uses_defaults(tmp_path):
    out_dir = build_dir(tmp_path)
    project_dir = tmp_path / "desktop-project"

    result = scaffold_project(out_dir, output_dir=project_dir)

    assert result.project_dir == project_dir
    assert result.app_name == "ARKlight App"
    assert result.app_id == "com.arklight.app"
    assert result.target == "linux"
    assert result.binary_name == "arklight-app"

    assert (project_dir / "main.c").exists()
    assert (project_dir / "Makefile").exists()
    assert (project_dir / "assets.gen.c").exists()
    assert (project_dir / "assets.gen.h").exists()
    assert (project_dir / "README.md").exists()
    assert (project_dir / ".gitignore").exists()
    assert (project_dir / "com.arklight.app.desktop").exists()


def test_scaffold_embeds_every_build_file(tmp_path):
    out_dir = build_dir(tmp_path)
    project_dir = tmp_path / "desktop-project"

    scaffold_project(out_dir, output_dir=project_dir)

    assets_c = (project_dir / "assets.gen.c").read_text()
    for name in ("index.html", "about.html", "styles.css", "arklight.js"):
        assert f'"{name}"' in assets_c


def test_scaffold_asset_count_matches_build_dir(tmp_path):
    out_dir = build_dir(tmp_path)
    project_dir = tmp_path / "desktop-project"

    scaffold_project(out_dir, output_dir=project_dir)

    n_files = sum(1 for p in out_dir.rglob("*") if p.is_file())
    assets_c = (project_dir / "assets.gen.c").read_text()
    assert f"const size_t ark_asset_count = {n_files};" in assets_c


def test_scaffold_main_c_includes_generated_header(tmp_path):
    out_dir = build_dir(tmp_path)
    project_dir = tmp_path / "desktop-project"

    scaffold_project(out_dir, output_dir=project_dir)

    main_c = (project_dir / "main.c").read_text()
    assert '#include "assets.gen.h"' in main_c
    assert 'ark:///index.html' in main_c


# --------------------------------------------------------------------
# Config-driven identity/window settings
# --------------------------------------------------------------------


def test_scaffold_reads_config_app_identity(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(
        tmp_path,
        '{"app_name": "My Cool Site!", "app_id": "com.example.mysite", '
        '"width": 900, "height": 600, "resizable": False}',
    )

    result = scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")

    assert result.app_name == "My Cool Site!"
    assert result.app_id == "com.example.mysite"
    assert result.binary_name == "my-cool-site"
    assert (result.project_dir / "com.example.mysite.desktop").exists()

    main_c = (result.project_dir / "main.c").read_text()
    assert "#define ARK_WINDOW_WIDTH 900" in main_c
    assert "#define ARK_WINDOW_HEIGHT 600" in main_c
    assert "#define ARK_RESIZABLE FALSE" in main_c
    # window_title defaults to app_name when unset, and app_name/title
    # get C-string-escaped for embedding in a #define.
    assert '#define ARK_APP_NAME "My Cool Site!"' in main_c
    assert '#define ARK_WINDOW_TITLE "My Cool Site!"' in main_c


def test_scaffold_window_title_overrides_app_name(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, '{"app_name": "My Site", "window_title": "A Different Title"}')

    result = scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")

    main_c = (result.project_dir / "main.c").read_text()
    assert '#define ARK_APP_NAME "My Site"' in main_c
    assert '#define ARK_WINDOW_TITLE "A Different Title"' in main_c


def test_scaffold_escapes_quotes_and_backslashes_in_app_name(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, r'{"app_name": "Weird \"Name\" \\ here"}')

    result = scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")

    main_c = (result.project_dir / "main.c").read_text()
    assert r'#define ARK_APP_NAME "Weird \"Name\" \\ here"' in main_c


# --------------------------------------------------------------------
# binary_name()
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "app_name, expected",
    [
        ("My Cool Site!", "my-cool-site"),
        ("ARKlight App", "arklight-app"),
        ("already-lowercase", "already-lowercase"),
        ("   Weird___Spacing   ", "weird-spacing"),
        ("!!!", "arklight-app"),
    ],
)
def test_binary_name(app_name, expected):
    assert runtime.binary_name(app_name) == expected


# --------------------------------------------------------------------
# Target validation
# --------------------------------------------------------------------


def test_scaffold_defaults_to_linux_target(tmp_path):
    out_dir = build_dir(tmp_path)
    result = scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")
    assert result.target == "linux"


def test_scaffold_unsupported_target_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    with pytest.raises(DesktopError, match="Unsupported desktop target"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project", target="windows")


# --------------------------------------------------------------------
# Validation errors
# --------------------------------------------------------------------


def test_scaffold_missing_build_dir_raises(tmp_path):
    with pytest.raises(DesktopError, match="Build directory not found"):
        scaffold_project(tmp_path / "nope", output_dir=tmp_path / "desktop-project")


def test_scaffold_build_dir_without_index_html_raises(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(DesktopError, match="no index.html"):
        scaffold_project(empty, output_dir=tmp_path / "desktop-project")


def test_scaffold_refuses_nonempty_output_dir(tmp_path):
    out_dir = build_dir(tmp_path)
    project_dir = tmp_path / "desktop-project"
    project_dir.mkdir()
    (project_dir / "existing.txt").write_text("hi")

    with pytest.raises(DesktopError, match="already exists and is not empty"):
        scaffold_project(out_dir, output_dir=project_dir)


def test_scaffold_allows_existing_empty_output_dir(tmp_path):
    out_dir = build_dir(tmp_path)
    project_dir = tmp_path / "desktop-project"
    project_dir.mkdir()

    result = scaffold_project(out_dir, output_dir=project_dir)
    assert (result.project_dir / "main.c").exists()


def test_scaffold_invalid_app_id_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, '{"app_id": "not-an-app-id"}')

    with pytest.raises(DesktopError, match="Invalid desktop.app_id"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")


def test_scaffold_single_segment_app_id_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, '{"app_id": "onlyone"}')

    with pytest.raises(DesktopError, match="Invalid desktop.app_id"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")


def test_scaffold_non_int_width_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, '{"width": "big"}')

    with pytest.raises(DesktopError, match="desktop.width must be a positive int"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")


def test_scaffold_zero_height_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, '{"height": 0}')

    with pytest.raises(DesktopError, match="desktop.height must be a positive int"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")


def test_scaffold_bool_width_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, '{"width": True}')

    with pytest.raises(DesktopError, match="desktop.width must be a positive int"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")


def test_scaffold_non_bool_resizable_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, '{"resizable": "yes"}')

    with pytest.raises(DesktopError, match="desktop.resizable must be a bool"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")


def test_scaffold_empty_app_name_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    write_config(tmp_path, '{"app_name": "   "}')

    with pytest.raises(DesktopError, match="desktop.app_name must be a non-empty string"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")


def test_scaffold_malformed_config_raises_desktop_error(tmp_path):
    out_dir = build_dir(tmp_path)
    (tmp_path / "arklight.config.py").write_text("this is not valid python (((")

    with pytest.raises(DesktopError, match="invalid Python"):
        scaffold_project(out_dir, output_dir=tmp_path / "desktop-project")


# --------------------------------------------------------------------
# generate_assets_source() -- pure function, no disk involved
# --------------------------------------------------------------------


def test_generate_assets_source_indexes_every_file():
    files = {"index.html": b"<html></html>", "assets/logo.svg": b"<svg></svg>"}
    source, header = runtime.generate_assets_source(files)

    assert "const size_t ark_asset_count = 2;" in source
    assert '"index.html"' in source
    assert '"assets/logo.svg"' in source
    assert "extern const ArkAsset ark_assets[];" in header
    assert "extern const size_t ark_asset_count;" in header


def test_generate_assets_source_guesses_mime_types():
    files = {"index.html": b"<html></html>", "styles.css": b"body {}", "data.bin": b"\x00\x01"}
    source, _ = runtime.generate_assets_source(files)

    assert "text/html" in source
    assert "text/css" in source
    assert "application/octet-stream" in source


def test_generate_assets_source_embeds_exact_bytes():
    files = {"index.html": bytes([0x00, 0xFF, 0x41, 0x0A])}
    source, _ = runtime.generate_assets_source(files)

    assert "0x00, 0xff, 0x41, 0x0a" in source


# --------------------------------------------------------------------
# CLI-level
# --------------------------------------------------------------------


def test_cli_desktop_scaffold_reports_success(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = build_dir(tmp_path)

    exit_code = main(["desktop", "scaffold", str(out_dir), "-o", "desktop-project"])

    assert exit_code == 0
    assert (tmp_path / "desktop-project" / "main.c").exists()
    captured = capsys.readouterr()
    assert "scaffolded a linux desktop project" in captured.out
    assert "com.arklight.app" in captured.out


def test_cli_desktop_scaffold_failure_returns_nonzero(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["desktop", "scaffold", "does-not-exist", "-o", "desktop-project"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "ARKlight desktop scaffold failed" in captured.err


def test_cli_desktop_without_subcommand_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        main(["desktop"])


def test_cli_desktop_scaffold_requires_output_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        main(["desktop", "scaffold", "ARK"])


def test_cli_desktop_scaffold_rejects_unsupported_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = build_dir(tmp_path)
    with pytest.raises(SystemExit):
        main(["desktop", "scaffold", str(out_dir), "-o", "desktop-project", "--target", "macos"])
