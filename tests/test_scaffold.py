from pathlib import Path
from unittest.mock import patch

import pytest

from arklight.cli.main import main
from arklight.cli.scaffold import ScaffoldError, new_project
from arklight.compiler.pipeline import build


def test_new_simple_writes_expected_files(tmp_path):
    result = new_project("my_site", template="simple", dest_dir=tmp_path)

    assert result.project_dir == tmp_path / "my_site"
    assert result.template == "simple"
    assert (tmp_path / "my_site" / "site.py").exists()
    assert (tmp_path / "my_site" / "README.md").exists()
    assert (tmp_path / "my_site" / "arklight.config.py").exists()


def test_new_production_writes_expected_files(tmp_path):
    result = new_project("my_site", template="production", dest_dir=tmp_path)

    project = result.project_dir
    for rel in [
        "site.py",
        "README.md",
        "components/__init__.py",
        "components/nav.py",
        "components/footer.py",
        "pages/__init__.py",
        "pages/home.py",
        "pages/about.py",
        "content/__init__.py",
        "content/site_content.py",
        "assets/icon.svg",
        "tests/test_site.py",
        ".gitignore",
        "arklight.config.py",
    ]:
        assert (project / rel).exists(), rel


def test_new_default_template_is_simple(tmp_path):
    result = new_project("my_site", dest_dir=tmp_path)
    assert result.template == "simple"


def test_new_unknown_template_raises(tmp_path):
    with pytest.raises(ScaffoldError, match="Unknown template"):
        new_project("my_site", template="bogus", dest_dir=tmp_path)


def test_new_empty_name_raises(tmp_path):
    with pytest.raises(ScaffoldError, match="must not be empty"):
        new_project("", dest_dir=tmp_path)


def test_new_name_with_path_separator_raises(tmp_path):
    with pytest.raises(ScaffoldError, match="path separator"):
        new_project("nested/name", dest_dir=tmp_path)


def test_new_refuses_existing_nonempty_dir(tmp_path):
    target = tmp_path / "my_site"
    target.mkdir()
    (target / "existing.txt").write_text("hi")

    with pytest.raises(ScaffoldError, match="already exists and is not empty"):
        new_project("my_site", dest_dir=tmp_path)


def test_new_allows_existing_empty_dir(tmp_path):
    target = tmp_path / "my_site"
    target.mkdir()

    result = new_project("my_site", dest_dir=tmp_path)
    assert (result.project_dir / "site.py").exists()


@pytest.mark.parametrize("template", ["simple", "production"])
def test_scaffolded_project_builds_successfully(tmp_path, template):
    """The real end-to-end guarantee: whatever `arklight new` writes,
    `arklight build` must be able to compile without any manual edits
    -- this is the "zero-thinking path" the templates promise."""
    result = new_project("my_site", template=template, dest_dir=tmp_path)

    out_dir = tmp_path / "dist"
    build_result = build(result.project_dir / "site.py", out_dir)

    assert (out_dir / "index.html").exists()
    assert (out_dir / "about.html").exists()
    assert build_result.written_paths


@pytest.mark.parametrize("template", ["simple", "production"])
def test_scaffolded_config_file_loads_as_empty_config(tmp_path, template):
    """The scaffolded `arklight.config.py` is fully commented out --
    it must still be valid Python that `arklight.config.load_config`
    can load, resulting in an empty (all-defaults) config."""
    from arklight.config import load_config

    result = new_project("my_site", template=template, dest_dir=tmp_path)

    assert load_config(result.project_dir) == {}


