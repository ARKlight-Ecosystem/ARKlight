"""
Tests for `v0.065` -- JS vocabulary addendum, stage 5/10 (see
`docs/version history/v0.065.md`): the string derivations catalog
(`Derive.capitalize` ... `Derive.is_empty`, 18 kinds). Same shape as
`tests/test_js_vocabulary_v0064.py`: API, registry, validation,
build-time initial values, HTML pre-fill, JS shipping, and a Node parity
sweep -- the catalog's whole job is for the build-time mirror
(`arklight/ir/js_string.py`) to agree with the shipped JavaScript,
including where Python's `str` and JavaScript's strings differ (UTF-16
indexing, `String(x)` coercion, whitespace, `$`-patterns).
"""

import json
import re
import shutil
import subprocess

import pytest

from arklight.api import Bind, Computed, Derive, Page, Predicate, Show, State, Text
from arklight.ast.nodes import DerivationRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.backend.js.render import JSBackend
from arklight.ir import js_string
from arklight.ir.build import _evaluate_derivation, build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import DERIVATION_REGISTRY, LITERAL_ARG_RULES
from arklight.ir.validate import ValidationError, validate_ark_ast

NEW_KINDS = (
    "capitalize", "title_case", "trim_start", "trim_end", "pad_start", "pad_end",
    "repeat", "slice_string", "char_at", "replace_first", "replace_all",
    "split_count", "reverse_string", "string_length", "includes_substring",
    "starts_with", "ends_with", "is_empty",
)
BOOLEAN_KINDS = ("includes_substring", "starts_with", "ends_with", "is_empty")

# A valid literal-argument dict for every kind that takes any.
SAMPLE_ARGS = {
    "pad_start": {"length": 5, "fill": "0"},
    "pad_end": {"length": 5, "fill": "0"},
    "repeat": {"count": 2},
    "slice_string": {"start": 1, "end": None},
    "char_at": {"index": 0},
    "replace_first": {"search": "a", "replacement": "b"},
    "replace_all": {"search": "a", "replacement": "b"},
    "split_count": {"sep": ","},
    "includes_substring": {"substring": "a"},
    "starts_with": {"substring": "a"},
    "ends_with": {"substring": "a"},
}


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _initial(derive, value):
    """Build-time initial value of `Computed("out", derive=derive)` over one state `s`."""
    tree = Page(State("s", value), Computed("out", deps=("s",), derive=derive))
    return _ir({"/": tree}).pages[0].computed_initial["out"]


def _validate(derive):
    tree = Page(State("s", "x"), Computed("out", deps=("s",), derive=derive))
    validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ref,kind,args",
    [
        (Derive.capitalize("a"), "capitalize", {}),
        (Derive.title_case("a"), "title_case", {}),
        (Derive.trim_start("a"), "trim_start", {}),
        (Derive.trim_end("a"), "trim_end", {}),
        (Derive.pad_start("a", 3, "0"), "pad_start", {"length": 3, "fill": "0"}),
        (Derive.pad_start("a", 3), "pad_start", {"length": 3, "fill": " "}),
        (Derive.pad_end("a", 3, "-"), "pad_end", {"length": 3, "fill": "-"}),
        (Derive.repeat("a", 4), "repeat", {"count": 4}),
        (Derive.slice_string("a", 1, 3), "slice_string", {"start": 1, "end": 3}),
        (Derive.slice_string("a"), "slice_string", {"start": 0, "end": None}),
        (Derive.char_at("a", 2), "char_at", {"index": 2}),
        (Derive.replace_first("a", "x", "y"), "replace_first", {"search": "x", "replacement": "y"}),
        (Derive.replace_all("a", "x", "y"), "replace_all", {"search": "x", "replacement": "y"}),
        (Derive.split_count("a", ","), "split_count", {"sep": ","}),
        (Derive.reverse_string("a"), "reverse_string", {}),
        (Derive.string_length("a"), "string_length", {}),
        (Derive.includes_substring("a", "x"), "includes_substring", {"substring": "x"}),
        (Derive.starts_with("a", "x"), "starts_with", {"substring": "x"}),
        (Derive.ends_with("a", "x"), "ends_with", {"substring": "x"}),
        (Derive.is_empty("a"), "is_empty", {}),
    ],
)
def test_derive_returns_derivation_ref(ref, kind, args):
    assert ref == DerivationRef(kind=kind, names=("a",), args=args)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_and_fragments_cover_every_v0065_kind():
    for kind in NEW_KINDS:
        assert kind in DERIVATION_REGISTRY
        assert kind in DERIVATION_FRAGMENTS


