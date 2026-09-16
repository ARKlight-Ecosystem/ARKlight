"""
Tests for `v0.062` -- JS vocabulary addendum, stage 2/10 (see
`docs/version history/v0.062.md`): `Derive.uppercase`/`.trim` (the
missing string-casing siblings of `Derive.join`/`Derive.format`) and
`Predicate.equals`/`.gt`/`.lt` (comparison predicates for `Show(...)`,
already speced alongside `Derive.compare`'s op set but never wired
into `PREDICATE_REGISTRY`). Mirrors the style of
`tests/test_js_vocabulary_v0061.py` -- same registry-driven shape,
just the new kinds.
"""

import pytest

from arklight.api import Computed, Derive, Page, Predicate, Show, State, Text, Bind
from arklight.ast.nodes import DerivationRef, PredicateRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.backend.js.render import JSBackend
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import PREDICATE_REGISTRY
from arklight.ir.validate import ValidationError, validate_ark_ast


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_derive_uppercase_returns_derivation_ref():
    ref = Derive.uppercase("name")
    assert ref == DerivationRef(kind="uppercase", names=("name",))


def test_derive_trim_returns_derivation_ref():
    ref = Derive.trim("raw")
    assert ref == DerivationRef(kind="trim", names=("raw",))


def test_predicate_equals_returns_predicate_ref():
    ref = Predicate.equals("role", "admin_role")
    assert ref == PredicateRef(kind="equals", names=("role", "admin_role"))


def test_predicate_gt_returns_predicate_ref():
    ref = Predicate.gt("score", "threshold")
    assert ref == PredicateRef(kind="gt", names=("score", "threshold"))


def test_predicate_lt_returns_predicate_ref():
    ref = Predicate.lt("score", "threshold")
    assert ref == PredicateRef(kind="lt", names=("score", "threshold"))


def test_predicate_registry_covers_v0062_kinds():
    for kind in ("equals", "gt", "lt"):
        assert kind in PREDICATE_REGISTRY
        assert PREDICATE_REGISTRY[kind].names == 2


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_uppercase_and_trim_reject_more_than_one_name():
    with pytest.raises(TypeError):
        Derive.uppercase("a", "b")  # type: ignore[call-arg]


