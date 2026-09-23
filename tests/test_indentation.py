import pytest

from arklight.parser.indentation import (
    BracketIndentationError,
    TreeNestingTooDeepError,
    check_bracket_nesting,
)
from arklight.parser.loader import SiteLoadError, load_site


def write_site(tmp_path, source: str):
    path = tmp_path / "site.py"
    path.write_text(source)
    return path


# ---------------------------------------------------------------------------
# check_bracket_nesting -- unit level
# ---------------------------------------------------------------------------


def test_properly_nested_call_is_untouched():
    source = (
        "foo(\n"
        "    1,\n"
        "    2,\n"
        ")\n"
    )
    check_bracket_nesting(source)  # no raise


def test_flat_continuation_line_raises():
    source = (
        "foo(\n"
        "1,\n"
        "2,\n"
        ")\n"
    )
    with pytest.raises(BracketIndentationError, match="line 1"):
        check_bracket_nesting(source, filename="site.py")


def test_continuation_indented_same_as_opener_raises():
    source = (
        "    foo(\n"
        "    1,\n"
        "    )\n"
    )
    with pytest.raises(BracketIndentationError):
        check_bracket_nesting(source)


def test_closing_line_alone_is_exempt_at_opener_indent():
    source = (
        "foo(\n"
        "    1,\n"
        "    2,\n"
        ")\n"
    )
    check_bracket_nesting(source)  # no raise: the lone `)` line is exempt


def test_nested_brackets_each_check_against_their_own_opener():
    source = (
        "foo(\n"
        "    bar(\n"
        "        1,\n"
        "    ),\n"
        "    2,\n"
        ")\n"
    )
    check_bracket_nesting(source)  # no raise


def test_inner_bracket_flat_against_its_own_opener_raises():
    source = (
        "foo(\n"
        "    bar(\n"
        "    1,\n"
        "    ),\n"
        ")\n"
    )
    with pytest.raises(BracketIndentationError, match="line 2"):
        check_bracket_nesting(source)


def test_single_line_call_is_never_flagged():
    check_bracket_nesting("foo(1, 2, 3)\n")


def test_list_and_dict_literals_are_covered_too():
    with pytest.raises(BracketIndentationError):
        check_bracket_nesting("data = [\n1,\n2,\n]\n")
    with pytest.raises(BracketIndentationError):
        check_bracket_nesting("data = {\n'a': 1,\n}\n")


def test_multiline_string_content_is_never_flagged():
    source = (
        "foo(\n"
        '    """\n'
        "not indented on purpose -- this is string content\n"
        '    """,\n'
        ")\n"
    )
    check_bracket_nesting(source)  # no raise


def test_unparseable_source_raises_nothing_here():
    # Genuine syntax errors are the loader's own ast.parse's job to
    # report; this check has nothing to add and must not mask that
    # error with an unrelated tokenizer failure.
    check_bracket_nesting("def broken(:\n")


# ---------------------------------------------------------------------------
# part 3 -- closing-only lines must be flush with their opener
# ---------------------------------------------------------------------------


def test_closing_line_flush_with_opener_passes():
    source = (
        "foo(\n"
        "    1,\n"
        ")\n"
    )
    check_bracket_nesting(source)  # no raise: flush, as before


def test_closing_line_indented_past_opener_raises():
    source = (
        "foo(\n"
        "    1,\n"
        "  )\n"  # 2, not 0 -- neither the opener's indent nor a mistake
                 # for continuation-line indent, just inconsistent
    )
    with pytest.raises(BracketIndentationError, match="site.py:3"):
        check_bracket_nesting(source, filename="site.py")


def test_closing_line_short_of_opener_raises():
    source = (
        "    foo(\n"
        "        1,\n"
        "    )\n"
    )
    check_bracket_nesting(source)  # flush at indent 4, still fine
    bad = (
        "    foo(\n"
        "        1,\n"
        "  )\n"
    )
    with pytest.raises(BracketIndentationError):
        check_bracket_nesting(bad)


