"""Markdown-as-content Stage M3: `content/` discovery and route
synthesis (`arklight.content.discovery`, plus the early step in
`arklight.compiler.pipeline`). Unit coverage of the discovery module,
then real `build()` runs over fixture projects -- including the
addendum's exit-test fixture."""

from pathlib import Path

import pytest

from arklight.ast.nodes import ARKNode
from arklight.compiler.pipeline import CompileError, build
from arklight.content.discovery import (
    ContentCollisionError,
    ContentError,
    check_python_route_collisions,
    discover_content,
    synthesize_page,
    synthesize_pages,
)
from arklight.content.frontmatter import FrontMatterError
from arklight.parser.discover import discover

PY_SITE = """\
# include <stdlib.ARKlight>
# include <markdown.ARKlight>

site = Site()

@site.page("/about")
def about():
    return Page(Heading("Python about"), title="About")
"""

EMPTY_SITE = (
    "# include <stdlib.ARKlight>\n"
    "# include <markdown.ARKlight>\n\n"
    "site = Site()\n"
)


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _routes(tmp_path: Path) -> list[str]:
    return [p.route for p in discover_content(tmp_path)]


# ---------------------------------------------------------------------------
# Trigger (Q2): .md files under content/, nothing else
# ---------------------------------------------------------------------------


def test_no_content_dir_discovers_nothing(tmp_path):
    assert discover_content(tmp_path) == []


def test_empty_content_dir_discovers_nothing(tmp_path):
    (tmp_path / "content").mkdir()
    assert discover_content(tmp_path) == []


def test_python_package_content_dir_discovers_nothing(tmp_path):
    # `production` template shape: content/ is a Python package.
    _write(tmp_path, "content/__init__.py", "")
    _write(tmp_path, "content/site_content.py", "FOOTER = 'x'\n")
    assert discover_content(tmp_path) == []


def test_hidden_and_non_md_files_are_ignored(tmp_path):
    _write(tmp_path, "content/.hidden.md", "# h\n")
    _write(tmp_path, "content/.git/notes.md", "# g\n")
    _write(tmp_path, "content/readme.txt", "t\n")
    _write(tmp_path, "content/real.md", "# r\n")
    assert _routes(tmp_path) == ["/real"]


# ---------------------------------------------------------------------------
# Route derivation
# ---------------------------------------------------------------------------


def test_filename_route_derivation(tmp_path):
    _write(tmp_path, "content/index.md", "# i\n")
    _write(tmp_path, "content/guide.md", "# g\n")
    _write(tmp_path, "content/docs/index.md", "# d\n")
    _write(tmp_path, "content/docs/setup.md", "# s\n")
    _write(tmp_path, "content/docs/deep/page.md", "# p\n")
    assert _routes(tmp_path) == ["/", "/docs", "/docs/deep/page", "/docs/setup", "/guide"]


def test_front_matter_route_overrides_filename(tmp_path):
    _write(tmp_path, "content/guide.md", "---\nroute: /start\n---\n# g\n")
    (page,) = discover_content(tmp_path)
    assert page.route == "/start"
    assert page.route_source == "front matter"


def test_filename_route_source_is_recorded(tmp_path):
    _write(tmp_path, "content/guide.md", "# g\n")
    (page,) = discover_content(tmp_path)
    assert page.route_source == "filename"
    assert page.relative_path == "content/guide.md"


def test_unsafe_filename_names_the_file_and_the_escape_hatch(tmp_path):
    _write(tmp_path, "content/my guide.md", "# g\n")
    with pytest.raises(ContentError) as exc:
        discover_content(tmp_path)
    message = str(exc.value)
    assert "content/my guide.md" in message
    assert "route:" in message


def test_unsafe_filename_is_fine_with_a_front_matter_route(tmp_path):
    _write(tmp_path, "content/my guide.md", "---\nroute: /guide\n---\n# g\n")
    assert _routes(tmp_path) == ["/guide"]


@pytest.mark.parametrize(
    "bad_route",
    ["guide", "/guide/", "//guide", "/a//b", "/a/../b", "/a b", "/a?x=1", "/a#frag"],
)
def test_invalid_front_matter_routes_are_diagnostics(tmp_path, bad_route):
    _write(tmp_path, "content/g.md", f'---\nroute: "{bad_route}"\n---\n# g\n')
    with pytest.raises(ContentError) as exc:
        discover_content(tmp_path)
    assert "content/g.md" in str(exc.value)


def test_root_route_is_valid_front_matter(tmp_path):
    _write(tmp_path, "content/home.md", "---\nroute: /\n---\n# h\n")
    assert _routes(tmp_path) == ["/"]


# ---------------------------------------------------------------------------
# Titles and descriptions
# ---------------------------------------------------------------------------


