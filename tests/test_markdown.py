import pytest

from arklight.api import (
    Blockquote,
    Code,
    Container,
    Em,
    Heading,
    HorizontalRule,
    Image,
    Item,
    Link,
    List,
    OrderedList,
    Page,
    Pre,
    Strong,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeaderCell,
    TableRow,
    Text,
)
from arklight.backend.html.render import HTMLBackend
from arklight.content.markdown import MarkdownSyntaxError, parse_markdown
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast


def render(blocks, title="T"):
    """Run parsed blocks through the exact pipeline a Python-authored
    page already goes through: normalize -> validate -> build ->
    HTMLBackend. Mirrors tests/test_html_backend.py's own `render`
    helper."""
    pages = {"/": Page(*blocks, title=title)}
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    ir = build_website_ir("site", normalized)
    return HTMLBackend().render(ir)["index.html"]


# ---------------------------------------------------------------------------
# One construct at a time
# ---------------------------------------------------------------------------


def test_atx_headings_all_levels():
    for level in range(1, 7):
        blocks = parse_markdown(f"{'#' * level} Title {level}")
        assert blocks == [Heading(f"Title {level}", level=level)]


def test_plain_paragraph_is_a_single_text_node():
    blocks = parse_markdown("Just plain text.")
    assert blocks == [Text("Just plain text.")]


def test_paragraph_soft_wraps_continuation_lines():
    blocks = parse_markdown("Line one\nLine two\nLine three")
    assert blocks == [Text("Line one Line two Line three")]


def test_bold_only_paragraph_is_a_bare_strong_node():
    blocks = parse_markdown("**bold**")
    assert blocks == [Strong("bold")]


def test_italic_only_paragraph_star_and_underscore():
    assert parse_markdown("*italic*") == [Em("italic")]
    assert parse_markdown("_italic_") == [Em("italic")]


def test_inline_code_only_paragraph():
    assert parse_markdown("`code`") == [Code("code")]


def test_link_only_paragraph():
    blocks = parse_markdown("[ARKlight](https://example.com)")
    assert blocks == [Link("ARKlight", href="https://example.com")]


def test_mixed_inline_paragraph_wraps_in_container():
    blocks = parse_markdown("A **bold** and *italic* word.")
    assert blocks == [
        Container(
            Text("A "),
            Strong("bold"),
            Text(" and "),
            Em("italic"),
            Text(" word."),
        )
    ]


def test_bullet_list():
    blocks = parse_markdown("- one\n- two\n- three")
    assert blocks == [List(Item("one"), Item("two"), Item("three"))]


def test_bullet_list_markers_star_and_plus():
    assert parse_markdown("* a\n* b") == [List(Item("a"), Item("b"))]
    assert parse_markdown("+ a\n+ b") == [List(Item("a"), Item("b"))]


def test_numbered_list():
    blocks = parse_markdown("1. first\n2. second")
    assert blocks == [OrderedList(Item("first"), Item("second"))]


def test_list_item_inline_markup_is_flattened_to_plain_text():
    blocks = parse_markdown("- a **bold** item")
    assert blocks == [List(Item("a bold item"))]


def test_heading_inline_markup_is_flattened_to_plain_text():
    blocks = parse_markdown("# A **bold** heading")
    assert blocks == [Heading("A bold heading", level=1)]


def test_standalone_image():
    blocks = parse_markdown("![a diagram](diagram.png)")
    assert blocks == [Image(src="diagram.png", alt="a diagram")]


def test_fenced_code_block():
    blocks = parse_markdown("```\nline one\nline two\n```")
    assert blocks == [Pre(Code("line one\nline two"))]


def test_fenced_code_block_with_language_info_string():
    blocks = parse_markdown('```python\nprint("hi")\n```')
    assert blocks == [Pre(Code('print("hi")'))]


def test_fenced_code_block_content_is_not_inline_parsed():
    blocks = parse_markdown("```\n**not bold**\n```")
    assert blocks == [Pre(Code("**not bold**"))]


def test_blockquote():
    blocks = parse_markdown("> a quote")
    assert blocks == [Blockquote(Text("a quote"))]


def test_blockquote_joins_continuation_lines():
    blocks = parse_markdown("> line one\n> line two")
    assert blocks == [Blockquote(Text("line one line two"))]


def test_horizontal_rule():
    for rule in ("---", "***", "___"):
        assert parse_markdown(rule) == [HorizontalRule()]


