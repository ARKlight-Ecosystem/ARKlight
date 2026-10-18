"""Markdown-as-content Stage M5: `markdown-simple`/`markdown-production`
templates (`arklight.cli.templates.markdown_simple`/`markdown_production`).

Follows `tests/test_scaffold.py`'s pattern for the existing `simple`/
`production` templates -- file-presence checks, then a real
`arklight build` over the scaffolded output, which is the addendum's
own exit test for this stage ("both layouts build successfully from a
fresh `arklight new` scaffold")."""

from pathlib import Path

import pytest

from arklight.cli.main import main
from arklight.cli.scaffold import new_project
from arklight.cli.templates import TEMPLATES
from arklight.compiler.pipeline import build
from arklight.config import load_config


def test_markdown_templates_are_registered():
    assert "markdown-simple" in TEMPLATES
    assert "markdown-production" in TEMPLATES


def test_new_markdown_simple_writes_expected_files(tmp_path):
    result = new_project("my_site", template="markdown-simple", dest_dir=tmp_path)

    project = result.project_dir
    assert result.template == "markdown-simple"
    for rel in ["site.py", "content/index.md", "content/about.md", "README.md", "arklight.config.py"]:
        assert (project / rel).exists(), rel


def test_markdown_simple_site_py_registers_no_decorated_pages(tmp_path):
    # The whole point of this template: every route comes from
    # content/*.md, discovered at build time -- site.py itself has no
    # @site.page(...) decorator at all.
    result = new_project("my_site", template="markdown-simple", dest_dir=tmp_path)
    site_source = (result.project_dir / "site.py").read_text(encoding="utf-8")
    assert "@site.page" not in site_source
    assert "site = Site()" in site_source


def test_new_markdown_production_writes_expected_files(tmp_path):
    result = new_project("my_site", template="markdown-production", dest_dir=tmp_path)

    project = result.project_dir
    assert result.template == "markdown-production"
    for rel in [
        "site.py",
        "README.md",
        "components/__init__.py",
        "components/nav.py",
        "components/footer.py",
        "pages/__init__.py",
        "pages/home.py",
        "content/about.md",
        "content/guide.md",
        "assets/icon.svg",
        "tests/test_site.py",
        ".gitignore",
        "arklight.config.py",
    ]:
        assert (project / rel).exists(), rel


def test_markdown_production_mixes_python_and_markdown_routes(tmp_path):
    # Q7's answer, verified directly: "/" is Python-authored
    # (pages/home.py via site.py's one @site.page decorator); "/about"
    # and "/guide" are Markdown-authored (content/*.md), with no
    # decorator claiming either.
    result = new_project("my_site", template="markdown-production", dest_dir=tmp_path)
    site_source = (result.project_dir / "site.py").read_text(encoding="utf-8")
    decorator_lines = [
        line.strip() for line in site_source.splitlines() if line.strip().startswith("@site.page")
    ]
    assert decorator_lines == ['@site.page("/")']


@pytest.mark.parametrize("template", ["markdown-simple", "markdown-production"])
def test_scaffolded_markdown_project_builds_successfully(tmp_path, template):
    """Addendum exit test for Stage M5, verified directly: both new
    templates build, unmodified, immediately after `arklight new`."""
    result = new_project("my_site", template=template, dest_dir=tmp_path)

    out_dir = tmp_path / "dist"
    build_result = build(result.project_dir / "site.py", out_dir)

    assert (out_dir / "index.html").exists()
    assert (out_dir / "about.html").exists()
    assert build_result.written_paths


def test_scaffolded_markdown_simple_content_renders(tmp_path):
    result = new_project("my_site", template="markdown-simple", dest_dir=tmp_path)
    out_dir = tmp_path / "dist"
    build(result.project_dir / "site.py", out_dir)

    index_html = (out_dir / "index.html").read_text(encoding="utf-8")
    about_html = (out_dir / "about.html").read_text(encoding="utf-8")
    assert "Build websites with Python." in index_html
    assert "<title>my_site</title>" in index_html
    assert "About" in about_html


def test_scaffolded_markdown_production_mixes_rendering(tmp_path):
    result = new_project("my_site", template="markdown-production", dest_dir=tmp_path)
    out_dir = tmp_path / "dist"
    build(result.project_dir / "site.py", out_dir)

    index_html = (out_dir / "index.html").read_text(encoding="utf-8")
    guide_html = (out_dir / "guide.html").read_text(encoding="utf-8")
    # "/" is Python-authored: it carries the nav/footer components.
    assert 'class="nav"' in index_html
    assert "<footer" in index_html
    # "/guide" is Markdown-authored: a fenced code block and a
    # blockquote from content/guide.md made it through the pipeline.
    assert "<pre" in guide_html
    assert "<blockquote" in guide_html


@pytest.mark.parametrize("template", ["markdown-simple", "markdown-production"])
def test_scaffolded_markdown_config_file_loads_as_empty_config(tmp_path, template):
    result = new_project("my_site", template=template, dest_dir=tmp_path)
    assert load_config(result.project_dir) == {}


def test_cli_new_with_markdown_simple_template(tmp_path, capsys):
    exit_code = main(["new", "my_site", "--template", "markdown-simple", "--dir", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "my_site" / "content" / "index.md").exists()
    captured = capsys.readouterr()
    assert "scaffolded a 'markdown-simple' project" in captured.out


def test_cli_new_with_markdown_production_template(tmp_path, capsys):
    exit_code = main(
        ["new", "my_site", "--template", "markdown-production", "--dir", str(tmp_path)]
    )

    assert exit_code == 0
    assert (tmp_path / "my_site" / "pages" / "home.py").exists()
    assert (tmp_path / "my_site" / "content" / "guide.md").exists()


def test_cli_new_help_lists_markdown_templates(capsys):
    with pytest.raises(SystemExit):
        main(["new", "--help"])
    captured = capsys.readouterr()
    assert "markdown-simple" in captured.out
    assert "markdown-production" in captured.out