def test_title_defaults_from_filename(tmp_path):
    _write(tmp_path, "content/getting-started.md", "# x\n")
    _write(tmp_path, "content/index.md", "# x\n")
    _write(tmp_path, "content/docs/index.md", "# x\n")
    titles = {p.route: p.title for p in discover_content(tmp_path)}
    assert titles == {"/": "Home", "/docs": "Docs", "/getting-started": "Getting Started"}


def test_front_matter_title_and_description_win(tmp_path):
    _write(
        tmp_path,
        "content/g.md",
        "---\ntitle: Real Title\ndescription: Real desc\n---\n# g\n",
    )
    (page,) = discover_content(tmp_path)
    assert (page.title, page.description) == ("Real Title", "Real desc")


def test_body_has_front_matter_removed(tmp_path):
    _write(tmp_path, "content/g.md", "---\ntitle: T\n---\n# Heading\n")
    (page,) = discover_content(tmp_path)
    assert "title: T" not in page.body
    assert "# Heading" in page.body


def test_utf8_bom_does_not_hide_front_matter(tmp_path):
    path = tmp_path / "content" / "g.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xef\xbb\xbf---\nroute: /bom\n---\n# g\n")
    assert _routes(tmp_path) == ["/bom"]


# ---------------------------------------------------------------------------
# Drafts
# ---------------------------------------------------------------------------


def test_drafts_are_excluded_entirely(tmp_path):
    _write(tmp_path, "content/live.md", "# l\n")
    _write(tmp_path, "content/wip.md", "---\ndraft: true\n---\n# w\n")
    assert _routes(tmp_path) == ["/live"]


def test_draft_does_not_participate_in_collisions(tmp_path):
    _write(tmp_path, "content/guide.md", "# g\n")
    _write(tmp_path, "content/guide/index.md", "---\ndraft: true\n---\n# g2\n")
    assert _routes(tmp_path) == ["/guide"]


def test_draft_does_not_collide_with_python_route(tmp_path):
    _write(tmp_path, "content/about.md", "---\ndraft: true\n---\n# a\n")
    check_python_route_collisions(discover_content(tmp_path), {"/about": "site.py:6"})


# ---------------------------------------------------------------------------
# Q6: collisions
# ---------------------------------------------------------------------------


def test_markdown_vs_markdown_collision_names_both_files(tmp_path):
    _write(tmp_path, "content/guide.md", "# a\n")
    _write(tmp_path, "content/guide/index.md", "# b\n")
    with pytest.raises(ContentCollisionError) as exc:
        discover_content(tmp_path)
    message = str(exc.value)
    assert "content/guide.md" in message
    assert "content/guide/index.md" in message
    assert "'/guide'" in message
    assert len(exc.value.collisions) == 1


def test_collision_after_front_matter_override(tmp_path):
    _write(tmp_path, "content/a.md", "---\nroute: /same\n---\n# a\n")
    _write(tmp_path, "content/b.md", "---\nroute: /same\n---\n# b\n")
    with pytest.raises(ContentCollisionError) as exc:
        discover_content(tmp_path)
    assert "route from front matter" in str(exc.value)


def test_override_that_removes_a_filename_collision_is_fine(tmp_path):
    _write(tmp_path, "content/guide.md", "# a\n")
    _write(tmp_path, "content/guide/index.md", "---\nroute: /guide-home\n---\n# b\n")
    assert _routes(tmp_path) == ["/guide", "/guide-home"]


def test_every_collision_is_reported_at_once(tmp_path):
    _write(tmp_path, "content/a.md", "---\nroute: /x\n---\n")
    _write(tmp_path, "content/b.md", "---\nroute: /x\n---\n")
    _write(tmp_path, "content/c.md", "---\nroute: /y\n---\n")
    _write(tmp_path, "content/d.md", "---\nroute: /y\n---\n")
    with pytest.raises(ContentCollisionError) as exc:
        discover_content(tmp_path)
    assert {c[0] for c in exc.value.collisions} == {"/x", "/y"}


def test_python_route_collision_names_both_sources(tmp_path):
    _write(tmp_path, "content/about.md", "# a\n")
    pages = discover_content(tmp_path)
    with pytest.raises(ContentCollisionError) as exc:
        check_python_route_collisions(pages, {"/about": "site.py:6 (@site.page)"})
    message = str(exc.value)
    assert "content/about.md" in message
    assert "site.py:6" in message


def test_no_python_collision_when_routes_differ(tmp_path):
    _write(tmp_path, "content/guide.md", "# g\n")
    check_python_route_collisions(discover_content(tmp_path), {"/about": "site.py:6"})


# ---------------------------------------------------------------------------
# Front matter errors surface unchanged
# ---------------------------------------------------------------------------


