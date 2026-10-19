"""Markdown-as-content Stage M4: asset and link resolution.

Unit coverage of the resolution rules in `arklight.content.markdown`
(`parse_markdown(..., content_path=...)`), then real `build()` runs
showing a Markdown-sourced reference is checked by the *existing*
`asset_check`/`link_check` exactly like a Python-authored one."""

from pathlib import Path

import pytest

from arklight.ast.nodes import ARKNode
from arklight.compiler.pipeline import CompileError, build
from arklight.content.discovery import discover_content, synthesize_pages
from arklight.content.markdown import (
    MarkdownReferenceError,
    MarkdownSyntaxError,
    parse_markdown,
)

PNG = b"\x89PNG\r\n\x1a\n"
EMPTY_SITE = (
    "# include <stdlib.ARKlight>\n"
    "# include <markdown.ARKlight>\n\n"
    "site = Site()\n"
)


def _write(root: Path, rel: str, text: str | bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def _first(nodes: list[ARKNode], type_name: str) -> ARKNode:
    """First node of `type_name`, searching the whole tree."""

    def walk(item):
        if isinstance(item, ARKNode):
            if item.type == type_name:
                return item
            return walk(item.children)
        if isinstance(item, (list, tuple)):
            for child in item:
                found = walk(child)
                if found is not None:
                    return found
        return None

    found = walk(nodes)
    assert found is not None, f"no {type_name} in tree"
    return found


def _img_src(md: str, content_path: str = "page.md") -> str:
    return _first(parse_markdown(md, content_path=content_path), "Image").props["src"]


def _link_href(md: str, content_path: str = "page.md", routes=None) -> str:
    nodes = parse_markdown(md, content_path=content_path, page_routes=routes or {})
    return _first(nodes, "Link").props["href"]


# ---------------------------------------------------------------------------
# Off by default: Stage M2 behavior is preserved
# ---------------------------------------------------------------------------


def test_without_content_path_references_are_untouched():
    nodes = parse_markdown("![a](./diagram.png)\n\n[l](guide.md)\n")
    assert _first(nodes, "Image").props["src"] == "./diagram.png"
    assert _first(nodes, "Link").props["href"] == "guide.md"


# ---------------------------------------------------------------------------
# Images: relative paths resolve against assets/
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "written, expected",
    [
        ("./diagram.png", "assets/diagram.png"),
        ("diagram.png", "assets/diagram.png"),
        ("img/a.png", "assets/img/a.png"),
        ("./img/../a.png", "assets/a.png"),
        ("assets/diagram.png", "assets/diagram.png"),
        ("./assets/diagram.png", "assets/diagram.png"),
        ("../assets/diagram.png", "assets/diagram.png"),
        ("diagram.png?v=2", "assets/diagram.png?v=2"),
    ],
)
def test_image_relative_paths_resolve_against_assets(written, expected):
    assert _img_src(f"![alt]({written})") == expected


@pytest.mark.parametrize(
    "written",
    [
        "https://example.com/x.png",
        "http://example.com/x.png",
        "//cdn.example.com/x.png",
        "data:image/png;base64,AAAA",
        "/assets/diagram.png",
        "/elsewhere/x.png",
    ],
)
def test_image_external_and_root_relative_references_are_left_alone(written):
    assert _img_src(f"![alt]({written})") == written


@pytest.mark.parametrize("written", ["../secret.png", "../../x.png", "a/../../x.png"])
def test_image_that_climbs_out_of_assets_is_a_reference_error(written):
    with pytest.raises(MarkdownReferenceError) as exc:
        parse_markdown(f"![alt]({written})", filename="content/g.md", content_path="g.md")
    message = str(exc.value)
    assert "content/g.md" in message
    assert written in message
    assert "assets/" in message


def test_reference_error_is_a_markdown_syntax_error():
    # So the pipeline's existing `except MarkdownSyntaxError` reports it.
    assert issubclass(MarkdownReferenceError, MarkdownSyntaxError)


def test_alt_text_and_other_props_survive_resolution():
    node = _first(parse_markdown("![My alt](./d.png)", content_path="p.md"), "Image")
    assert node.props == {"src": "assets/d.png", "alt": "My alt"}


