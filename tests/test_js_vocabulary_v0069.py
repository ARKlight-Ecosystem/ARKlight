"""
Tests for `v0.069` -- JS vocabulary addendum, stage 9/10 (see
`docs/version history/v0.069.md`): the cross-language formatting/case
batteries (`Derive.to_ordinal`, `Derive.humanize_bytes`,
`Derive.humanize_duration`, `Derive.to_snake_case`,
`Derive.to_camel_case`, `Derive.to_kebab_case`, `Derive.to_title_case`).

Same shape as `tests/test_js_vocabulary_v0068.py`: API, registry, and
build-time initial values. The Node parity sweep at the bottom runs the
*shipped* JavaScript fragments and checks the Python build-time mirror
agrees with them on every sample, since that agreement is the whole
contract.
"""

import json
import shutil
import subprocess

import pytest

from arklight.api import Computed, Derive, Page, State
from arklight.ast.nodes import DerivationRef
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.ir import js_numeric, js_string
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import DERIVATION_REGISTRY, LITERAL_ARG_RULES
from arklight.ir.validate import ValidationError, validate_ark_ast

NEW_KINDS = (
    "to_ordinal", "humanize_bytes", "humanize_duration",
    "to_snake_case", "to_camel_case", "to_kebab_case", "to_title_case",
)
_NODE = shutil.which("node")


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _initial(derive, **state):
    tree = Page(
        *(State(name, value) for name, value in state.items()),
        Computed("out", deps=tuple(state), derive=derive),
    )
    return _ir({"/": tree}).pages[0].computed_initial["out"]


def _validate(derive):
    tree = Page(State("x", 1), Computed("out", deps=("x",), derive=derive))
    validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# API and registry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method",
    ["to_ordinal", "humanize_bytes", "humanize_duration",
     "to_snake_case", "to_camel_case", "to_kebab_case", "to_title_case"],
)
def test_derive_returns_a_single_name_derivation_ref(method):
    ref = getattr(Derive, method)("x")
    assert ref == DerivationRef(kind=method, names=("x",))


def test_registry_and_fragments_cover_every_v0069_kind():
    for kind in NEW_KINDS:
        assert kind in DERIVATION_REGISTRY
        assert kind in DERIVATION_FRAGMENTS
        assert DERIVATION_REGISTRY[kind].min_names == 1
        assert DERIVATION_REGISTRY[kind].max_names == 1
        assert kind not in LITERAL_ARG_RULES  # no literal arguments


def test_registry_and_fragment_keys_stay_in_lockstep():
    assert set(DERIVATION_REGISTRY) == set(DERIVATION_FRAGMENTS)


def test_the_case_and_formatting_kinds_take_exactly_one_name():
    for kind in NEW_KINDS:
        with pytest.raises(ValidationError):
            _validate(DerivationRef(kind=kind, names=("x", "x")))


def test_unexpected_arguments_are_rejected():
    for kind in NEW_KINDS:
        with pytest.raises(ValidationError):
            _validate(DerivationRef(kind=kind, names=("x",), args={"extra": 1}))


# ---------------------------------------------------------------------------
# Documented examples (build-time mirror)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (12, "12th"),
     (13, "13th"), (21, "21st"), (22, "22nd"), (23, "23rd"), (101, "101st"),
     (111, "111th"), (0, "0th"), (-1, "-1st"), (1.5, "1.5"), (float("inf"), "Infinity")],
)
def test_to_ordinal_suffixes(value, expected):
    assert js_numeric.js_to_ordinal(float(value)) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(0, "0 B"), (512, "512 B"), (1024, "1 KB"), (1536, "1.5 KB"),
     (1048576, "1 MB"), (1073741824, "1 GB"), (1048535, "1 MB"),
     (1099511627776, "1 TB"), (-2048, "-2 KB"), (float("inf"), "Infinity")],
)
def test_humanize_bytes_examples(value, expected):
    assert js_numeric.js_humanize_bytes(float(value)) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(0, "0s"), (0.9, "0s"), (45, "45s"), (59, "59s"), (60, "1m"), (90, "1m 30s"),
     (3600, "1h"), (8100, "2h 15m"), (86400, "1d"), (90061, "1d 1h"), (-8100, "-2h 15m")],
)
def test_humanize_duration_examples(value, expected):
    assert js_numeric.js_humanize_duration(float(value)) == expected


@pytest.mark.parametrize(
    "value, snake, camel, kebab, title",
    [
        ("HelloWorld", "hello_world", "helloWorld", "hello-world", "Hello World"),
        ("hello world", "hello_world", "helloWorld", "hello-world", "Hello World"),
        ("HTTPServer", "http_server", "httpServer", "http-server", "Http Server"),
        ("some-kebab_mix  here", "some_kebab_mix_here", "someKebabMixHere",
         "some-kebab-mix-here", "Some Kebab Mix Here"),
        ("hello_WORLD", "hello_world", "helloWorld", "hello-world", "Hello World"),
        ("", "", "", "", ""),
        ("   ", "", "", "", ""),
    ],
)
def test_case_converters_examples(value, snake, camel, kebab, title):
    assert js_string.js_to_snake_case(value) == snake
    assert js_string.js_to_camel_case(value) == camel
    assert js_string.js_to_kebab_case(value) == kebab
    assert js_string.js_to_title_case(value) == title


# ---------------------------------------------------------------------------
# Build-time initial values agree with the mirror
# ---------------------------------------------------------------------------