def test_bad_front_matter_propagates_with_file_name(tmp_path):
    _write(tmp_path, "content/g.md", "---\ntitel: x\n---\n# g\n")
    with pytest.raises(FrontMatterError) as exc:
        discover_content(tmp_path)
    assert "content/g.md" in str(exc.value)
    assert "titel" in str(exc.value)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_result_is_sorted_by_route_regardless_of_creation_order(tmp_path):
    for name in ["zeta", "alpha", "mid"]:
        _write(tmp_path, f"content/{name}.md", "# x\n")
    assert _routes(tmp_path) == ["/alpha", "/mid", "/zeta"]


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


def test_synthesize_page_builds_a_page_node(tmp_path):
    _write(
        tmp_path,
        "content/g.md",
        "---\ntitle: T\ndescription: D\n---\n# Heading\n\nbody\n",
    )
    (page,) = discover_content(tmp_path)
    node = synthesize_page(page)
    assert isinstance(node, ARKNode)
    assert node.type == "Page"
    assert node.props["title"] == "T"
    assert node.props["description"] == "D"
    assert node.children[0].type == "Heading"


def test_synthesize_page_omits_description_when_absent(tmp_path):
    _write(tmp_path, "content/g.md", "# g\n")
    (page,) = discover_content(tmp_path)
    assert "description" not in synthesize_page(page).props


def test_synthesize_pages_is_keyed_by_route(tmp_path):
    _write(tmp_path, "content/index.md", "# i\n")
    _write(tmp_path, "content/guide.md", "# g\n")
    assert list(synthesize_pages(discover_content(tmp_path))) == ["/", "/guide"]


# ---------------------------------------------------------------------------
# discover(): the require_pages kwarg must not change the default
# ---------------------------------------------------------------------------


def test_discover_still_requires_pages_by_default():
    with pytest.raises(ValueError, match="No pages registered"):
        discover(EMPTY_SITE)


def test_discover_require_pages_false_allows_a_pageless_site():
    result = discover(EMPTY_SITE, require_pages=False)
    assert result.variable_name == "site"
    assert result.pages == []


def test_discover_require_pages_false_still_requires_a_site():
    with pytest.raises(ValueError, match="No `Site\\(\\)` instantiation"):
        discover("x = 1\n", require_pages=False)


# ---------------------------------------------------------------------------
# Opt-in gate: `# include <markdown.ARKlight>`
# ---------------------------------------------------------------------------


def test_build_fails_with_no_pages_when_gate_is_missing(tmp_path):
    # EMPTY_SITE carries the gate; a site.py without it registers no
    # @site.page(...) of its own, and the content/*.md below is never
    # discovered -- so the project genuinely has no pages.
    _write(tmp_path, "site.py", "# include <stdlib.ARKlight>\n\nsite = Site()\n")
    _write(tmp_path, "content/guide.md", "# Guide\n")
    with pytest.raises(CompileError, match="No pages registered"):
        build(tmp_path / "site.py", tmp_path / "ARK")


def test_build_succeeds_once_gate_is_added(tmp_path):
    _write(tmp_path, "site.py", EMPTY_SITE)
    _write(tmp_path, "content/guide.md", "# Guide\n")
    result = build(tmp_path / "site.py", tmp_path / "ARK")
    assert "/guide" in {page.route for page in result.ir.pages}


def test_missing_gate_is_a_no_op_for_a_project_with_no_markdown(tmp_path):
    # No content/ at all: whether or not the gate is present, a plain
    # Python-only project builds exactly as it always has.
    site = _write(tmp_path, "site.py", PY_SITE)
    result = build(site, tmp_path / "ARK")
    assert "/about" in {page.route for page in result.ir.pages}


# ---------------------------------------------------------------------------
# End to end through a real build()
# ---------------------------------------------------------------------------


def _exit_test_project(root: Path) -> Path:
    """The addendum's M3 exit-test fixture: three content files -- one
    with a `route` override, one draft, one colliding with a
    `@site.page` route."""
    site = _write(root, "site.py", PY_SITE)
    _write(
        root,
        "content/guide.md",
        "---\ntitle: Getting Started\nroute: /start\ndescription: How to begin\n---\n\n"
        "# Hello\n\nSome **bold** text.\n",
    )
    _write(root, "content/wip.md", "---\ndraft: true\n---\n\n# Secret\n")
    _write(root, "content/about.md", "# Markdown about\n")
    return site


def test_exit_test_fixture_produces_the_one_expected_collision(tmp_path):
    site = _exit_test_project(tmp_path)
    with pytest.raises(CompileError) as exc:
        build(site, tmp_path / "ARK")
    message = str(exc.value)
    assert "content/about.md" in message
    assert "site.py:7" in message
    assert "'/about'" in message
    # Exactly one collision: the override and the draft are not in it.
    assert "/start" not in message
    assert "wip.md" not in message