# ---------------------------------------------------------------------------
# Links to files (a downloadable PDF) resolve against assets/ too
# ---------------------------------------------------------------------------


def test_link_to_a_file_resolves_against_assets():
    assert _link_href("[manual](./manual.pdf)") == "assets/manual.pdf"


def test_link_external_fragment_and_root_relative_are_left_alone():
    assert _link_href("[x](https://example.com)") == "https://example.com"
    assert _link_href("[x](mailto:a@b.c)") == "mailto:a@b.c"
    assert _link_href("[x](#top)") == "#top"
    assert _link_href("[x](/guide)") == "/guide"
    assert _link_href("[x](/typo)") == "/typo"


# ---------------------------------------------------------------------------
# Links between Markdown pages resolve to routes
# ---------------------------------------------------------------------------

ROUTES = {
    "index.md": "/",
    "guide.md": "/guide",
    "docs/index.md": "/docs",
    "docs/setup.md": "/install-guide",  # a front matter `route` override
    "docs/deep/page.md": "/docs/deep/page",
}


@pytest.mark.parametrize(
    "content_path, written, expected",
    [
        ("index.md", "guide.md", "/guide"),
        ("index.md", "./guide.md", "/guide"),
        ("index.md", "docs/index.md", "/docs"),
        ("index.md", "docs/setup.md", "/install-guide"),  # override honored
        ("docs/index.md", "setup.md", "/install-guide"),
        ("docs/index.md", "../guide.md", "/guide"),
        ("docs/setup.md", "../index.md", "/"),
        ("docs/setup.md", "deep/page.md", "/docs/deep/page"),
        ("docs/deep/page.md", "../../guide.md", "/guide"),
    ],
)
def test_markdown_links_resolve_to_routes(content_path, written, expected):
    assert _link_href(f"[l]({written})", content_path, ROUTES) == expected


def test_markdown_link_target_matching_is_exact_case():
    # Same philosophy as asset_check: `Guide.md` is not `guide.md` on a
    # case-sensitive host, so it must not quietly resolve.
    with pytest.raises(MarkdownReferenceError):
        _link_href("[l](Guide.md)", "index.md", ROUTES)


def test_markdown_link_keeps_fragment_and_query():
    assert _link_href("[l](guide.md#install)", "index.md", ROUTES) == "/guide#install"
    assert _link_href("[l](guide.md?x=1)", "index.md", ROUTES) == "/guide?x=1"
    assert _link_href("[l](guide.md?x=1#f)", "index.md", ROUTES) == "/guide?x=1#f"


def test_link_to_a_missing_or_draft_page_names_file_and_target():
    with pytest.raises(MarkdownReferenceError) as exc:
        parse_markdown(
            "[l](nope.md)", filename="content/index.md", content_path="index.md",
            page_routes=ROUTES,
        )
    message = str(exc.value)
    assert "content/index.md" in message
    assert "content/nope.md" in message
    assert "draft" in message


def test_link_to_a_page_with_no_route_table_is_an_error_not_a_dead_link():
    with pytest.raises(MarkdownReferenceError):
        parse_markdown("[l](guide.md)", content_path="index.md")


def test_markdown_link_that_climbs_out_of_content_is_an_error():
    with pytest.raises(MarkdownReferenceError) as exc:
        parse_markdown(
            "[l](../outside.md)", filename="content/index.md", content_path="index.md",
            page_routes=ROUTES,
        )
    assert "climbs out of content/" in str(exc.value)


# ---------------------------------------------------------------------------
# Where references can appear
# ---------------------------------------------------------------------------


def test_references_are_resolved_inside_blockquotes_and_tables():
    md = "> see [g](guide.md)\n\n| a |\n| - |\n| [g](guide.md) |\n"
    nodes = parse_markdown(md, content_path="index.md", page_routes=ROUTES)
    hrefs = []

    def walk(item):
        if isinstance(item, ARKNode):
            if item.type == "Link":
                hrefs.append(item.props["href"])
            walk(item.children)
        elif isinstance(item, (list, tuple)):
            for c in item:
                walk(c)

    walk(nodes)
    assert hrefs == ["/guide", "/guide"]


