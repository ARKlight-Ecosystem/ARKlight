"""`# define <name> -> <text>` -- C's `#define`: at compile time the left
name is replaced by the right-hand text. It is not an include (it binds
nothing) and not an alias between included objects (what it was in
0.06501)."""

import sys
import types

import pytest

from arklight.parser.loader import SiteLoadError, load_site
from arklight.parser.preamble import (
    Directive,
    PreambleCollisionError,
    PreambleError,
    apply_defines,
    normalize_preamble,
    parse_preamble,
    prepare_source,
    resolve_preamble,
    validate_preamble,
)


def _validated(source: str):
    normalized = normalize_preamble(parse_preamble(source), filename="t.py")
    validate_preamble(normalized)
    return normalized


def write_site(tmp_path, source: str):
    path = tmp_path / "site.py"
    path.write_text(source)
    return path


_TAIL = """
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi", level=LEVEL))
"""


# ---------------------------------------------------------------------------
# Parsing: the right side is whatever the rest of the line says
# ---------------------------------------------------------------------------


def test_define_is_parsed_with_its_text_verbatim():
    assert parse_preamble('# define GREETING -> "hello  world"\n') == [
        Directive("define", 1, name="GREETING", text='"hello  world"')
    ]


@pytest.mark.parametrize("text", ["3", "3.5", "True", '"a # b"', "Button", "len([1, 2])"])
def test_the_right_side_can_be_any_text(text):
    (directive,) = parse_preamble(f"# define X -> {text}\n")
    assert directive.text == text


def test_spacing_around_the_arrow_is_free():
    (directive,) = parse_preamble("#define   X->7\n")
    assert (directive.name, directive.text) == ("X", "7")


def test_a_comment_that_merely_mentions_define_is_just_a_comment():
    assert parse_preamble("# define the term -> later on\n") == []


def test_a_define_binds_nothing():
    assert resolve_preamble("# define LEVEL -> 3\nx = LEVEL\n") == {}


# ---------------------------------------------------------------------------
# Substitution: whole tokens of code, never strings or comments
# ---------------------------------------------------------------------------


def test_replaces_whole_names_only():
    out, n = apply_defines("Btn = 1\nBtn2 = Btn\nxBtn = Btn\n", {"Btn": "Button"})
    assert out == "Button = 1\nBtn2 = Button\nxBtn = Button\n"
    assert n == 3


def test_never_touches_strings_or_comments():
    src = 'x = "Btn"  # Btn\ny = Btn\nz = \'\'\'Btn\n Btn\'\'\'\n'
    out, n = apply_defines(src, {"Btn": "Button"})
    assert out == 'x = "Btn"  # Btn\ny = Button\nz = \'\'\'Btn\n Btn\'\'\'\n'
    assert n == 1


def test_never_touches_names_inside_fstrings_on_any_python():
    out, n = apply_defines('x = f"{Btn} and Btn"\ny = Btn\n', {"Btn": "Button"})
    assert out == 'x = f"{Btn} and Btn"\ny = Button\n'
    assert n == 1


def test_several_replacements_on_one_line_are_all_made():
    out, n = apply_defines("f(A, B, A)\n", {"A": "1", "B": "two_words"})
    assert out == "f(1, two_words, 1)\n"
    assert n == 3


def test_replaced_text_is_not_scanned_again():
    out, _ = apply_defines("x = A\n", {"A": "B", "B": "3"})
    assert out == "x = B\n"


def test_line_numbers_do_not_move():
    src = "a = 1\nb = A\n\nc = A\n"
    out, _ = apply_defines(src, {"A": "long_replacement_text"})
    assert out.count("\n") == src.count("\n")
    assert out.splitlines()[3] == "c = long_replacement_text"


def test_no_defines_means_the_source_is_returned_as_is():
    src = "x = 1\n"
    assert apply_defines(src, {}) == (src, 0)
    assert prepare_source(src).source == src


# ---------------------------------------------------------------------------
# Normalization records; validation raises
# ---------------------------------------------------------------------------


def test_normalization_collects_the_define_table():
    normalized = normalize_preamble(
        parse_preamble("# define A -> 1\n# define B -> two\n"), filename="t.py"
    )
    assert {k: (v.text, v.lineno) for k, v in normalized.defines.items()} == {
        "A": ("1", 1),
        "B": ("two", 2),
    }
    assert normalized.problems == []


@pytest.mark.parametrize("name", ["a-b", "1abc", "if", "None", "a.b"])
def test_left_side_must_be_a_replaceable_identifier(name):
    normalized = normalize_preamble(parse_preamble(f"# define {name} -> 1\n"), filename="t.py")
    assert normalized.defines == {}
    assert "single Python identifier" in str(normalized.problems[0])
    with pytest.raises(PreambleError, match="single Python identifier"):
        validate_preamble(normalized)


def test_empty_right_side_is_recorded_not_silently_a_comment():
    normalized = normalize_preamble(parse_preamble("# define X ->\n"), filename="t.py")
    assert "nothing on the right" in str(normalized.problems[0])


def test_two_defines_disagreeing_about_a_name_is_a_collision():
    with pytest.raises(PreambleCollisionError, match="already defined at line 1"):
        _validated("# define X -> 1\n# define X -> 2\n")


