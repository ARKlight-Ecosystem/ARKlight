import pytest

from arklight.content.frontmatter import (
    FrontMatter,
    FrontMatterError,
    KNOWN_KEYS,
    parse_front_matter,
)


# ---------------------------------------------------------------------------
# No front matter -> all-defaults, source untouched
# ---------------------------------------------------------------------------


def test_no_front_matter_returns_defaults_and_unchanged_body():
    source = "# Getting Started\n\nSome text.\n"
    front_matter, body = parse_front_matter(source)
    assert front_matter == FrontMatter()
    assert front_matter.title is None
    assert front_matter.description is None
    assert front_matter.route is None
    assert front_matter.draft is False
    assert body == source


def test_empty_file_has_no_front_matter():
    front_matter, body = parse_front_matter("")
    assert front_matter == FrontMatter()
    assert body == ""


def test_dashes_not_on_first_line_are_not_front_matter():
    source = "Some text.\n---\ntitle: Nope\n---\n"
    front_matter, body = parse_front_matter(source)
    assert front_matter == FrontMatter()
    assert body == source


# ---------------------------------------------------------------------------
# A full block parses to a small dataclass
# ---------------------------------------------------------------------------


def test_full_front_matter_block_parses():
    source = (
        "---\n"
        "title: Getting Started\n"
        "description: How to start using ARKlight\n"
        "route: /guide\n"
        "draft: false\n"
        "---\n"
        "# Getting Started\n"
        "...\n"
    )
    front_matter, body = parse_front_matter(source, filename="content/guide.md")
    assert front_matter == FrontMatter(
        title="Getting Started",
        description="How to start using ARKlight",
        route="/guide",
        draft=False,
    )
    assert body == "# Getting Started\n...\n"


def test_draft_true_is_recognized():
    source = "---\ndraft: true\n---\nBody.\n"
    front_matter, _ = parse_front_matter(source)
    assert front_matter.draft is True


def test_draft_is_case_insensitive():
    source = "---\ndraft: True\n---\nBody.\n"
    front_matter, _ = parse_front_matter(source)
    assert front_matter.draft is True


def test_partial_front_matter_leaves_other_fields_default():
    source = "---\ntitle: Only A Title\n---\nBody.\n"
    front_matter, _ = parse_front_matter(source)
    assert front_matter == FrontMatter(title="Only A Title")


def test_empty_block_parses_to_defaults():
    source = "---\n---\nBody.\n"
    front_matter, body = parse_front_matter(source)
    assert front_matter == FrontMatter()
    assert body == "Body.\n"


def test_blank_lines_inside_block_are_ignored():
    source = "---\ntitle: With Gaps\n\n\nroute: /with-gaps\n---\nBody.\n"
    front_matter, _ = parse_front_matter(source)
    assert front_matter == FrontMatter(title="With Gaps", route="/with-gaps")


def test_quoted_values_are_unquoted():
    source = "---\ntitle: \"Quoted: Title\"\nroute: '/quoted'\n---\nBody.\n"
    front_matter, _ = parse_front_matter(source)
    assert front_matter.title == "Quoted: Title"
    assert front_matter.route == "/quoted"


def test_mismatched_quotes_are_left_alone():
    source = "---\ntitle: 'mismatched\"\n---\nBody.\n"
    front_matter, _ = parse_front_matter(source)
    assert front_matter.title == "'mismatched\""


def test_known_keys_is_exactly_the_closed_set():
    assert KNOWN_KEYS == {"title", "description", "route", "draft"}


# ---------------------------------------------------------------------------
# Malformed block -- unterminated fence
# ---------------------------------------------------------------------------


def test_unterminated_block_raises_naming_file():
    source = "---\ntitle: No Closing Fence\n"
    with pytest.raises(FrontMatterError, match=r"content/orphan\.md.*unterminated"):
        parse_front_matter(source, filename="content/orphan.md")


def test_unterminated_block_default_filename():
    with pytest.raises(FrontMatterError, match=r"<content>.*unterminated"):
        parse_front_matter("---\ntitle: X\n")


# ---------------------------------------------------------------------------
# Malformed block -- bad line shape
# ---------------------------------------------------------------------------


def test_line_without_colon_raises_with_line_number():
    source = "---\ntitle no colon here\n---\nBody.\n"
    with pytest.raises(FrontMatterError, match=r"content/bad\.md:2:"):
        parse_front_matter(source, filename="content/bad.md")


# ---------------------------------------------------------------------------
# Malformed block -- unrecognized key
# ---------------------------------------------------------------------------


def test_unrecognized_key_raises_naming_file_and_key():
    source = "---\nauthor: Someone\n---\nBody.\n"
    with pytest.raises(FrontMatterError, match=r"content/page\.md:2:.*'author'"):
        parse_front_matter(source, filename="content/page.md")


def test_unrecognized_key_error_lists_known_keys():
    source = "---\nbogus: 1\n---\nBody.\n"
    with pytest.raises(FrontMatterError, match=r"description.*draft.*route.*title"):
        parse_front_matter(source)


# ---------------------------------------------------------------------------
# Malformed block -- duplicate key
# ---------------------------------------------------------------------------


def test_duplicate_key_raises_naming_both_lines():
    source = "---\ntitle: First\ntitle: Second\n---\nBody.\n"
    with pytest.raises(FrontMatterError, match=r":3:.*'title'.*line 2"):
        parse_front_matter(source, filename="content/dup.md")


# ---------------------------------------------------------------------------
# Malformed block -- bad draft value
# ---------------------------------------------------------------------------


def test_bad_draft_value_raises_with_line_number():
    source = "---\ndraft: maybe\n---\nBody.\n"
    with pytest.raises(FrontMatterError, match=r"content/draft\.md:2:.*'draft'.*'maybe'"):
        parse_front_matter(source, filename="content/draft.md")


# ---------------------------------------------------------------------------
# Line numbers / body reconstruction
# ---------------------------------------------------------------------------


def test_body_preserves_content_after_closing_fence_exactly():
    source = "---\ntitle: X\n---\nLine one.\n\nLine two.\n"
    _, body = parse_front_matter(source)
    assert body == "Line one.\n\nLine two.\n"


def test_crlf_line_endings_are_handled():
    source = "---\r\ntitle: CRLF\r\n---\r\nBody.\r\n"
    front_matter, body = parse_front_matter(source)
    assert front_matter.title == "CRLF"
    assert body == "Body.\r\n"
