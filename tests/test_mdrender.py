import io

from arklight.cli.mdrender import render_markdown, resolve_color, supports_color


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------


def test_color_false_returns_text_completely_unchanged():
    source = "# Title\n\nSome **bold** and `code` and a [link](https://x.example).\n"
    assert render_markdown(source, color=False) == source


def test_heading_gets_bold_and_is_still_readable_as_plain_text():
    result = render_markdown("## Section Title\n", color=True)
    assert "\x1b[" in result
    assert "## Section Title" in _strip_ansi(result)


def test_bold_and_italic_and_inline_code_are_styled():
    result = render_markdown("Some **bold**, *italic*, and `code`.\n", color=True)
    assert "\x1b[1m" in result  # bold
    assert "\x1b[3m" in result  # italic
    assert "\x1b[38;5;180m" in result  # inline code color
    assert _strip_ansi(result) == "Some bold, italic, and code.\n"


def test_code_fence_content_is_not_treated_as_markdown():
    source = "```python\n**not bold**\n```\n"
    result = render_markdown(source, color=True)
    stripped = _strip_ansi(result)
    assert stripped == source
    # The fence content is styled as a block, but never inline-styled --
    # the literal "**not bold**" text must survive intact.
    assert "**not bold**" in result


def test_bullet_list_gets_a_bullet_glyph():
    result = render_markdown("- one\n- two\n", color=True)
    assert "\u2022" in result
    assert _strip_ansi(result) == "\u2022 one\n\u2022 two\n"


def test_numbered_list_keeps_its_own_numbers():
    result = render_markdown("1. first\n2. second\n", color=True)
    assert _strip_ansi(result) == "1. first\n2. second\n"


def test_blockquote_gets_a_bar():
    result = render_markdown("> quoted text\n", color=True)
    assert "\u2502" in result


def test_horizontal_rule_is_dimmed_not_rewritten():
    result = render_markdown("---\n", color=True)
    assert _strip_ansi(result) == "---\n"


def test_table_row_passes_through_unmatched_by_hrule_or_bullet():
    source = "| a | b |\n| - | - |\n| 1 | 2 |\n"
    result = render_markdown(source, color=True)
    assert _strip_ansi(result) == source


def test_link_shows_text_and_url():
    result = render_markdown("[ARKlight](https://example.com)\n", color=True)
    stripped = _strip_ansi(result)
    assert "ARKlight" in stripped
    assert "https://example.com" in stripped


def test_plain_paragraph_with_no_markup_is_unchanged_after_stripping():
    source = "Just an ordinary sentence with no markup at all.\n"
    assert _strip_ansi(render_markdown(source, color=True)) == source


# ---------------------------------------------------------------------------
# supports_color / resolve_color
# ---------------------------------------------------------------------------


def test_supports_color_false_for_non_tty_stream(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    assert supports_color(io.StringIO()) is False


def test_supports_color_true_when_stream_claims_a_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)

    class _FakeTTY(io.StringIO):
        def isatty(self):
            return True

    assert supports_color(_FakeTTY()) is True


def test_no_color_env_var_wins_even_on_a_tty(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)

    class _FakeTTY(io.StringIO):
        def isatty(self):
            return True

    assert supports_color(_FakeTTY()) is False


def test_force_color_wins_even_without_a_tty(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert supports_color(io.StringIO()) is True


def test_resolve_color_always_and_never_are_unconditional(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    assert resolve_color("always", stream=io.StringIO()) is True
    assert resolve_color("never", stream=io.StringIO()) is False


def test_resolve_color_auto_defers_to_supports_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert resolve_color("auto", stream=io.StringIO()) is False


def _strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)