def test_registry_and_fragment_keys_stay_in_lockstep():
    assert set(DERIVATION_REGISTRY) == set(DERIVATION_FRAGMENTS)


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_every_new_kind_reads_exactly_one_name(kind):
    spec = DERIVATION_REGISTRY[kind]
    assert (spec.min_names, spec.max_names) == (1, 1)


def test_every_literal_argument_of_the_new_kinds_has_a_validation_rule():
    # Guards the next contributor: an `extra_args` entry with no rule
    # would reach the browser unchecked.
    for kind in NEW_KINDS:
        assert set(DERIVATION_REGISTRY[kind].extra_args) == set(LITERAL_ARG_RULES.get(kind, {}))
        assert set(SAMPLE_ARGS.get(kind, {})) == set(DERIVATION_REGISTRY[kind].extra_args)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_sample_arguments_are_valid(kind):
    _validate(DerivationRef(kind=kind, names=("s",), args=SAMPLE_ARGS.get(kind, {})))


@pytest.mark.parametrize(
    "derive,message",
    [
        (Derive.pad_start("s", -1), r"from 0 to 1000"),
        (Derive.pad_start("s", 1001), r"from 0 to 1000"),
        (Derive.pad_end("s", 2.5), r"length=2\.5.*must be an integer\."),
        (Derive.pad_start("s", True), r"must be an integer\."),
        (Derive.pad_start("s", "3"), r"must be an integer\."),
        (Derive.pad_start("s", 3, 0), r"fill=0.*must be a string"),
        (Derive.pad_end("s", 3, None), r"must be a string"),
        (Derive.repeat("s", -1), r"count=-1.*from 0 to 1000"),
        (Derive.repeat("s", 1001), r"from 0 to 1000"),
        (Derive.slice_string("s", "1"), r"start='1'.*must be an integer\."),
        (Derive.slice_string("s", None), r"start=None.*must be an integer\."),
        (Derive.slice_string("s", 0, 2.5), r"end=2\.5.*must be an integer\."),
        (Derive.slice_string("s", 0, True), r"must be an integer\."),
        (Derive.char_at("s", -1), r"index=-1.*from 0 to"),
        (Derive.char_at("s", 1.0), r"must be an integer\."),
        (Derive.replace_first("s", "", "x"), r"search=''.*non-empty string"),
        (Derive.replace_all("s", "", "x"), r"non-empty string"),
        (Derive.replace_all("s", 5, "x"), r"search=5.*must be a string"),
        (Derive.replace_first("s", "a", None), r"replacement=None.*must be a string"),
        (Derive.split_count("s", ""), r"sep=''.*non-empty string"),
        (Derive.includes_substring("s", 5), r"substring=5.*must be a string"),
        (Derive.starts_with("s", None), r"must be a string"),
        (Derive.ends_with("s", ["a"]), r"must be a string"),
    ],
)
def test_bad_literal_arguments_are_build_errors(derive, message):
    with pytest.raises(ValidationError, match=message):
        _validate(derive)


@pytest.mark.parametrize(
    "derive",
    [
        Derive.pad_start("s", 0, ""),
        Derive.pad_start("s", 1000, "ab"),
        Derive.repeat("s", 0),
        Derive.repeat("s", 1000),
        Derive.slice_string("s", -5, -1),
        Derive.slice_string("s", 0, None),
        Derive.slice_string("s", 5, 2),
        Derive.char_at("s", 0),
        Derive.replace_all("s", "a", ""),
        Derive.includes_substring("s", ""),
        Derive.starts_with("s", ""),
    ],
)
def test_boundary_literal_arguments_are_accepted(derive):
    _validate(derive)