def test_exit_test_fixture_produces_exactly_the_two_expected_pages(tmp_path):
    site = _exit_test_project(tmp_path)
    (tmp_path / "content" / "about.md").unlink()  # remove the collision
    out = tmp_path / "ARK"
    result = build(site, out)

    routes = sorted(page.route for page in result.ir.pages)
    assert routes == ["/about", "/start"]  # the Python page + the overridden md page
    assert (out / "about.html").exists()
    assert (out / "start.html").exists()
    assert not (out / "guide.html").exists()  # route override, not filename route
    assert not (out / "wip.html").exists()  # draft is never built

    start = (out / "start.html").read_text(encoding="utf-8")
    assert "<title>Getting Started</title>" in start
    assert 'name="description" content="How to begin"' in start
    assert "<strong>bold</strong>" in start
    assert "Secret" not in "".join(p.read_text(encoding="utf-8") for p in out.glob("*.html"))


def test_markdown_only_site_builds_with_no_site_page_decorators(tmp_path):
    site = _write(tmp_path, "site.py", EMPTY_SITE)
    _write(tmp_path, "content/index.md", "# Home\n\nWelcome.\n")
    _write(tmp_path, "content/docs/setup.md", "# Setup\n")
    out = tmp_path / "ARK"
    build(site, out)
    assert "Welcome." in (out / "index.html").read_text(encoding="utf-8")
    assert (out / "docs" / "setup.html").exists()


def test_site_with_no_pages_and_no_content_still_fails_as_before(tmp_path):
    site = _write(tmp_path, "site.py", EMPTY_SITE)
    with pytest.raises(CompileError, match="No pages registered"):
        build(site, tmp_path / "ARK")


def test_site_with_only_drafts_still_fails_as_before(tmp_path):
    site = _write(tmp_path, "site.py", EMPTY_SITE)
    _write(tmp_path, "content/wip.md", "---\ndraft: true\n---\n# w\n")
    with pytest.raises(CompileError, match="No pages registered"):
        build(site, tmp_path / "ARK")


def test_python_only_project_is_unaffected(tmp_path):
    site = _write(tmp_path, "site.py", PY_SITE)
    result = build(site, tmp_path / "ARK")
    assert [p.route for p in result.ir.pages] == ["/about"]


def test_python_package_content_dir_is_unaffected(tmp_path):
    site = _write(tmp_path, "site.py", PY_SITE)
    _write(tmp_path, "content/__init__.py", "")
    _write(tmp_path, "content/site_content.py", "FOOTER = 'x'\n")
    result = build(site, tmp_path / "ARK")
    assert [p.route for p in result.ir.pages] == ["/about"]


def test_markdown_pages_mix_with_python_pages(tmp_path):
    site = _write(tmp_path, "site.py", PY_SITE)
    _write(tmp_path, "content/guide.md", "# Guide\n")
    result = build(site, tmp_path / "ARK")
    assert sorted(p.route for p in result.ir.pages) == ["/about", "/guide"]


def test_markdown_collision_with_python_page_is_a_compile_error(tmp_path):
    site = _write(tmp_path, "site.py", PY_SITE)
    _write(tmp_path, "content/about.md", "# a\n")
    with pytest.raises(CompileError, match="Duplicate route"):
        build(site, tmp_path / "ARK")


def test_bad_front_matter_is_a_compile_error_naming_the_file(tmp_path):
    site = _write(tmp_path, "site.py", PY_SITE)
    _write(tmp_path, "content/g.md", "---\ntitel: x\n---\n# g\n")
    with pytest.raises(CompileError, match="content/g.md"):
        build(site, tmp_path / "ARK")


def test_unterminated_fence_is_a_compile_error_naming_the_file(tmp_path):
    site = _write(tmp_path, "site.py", PY_SITE)
    _write(tmp_path, "content/g.md", "# g\n\n```py\nnever closed\n")
    with pytest.raises(CompileError, match="content/g.md"):
        build(site, tmp_path / "ARK")


def test_raw_html_in_content_is_escaped_not_live(tmp_path):
    # M2's guarantee, checked through the real discovery path too.
    site = _write(tmp_path, "site.py", EMPTY_SITE)
    _write(tmp_path, "content/index.md", "# Hi\n\n<script>alert(1)</script>\n")
    out = tmp_path / "ARK"
    build(site, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html  # visible as text, not silently dropped


def test_build_is_deterministic(tmp_path):
    site = _write(tmp_path, "site.py", EMPTY_SITE)
    for name in ["zeta", "alpha", "mid"]:
        _write(tmp_path, f"content/{name}.md", f"# {name}\n")
    build(site, tmp_path / "A")
    build(site, tmp_path / "B")
    for name in ["zeta", "alpha", "mid"]:
        assert (tmp_path / "A" / f"{name}.html").read_bytes() == (
            tmp_path / "B" / f"{name}.html"
        ).read_bytes()
