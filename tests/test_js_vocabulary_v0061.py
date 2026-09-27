"""
Tests for `v0.061` -- JS vocabulary addendum, stage 1/10 (see
`docs/version history/v0.061.md`): `Derive.subtract`/`.divide`/`.min`/
`.max`, the missing math siblings of `Derive.sum`/`.multiply`. Mirrors
the style of `tests/test_vdom_4.py` -- same registry-driven shape,
just the four new kinds.
"""

import pytest

from arklight.api import Computed, Derive, Page, State, Text, Bind
from arklight.ast.nodes import DerivationRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.derivations import DERIVATION_FRAGMENTS
from arklight.backend.js.render import JSBackend
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import ValidationError, validate_ark_ast


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_derive_subtract_returns_derivation_ref():
    ref = Derive.subtract("total", "discount")
    assert ref == DerivationRef(kind="subtract", names=("total", "discount"))


def test_derive_divide_returns_derivation_ref():
    ref = Derive.divide("total", "count")
    assert ref == DerivationRef(kind="divide", names=("total", "count"))


def test_derive_min_returns_derivation_ref():
    ref = Derive.min("a", "b", "c")
    assert ref == DerivationRef(kind="min", names=("a", "b", "c"))


def test_derive_max_returns_derivation_ref():
    ref = Derive.max("a", "b", "c")
    assert ref == DerivationRef(kind="max", names=("a", "b", "c"))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind_fn", [Derive.subtract, Derive.divide])
def test_subtract_and_divide_require_at_least_two_names(kind_fn):
    tree = Page(
        State("a", 10.0),
        Computed("result", deps=("a",), derive=kind_fn("a")),
    )
    with pytest.raises(ValidationError, match="needs at least 2"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_min_accepts_a_single_name():
    tree = Page(
        State("a", 10.0),
        Computed("result", deps=("a",), derive=Derive.min("a")),
        Text(Bind("result")),
    )
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


# ---------------------------------------------------------------------------
# IR build -- build-time initial value evaluation
# ---------------------------------------------------------------------------


def test_ir_build_evaluates_subtract_initial_value():
    tree = Page(
        State("total", 100.0),
        State("discount", 15.0),
        Computed("net", deps=("total", "discount"), derive=Derive.subtract("total", "discount")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial == {"net": 85.0}


def test_ir_build_evaluates_chained_subtract_initial_value():
    tree = Page(
        State("total", 100.0),
        State("a", 10.0),
        State("b", 5.0),
        Computed("result", deps=("total", "a", "b"), derive=Derive.subtract("total", "a", "b")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial == {"result": 85.0}


def test_ir_build_evaluates_divide_initial_value():
    tree = Page(
        State("total", 100.0),
        State("count", 4.0),
        Computed("share", deps=("total", "count"), derive=Derive.divide("total", "count")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial == {"share": 25.0}


def test_ir_build_divide_by_zero_matches_js_infinity_not_python_exception():
    tree = Page(
        State("total", 100.0),
        State("count", 0.0),
        Computed("share", deps=("total", "count"), derive=Derive.divide("total", "count")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial["share"] == float("inf")


def test_ir_build_evaluates_min_and_max_initial_values():
    tree = Page(
        State("a", 3.0),
        State("b", 7.0),
        State("c", 1.0),
        Computed("lowest", deps=("a", "b", "c"), derive=Derive.min("a", "b", "c")),
        Computed("highest", deps=("a", "b", "c"), derive=Derive.max("a", "b", "c")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial == {"lowest": 1.0, "highest": 7.0}


# ---------------------------------------------------------------------------
# HTML backend
# ---------------------------------------------------------------------------


def test_html_render_prefills_bind_text_with_subtract_initial_value():
    tree = Page(
        State("total", 100.0),
        State("discount", 15.0),
        Computed("net", deps=("total", "discount"), derive=Derive.subtract("total", "discount")),
        Text(Bind("net")),
    )
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    # Bugfix (ARKlight-ISSUE-REGISTER.md #4): 100.0 - 15.0 is the
    # Python float 85.0, but the client runtime's `String()` coercion
    # spells that same value "85" (JS has only one number type, no
    # trailing ".0" for an integral value) -- the server-rendered
    # initial value must match what the runtime recomputes, not
    # Python's own `str()` spelling.
    assert 'data-ark-bind="net">85<' in html


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind,derive",
    [
        ("subtract", Derive.subtract("a", "b")),
        ("divide", Derive.divide("a", "b")),
        ("min", Derive.min("a", "b")),
        ("max", Derive.max("a", "b")),
    ],
)
def test_js_render_ships_only_the_used_new_derivation_kind(kind, derive):
    tree = Page(
        State("a", 10.0),
        State("b", 3.0),
        Computed("result", deps=("a", "b"), derive=derive),
        Text(Bind("result")),
    )
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert f"{kind}: function" in js
    for other in ("sum", "multiply", "join", "count", "format", "compare", "subtract", "divide", "min", "max"):
        if other != kind:
            assert f"{other}: function" not in js


def test_derivation_fragments_registry_covers_v0061_kinds():
    for kind in ("subtract", "divide", "min", "max"):
        assert kind in DERIVATION_FRAGMENTS


# ---------------------------------------------------------------------------
# End-to-end: build-time initial value agrees with a Node evaluation of
# the shipped runtime's own new fragments (kind-for-kind parity between
# arklight.ir.build._evaluate_derivation and
# arklight/backend/js/derivations/{subtract,divide,min,max}.py).
# ---------------------------------------------------------------------------


def test_node_runtime_recompute_matches_build_time_initial_value_for_subtract():
    node = pytest.importorskip("shutil").which("node")
    if not node:
        pytest.skip("node not available in this environment")

    import json
    import subprocess

    from arklight.backend.js.derivations.subtract import JS_FRAGMENT

    tree = Page(
        State("total", 100.0),
        State("a", 10.0),
        State("b", 5.0),
        Computed("result", deps=("total", "a", "b"), derive=Derive.subtract("total", "a", "b")),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].computed_initial["result"] == 85.0

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
      {json.dumps({"total": 100.0, "a": 10.0, "b": 5.0})},
      {json.dumps(ir.pages[0].computed)}
    );
    console.log(state.result);
    """
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    assert float(result.stdout.strip()) == ir.pages[0].computed_initial["result"]