def test_missing_and_unexpected_arguments_are_rejected():
    with pytest.raises(ValidationError, match="missing required argument"):
        _validate(DerivationRef(kind="pad_start", names=("s",), args={"length": 3}))
    with pytest.raises(ValidationError, match="unexpected argument"):
        _validate(DerivationRef(kind="capitalize", names=("s",), args={"x": 1}))


def test_arity_and_deps_are_enforced():
    tree = Page(
        State("a", "x"), State("b", "y"),
        Computed("out", deps=("a", "b"), derive=DerivationRef(kind="capitalize", names=("a", "b"))),
    )
    with pytest.raises(ValidationError, match="needs exactly 1"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))
    tree = Page(State("a", "x"), Computed("out", deps=("a",), derive=Derive.capitalize("b")))
    with pytest.raises(ValidationError, match="isn't in this Computed"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# Build-time initial values -- exact expected results
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "derive,value,expected",
    [
        # capitalize / title_case: first code unit only, rest untouched
        (Derive.capitalize("s"), "hello world", "Hello world"),
        (Derive.capitalize("s"), "", ""),
        (Derive.capitalize("s"), "élan", "Élan"),
        (Derive.capitalize("s"), "ß", "SS"),
        (Derive.capitalize("s"), "  x", "  x"),
        (Derive.title_case("s"), "hello wORLD  foo", "Hello WORLD  Foo"),
        (Derive.title_case("s"), "  leading", "  Leading"),
        (Derive.title_case("s"), "tab\tsep\nnl", "Tab\tSep\nNl"),
        (Derive.title_case("s"), "a\u00a0b", "A\u00a0B"),
        # trims use JavaScript's whitespace set, not str.strip()'s
        (Derive.trim_start("s"), "  a b  ", "a b  "),
        (Derive.trim_end("s"), "  a b  ", "  a b"),
        (Derive.trim_start("s"), "\ufeff\u00a0\u2003x", "x"),
        (Derive.trim_end("s"), "x\u3000\u2028", "x"),
        (Derive.trim_start("s"), "\x1c\x85x", "\x1c\x85x"),  # not whitespace in JS
        (Derive.trim_end("s"), "x\x1f\x85", "x\x1f\x85"),
        # padding
        (Derive.pad_start("s", 3, "0"), "7", "007"),
        (Derive.pad_end("s", 4, "ab"), "7", "7aba"),
        (Derive.pad_start("s", 2), "abc", "abc"),
        (Derive.pad_start("s", 6, ""), "abc", "abc"),
        (Derive.pad_end("s", 6, "xy"), "abc", "abcxyx"),
        (Derive.pad_start("s", 4, "-"), "😀", "--😀"),  # 😀 is two UTF-16 units
        # repeat
        (Derive.repeat("s", 3), "ab", "ababab"),
        (Derive.repeat("s", 0), "ab", ""),
        # slice / char_at index UTF-16 code units
        (Derive.slice_string("s", 1, 3), "hello", "el"),
        (Derive.slice_string("s", -3), "hello", "llo"),
        (Derive.slice_string("s", 2), "hello", "llo"),
        (Derive.slice_string("s", 3, 1), "hello", ""),
        (Derive.slice_string("s", -100, 2), "hello", "he"),
        (Derive.slice_string("s", 0, -1), "hello", "hell"),
        (Derive.slice_string("s", 0, 0), "hello", ""),
        (Derive.slice_string("s", 0, 2), "😀a", "😀"),
        (Derive.slice_string("s", 0, 3), "😀a", "😀a"),
        (Derive.char_at("s", 1), "hello", "e"),
        (Derive.char_at("s", 10), "hello", ""),
        (Derive.char_at("s", 0), "😀", "\ud83d"),
        (Derive.char_at("s", 1), "😀", "\ude00"),
        # replace: literal text, never a pattern
        (Derive.replace_first("s", ".", "-"), "a.b.c", "a-b.c"),
        (Derive.replace_all("s", ".", "-"), "a.b.c", "a-b-c"),
        (Derive.replace_all("s", ".", "-"), "abc", "abc"),  # a regex `.` would give "---"
        (Derive.replace_all("s", "a|b", "-"), "a|b a b", "- a b"),
        (Derive.replace_all("s", "(", "["), "f(x)", "f[x)"),
        (Derive.replace_first("s", "a", "[$&]"), "cat", "c[$&]t"),
        (Derive.replace_all("s", "-", "$$"), "a-b-c", "a$$b$$c"),
        (Derive.replace_all("s", "b", "$1$`$'"), "abc", "a$1$`$'c"),
        (Derive.replace_all("s", "aa", "x"), "aaaaa", "xxa"),
        (Derive.replace_all("s", "a", ""), "banana", "bnn"),
        (Derive.replace_first("s", "z", "y"), "abc", "abc"),
        # split_count
        (Derive.split_count("s", ","), "a,b,c", 3),
        (Derive.split_count("s", ","), "", 1),
        (Derive.split_count("s", ","), ",", 2),
        (Derive.split_count("s", "aa"), "aaa", 2),
        (Derive.split_count("s", " "), "a  b", 3),
        # reverse: by code point
        (Derive.reverse_string("s"), "abc", "cba"),
        (Derive.reverse_string("s"), "a😀b", "b😀a"),
        (Derive.reverse_string("s"), "", ""),
        # length: UTF-16 code units
        (Derive.string_length("s"), "hello", 5),
        (Derive.string_length("s"), "😀", 2),
        (Derive.string_length("s"), "", 0),
        (Derive.string_length("s"), "é", 1),
        # coercion follows `String(x)`, not Python's `str(x)`
        (Derive.string_length("s"), 12345, 5),
        (Derive.string_length("s"), 1.5, 3),
        (Derive.string_length("s"), 5.0, 1),  # "5", not "5.0"
        (Derive.string_length("s"), True, 4),  # "true", not "True"
        (Derive.string_length("s"), None, 4),  # "null", not "None"
        (Derive.capitalize("s"), 1e21, "1e+21"),
        (Derive.capitalize("s"), 1e-7, "1e-7"),
        (Derive.capitalize("s"), False, "False"),
        (Derive.string_length("s"), [1, None, "ab"], 5),  # "1,,ab"
        (Derive.capitalize("s"), {"a": 1}, "[object Object]"),
        # predicates-as-derivations return real booleans
        (Derive.includes_substring("s", "ell"), "hello", True),
        (Derive.includes_substring("s", "xyz"), "hello", False),
        (Derive.includes_substring("s", ""), "hello", True),
        (Derive.starts_with("s", "he"), "hello", True),
        (Derive.starts_with("s", "lo"), "hello", False),
        (Derive.ends_with("s", "lo"), "hello", True),
        (Derive.ends_with("s", "he"), "hello", False),
        (Derive.includes_substring("s", "😀"), "a😀b", True),
        (Derive.is_empty("s"), "", True),
        (Derive.is_empty("s"), "x", False),
        (Derive.is_empty("s"), " ", False),
        (Derive.is_empty("s"), 0, False),
        (Derive.is_empty("s"), False, False),
        (Derive.is_empty("s"), None, False),
    ],
)
def test_ir_build_evaluates_initial_value(derive, value, expected):
    result = _initial(derive, value)
    assert result == expected
    assert type(result) is type(expected)