def test_build_time_initial_values_use_the_mirror():
    assert _initial(Derive.to_ordinal("x"), x=22) == "22nd"
    assert _initial(Derive.humanize_bytes("x"), x=1536) == "1.5 KB"
    assert _initial(Derive.humanize_duration("x"), x=8100) == "2h 15m"
    assert _initial(Derive.to_snake_case("x"), x="HTTPServer") == "http_server"
    assert _initial(Derive.to_camel_case("x"), x="hello_world") == "helloWorld"
    assert _initial(Derive.to_kebab_case("x"), x="HelloWorld") == "hello-world"
    assert _initial(Derive.to_title_case("x"), x="hello_WORLD") == "Hello World"


def test_build_time_ordinal_reads_strings_as_numbers():
    assert _initial(Derive.to_ordinal("x"), x="3") == "3rd"
    assert _initial(Derive.to_ordinal("x"), x="nope") == "0th"


def test_number_to_string_matches_javascript_for_whole_floats():
    # Regression: `js_numeric` used to carry its own `repr`-based copy,
    # which printed `45.0`. JavaScript's `String(45)` is `"45"`.
    assert js_numeric.js_to_ordinal(2.0) == "2nd"
    assert js_numeric.js_humanize_duration(45.0) == "45s"


# ---------------------------------------------------------------------------
# Node parity: run the shipped JS fragments and the Python mirror side by side
# ---------------------------------------------------------------------------

_NUMBER_INPUTS = [
    0, 1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101, 111, 112, 113, -1, -2, -11,
    1.5, "abc", "", "Infinity", "-Infinity", "1e21", "3", " 7 ", "-0", 0.5, 2**40,
]
_BYTE_INPUTS = [
    0, 1, 512, 1023, 1024, 1536, 1048535, 1048576, 1073741823, 1073741824,
    1e15, 1e30, "abc", "-2048", "Infinity", 0.5, 1023.95, 5 * 1024 + 300,
]
_DURATION_INPUTS = [
    0, "0.5", 1, 45, 59, 60, 90, 3600, 8100, 86399, 86400, 90061, "-8100",
    "Infinity", 1e10, "abc", 3599.9,
]
_CASE_INPUTS = [
    "", "hello world", "HelloWorld", "helloWorld", "HTTPServer", "iPhone15Pro",
    "XMLHttpRequest", "some_snake-kebab  mix", "  leading and trailing  ",
    "café au lait", "ÉCOLE normale", "über cool", "版本 v2", "a1b2c3", "ABc",
    "𝒜bc", "😀 emoji", "\ud83d lone", "ǅungla", "straße", "ΟΔΟΣ ΣΟΦΟΣ",
    "hello_world-2", "A", "v2Beta", "x", "ALLCAPS", "mIXed Case", "a.b.c",
    "one\ttwo\nthree", "snake_case_already", "kebab-case-already", "3D Model",
]

_PYTHON = {
    "to_ordinal": lambda v: js_numeric.js_to_ordinal(_to_number(v)),
    "humanize_bytes": lambda v: js_numeric.js_humanize_bytes(_to_number(v)),
    "humanize_duration": lambda v: js_numeric.js_humanize_duration(_to_number(v)),
    "to_snake_case": lambda v: js_string.js_to_snake_case(js_string.js_to_string(v)),
    "to_camel_case": lambda v: js_string.js_to_camel_case(js_string.js_to_string(v)),
    "to_kebab_case": lambda v: js_string.js_to_kebab_case(js_string.js_to_string(v)),
    "to_title_case": lambda v: js_string.js_to_title_case(js_string.js_to_string(v)),
}


def _to_number(value):
    """`Number(x) || 0`, mirroring `arklight.ir.build._coerce_number`."""
    from arklight.ir.build import _coerce_number

    return _coerce_number(value)


def _node_results(kind, values):
    frags = ",\n".join(DERIVATION_FRAGMENTS[k] for k in NEW_KINDS)
    script = (
        "const D = {\n" + frags + "\n};\n"
        f"const inputs = {json.dumps(values)};\n"
        f"console.log(JSON.stringify(inputs.map(v => D[{kind!r}]({{x: v}}, ['x'], {{}}))));\n"
    )
    out = subprocess.run([_NODE, "-"], input=script, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


_PARITY_CASES = [
    ("to_ordinal", _NUMBER_INPUTS),
    ("humanize_bytes", _BYTE_INPUTS),
    ("humanize_duration", _DURATION_INPUTS),
    ("to_snake_case", _CASE_INPUTS),
    ("to_camel_case", _CASE_INPUTS),
    ("to_kebab_case", _CASE_INPUTS),
    ("to_title_case", _CASE_INPUTS),
]


@pytest.mark.skipif(_NODE is None, reason="node is not installed")
@pytest.mark.parametrize("kind, inputs", _PARITY_CASES)
def test_python_mirror_matches_the_shipped_javascript(kind, inputs):
    js_out = _node_results(kind, inputs)
    py_out = [_PYTHON[kind](value) for value in inputs]
    assert py_out == js_out, [
        (value, py, js)
        for value, py, js in zip(inputs, py_out, js_out)
        if py != js
    ]


@pytest.mark.skipif(_NODE is None, reason="node is not installed")
def test_a_page_with_a_v0069_kind_ships_a_working_recompute_pass():
    from arklight.backend.js.render import JSBackend

    tree = Page(
        State("bytes", 2048),
        Computed("label", deps=("bytes",), derive=Derive.humanize_bytes("bytes")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "humanize_bytes: function" in js