def test_pipe_table():
    source = "| a | b |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"
    blocks = parse_markdown(source)
    assert blocks == [
        Table(
            TableHead(TableRow(TableHeaderCell(Text("a")), TableHeaderCell(Text("b")))),
            TableBody(
                TableRow(TableCell(Text("1")), TableCell(Text("2"))),
                TableRow(TableCell(Text("3")), TableCell(Text("4"))),
            ),
        )
    ]


def test_table_cell_inline_markup_becomes_real_nodes():
    source = "| a |\n| --- |\n| **bold** |"
    blocks = parse_markdown(source)
    assert blocks == [
        Table(
            TableHead(TableRow(TableHeaderCell(Text("a")))),
            TableBody(TableRow(TableCell(Strong("bold")))),
        )
    ]


# ---------------------------------------------------------------------------
# Unterminated fence
# ---------------------------------------------------------------------------


def test_unterminated_fence_raises_naming_file_and_line():
    with pytest.raises(MarkdownSyntaxError, match=r"content/broken\.md:1:.*unterminated"):
        parse_markdown("```\nnever closed", filename="content/broken.md")


# ---------------------------------------------------------------------------
# Exit test: one fixture exercising every construct in the mapping
# table round-trips through the real pipeline, and a raw HTML block
# renders as escaped text, never a live element.
# ---------------------------------------------------------------------------

FIXTURE = """\
# Getting Started

Welcome to **ARKlight** -- this paragraph has *italic*, `inline code`,
and a [link](https://arklight.example/docs) in it.

## Features

- Zero runtime dependencies
- Static output, every time
- Works without *any* JavaScript

## Steps

1. Install ARKlight
2. Run `arklight new`
3. Run `arklight build`

> Markdown is content, never executable source.

| Feature | Status |
| --- | :---: |
| Headings | done |
| **Tables** | done |

---

![ARKlight logo](logo.png)

```python
def hello():
    print("hi")
```

Raw HTML stays text: <script>alert('not live')</script>
"""


def test_fixture_round_trips_to_the_expected_ir_tree():
    blocks = parse_markdown(FIXTURE, filename="content/guide.md")
    assert blocks == [
        Heading("Getting Started", level=1),
        Container(
            Text("Welcome to "),
            Strong("ARKlight"),
            Text(" -- this paragraph has "),
            Em("italic"),
            Text(", "),
            Code("inline code"),
            Text(", and a "),
            Link("link", href="https://arklight.example/docs"),
            Text(" in it."),
        ),
        Heading("Features", level=2),
        List(
            Item("Zero runtime dependencies"),
            Item("Static output, every time"),
            Item("Works without any JavaScript"),
        ),
        Heading("Steps", level=2),
        OrderedList(
            Item("Install ARKlight"),
            Item("Run arklight new"),
            Item("Run arklight build"),
        ),
        Blockquote(Text("Markdown is content, never executable source.")),
        Table(
            TableHead(
                TableRow(TableHeaderCell(Text("Feature")), TableHeaderCell(Text("Status")))
            ),
            TableBody(
                TableRow(TableCell(Text("Headings")), TableCell(Text("done"))),
                TableRow(TableCell(Strong("Tables")), TableCell(Text("done"))),
            ),
        ),
        HorizontalRule(),
        Image(src="logo.png", alt="ARKlight logo"),
        Pre(Code('def hello():\n    print("hi")')),
        Text("Raw HTML stays text: <script>alert('not live')</script>"),
    ]


def test_fixture_builds_through_the_real_compiler_pipeline():
    blocks = parse_markdown(FIXTURE, filename="content/guide.md")
    # No second renderer: this is the exact normalize/validate/build/
    # HTMLBackend path a Python-authored page already goes through
    # (acceptance criterion 2 of the parent proposal).
    html = render(blocks, title="Getting Started")
    assert "<h1>Getting Started</h1>" in html
    assert "<h2>Features</h2>" in html
    assert "<strong>ARKlight</strong>" in html
    assert "<em>italic</em>" in html
    assert "<code>inline code</code>" in html
    assert '<a href="https://arklight.example/docs">link</a>' in html
    assert "<ul>" in html and "<li>Zero runtime dependencies</li>" in html
    assert "<ol>" in html and "<li>Install ARKlight</li>" in html
    assert "<blockquote>" in html
    assert "<table>" in html and "<th>" in html and "<td>" in html
    assert "<hr />" in html
    assert '<img src="logo.png" alt="ARKlight logo" />' in html
    assert '<pre><code>def hello():\n    print(&quot;hi&quot;)</code></pre>' in html


def test_raw_html_block_renders_as_escaped_text_never_a_live_element():
    blocks = parse_markdown(FIXTURE, filename="content/guide.md")
    html = render(blocks)
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert(&#x27;not live&#x27;)&lt;/script&gt;" in html