def test_slice_that_cuts_an_emoji_in_half_yields_a_lone_surrogate_like_javascript():
    assert _initial(Derive.slice_string("s", 0, 1), "😀") == "\ud83d"
    assert _initial(Derive.slice_string("s", 0, 2), "😀") == "😀"
    assert _initial(Derive.slice_string("s", 1), "😀") == "\ude00"


def test_state_is_read_through_derived_values_too():
    tree = Page(
        State("s", "  hello world  "),
        Computed("trimmed", deps=("s",), derive=Derive.trim_start("s")),
        Computed("title", deps=("trimmed",), derive=Derive.title_case("trimmed")),
        Computed("n", deps=("title",), derive=Derive.string_length("title")),
    )
    computed = _ir({"/": tree}).pages[0].computed_initial
    assert computed["title"] == "Hello World  "
    assert computed["n"] == 13


# ---------------------------------------------------------------------------
# js_string helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "number,text",
    [
        (5.0, "5"), (0.5, "0.5"), (100.0, "100"), (-0.0, "0"), (0.0, "0"), (-3.0, "-3"),
        (0.1 + 0.2, "0.30000000000000004"), (1e21, "1e+21"), (1e-7, "1e-7"),
        (1e-6, "0.000001"), (1.5e-7, "1.5e-7"), (123456789012345680000.0, "123456789012345680000"),
        (1.2345e25, "1.2345e+25"), (float("inf"), "Infinity"), (float("-inf"), "-Infinity"),
        (float("nan"), "NaN"),
    ],
)
def test_js_number_to_string_matches_ecmascript(number, text):
    assert js_string.js_number_to_string(number) == text