def test_repeating_the_same_define_is_harmless():
    assert list(_validated("# define X -> 1\n# define X -> 1\n").defines) == ["X"]


def test_a_define_may_not_take_the_name_of_included_vocabulary():
    with pytest.raises(PreambleError, match=r"`Button` is already provided by `# include <stdlib.ARKlight>`"):
        _validated("# define Button -> 5\n# include <stdlib.ARKlight>\n")


def test_order_of_define_and_include_does_not_matter_for_that_rule():
    with pytest.raises(PreambleError, match="already provided"):
        _validated("# include <stdlib.ARKlight>\n# define Button -> 5\n")


def test_a_define_mentioning_another_define_is_refused_not_half_expanded():
    with pytest.raises(PreambleError, match="mentions `B`, which is itself a `# define`"):
        _validated("# define A -> B + 1\n# define B -> 3\n")


def test_a_define_mentioning_a_name_inside_a_string_is_fine():
    _validated('# define A -> "B"\n# define B -> 3\n')


def test_a_define_text_that_will_not_tokenize_alone_is_left_to_the_parse_check():
    _validated("# define OPEN -> (\n")  # tokenizer error swallowed here


# ---------------------------------------------------------------------------
# The file must still parse afterwards, and the error says why
# ---------------------------------------------------------------------------


def test_a_define_that_breaks_the_file_names_the_defines_in_effect():
    src = "# define size -> 12\nf(size=1)\n"
    with pytest.raises(PreambleError) as excinfo:
        prepare_source(src, filename="t.py")
    message = str(excinfo.value)
    assert "no longer parses once its `# define`s are applied" in message
    assert "`size -> 12` (line 1)" in message
    assert "keyword-argument names included" in message


def test_a_file_that_was_already_broken_is_not_blamed_on_the_defines():
    broken = "# define A -> 1\nx = (\n"
    assert prepare_source(broken).source == broken  # the loader's parse reports it


# ---------------------------------------------------------------------------
# End to end through load_site
# ---------------------------------------------------------------------------


def test_load_site_applies_a_define(tmp_path):
    path = write_site(tmp_path, "# include <stdlib.ARKlight>\n# define LEVEL -> 3\n" + _TAIL)
    site, _ = load_site(path)
    assert site.routes["/"]().children[0].props == {"level": 3}


def test_discovery_and_execution_both_see_the_applied_source(tmp_path):
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\n"
        "# define SITE -> hub\n"
        "# define ROUTE -> \"/\"\n"
        "SITE = Site()\n\n"
        "@SITE.page(ROUTE)\n"
        "def home():\n"
        "    return Page(Heading('Hi'))\n",
    )
    site, discovered = load_site(path)
    assert discovered.variable_name == "hub"
    assert "/" in site.routes


def test_a_define_needs_no_include(tmp_path):
    # Nothing here binds vocabulary; the star import supplies it. The
    # define stands on its own.
    path = write_site(tmp_path, "# define LEVEL -> 2\nfrom arklight import *\n" + _TAIL)
    site, _ = load_site(path)
    assert site.routes["/"]().children[0].props == {"level": 2}


def test_a_define_that_breaks_the_site_surfaces_as_site_load_error(tmp_path):
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\n# define LEVEL -> +\n" + _TAIL,
    )
    with pytest.raises(SiteLoadError, match="no longer parses once its `# define`s are applied"):
        load_site(path)


def test_a_define_is_per_file_and_never_leaks_into_another_module(tmp_path):
    # If the site's `LEVEL -> 3` leaked into helper.py, its `LEVEL = 99`
    # would become `3 = 99`, a SyntaxError.
    (tmp_path / "helper.py").write_text("LEVEL = 99\nvalue = LEVEL\n")
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\n# define LEVEL -> 3\nimport helper\n"
        "site = Site()\n\n@site.page('/')\ndef home():\n"
        "    return Page(Heading('Hi', level=helper.value))\n",
    )
    site, _ = load_site(path)
    assert site.routes["/"]().children[0].props == {"level": 99}


def test_old_alias_style_define_is_now_plain_text_substitution(tmp_path, monkeypatch):
    fake = types.ModuleType("fake_acc_define_alias")
    fake.Widget = lambda *a, **k: None
    fake.__all__ = ["Widget"]
    monkeypatch.setitem(sys.modules, "fake_acc_define_alias", fake)
    src = "# include <acc.fake_acc_define_alias>\n# define W -> Widget\nx = W\n"
    prepared = prepare_source(src, filename="t.py")
    assert prepared.source.endswith("x = Widget\n")
    assert prepared.resolved.bindings["Widget"] is fake.Widget


# ---------------------------------------------------------------------------
# `# use` is reserved, not silently ignored
# ---------------------------------------------------------------------------


def test_use_is_reserved_and_refused_until_the_proposal_is_accepted():
    with pytest.raises(PreambleError, match=r"`# use <\.\.\.>` is reserved for a proposal"):
        resolve_preamble("# use <UI.ARKlight>\n", filename="t.py")


def test_use_after_the_first_statement_is_an_ordinary_comment():
    assert resolve_preamble("x = 1\n# use <UI.ARKlight>\n") == {}