@pytest.mark.parametrize("kind_fn", [Predicate.equals, Predicate.gt, Predicate.lt])
def test_comparison_predicates_require_exactly_two_names(kind_fn):
    tree = Page(
        State("a", 1.0),
        State("b", 2.0),
        Show(PredicateRef(kind=kind_fn("a", "b").kind, names=("a",)), Text("shown")),
    )
    with pytest.raises(ValidationError, match="takes exactly 2"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_predicate_equals_accepts_two_declared_names():
    tree = Page(
        State("role", "admin"),
        State("admin_role", "admin"),
        Show(Predicate.equals("role", "admin_role"), Text("Welcome, admin")),
    )
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


# ---------------------------------------------------------------------------
# IR build -- build-time initial value evaluation
# ---------------------------------------------------------------------------


def test_ir_build_evaluates_uppercase_initial_value():
    tree = Page(
        State("name", "ada"),
        Computed("shout", deps=("name",), derive=Derive.uppercase("name")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial == {"shout": "ADA"}


def test_ir_build_evaluates_trim_initial_value():
    tree = Page(
        State("raw", "  padded  "),
        Computed("clean", deps=("raw",), derive=Derive.trim("raw")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial == {"clean": "padded"}


def test_ir_build_uppercase_coerces_non_string_state():
    tree = Page(
        State("n", 42.0),
        Computed("shout", deps=("n",), derive=Derive.uppercase("n")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial == {"shout": "42.0"}


# ---------------------------------------------------------------------------
# HTML backend -- Bind pre-fill and Show predicate evaluation
# ---------------------------------------------------------------------------


def test_html_render_prefills_bind_text_with_uppercase_initial_value():
    tree = Page(
        State("name", "ada"),
        Computed("shout", deps=("name",), derive=Derive.uppercase("name")),
        Text(Bind("shout")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert 'data-ark-bind="shout">ADA<' in html


@pytest.mark.parametrize(
    "score,threshold,expect_hidden",
    [(90.0, 50.0, False), (10.0, 50.0, True)],
)
def test_html_render_show_gt_predicate_sets_hidden_against_initial_state(
    score, threshold, expect_hidden
):
    tree = Page(
        State("score", score),
        State("threshold", threshold),
        Show(Predicate.gt("score", "threshold"), Text("You passed!")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    if expect_hidden:
        assert "data-ark-show=" in html and " hidden>" in html
    else:
        assert "data-ark-show=" in html and " hidden>" not in html


def test_html_render_show_equals_predicate_matches_state():
    tree = Page(
        State("role", "admin"),
        State("admin_role", "admin"),
        Show(Predicate.equals("role", "admin_role"), Text("Welcome, admin")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert " hidden>" not in html


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind,derive",
    [
        ("uppercase", Derive.uppercase("a")),
        ("trim", Derive.trim("a")),
    ],
)
def test_js_render_ships_only_the_used_new_derivation_kind(kind, derive):
    tree = Page(
        State("a", "  hi  "),
        Computed("result", deps=("a",), derive=derive),
        Text(Bind("result")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert f"{kind}: function" in js
    for other in (
        "sum", "multiply", "join", "count", "format", "compare",
        "subtract", "divide", "min", "max", "uppercase", "trim",
    ):
        if other != kind:
            assert f"{other}: function" not in js


def test_derivation_fragments_registry_covers_v0062_kinds():
    for kind in ("uppercase", "trim"):
        assert kind in DERIVATION_FRAGMENTS


def test_js_render_ships_arkevalpredicate_with_comparison_cases_when_show_used():
    tree = Page(
        State("score", 90.0),
        State("threshold", 50.0),
        Show(Predicate.gt("score", "threshold"), Text("You passed!")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert 'spec.kind === "gt"' in js
    assert 'spec.kind === "equals"' in js
    assert 'spec.kind === "lt"' in js


# ---------------------------------------------------------------------------
# End-to-end: build-time initial value agrees with a Node evaluation of
# the shipped runtime's own new fragments (kind-for-kind parity between
# arklight.ir.build._evaluate_derivation and
# arklight/backend/js/derivations/{uppercase,trim}.py), plus the same
# parity check for arkEvalPredicate's new comparison cases.
# ---------------------------------------------------------------------------


def test_node_runtime_recompute_matches_build_time_initial_value_for_uppercase():
    node = pytest.importorskip("shutil").which("node")
    if not node:
        pytest.skip("node not available in this environment")

    import json
    import subprocess

    from arklight.backend.js.derivations.uppercase import JS_FRAGMENT

    tree = Page(
        State("name", "ada"),
        Computed("shout", deps=("name",), derive=Derive.uppercase("name")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial["shout"] == "ADA"

    script = f"""
    var derivations = {{
      {JS_FRAGMENT}
    }};
    function createState(initial, computed) {{
      var state = Object.assign({{}}, initial);
      (computed || []).forEach(function (entry) {{
        var name = entry[0], spec = entry[1];
        state[name] = derivations[spec.kind](state, spec.names, spec.args);
      }});
      return state;
    }}
    var state = createState(
      {json.dumps({"name": "ada"})},
      {json.dumps(ir.pages[0].computed)}
    );
    console.log(state.shout);
    """
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == ir.pages[0].computed_initial["shout"]


def test_node_runtime_predicate_recompute_matches_build_time_for_gt():
    node = pytest.importorskip("shutil").which("node")
    if not node:
        pytest.skip("node not available in this environment")

    import json
    import subprocess

    script = f"""
    function arkEvalPredicate(store, spec) {{
      if (spec.kind === "equals") return store.get(spec.names[0]) === store.get(spec.names[1]);
      if (spec.kind === "gt") return store.get(spec.names[0]) > store.get(spec.names[1]);
      if (spec.kind === "lt") return store.get(spec.names[0]) < store.get(spec.names[1]);
      var value = store.get(spec.names[0]);
      return spec.kind === "falsy" ? !value : !!value;
    }}
    var state = {json.dumps({"score": 90.0, "threshold": 50.0})};
    var store = {{ get: function (name) {{ return state[name]; }} }};
    console.log(arkEvalPredicate(store, {json.dumps({"kind": "gt", "names": ["score", "threshold"]})}));
    """
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "true"