def test_reported_regression_mismatched_container_closers_raises():
    # The exact shape reported against ARKlight's own component-tree
    # DSL: two sibling `container(...)` calls whose closing `)` isn't
    # flush with the `container(` that opened it (7 vs. 6, 7 vs. 5).
    # Part 2 exempted any closing-only line outright and let this
    # through; part 3 must not.
    source = (
        "page(\n"
        "       container(\n"
        "             1,\n"
        "      )\n"
        "\n"
        "      container(\n"
        "             2,\n"
        "     )\n"
        ")\n"
    )
    with pytest.raises(BracketIndentationError, match="site.py:4"):
        check_bracket_nesting(source, filename="site.py")


def test_nested_closers_on_one_line_only_checked_against_innermost():
    source = (
        "foo(\n"
        "    bar(\n"
        "        1,\n"
        "    ))\n"
    )
    check_bracket_nesting(source)  # no raise: "    ))" flush with `bar(`


def test_closing_line_with_trailing_sibling_code_still_exempt_from_flush():
    # A line that closes a bracket and then goes on to open the next
    # sibling ("), Container(") is not a bare "closing-only" line, so
    # the flush rule doesn't apply to it -- only the new bracket it
    # opens gets checked, same as any other opener.
    source = (
        "Row(Column(\n"
        "    Text('a'),\n"
        "), Column(\n"
        "    Text('b'),\n"
        "))\n"
    )
    check_bracket_nesting(source)  # no raise


# ---------------------------------------------------------------------------
# part 3 -- nesting depth is capped for readability
# ---------------------------------------------------------------------------


def _nested_source(depth: int) -> str:
    lines = [f"{'    ' * i}wrap(" for i in range(depth)]
    lines.append(f"{'    ' * depth}1,")
    for i in reversed(range(depth)):
        lines.append(f"{'    ' * i})")
    return "\n".join(lines) + "\n"


def test_nesting_within_default_max_depth_passes():
    check_bracket_nesting(_nested_source(8))  # no raise: exactly at the cap


def test_nesting_past_default_max_depth_raises():
    with pytest.raises(TreeNestingTooDeepError):
        check_bracket_nesting(_nested_source(9))


def test_too_deep_error_is_also_a_bracket_indentation_error():
    # So every existing `except BracketIndentationError` call site
    # keeps handling this without being touched.
    with pytest.raises(BracketIndentationError):
        check_bracket_nesting(_nested_source(9))


def test_custom_max_depth_is_respected():
    check_bracket_nesting(_nested_source(3), max_depth=3)  # no raise
    with pytest.raises(TreeNestingTooDeepError):
        check_bracket_nesting(_nested_source(4), max_depth=3)


def test_load_site_rejects_component_tree_nested_too_deeply(tmp_path):
    depth = 9  # one past DEFAULT_MAX_NESTING_DEPTH
    lines = [f"{'    ' * (i + 1)}Container(" for i in range(depth)]
    lines[0] = "    return Container("
    lines.append(f"{'    ' * (depth + 1)}Text('leaf'),")
    for i in reversed(range(depth)):
        lines.append(f"{'    ' * (i + 1)})")
    body = "\n".join(lines)
    source = (
        "# include <stdlib.ARKlight>\n"
        "site = Site()\n"
        "\n"
        "@site.page('/')\n"
        "def home():\n"
        f"{body}\n"
    )
    path = write_site(tmp_path, source)
    with pytest.raises(SiteLoadError):
        load_site(path)


# ---------------------------------------------------------------------------
# integration -- load_site surfaces the same diagnostic
# ---------------------------------------------------------------------------


def test_load_site_rejects_flat_component_tree(tmp_path):
    source = (
        "# include <stdlib.ARKlight>\n"
        "site = Site()\n"
        "\n"
        "@site.page('/')\n"
        "def home():\n"
        "    return Page(\n"
        "    Text('hi'),\n"
        "    )\n"
    )
    path = write_site(tmp_path, source)
    with pytest.raises(SiteLoadError):
        load_site(path)


def test_load_site_accepts_properly_nested_component_tree(tmp_path):
    source = (
        "# include <stdlib.ARKlight>\n"
        "site = Site()\n"
        "\n"
        "@site.page('/')\n"
        "def home():\n"
        "    return Page(\n"
        "        Text('hi'),\n"
        "    )\n"
    )
    path = write_site(tmp_path, source)
    site_obj, _discovered = load_site(path)
    assert site_obj.routes