def test_cli_new_scaffolds_and_reports_files(tmp_path, capsys):
    exit_code = main(["new", "my_site", "--dir", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "my_site" / "site.py").exists()
    captured = capsys.readouterr()
    assert "scaffolded a 'simple' project" in captured.out


def test_cli_new_with_production_template(tmp_path, capsys):
    exit_code = main(["new", "my_site", "--template", "production", "--dir", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "my_site" / "pages" / "home.py").exists()


def test_cli_new_invalid_template_is_rejected_by_argparse(tmp_path):
    with pytest.raises(SystemExit):
        main(["new", "my_site", "--template", "bogus", "--dir", str(tmp_path)])


def test_cli_new_failure_returns_nonzero(tmp_path, capsys):
    target = tmp_path / "my_site"
    target.mkdir()
    (target / "existing.txt").write_text("hi")

    exit_code = main(["new", "my_site", "--dir", str(tmp_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "ARKlight new failed" in captured.err


def test_cli_new_default_dir_is_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exit_code = main(["new", "my_site"])

    assert exit_code == 0
    assert (tmp_path / "my_site" / "site.py").exists()


# --- the `production` template's architecture --------------------------------
#
# Layout `arklight new --explain-architecture` recommends: routes thin,
# content/markup/logic each in their own module, plain functions and a
# registered @component mixed freely.


def _built_production(tmp_path):
    result = new_project("my_site", template="production", dest_dir=tmp_path)
    out_dir = tmp_path / "dist"
    build(result.project_dir / "site.py", out_dir)
    return result.project_dir, out_dir


def test_production_site_py_holds_routes_and_no_markup(tmp_path):
    project = new_project("my_site", template="production", dest_dir=tmp_path).project_dir
    source = (project / "site.py").read_text()

    assert '@site.page("/")' in source
    assert '@site.page("/about")' in source
    for markup in ("Heading(", "Text(", "Container(", "Page("):
        assert markup not in source, f"site.py should only route, found {markup}"


def test_production_nav_is_a_registered_component_with_a_checked_prop(tmp_path):
    """Demonstrates the guide's "mix freely" point: nav.py is registered,
    footer.py stays a plain function -- both work with zero extra setup."""
    project = new_project("my_site", template="production", dest_dir=tmp_path).project_dir
    nav_source = (project / "components" / "nav.py").read_text()
    footer_source = (project / "components" / "footer.py").read_text()

    assert "@component(" in nav_source
    assert "Prop(default=None)" in nav_source
    assert "@component" not in footer_source
    assert "def footer():" in footer_source


def test_production_pages_share_nav_active_state_and_footer(tmp_path):
    _, out_dir = _built_production(tmp_path)

    home = (out_dir / "index.html").read_text()
    about = (out_dir / "about.html").read_text()
    assert '<a href="index.html" class="active">Home</a>' in home
    assert '<a href="about.html">About</a>' in home
    assert '<a href="about.html" class="active">About</a>' in about
    assert "<footer" in home and "<footer" in about


def test_production_pages_carry_favicon_and_description(tmp_path):
    _, out_dir = _built_production(tmp_path)
    html = (out_dir / "index.html").read_text()

    assert '<link rel="icon" href="assets/icon.svg">' in html
    assert '<meta name="description"' in html
    assert (out_dir / "assets" / "icon.svg").exists()


def test_production_registered_component_survives_repeated_builds(tmp_path):
    """The template ships a registered @component in an imported
    module (components/nav.py). Confirms it survives every rebuild --
    e.g. every `arklight live-streaming` rebuild (register #2)."""
    result = new_project("my_site", template="production", dest_dir=tmp_path)
    for i in range(3):
        build(result.project_dir / "site.py", tmp_path / f"dist{i}")
        assert (tmp_path / f"dist{i}" / "index.html").exists()


def test_production_projects_own_tests_pass(tmp_path):
    """The scaffolded `tests/` must pass, unedited, in the scaffolded project."""
    import subprocess
    import sys

    result = new_project("my_site", template="production", dest_dir=tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=result.project_dir,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_production_output_can_be_made_a_pwa_with_its_own_icon(tmp_path):
    """README's PWA recipe: `arklight pwa ARK --icon assets/icon.svg:any`."""
    import json

    from arklight.cli.main import _parse_icon_spec
    from arklight.pwa import enable_pwa

    _, out_dir = _built_production(tmp_path)
    icon = _parse_icon_spec("assets/icon.svg:any")
    assert icon["type"] == "image/svg+xml"

    enable_pwa(out_dir, name="My Site", icons=[icon])

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest["icons"] == [icon]
    assert (out_dir / icon["src"]).exists()


def test_scaffolded_config_lists_every_known_section(tmp_path):
    """The generated config used to show only `live_streaming`, leaving
    the other five sections undiscoverable, and pointed at a README
    section that doesn't exist."""
    from arklight.config import _KNOWN_SECTIONS

    project = new_project("my_site", template="production", dest_dir=tmp_path).project_dir
    text = (project / "arklight.config.py").read_text()

    for section_name in _KNOWN_SECTIONS:
        assert f'"{section_name}"' in text, section_name
    assert 'the "Configuration" section of the ARKlight README' not in text