def test_js_to_string_of_integers_beyond_2_53_uses_number_formatting():
    assert js_string.js_to_string(2**53) == "9007199254740992"
    assert js_string.js_to_string(10**25) == "1e+25"
    assert js_string.js_to_string(-(10**25)) == "-1e+25"


@pytest.mark.parametrize("text", ["", "abc", "😀", "a😀b😀", "\ud83d", "\ude00", "\ud83d\ude00"])
def test_units_round_trip(text):
    normalized = js_string.from_units(js_string.to_units(text))
    assert js_string.to_units(normalized) == js_string.to_units(text)
    assert all(ord(c) < 0x10000 for c in js_string.to_units(text))


def test_adjacent_lone_surrogates_are_recombined_like_javascript():
    # In JavaScript "\ud83d\ude00" *is* the emoji; Python keeps two chars.
    assert js_string.js_length("\ud83d\ude00") == 2
    assert js_string.js_reverse("\ud83d\ude00") == "😀"


# ---------------------------------------------------------------------------
# HTML pre-fill
# ---------------------------------------------------------------------------


def test_html_prefill_spells_booleans_the_javascript_way():
    tree = Page(
        State("empty", ""), State("full", "abc"),
        Computed("a", deps=("empty",), derive=Derive.is_empty("empty")),
        Computed("b", deps=("full",), derive=Derive.is_empty("full")),
        Computed("c", deps=("full",), derive=Derive.starts_with("full", "ab")),
        Text(Bind("a")), Text(Bind("b")), Text(Bind("c")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))[
        "index.html"
    ]
    assert 'data-ark-bind="a">true<' in html
    assert 'data-ark-bind="b">false<' in html
    assert 'data-ark-bind="c">true<' in html


