import shutil
from pathlib import Path

import pytest

from arklight.cli.android import AndroidError, scaffold_project, sync_assets
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


def write_site(tmp_path: Path, text: str = SIMPLE_SITE) -> Path:
    path = tmp_path / "site.py"
    path.write_text(text)
    return path


def build_dir(tmp_path: Path, text: str = SIMPLE_SITE) -> Path:
    site_path = write_site(tmp_path, text)
    out_dir = tmp_path / "ARK"
    build(site_path, out_dir)
    return out_dir


def scaffolded_project(tmp_path: Path) -> tuple[Path, Path]:
    out_dir = build_dir(tmp_path)
    project_dir = tmp_path / "android-project"
    scaffold_project(out_dir, output_dir=project_dir)
    return out_dir, project_dir


# --------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------


def test_sync_with_no_changes_reports_empty_patch(tmp_path):
    out_dir, project_dir = scaffolded_project(tmp_path)

    result = sync_assets(out_dir, output_dir=project_dir)

    assert result.patch_text == ""
    assert result.removed_paths == []
    assert result.patch_path == project_dir / "sync.patch"
    assert result.patch_path.read_text() == ""


def test_sync_picks_up_content_change(tmp_path):
    site_path = write_site(tmp_path)
    out_dir = tmp_path / "ARK"
    build(site_path, out_dir)
    project_dir = tmp_path / "android-project"
    scaffold_project(out_dir, output_dir=project_dir)

    # Change the site content and rebuild into the same ARK/ dir.
    site_path.write_text(SIMPLE_SITE.replace("Hello from ARKlight.", "Hello again."))
    build(site_path, out_dir)

    result = sync_assets(out_dir, output_dir=project_dir)

    assert "Hello again." in (project_dir / "app/src/main/assets/index.html").read_text()
    assert "diff --git a/index.html b/index.html" in result.patch_text
    assert "-<h1>Hi</h1><p>Hello from ARKlight.</p>" in result.patch_text
    assert "+<h1>Hi</h1><p>Hello again.</p>" in result.patch_text
    assert result.patch_path.read_text() == result.patch_text


def test_sync_only_touches_assets_dir(tmp_path):
    out_dir, project_dir = scaffolded_project(tmp_path)
    manifest = project_dir / "app/src/main/AndroidManifest.xml"
    before = manifest.read_text()

    sync_assets(out_dir, output_dir=project_dir)

    assert manifest.read_text() == before


def test_sync_reports_removed_files(tmp_path):
    out_dir, project_dir = scaffolded_project(tmp_path)
    assert (project_dir / "app/src/main/assets/about.html").exists()

    # `build()` never cleans stale files out of an existing output
    # directory (matches plain `arklight build`'s own behavior) -- a
    # page dropped from the site file only disappears from `out_dir`
    # itself with a fresh build directory, same as a real
    # `rm -rf ARK && arklight build ...` would produce.
    one_page_site = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"), Text("Hello from ARKlight."))
"""
    shutil.rmtree(out_dir)
    site_path = tmp_path / "site.py"
    site_path.write_text(one_page_site)
    build(site_path, out_dir)

    result = sync_assets(out_dir, output_dir=project_dir)

    assert not (project_dir / "app/src/main/assets/about.html").exists()
    assert project_dir / "app/src/main/assets/about.html" in result.removed_paths
    assert "deleted file mode" in result.patch_text


def test_sync_custom_patch_path(tmp_path):
    out_dir, project_dir = scaffolded_project(tmp_path)
    site_path = tmp_path / "site.py"
    site_path.write_text(SIMPLE_SITE.replace("Hi", "Hey"))
    build(site_path, out_dir)

    patch_path = tmp_path / "custom.patch"
    result = sync_assets(out_dir, output_dir=project_dir, patch_path=patch_path)

    assert result.patch_path == patch_path
    assert patch_path.is_file()
    assert not (project_dir / "sync.patch").exists()


# --------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------


def test_sync_missing_build_dir_raises(tmp_path):
    with pytest.raises(AndroidError, match="Build directory not found"):
        sync_assets(tmp_path / "nope", output_dir=tmp_path / "android-project")


def test_sync_unscaffolded_project_raises(tmp_path):
    out_dir = build_dir(tmp_path)
    with pytest.raises(AndroidError, match="doesn't look like an `arklight android scaffold`-ed project"):
        sync_assets(out_dir, output_dir=tmp_path / "not-a-project")
