"""
Stage M6 of the Markdown-as-first-class-content landing order (see
`docs/Foundational/DESIGN-NOTES.md`'s "Design record: Markdown as
first-class content"): style hooks on
Markdown-sourced IR nodes, and the default stylesheet that styles
them. Companion to `tests/test_markdown.py` (Stage M2, untouched by
this stage -- every assertion there keeps using a bare `parse_markdown(
...)` call, which still returns the exact Stage M2-M4 tree with no
`class_name`/`id` added, by design: see `style_hooks`'s docstring in
`arklight.content.markdown`).
"""

from pathlib import Path

import pytest

from arklight.api import DuplicateStyleNameError, Page, RESERVED_UTILITY_CLASSES, Site, Text
from arklight.backend.css.markdown_defaults import HOOK_CLASS_NAMES, MARKDOWN_CSS_BODY
from arklight.backend.css.render import CSSBackend, STYLESHEET_PATH
from arklight.backend.html.render import HTMLBackend
from arklight.content.discovery import discover_content, synthesize_page
from arklight.content.markdown import parse_markdown
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast


def render(blocks, title="T"):
    """Same helper as tests/test_markdown.py: the real
    normalize -> validate -> build -> HTMLBackend pipeline."""
    pages = {"/": Page(*blocks, title=title)}
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    ir = build_website_ir("site", normalized)
    return HTMLBackend().render(ir)["index.html"]


# ---------------------------------------------------------------------------
# style_hooks defaults to False -- Stage M2-M4 callers see no change at all
# ---------------------------------------------------------------------------


def test_style_hooks_default_is_off():
    from arklight.api import Heading

    blocks = parse_markdown("# Title")
    assert blocks == [Heading("Title", level=1)]
    assert "class_name" not in blocks[0].props
    assert "id" not in blocks[0].props


# ---------------------------------------------------------------------------
# style_hooks=True -- one construct at a time
# ---------------------------------------------------------------------------


def test_heading_gets_level_class_and_slugged_id():
    blocks = parse_markdown("## Getting Started!", style_hooks=True)
    assert blocks[0].props["class_name"] == "ark-md-h2"
    assert blocks[0].props["id"] == "getting-started"


def test_duplicate_heading_text_gets_a_unique_id():
    blocks = parse_markdown("# Setup\n\n## Setup", style_hooks=True)
    ids = [b.props["id"] for b in blocks if b.type == "Heading"]
    assert ids == ["setup", "setup-2"]


def test_single_run_paragraph_gets_paragraph_class():
    blocks = parse_markdown("Just plain text.", style_hooks=True)
    assert blocks[0].type == "Text"
    assert blocks[0].props["class_name"] == "ark-md-p"


def test_multi_run_paragraph_container_gets_paragraph_class():
    blocks = parse_markdown("Some **bold** text.", style_hooks=True)
    assert blocks[0].type == "Container"
    assert blocks[0].props["class_name"] == "ark-md-p"
    # Inline runs inside the paragraph are NOT individually classed --
    # default styling reaches them via a descendant selector off
    # .ark-md-p instead (see markdown_defaults.py).
    for child in blocks[0].children:
        assert "class_name" not in child.props


def test_whole_paragraph_collapsed_to_bare_inline_node_gets_its_own_class():
    assert parse_markdown("**bold**", style_hooks=True)[0].props["class_name"] == "ark-md-strong"
    assert parse_markdown("*italic*", style_hooks=True)[0].props["class_name"] == "ark-md-em"
    assert parse_markdown("`code`", style_hooks=True)[0].props["class_name"] == "ark-md-code"
    assert (
        parse_markdown("[x](/y)", style_hooks=True)[0].props["class_name"] == "ark-md-link"
    )


def test_list_and_items_get_classes():
    blocks = parse_markdown("- a\n- b", style_hooks=True)
    assert blocks[0].props["class_name"] == "ark-md-list"
    assert all(item.props["class_name"] == "ark-md-item" for item in blocks[0].children)


