import pytest

from arklight.parser.indentation import BracketIndentationError, check_bracket_nesting
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