def test_fenced_code_is_never_rewritten():
    md = "```\n![a](./diagram.png)\n[l](nope.md)\n```\n"
    nodes = parse_markdown(md, content_path="index.md", page_routes={})
    code = _first(nodes, "Code")
    assert "".join(code.children) == "![a](./diagram.png)\n[l](nope.md)"


# ---------------------------------------------------------------------------
# Wiring through discovery / synthesis
# ---------------------------------------------------------------------------


def test_synthesize_pages_builds_the_route_table_from_discovered_pages(tmp_path):
    _write(tmp_path, "content/index.md", "# Home\n\n[setup](docs/setup.md)\n")
    _write(tmp_path, "content/docs/setup.md", "---\nroute: /install\n---\n# S\n")
    pages = synthesize_pages(discover_content(tmp_path))
    # Stage M9 (docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md):
    # `pages["/"]`'s children now open with the automatic nav (itself
    # full of `Link`s, one per discovered page) and close with the
    # automatic footer -- skip past the nav to reach the body's own
    # markdown-resolved link, same as before this stage.
    body = pages["/"].children[1:]
    assert _first(body, "Link").props["href"] == "/install"


def test_synthesize_pages_rejects_a_link_to_a_draft(tmp_path):
    _write(tmp_path, "content/index.md", "# Home\n\n[wip](wip.md)\n")
    _write(tmp_path, "content/wip.md", "---\ndraft: true\n---\n# W\n")
    with pytest.raises(MarkdownReferenceError):
        synthesize_pages(discover_content(tmp_path))


# ---------------------------------------------------------------------------
# End to end: the existing asset_check / link_check judge Markdown refs
# ---------------------------------------------------------------------------


def _md_site(root: Path) -> Path:
    return _write(root, "site.py", EMPTY_SITE)


def test_present_image_resolves_and_copies_through_unchanged(tmp_path):
    site = _md_site(tmp_path)
    _write(tmp_path, "assets/diagram.png", PNG)
    _write(tmp_path, "content/index.md", "# Home\n\n![Diagram](./diagram.png)\n")
    out = tmp_path / "ARK"
    build(site, out)

    assert 'src="assets/diagram.png"' in (out / "index.html").read_text(encoding="utf-8")
    assert (out / "assets" / "diagram.png").read_bytes() == PNG


def test_image_on_a_nested_page_is_rewritten_relative_to_that_page(tmp_path):
    site = _md_site(tmp_path)
    _write(tmp_path, "assets/diagram.png", PNG)
    _write(tmp_path, "content/docs/setup.md", "# Setup\n\n![Diagram](diagram.png)\n")
    out = tmp_path / "ARK"
    build(site, out)

    html = (out / "docs" / "setup.html").read_text(encoding="utf-8")
    assert 'src="../assets/diagram.png"' in html
    assert (out / "assets" / "diagram.png").exists()


def test_missing_image_fails_the_build_with_the_asset_report(tmp_path, capsys):
    site = _md_site(tmp_path)
    _write(tmp_path, "assets/other.png", PNG)
    _write(tmp_path, "content/index.md", "# Home\n\n![Diagram](./diagram.png)\n")
    out = tmp_path / "ARK"
    with pytest.raises(CompileError, match="Asset check failed"):
        build(site, out)

    err = capsys.readouterr().err
    assert "ASSET CHECK FAILED" in err
    assert "[MISSING] assets/diagram.png" in err
    assert "'diagram.png' not found in assets/" in err
    assert "used by: / <Image src>" in err
    assert not out.exists()  # nothing written