def test_html_prefill_of_an_existing_boolean_derivation_now_matches_the_client_too():
    tree = Page(
        State("a", 1), State("b", 2),
        Computed("gt", deps=("a", "b"), derive=Derive.compare("a", "b", "gt")),
        Text(Bind("gt")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-bind="gt">false<' in html


def test_html_prefill_of_a_lone_surrogate_does_not_crash_the_utf8_write():
    tree = Page(
        State("s", "😀"),
        Computed("half", deps=("s",), derive=Derive.char_at("s", 0)),
        Text(Bind("half")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-bind="half">\ufffd<' in html
    html.encode("utf-8")  # must not raise


def test_html_prefill_keeps_surrogate_halves_that_a_join_puts_back_together():
    # `char_at(0)` + `char_at(1)` of an emoji are two lone halves, but the
    # client's `join` recombines them into the emoji, so the pre-fill must too.
    tree = Page(
        State("s", "😀"),
        Computed("hi", deps=("s",), derive=Derive.char_at("s", 0)),
        Computed("lo", deps=("s",), derive=Derive.char_at("s", 1)),
        Computed("both", deps=("hi", "lo"), derive=Derive.join("hi", "lo", sep="")),
        Computed("swapped", deps=("hi", "lo"), derive=Derive.join("lo", "hi", sep="")),
        Text(Bind("both")), Text(Bind("swapped")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-bind="both">😀<' in html
    # Reversed, low half first: still two lone halves in JavaScript too.
    assert 'data-ark-bind="swapped">\ufffd\ufffd<' in html
    html.encode("utf-8")  # must not raise


def test_html_prefill_of_a_new_derivation_and_a_boolean_show_guard():
    tree = Page(
        State("q", ""),
        Computed("blank", deps=("q",), derive=Derive.is_empty("q")),
        Show(Predicate.truthy("blank"), Text("Type something")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    i = html.index("data-ark-show")
    assert "hidden" not in html[i : i + 120]

    tree = Page(
        State("q", "x"),
        Computed("blank", deps=("q",), derive=Derive.is_empty("q")),
        Show(Predicate.truthy("blank"), Text("Type something")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    i = html.index("data-ark-show")
    assert " hidden" in html[i : i + 200]


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_js_render_ships_only_the_used_new_derivation_kind(kind):
    tree = Page(
        State("a", "hello"),
        Computed(
            "result", deps=("a",),
            derive=DerivationRef(kind=kind, names=("a",), args=SAMPLE_ARGS.get(kind, {})),
        ),
        Text(Bind("result")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert re.search(rf"\b{kind}: function", js)
    for other in DERIVATION_REGISTRY:
        if other != kind:
            assert not re.search(rf"\b{other}: function", js), other


def test_new_fragments_use_no_eval_or_new_function_or_regexp():
    for kind in NEW_KINDS:
        fragment = DERIVATION_FRAGMENTS[kind]
        assert "eval(" not in fragment
        assert "new Function" not in fragment
        assert "RegExp" not in fragment


def test_only_title_case_contains_a_regex_and_it_is_a_fixed_literal():
    with_regex = [k for k in NEW_KINDS if re.search(r"/[^/\n]+/[gimsuy]*[.,;)]", DERIVATION_FRAGMENTS[k])]
    assert with_regex == ["title_case"]
    assert "args" not in re.search(r"replace\((/.*?/g)", DERIVATION_FRAGMENTS["title_case"]).group(1)


def test_replace_fragments_treat_search_and_replacement_as_plain_text():
    first = DERIVATION_FRAGMENTS["replace_first"]
    # The replacement is returned from a function, so `$&`/`$1` aren't expanded.
    assert re.search(r"replace\(args\.search,\s*function\s*\(\)\s*\{\s*return args\.replacement;", first)
    every = DERIVATION_FRAGMENTS["replace_all"]
    assert "split(args.search).join(args.replacement)" in every
    assert "replaceAll" not in every


# ---------------------------------------------------------------------------
# Node parity: the build-time mirror agrees with the shipped fragments
# ---------------------------------------------------------------------------

_NODE = shutil.which("node")

_STRING_INPUTS = [
    "", " ", "a", "hello world", "HELLO", "Hello World", "  padded  ", "a  b   c", "hello wORLD",
    "The Quick brown-fox_jumps\tover\nthe lazy dog", "a.b.c", "aaaa", "banana", "$&$1$$",
    "😀", "a😀b", "😀😀", "😀 x 😀", "é", "ß", "ǆ", "ﬁ", "İ", "ﬃ ǆ",
    "\ufeffx\u00a0", "\u2003\u3000y\u2028", "\x1cx\x1f", "\x85 x \x85", "\u180ex\u200b", "\ud83d", "\ude00", "x\ud83d",
    "tab\tsep\nnl\r\nend", "a,b,,c,", "one two  three ", "0", "-5", "Zoë 😀 ünï",
]
_OTHER_STATE_VALUES = [
    0, 1, -1, 42, 5.0, 0.5, 100.0, -0.0, 0.1 + 0.2, 1e21, 1e-7, 1.5e-6, 123456789012345680000.0,
    10**25, 2**53, float("inf"), float("-inf"), float("nan"), True, False, None,
    [], [1, 2], [1, None, "a"], ["x", ["y", "z"]], {"a": 1},
]
_PAD_ARGS = [(0, " "), (1, "x"), (5, "0"), (5, "ab"), (8, "xyz"), (5, ""), (4, "😀"), (5, "\ud83d"), (20, "-=")]
_SLICES = [(0, None), (1, None), (-2, None), (2, 4), (-3, -1), (5, 2), (100, None), (0, 0), (-100, 3), (0, 1), (1, 2), (0, -1), (3, -100)]
_SEARCHES = ["a", "aa", "x", "o", " ", ".", "😀", "\ud83d", "\ude00", "$", "an", "b", "l", "\t", "é"]
_REPLACEMENTS = ["", "-", "$&", "$1", "$$", "$`", "$'", "[$&]", "😀", "\ud83d", "aa"]
_NEEDLES = ["", "a", "he", "d", "lo", "😀", "\ud83d", "\ude00", "é", " ", "Hello"]
_SEPS = [" ", "a", "aa", ",", "😀", "\ud83d", "x", "\t", "an"]


def _parity_cases():
    cases = []
    text_inputs = _STRING_INPUTS + _OTHER_STATE_VALUES
    for kind in ("capitalize", "title_case", "trim_start", "trim_end", "reverse_string", "string_length", "is_empty"):
        cases += [(kind, value, {}) for value in text_inputs]
    for value in _STRING_INPUTS:
        for length, fill in _PAD_ARGS:
            cases.append(("pad_start", value, {"length": length, "fill": fill}))
            cases.append(("pad_end", value, {"length": length, "fill": fill}))
        for count in (0, 1, 3):
            cases.append(("repeat", value, {"count": count}))
        for start, end in _SLICES:
            cases.append(("slice_string", value, {"start": start, "end": end}))
        for index in (0, 1, 2, 3, 5, 100):
            cases.append(("char_at", value, {"index": index}))
        for search in _SEARCHES:
            cases.append(("split_count", value, {"sep": search}))
            for replacement in _REPLACEMENTS:
                cases.append(("replace_first", value, {"search": search, "replacement": replacement}))
                cases.append(("replace_all", value, {"search": search, "replacement": replacement}))
        for needle in _NEEDLES:
            for kind in ("includes_substring", "starts_with", "ends_with"):
                cases.append((kind, value, {"substring": needle}))
    for value in _OTHER_STATE_VALUES:
        cases.append(("slice_string", value, {"start": 1, "end": None}))
        cases.append(("pad_start", value, {"length": 6, "fill": "0"}))
        cases.append(("includes_substring", value, {"substring": "1"}))
        cases.append(("split_count", value, {"sep": ","}))
        cases.append(("char_at", value, {"index": 0}))
    return cases


@pytest.mark.skipif(_NODE is None, reason="node not available in this environment")
def test_node_recompute_matches_build_time_initial_value_across_the_catalog():
    cases = _parity_cases()
    assert len(cases) > 15000
    fragments = ",\n".join(DERIVATION_FRAGMENTS[kind] for kind in NEW_KINDS)
    script = f"""
    var derivations = {{
{fragments}
    }};
    var cases = {json.dumps(cases)};
    console.log(JSON.stringify(cases.map(function (c) {{
      var state = {{ n0: c[1] }};
      return derivations[c[0]](state, ["n0"], c[2]);
    }})));
    """
    # Via stdin: the case list is far past the command-line length limit.
    node_out = json.loads(
        subprocess.run(
            [_NODE, "-"], input=script, capture_output=True, text=True, encoding="utf-8", check=True
        ).stdout
    )
    assert len(node_out) == len(cases)

    mismatches = []
    for (kind, value, args), from_js in zip(cases, node_out):
        built = _evaluate_derivation(
            {"kind": kind, "names": ["n0"], "args": args}, get={"n0": value}.__getitem__
        )
        if type(built) is not type(from_js) or built != from_js:
            mismatches.append((kind, value, args, built, from_js))
    assert not mismatches, mismatches[:10]
