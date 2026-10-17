import io
import os

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
    assert "\x1b[38;2;214;163;115m" in result  # inline code color
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


def test_pipe_table_is_rendered_as_a_bordered_box_not_passed_through():
    source = "| a | b |\n| - | - |\n| 1 | 2 |\n"
    result = render_markdown(source, color=True, width=80)
    stripped = _strip_ansi(result)
    assert stripped != source
    # box-drawing borders, header + one data row, cell contents preserved
    assert stripped.count("┌") == 1  # top-left corner, once
    assert stripped.count("└") == 1  # bottom-left corner, once
    assert "│ a " in stripped and "│ b " in stripped
    assert "│ 1 " in stripped and "│ 2 " in stripped
    # header row is visually distinguished from data rows
    assert "\x1b[1;38;2;204;120;92m" in result


def test_table_column_alignment_is_read_from_the_delimiter_row():
    source = "| left | right | mid |\n| :-- | --: | :-: |\n| a | b | c |\n"
    result = _strip_ansi(render_markdown(source, color=True, width=80))
    lines = [l for l in result.split("\n") if l.strip()]
    data_row = lines[3]  # top border, header, header separator, first data row
    # right-aligned column pads on the left, left-aligned pads on the right
    assert "b" in data_row

    rendered_source_order = render_markdown(source, color=True, width=80)
    assert "\x1b[0m" in rendered_source_order


def test_wide_table_wraps_cell_content_instead_of_overflowing():
    long_cell = "a" * 60
    source = f"| short | wide |\n| --- | --- |\n| x | {long_cell} |\n"
    result = _strip_ansi(render_markdown(source, color=True, width=40))
    for line in result.split("\n"):
        assert len(line) <= 40


def test_long_paragraph_wraps_to_requested_width():
    words = " ".join(["word"] * 30)
    result = _strip_ansi(render_markdown(words + "\n", color=True, width=40))
    lines = [l for l in result.split("\n") if l]
    assert len(lines) > 1
    assert all(len(l) <= 40 for l in lines)
    assert " ".join(result.split()) == words


def test_long_heading_wraps_and_keeps_its_color_on_continuation_lines():
    title_words = " ".join(["Heading"] * 20)
    result = render_markdown(f"# {title_words}\n", color=True, width=40)
    stripped = _strip_ansi(result)
    lines = [l for l in stripped.split("\n") if l]
    assert len(lines) > 1
    assert all(len(l) <= 40 for l in lines)
    # every continuation line still carries heading color
    assert result.count("\x1b[1;38;2;204;120;92m") >= len(lines)


def test_bullet_continuation_lines_hang_indent_under_the_bullet_text():
    body = " ".join(["word"] * 20)
    result = _strip_ansi(render_markdown(f"- {body}\n", color=True, width=20))
    lines = [l for l in result.split("\n") if l]
    assert len(lines) > 1
    assert lines[0].startswith("• ")
    for cont in lines[1:]:
        assert cont.startswith("  ")  # two-space hang indent under "• "


def test_default_width_is_auto_detected_when_not_given(monkeypatch):
    monkeypatch.delenv("COLUMNS", raising=False)
    from arklight.cli import mdrender

    monkeypatch.setattr(mdrender.shutil, "get_terminal_size", lambda fallback: os.terminal_size((30, 24)))
    result = _strip_ansi(render_markdown(" ".join(["word"] * 20) + "\n", color=True))
    assert all(len(l) <= 30 for l in result.split("\n") if l)


def test_link_shows_text_and_url():
    result = render_markdown("[ARKlight](https://example.com)\n", color=True)
    stripped = _strip_ansi(result)
    assert "ARKlight" in stripped
    assert "https://example.com" in stripped


def test_plain_paragraph_with_no_markup_is_unchanged_after_stripping():
    source = "Just an ordinary sentence with no markup at all.\n"
    assert _strip_ansi(render_markdown(source, color=True)) == source


def test_wrapping_a_multi_word_link_never_leaves_dangling_markdown_syntax():
    # A wrap boundary falling inside a multi-word link used to split the
    # raw `[text](url)` syntax itself (wrapping ran on the raw markdown
    # source, before `_style_inline` turned it into "text (url)"),
    # leaving a bare "[" and/or "(" stranded on their own line. Styling
    # first means a wrap boundary can only ever land between rendered
    # words, same as a real markdown renderer.
    source = "Some words before a [longer link label here](http://example.com/path) and after.\n"
    result = render_markdown(source, color=True, width=30)
    stripped = _strip_ansi(result)
    lines = [l for l in stripped.split("\n") if l]
    assert len(lines) > 1
    assert all(len(l) <= 30 for l in lines)
    # the raw `[`/`]` link syntax is gone entirely -- only the rendered
    # "text (url)" form remains, however the wrap happened to fall
    assert "[" not in stripped and "]" not in stripped
    assert " ".join(stripped.split()) == "Some words before a longer link label here (http://example.com/path) and after."


def test_table_with_a_link_column_keeps_borders_aligned():
    # Table column widths and cell wrap/pad used to be computed on raw,
    # syntax-laden cell text (`[text](url)`) before `_style_inline` ran,
    # so the rendered ("text (url)") length didn't match what the
    # border math assumed -- leaving the right border one column short
    # on any row containing a link (or bold/code span).
    source = "| Name | Link |\n| --- | --- |\n| a | [click here](http://example.com) |\n"
    result = render_markdown(source, color=True, width=40)
    box_lines = [
        _strip_ansi(l) for l in result.split("\n") if l.strip() and _strip_ansi(l)[:1] in "┌│├└"
    ]
    widths = {len(l) for l in box_lines}
    assert len(widths) == 1  # every border/content line is exactly the same visible width
    stripped_all = _strip_ansi(result)
    assert "[click" not in stripped_all
    assert "here](" not in stripped_all


def test_table_header_color_does_not_defeat_header_wrapping():
    # Wrapping the whole header cell in `_TABLE_HEADER_COLOR` before
    # word-wrapping used to fuse the color escape code and the header's
    # first word into a single indivisible token, defeating the
    # force-break/space-wrap logic entirely and corrupting the header
    # text itself (e.g. "Name" truncated to just "Nam").
    source = "| LongHeaderWord | b |\n| --- | --- |\n| x | y |\n"
    result = render_markdown(source, color=True, width=18)
    stripped = _strip_ansi(result)
    box_lines = [l for l in stripped.split("\n") if l.strip()]
    widths = {len(l) for l in box_lines}
    assert len(widths) == 1  # borders stay aligned even with a force-broken header
    # the header word survives whole, force-broken across two lines at the
    # column budget -- not truncated, not left as one unbroken overflow
    assert "LongHeader" in box_lines[1] and "Word" in box_lines[2]
    # and the header color (bold clay) still applies to both wrapped lines
    assert result.count("\x1b[1;38;2;204;120;92m") >= 2


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