def test_ordered_list_and_items_get_classes():
    blocks = parse_markdown("1. a\n2. b", style_hooks=True)
    assert blocks[0].props["class_name"] == "ark-md-ordered-list"
    assert all(item.props["class_name"] == "ark-md-item" for item in blocks[0].children)


def test_fenced_code_block_gets_pre_and_code_block_classes():
    blocks = parse_markdown("```\nx = 1\n```", style_hooks=True)
    assert blocks[0].type == "Pre"
    assert blocks[0].props["class_name"] == "ark-md-pre"
    assert blocks[0].children[0].props["class_name"] == "ark-md-code-block"


def test_blockquote_hr_and_image_get_classes():
    blocks = parse_markdown("> a quote\n\n---\n\n![alt](./x.png)", style_hooks=True)
    assert blocks[0].props["class_name"] == "ark-md-blockquote"
    assert blocks[1].props["class_name"] == "ark-md-hr"
    assert blocks[2].props["class_name"] == "ark-md-img"


def test_table_family_gets_classes():
    blocks = parse_markdown(
        "| a | b |\n| - | - |\n| 1 | 2 |",
        style_hooks=True,
    )
    table = blocks[0]
    assert table.props["class_name"] == "ark-md-table"
    thead, tbody = table.children
    assert thead.props["class_name"] == "ark-md-thead"
    assert tbody.props["class_name"] == "ark-md-tbody"
    assert thead.children[0].props["class_name"] == "ark-md-tr"
    assert thead.children[0].children[0].props["class_name"] == "ark-md-th"
    assert tbody.children[0].children[0].props["class_name"] == "ark-md-td"


def test_hooked_fixture_renders_hook_classes_into_real_html():
    blocks = parse_markdown("## Hello There\n\nSome text.", style_hooks=True)
    html = render(blocks)
    assert 'class="ark-md-h2"' in html
    assert 'id="hello-there"' in html
    assert 'class="ark-md-p"' in html


# ---------------------------------------------------------------------------
# discovery.synthesize_page: hooks apply automatically, no opt-in
# ---------------------------------------------------------------------------


def test_synthesize_page_applies_style_hooks_automatically(tmp_path: Path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "guide.md").write_text("# Guide\n\nBody text.\n", encoding="utf-8")

    [page] = discover_content(tmp_path)
    node = synthesize_page(page)

    heading = node.children[0]
    assert heading.props["class_name"] == "ark-md-h1"
    assert heading.props["id"] == "guide"


# ---------------------------------------------------------------------------
# Default stylesheet + RESERVED_UTILITY_CLASSES protection
# ---------------------------------------------------------------------------


def test_css_backend_always_includes_markdown_defaults():
    pages = {"/": Page(Text("hi"))}
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    ir = build_website_ir("site", normalized)

    css = CSSBackend().render(ir)[STYLESHEET_PATH]

    assert ".ark-md-h1" in css
    assert ".ark-md-table" in css


def test_markdown_hook_classes_are_reserved():
    assert "ark-md-h1" in RESERVED_UTILITY_CLASSES
    assert HOOK_CLASS_NAMES <= RESERVED_UTILITY_CLASSES


def test_site_style_refuses_to_collide_with_a_markdown_hook_class():
    site = Site()
    with pytest.raises(DuplicateStyleNameError):
        site.style("ark-md-h1", {"color": "red"})
    # The documented escape hatch still works.
    site.style("ark-md-h1", {"color": "red"}, allow_redefine=True)
    assert "ark-md-h1" in site.custom_styles


def test_markdown_css_body_has_no_id_selectors():
    # arklight.backend.css.selectors has no `#id` selector support at
    # all (see markdown_defaults.py's module docstring) -- confirm the
    # shipped default stylesheet never relies on one. The default
    # stylesheet does use `#` for hex colors (e.g. `#cc785c`), so this
    # checks for an actual `#name {`-shaped selector, not a bare `#`.
    import re

    assert re.search(r"#[a-zA-Z][\w-]*\s*\{", MARKDOWN_CSS_BODY) is None