def test_missing_image_report_has_the_same_shape_as_a_python_page(tmp_path, capsys):
    """The addendum's exit test: same diagnostic shape a Python-authored
    page already produces for the same missing file."""
    md_root = tmp_path / "md"
    md_root.mkdir()
    _write(md_root, "assets/other.png", PNG)
    _write(md_root, "content/index.md", "# Home\n\n![Diagram](./diagram.png)\n")
    with pytest.raises(CompileError):
        build(_md_site(md_root), md_root / "ARK")
    md_err = capsys.readouterr().err

    py_root = tmp_path / "py"
    py_root.mkdir()
    _write(py_root, "assets/other.png", PNG)
    _write(
        py_root,
        "site.py",
        '# include <stdlib.ARKlight>\n# include <markdown.ARKlight>\n\nsite = Site()\n\n@site.page("/")\ndef home():\n'
        '    return Page(Image(src="assets/diagram.png", alt="Diagram"))\n',
    )
    with pytest.raises(CompileError):
        build(py_root / "site.py", py_root / "ARK")
    py_err = capsys.readouterr().err

    def entry(report: str) -> list[str]:
        lines = report.splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("  [MISSING]"))
        return [line.strip() for line in lines[start : start + 3]]

    assert entry(md_err) == entry(py_err)


def test_wrong_case_image_name_is_reported_as_a_case_problem(tmp_path, capsys):
    site = _md_site(tmp_path)
    _write(tmp_path, "assets/Diagram.png", PNG)
    _write(tmp_path, "content/index.md", "# Home\n\n![d](diagram.png)\n")
    with pytest.raises(CompileError):
        build(site, tmp_path / "ARK")
    assert "[CASE] assets/diagram.png" in capsys.readouterr().err


def test_pdf_link_is_asset_checked_and_copied(tmp_path, capsys):
    site = _md_site(tmp_path)
    _write(tmp_path, "content/index.md", "# Home\n\n[Manual](manual.pdf)\n")
    with pytest.raises(CompileError):
        build(site, tmp_path / "ARK")
    assert "[MISSING] assets/manual.pdf" in capsys.readouterr().err

    _write(tmp_path, "assets/manual.pdf", b"%PDF-1.4")
    out = tmp_path / "ARK"
    build(site, out)
    assert 'href="assets/manual.pdf"' in (out / "index.html").read_text(encoding="utf-8")
    assert (out / "assets" / "manual.pdf").read_bytes() == b"%PDF-1.4"


def test_links_between_markdown_pages_build_and_honor_route_overrides(tmp_path):
    site = _md_site(tmp_path)
    _write(tmp_path, "content/index.md", "# Home\n\n[setup](docs/setup.md)\n")
    _write(tmp_path, "content/docs/setup.md", "---\nroute: /install\n---\n# S\n\n[home](../index.md)\n")
    out = tmp_path / "ARK"
    build(site, out)
    assert 'href="install.html"' in (out / "index.html").read_text(encoding="utf-8")
    assert 'href="index.html"' in (out / "install.html").read_text(encoding="utf-8")


def test_root_relative_typo_in_markdown_gets_the_same_link_report_as_python(tmp_path, capsys):
    site = _md_site(tmp_path)
    _write(tmp_path, "content/index.md", "# Home\n\n[x](/typo)\n")
    with pytest.raises(CompileError, match="Link check failed"):
        build(site, tmp_path / "ARK")
    err = capsys.readouterr().err
    assert "LINK CHECK FAILED" in err
    assert "[UNKNOWN-ROUTE] /typo" in err
    assert "used by: / <Link href>" in err


def test_link_to_a_draft_page_fails_the_build_naming_the_file(tmp_path):
    site = _md_site(tmp_path)
    _write(tmp_path, "content/index.md", "# Home\n\n[wip](wip.md)\n")
    _write(tmp_path, "content/wip.md", "---\ndraft: true\n---\n# W\n")
    with pytest.raises(CompileError, match=r"content/index\.md.*wip\.md"):
        build(site, tmp_path / "ARK")


def test_image_climbing_out_of_assets_fails_the_build_naming_the_file(tmp_path):
    site = _md_site(tmp_path)
    _write(tmp_path, "content/index.md", "# Home\n\n![x](../../secret.png)\n")
    with pytest.raises(CompileError, match=r"content/index\.md.*climbs out of assets/"):
        build(site, tmp_path / "ARK")


def test_external_references_pass_through_a_real_build(tmp_path):
    site = _md_site(tmp_path)
    _write(
        tmp_path,
        "content/index.md",
        "# Home\n\n![x](https://example.com/x.png)\n\n[e](https://example.com)\n",
    )
    out = tmp_path / "ARK"
    build(site, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'src="https://example.com/x.png"' in html
    assert 'href="https://example.com"' in html
