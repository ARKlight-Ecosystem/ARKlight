"""
Website IR.

The Website IR is deliberately a *separate* data structure from the ARK
AST, even though in v0.001 they look structurally similar
(`type` / `props` / `children`). The distinction matters going forward:

- ARK AST is "what the user's Python called" -- it's shaped by the
  public API's function-call ergonomics.
- Website IR is "what the website *means*" -- backend-independent
  intent that any backend (HTML, CSS and JS today) can
  consume without knowing anything about ARKlight's Python API.

Keeping them separate now means later milestones can let the IR diverge
from the ARK AST (e.g. one ARK node expanding into several IR nodes, or
site-wide concerns like navigation being synthesized into the IR) without
disturbing the public API or the validator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import math
import re

from arklight import experimental
from arklight.ast.nodes import ActionRef, ARKNode, DerivationRef
from arklight.ir import js_list, js_numeric, js_string
from arklight.ir.components import COMPONENT_ORIGIN_PROP_KEY, ComponentOrigin
from arklight.provider import ProviderDeclaration


@dataclass
class IRNode:
    """A single node in the Website IR."""

    type: str
    props: dict[str, Any] = field(default_factory=dict)
    children: list["IRNode | str"] = field(default_factory=list)
    # v0.060, Stage 3 (USER-DEFINED-COMPONENTS-IMPLEMENTATION.md [retired -- see CHANGELOG.md]):
    # set (by `_ark_node_to_ir_node`, popped straight off the incoming
    # `ARKNode`'s props under `COMPONENT_ORIGIN_PROP_KEY`) when this
    # node is the rendered root of a `mode="registry"` component call
    # that has at least one backend override registered -- `None` for
    # every other node, which is every node on every site before Stage
    # 3, and most nodes after it too (only a component that both opts
    # into `mode="registry"` *and* registers a backend override ever
    # produces a non-`None` value here). `arklight.ir.component_dispatch.
    # resolve_backend_dispatch` is the only real reader; it always
    # clears this back to `None` on its way past a node, matched or
    # not, so it never reaches a backend's own attribute-rendering code.
    component_origin: ComponentOrigin | None = None


@dataclass
class IRPage:
    route: str
    root: IRNode
    # v0.0035: page-scoped reactive state declared via `State(...)`,
    # extracted from the Page node's children rather than living as a
    # prop on some other node -- state belongs to the page, the same
    # way `title` does. Empty for pages that declare no state.
    state: dict[str, Any] = field(default_factory=dict)
    # `vdom-4` (REFACTOR-INDEX.md row 12): page-scoped
    # derived state declared via `Computed(...)`, extracted the same
    # way `state` above is. `computed` is an ordered (`name`, spec)
    # list, one entry per `Computed(...)` on the page, in dependency
    # order (a Computed(...) that reads another Computed(...) always
    # comes after it) -- `arklight/backend/js/render.py` embeds this
    # ordering directly as the client runtime's recompute pass order,
    # so it never has to re-derive a topological sort itself. Each
    # spec is `{"deps": [...], "kind": ..., "names": [...], "args":
    # {...}}`, a plain-dict mirror of the `DerivationRef` that produced
    # it (JSON-serializable, unlike the dataclass itself). `computed_
    # initial` is this page's build-time-evaluated initial value per
    # `Computed(...)` name -- computed once, in the same dependency
    # order, so `Bind("total")` renders correct text even with JS
    # disabled, the same guarantee `state`+`_render_bind` already give
    # a plain `State(...)`. Both empty for pages that declare no
    # `Computed(...)`.
    computed: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    computed_initial: dict[str, Any] = field(default_factory=dict)
    # `vdom-5` (REFACTOR-INDEX.md row 13): page-scoped
    # watch effects declared via `Watch(name, then=Action.*(...))`,
    # extracted the same way `state`/`computed` above are. Each entry
    # is `{"name": ..., "then": {"action": ..., "state": ...,
    # "args": {...}, "modifiers": [...]}}` -- a plain-dict,
    # JSON-serializable mirror of the `ActionRef` that produced it
    # (same shape `_derivation_ref_to_spec` gives `Computed(...)`'s
    # `derive=`), carried into the HTML backend's `data-ark-watch`
    # hydration blob and read by the JS runtime's `wireWatchers`
    # (`arklight/backend/js/runtime/watch.py`). Order is declaration
    # order -- unlike `computed`, watch effects don't depend on each
    # other, so there's no dependency graph to topologically sort.
    # Empty for pages that declare no `Watch(...)`.
    watch: list[dict[str, Any]] = field(default_factory=list)
    # `vdom-8` (REFACTOR-INDEX.md row 16): names of the
    # `State(...)` keys declared with `persist=True`, in declaration
    # order. Carries no value of its own (unlike `state`) -- it's a
    # plain list of keys the JS runtime should read an override for
    # from `localStorage` on init and write back out to on every
    # change (see `arklight/backend/js/runtime/state.py`'s
    # `initState()`). Empty for pages that declare no persisted
    # `State(...)`.
    persist: list[str] = field(default_factory=list)
    # `v0.063` (docs/version history/v0.063.md): `(name, query)` pairs
    # for every `State(..., media=...)` on this page, in declaration
    # order -- the same marker/`<body>`-attribute duality every other
    # piece of hydration state above already uses (see
    # `arklight/backend/js/runtime/state.py`'s `initState()`, which
    # overrides each name's initial value with
    # `matchMedia(query).matches` on init and attaches a "change"
    # listener that keeps writing it after that). Carries no value of
    # its own here -- `state[name]` above already holds this key's
    # (server-rendered-guess) initial value, same shape `persist`
    # already establishes for a key with a second, non-`Action.*(...)`
    # writer. Empty for pages that declare no media-driven `State(...)`.
    media: list[tuple[str, str]] = field(default_factory=list)
    # `v0.064` (docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md):
    # `(name, param, type_tag, history_mode)` tuples for every
    # `State(..., query=...)` on this page, in declaration order --
    # same marker/`<body>`-attribute duality every piece of hydration
    # state above already uses (see `arklight/backend/js/runtime/
    # state.py`'s `initState()`, which overrides each name's initial
    # value with the matching `URLSearchParams(location.search)` entry
    # on init, keeps it live across `popstate`, and writes it back out
    # via `history.replaceState`/`pushState` on every change).
    # `param` is the query-string key itself (`State("page", ...,
    # query="page")`'s `"page"` -- usually, but not necessarily, the
    # same string as `name`). `type_tag` is one of `"int"`/`"bool"`/
    # `"str"`, derived from `initial`'s own Python type at build time
    # -- the coercion the client needs to turn a raw string query
    # value back into the right JS type, the same type-carrying
    # mechanism that already lets `Computed(...)` be evaluated at
    # build time. `history_mode` is `"replace"` (the unmarked default)
    # or `"push"` (`arklight.ir.schema.KNOWN_QUERY_HISTORY_MODES`),
    # always resolved to one of the two here so the runtime never has
    # to guess a default itself. Carries no value of its own -- like
    # `persist`/`media` above, `state[name]` already holds this key's
    # server-rendered initial value. Empty for pages that declare no
    # query-tracked `State(...)`.
    query: list[tuple[str, str, str, str]] = field(default_factory=list)


@dataclass
class WebsiteIR:
    """The full compiled site: every route, mapped to its IR tree."""

    site_name: str
    pages: list[IRPage] = field(default_factory=list)
    # v0.042: site-wide custom CSS classes registered via `Site.style(...)`
    # -- name -> {css-property: value}. Structured input only (a plain
    # dict), never a raw CSS string, same boundary the rest of the
    # project holds. Empty for sites that never call `site.style(...)`.
    custom_styles: dict[str, dict[str, str]] = field(default_factory=dict)
    # EXPERIMENTAL (docs/Foundational/EXPERIMENTAL-APIS.md): (condition, class_name,
    # {prop: value}) triples registered via `site.media_query(...)`.
    # Kept separate from `custom_styles` -- see `Site.media_query`'s
    # docstring for why this isn't folded into the same dict. Empty
    # for sites that never call `site.media_query(...)` (i.e. every
    # site that stays fully within the intrinsic layout model).
    media_queries: list = field(default_factory=list)
    # EXPERIMENTAL (docs/Foundational/EXPERIMENTAL-APIS.md): every `ExperimentalUsage`
    # recorded during compilation, in call order -- the CLI drains this
    # (deduplicated by feature id) to print the end-of-build summary
    # block via `arklight.experimental.print_summary`.
    experimental_usages: list = field(default_factory=list)
    # EXPERIMENTAL (docs/Foundational/EXPERIMENTAL-APIS.md, feature
    # `provider-integration`; `Provider` stage 2 of 6, `v0.066` -- see
    # `docs/version history/v0.066.md` and `arklight/provider.py`):
    # straight passthrough of `Site(provider=...)`, same shape as
    # `media_queries`/`app_shell` above. Stage 1 (`0.06514`) only
    # stored the declaration on `Site` and emitted the experimental
    # banner; this is the first point a declared `Provider` reaches
    # the IR at all. Still nothing is emitted from it here -- no
    # backend reads this field yet, so a build with a Provider stays
    # byte-identical to one without, apart from the reports every
    # gated experimental feature already gets. `None` for sites that
    # never call `Site(provider=...)`.
    provider: ProviderDeclaration | None = None
    # CSS backend refactor: `--ark-*` custom property overrides
    # registered via `Site(max_width=..., bg=...)` -- var name (e.g.
    # "--ark-max-width") -> value. Empty for sites that pass neither,
    # in which case `CSSBackend` falls back to its own defaults.
    css_var_overrides: dict[str, str] = field(default_factory=dict)
    # Sitewide default for <html lang="...">. Previously this was a
    # literal "en" baked into the HTML backend with no override path
    # at all -- wrong for every non-English site, and there was no way
    # to fix it short of hand-editing generated HTML after every
    # build. Defaults to "en" (unchanged rendered output for a site
    # that doesn't set `Site(lang=...)`); a per-page `Page(lang=...)`
    # prop, read the same way `title`/`favicon`/`description` already
    # are, overrides this per route.
    lang: str = "en"
    # v0.048 Stage B ("CSS media queries + `<head>` extension" -- see
    # docs/Foundational/DESIGN-NOTES.md): (condition, generated_class_name,
    # {prop: value}) triples, one per media condition on every node
    # that carried a `responsive_style={...}` prop anywhere on the
    # site. Populated by `build_website_ir`/`_ark_node_to_ir_node`
    # below, which also strips `responsive_style` out of the node's
    # own IR props (it isn't a real HTML attribute) and folds the
    # matching generated class into that node's `class_name` instead.
    # `CSSBackend` compiles this into real `@media (...) { .arkgen-N {
    # ... } }` rules, same shape as `media_queries` above but keyed to
    # a synthesized per-node class instead of an author-chosen one.
    # Empty for sites that never use `responsive_style=`.
    responsive_rules: list = field(default_factory=list)
    # Structural addendum (see docs/Foundational/DESIGN-NOTES.md "CSS selector
    # algebra + at-rule vocabulary"): straight passthroughs of
    # `Site.style_selector`/`keyframes`/`font_face`/`container_query`/
    # `supports`/`page_rule`/`import_style` registrations. Each keeps
    # the exact shape its `Site` method already validated and
    # normalized -- see `arklight/backend/css/at_rules.py` for what
    # consumes each one. Empty for sites that never call the
    # corresponding method.
    selector_rules: list = field(default_factory=list)
    keyframes: dict = field(default_factory=dict)
    font_faces: list = field(default_factory=list)
    container_queries: list = field(default_factory=list)
    supports_rules: list = field(default_factory=list)
    page_rules: list = field(default_factory=list)
    style_imports: list = field(default_factory=list)
    # htmx-4 (REFACTOR-INDEX.md row 9): straight
    # passthrough of `Site(app_shell=...)`, same shape as `lang`
    # above. `HTMLBackend` reads this to decide whether to emit
    # `hx-boost="true"` on `<body>` and route the page's state marker
    # through the app-shell-safe shape (see
    # `arklight/backend/html/page_render.py`); the JS backend reads it
    # to decide whether every page needs HTMX loaded, not just ones
    # that already needed it for a behavior/State(...) (see
    # `arklight/backend/js/render.py`'s `needs_htmx`). Defaults to
    # `False`, unchanged output for every existing caller.
    app_shell: bool = False
    # Runtime policy enforcement (arklight/backend/html/csp.py): straight
    # passthrough of `Site(strict_csp=..., trusted_script_origins=...)`,
    # same shape as `app_shell`/`lang` above. `HTMLBackend` reads both to
    # decide whether/what CSP meta tag to emit per page -- see
    # `Site.__init__`'s own comment (arklight/api.py) for the full
    # reasoning, including why style-src is deliberately never touched
    # and why `strict_csp=False` (not a nonce) is the general escape
    # valve for any hand-injected inline script. Defaults preserve today's
    # (pre-feature) output only when explicitly disabled; the *default*
    # for a new build is `strict_csp=True`, which is a deliberate,
    # unconditional new-default addition -- see PROGRESS.md's entry for
    # this feature for why that's called out rather than folded silently
    # into "added an override" per CONFIGURABILITY.md's own rule.
    strict_csp: bool = True
    trusted_script_origins: list[str] = field(default_factory=list)
    # Runtime policy enforcement, devtools mirror (arklight/backend/js/
    # render.py's `_experimental_console_reminder_js`): a compile-time
    # "[EXPERIMENTAL FEATURE ACTIVE]" banner (arklight/experimental.py)
    # only ever reaches whoever ran `arklight build` -- anyone who
    # opens the *shipped site* in a browser and pops devtools sees
    # nothing about it at all. This mirrors the same deduplicated
    # per-feature warning into a `console.warn(...)` block in the
    # generated `arklight.js`, so an experimental feature stays visible
    # to whoever's actually looking at the running page, not just
    # whoever built it. `True` by default -- same "warn, don't hide"
    # stance as the compile-time banner itself, which has no opt-out at
    # all. This one *does* get an opt-out (arklight.config.py's
    # `CONFIG = {"experimental": {"devtools_console_reminder": False}}`,
    # read by `arklight.cli.main`) since, unlike the compile-time
    # banner, it ships extra bytes into every page's JS and some
    # projects may already have their own devtools-console conventions
    # they don't want ARKlight talking over. No `Site(...)` kwarg
    # equivalent, same reasoning as `heavy_reliance_nudge` having none
    # (docs/Foundational/EXPERIMENTAL-APIS.md): this is a build-tool-
    # behavior toggle, not a design decision the site file itself makes.
    devtools_console_reminder: bool = True
    # EXPERIMENTAL (docs/Foundational/EXPERIMENTAL-APIS.md): `(output_files: dict[str,
    # str]) -> dict[str, str]` callables registered via
    # `site.register_script_extension(...)`
    # (arklight.backend.script_extension.register), in call order --
    # straight passthrough, same shape as `style_imports` etc. above.
    # `arklight.compiler.pipeline.build` runs these last, after every
    # backend's own render()+postprocess() pass, over the combined
    # output dict. No longer populated by `Site.raw_postprocess(...)`,
    # which is deprecated and no-op as of the script-extension
    # capability (see `arklight/experimental.py`'s `raw-postprocess`
    # entry). Empty for sites that never register a ScriptExtension.
    raw_postprocessors: list = field(default_factory=list)


@dataclass
class _ResponsiveStyleCollector:
    """
    v0.048 Stage B: walks alongside `_ark_node_to_ir_node`, assigning
    each `responsive_style={...}`-carrying node a deterministic,
    site-wide-unique generated class name (`arkgen-1`, `arkgen-2`,
    ...) in build order -- pages in `pages` dict order, depth-first
    within each page -- so two builds of the same source produce
    identical output. Also records one `ExperimentalUsage` per node
    (not per media condition) under the same `css-media-queries`
    feature `Site.media_query(...)` already gates (see
    docs/Foundational/EXPERIMENTAL-APIS.md): a viewport-keyed `@media` rule is a
    viewport-keyed `@media` rule regardless of which authoring surface
    produced it.
    """

    counter: int = 0
    rules: list[tuple[str, str, dict[str, str]]] = field(default_factory=list)
    experimental_usages: list = field(default_factory=list)

    def collect(
        self,
        node_type: str,
        responsive_style: dict[str, dict[str, Any]],
        *,
        on_warning: Callable[[str], None] | None,
    ) -> str:
        self.counter += 1
        class_name = f"arkgen-{self.counter}"
        for condition, rules in responsive_style.items():
            self.rules.append((condition, class_name, dict(rules)))
        self.experimental_usages.append(
            experimental.emit("css-media-queries", on_warning=on_warning, component=node_type)
        )
        return class_name


def _ark_node_to_ir_node(
    node: ARKNode,
    *,
    collector: _ResponsiveStyleCollector,
    on_warning: Callable[[str], None] | None = None,
) -> IRNode:
    props = dict(node.props)

    # v0.048 Stage B: `responsive_style` is a compile-time-only prop --
    # it never reaches the HTML backend as an attribute (there's no
    # such thing as a `responsive_style="..."` HTML attribute). It's
    # popped here, converted into a generated scoped class folded into
    # `class_name`, and the actual `{condition: {prop: value}}` rules
    # are handed to the collector for `CSSBackend` to compile.
    responsive_style = props.pop("responsive_style", None)
    if responsive_style:
        generated_class = collector.collect(node.type, responsive_style, on_warning=on_warning)
        existing_class = props.get("class_name")
        classes = existing_class.split() if isinstance(existing_class, str) and existing_class else []
        if generated_class not in classes:
            classes.append(generated_class)
        props["class_name"] = " ".join(classes)

    # v0.060, Stage 3: same "pop a compile-time-only prop, lift it onto
    # its own IRNode field" treatment `responsive_style` just got above
    # -- `COMPONENT_ORIGIN_PROP_KEY` is never a real HTML attribute
    # either, it's `arklight.ir.components._tag_component_origin`'s own
    # internal marker, absent from every node except the rendered root
    # of a `mode="registry"` component call that has a backend override
    # registered (see that function's docstring for why it's this
    # narrowly scoped).
    component_origin = props.pop(COMPONENT_ORIGIN_PROP_KEY, None)

    # `Provider`, stage 4 of 6 (`v0.068` -- see
    # `docs/Implementation/PROVIDER-SDK-ADDENDUM.md`): unlike
    # `responsive_style` above, `scripts` is *not* popped -- it's a real
    # `Page(...)` prop the HTML backend reads directly off `page.root`
    # (`arklight/backend/html/head_meta.py`, same convention `links`/
    # `meta` already use), not a compile-time-only one lifted onto its
    # own IRNode field. This only records the gate: one `ExperimentalUsage`
    # per `Page(scripts=[...])`, reusing `collector.experimental_usages`
    # (already folded into `WebsiteIR.experimental_usages`, see
    # `build_website_ir` below) rather than adding a second, parallel
    # list just for this one prop.
    if node.type == "Page" and props.get("scripts"):
        collector.experimental_usages.append(
            experimental.emit("provider-scripts", on_warning=on_warning, component="Page")
        )

    children: list[IRNode | str] = []
    for child in node.children:
        if isinstance(child, ARKNode):
            children.append(_ark_node_to_ir_node(child, collector=collector, on_warning=on_warning))
        else:
            children.append(str(child))
    return IRNode(type=node.type, props=props, children=children, component_origin=component_origin)


def ark_node_to_ir_node(
    node: ARKNode, *, on_warning: Callable[[str], None] | None = None
) -> IRNode:
    """
    Public, single-node wrapper around `_ark_node_to_ir_node` -- v0.060
    Stage 3's own reason for needing one: `arklight.ir.component_dispatch`
    converts a backend override's freshly-rendered subtree straight to
    `IRNode` without going through a whole-site `build_website_ir` call
    (there's no `Site`, no page, no route to build a *whole* IR from at
    that point in the pipeline -- just one subtree).

    Uses a throwaway, single-call `_ResponsiveStyleCollector`: a
    `responsive_style={...}` prop used *inside* a backend override's
    own subtree still gets its generated class name folded into
    `class_name` here, exactly like anywhere else, but the underlying
    `@media` rule this collector gathers has nowhere to go -- there's
    no site-wide `WebsiteIR.responsive_rules` list left to hand it to
    at this point in `resolve_backend_dispatch`'s own pass, which runs
    once per backend, after `WebsiteIR` already exists. This is a known
    Stage 3 limitation (a documented gap, not a silent bug): a backend
    override that needs a responsive rule of its own should register it
    via `site.media_query(...)` instead, which -- unlike `responsive_style`
    -- is collected once, up front, independent of any one node.
    """
    return _ark_node_to_ir_node(node, collector=_ResponsiveStyleCollector(), on_warning=on_warning)


def _derivation_ref_to_spec(derive: DerivationRef) -> dict[str, Any]:
    """Plain-dict, JSON-serializable mirror of a `DerivationRef` --
    see `IRPage.computed`'s docstring for why this shape (rather than
    the dataclass itself) is what gets carried into the IR."""
    return {"kind": derive.kind, "names": list(derive.names), "args": dict(derive.args)}


def _action_ref_to_spec(action: ActionRef) -> dict[str, Any]:
    """Plain-dict, JSON-serializable mirror of an `ActionRef` -- same
    role `_derivation_ref_to_spec` plays for `DerivationRef`, used by
    `Watch(...)`'s `then=` (`vdom-5`, `IRPage.watch`)."""
    return {
        "action": action.action,
        "state": action.state,
        "args": dict(action.args),
        "modifiers": list(action.modifiers),
    }


def _topological_order_computed(computed_defs: dict[str, dict[str, Any]]) -> list[str]:
    """
    Depth-first topological sort of the `Computed(...) -> Computed(...)`
    dependency graph (edges to a `State(...)` name are leaves -- state
    has no further deps to walk). Validation (`arklight.ir.validate`,
    `_find_computed_cycle`) has already rejected any cycle by the time
    this runs, so this assumes a DAG and does not re-detect one.
    """
    order: list[str] = []
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        for dep in computed_defs[name]["deps"]:
            if dep in computed_defs:
                visit(dep)
        order.append(name)

    for name in computed_defs:
        visit(name)
    return order


def _coerce_number(value: Any) -> float:
    """Python-side mirror of the client runtime's `Number(x) || 0`
    coercion (see `arklight/backend/js/derivations/sum.py` /
    `multiply.py`), so a build-time `sum`/`multiply` initial value
    (used to pre-fill `Bind(...)` text -- see `_evaluate_derivation`)
    agrees with what the browser recomputes on the first state change."""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    # `Number(x) || 0`: `||` also turns `NaN` and `-0` into `+0`. Matters
    # once a derivation can *produce* `NaN` (`v0.064`'s `sqrt(-1)`,
    # `log(0) - log(0)`) that a later `Computed(...)` then reads.
    return 0.0 if (number == 0 or math.isnan(number)) else number


_FORMAT_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

# `v0.064`: kind -> build-time mirror, for the math derivations whose
# evaluation is one call. Unary kinds take one coerced number; variadic
# kinds take the list of coerced numbers.
_MATH_UNARY: dict[str, Callable[[float], float]] = {
    "absolute": abs,
    "ceiling": js_numeric.js_ceil,
    "floor": js_numeric.js_floor,
    "truncate_number": js_numeric.js_trunc,
    "sign": js_numeric.js_sign,
    "sqrt": js_numeric.js_sqrt,
    "cbrt": js_numeric.js_cbrt,
    "exp": js_numeric.js_exp,
    "log": js_numeric.js_log,
    "log2": js_numeric.js_log2,
    "log10": js_numeric.js_log10,
}
_MATH_VARIADIC: dict[str, Callable[[list[float]], float]] = {
    "hypot": js_numeric.js_hypot,
    "average": js_numeric.js_average,
    "median": js_numeric.js_median,
    "gcd": js_numeric.js_gcd,
    "lcm": js_numeric.js_lcm,
}

# `v0.065`: the string derivations catalog. Every kind reads its one
# input through `js_string.js_to_string` (JavaScript's `String(x)`) and
# reproduces `String.prototype.*` via `arklight/ir/js_string.py`. The
# first table holds the kinds with no literal argument, the second the
# ones that take their parameters from `args`.
_STRING_UNARY: dict[str, Callable[[str], Any]] = {
    "capitalize": js_string.js_capitalize,
    "title_case": js_string.js_title_case,
    "trim_start": js_string.js_trim_start,
    "trim_end": js_string.js_trim_end,
    "reverse_string": js_string.js_reverse,
    "string_length": js_string.js_length,
    "is_empty": js_string.js_is_empty,
    # `v0.069`: JS vocabulary addendum stage 9/10 -- case converters.
    "to_snake_case": js_string.js_to_snake_case,
    "to_camel_case": js_string.js_to_camel_case,
    "to_kebab_case": js_string.js_to_kebab_case,
    "to_title_case": js_string.js_to_title_case,
}
_STRING_WITH_ARGS: dict[str, Callable[[str, dict[str, Any]], Any]] = {
    "pad_start": lambda s, a: js_string.js_pad_start(s, a["length"], a["fill"]),
    "pad_end": lambda s, a: js_string.js_pad_end(s, a["length"], a["fill"]),
    "repeat": lambda s, a: js_string.js_repeat(s, a["count"]),
    "slice_string": lambda s, a: js_string.js_slice(s, a["start"], a["end"]),
    "char_at": lambda s, a: js_string.js_char_at(s, a["index"]),
    "replace_first": lambda s, a: js_string.js_replace_first(s, a["search"], a["replacement"]),
    "replace_all": lambda s, a: js_string.js_replace_all(s, a["search"], a["replacement"]),
    "split_count": lambda s, a: js_string.js_split_count(s, a["sep"]),
    "includes_substring": lambda s, a: js_string.js_includes(s, a["substring"]),
    "starts_with": lambda s, a: js_string.js_starts_with(s, a["substring"]),
    "ends_with": lambda s, a: js_string.js_ends_with(s, a["substring"]),
}

# `v0.067`: the list-scalar derivations catalog. Each kind reads its one
# input -- the raw state value, since what counts as a list is decided by
# `arklight/ir/js_list.py` exactly as the client's `Array.isArray` does --
# and reduces it to a scalar. The first table holds the kinds with no
# literal argument, the second the ones that take theirs from `args`.
_LIST_UNARY: dict[str, Callable[[Any], Any]] = {
    "list_length": js_list.js_list_length,
    "list_min": js_list.js_list_min,
    "list_max": js_list.js_list_max,
    "list_average": js_list.js_list_average,
    "list_first": js_list.js_list_first,
    "list_last": js_list.js_list_last,
}
_LIST_WITH_ARGS: dict[str, Callable[[Any, dict[str, Any]], Any]] = {
    "list_includes": lambda v, a: js_list.js_list_includes(v, a["value"]),
    "list_any": lambda v, a: js_list.js_list_any(v, a["op"], a["value"]),
    "list_all": lambda v, a: js_list.js_list_all(v, a["op"], a["value"]),
}


def _evaluate_derivation(spec: dict[str, Any], *, get: Callable[[str], Any]) -> Any:
    """
    Build-time evaluation of a single `Computed(...)`'s initial value,
    mirroring `arklight/backend/js/derivations/*.py`'s runtime
    semantics kind-for-kind so server-rendered `Bind(...)` text never
    disagrees with what the client recomputes. `get` resolves a
    `State(...)`/already-evaluated `Computed(...)` name to its current
    value -- callers evaluate `Computed(...)` entries in
    `_topological_order_computed`'s order so every dependency `get`
    reaches here has already been computed.
    """
    kind = spec["kind"]
    names: list[str] = spec["names"]
    args: dict[str, Any] = spec["args"]

    if kind == "sum":
        # Explicit loop, not `sum()`: Python 3.12's float `sum()` is
        # compensated and can differ from JavaScript's plain `reduce`
        # in the last digit (`0.1` ten times: `1.0` vs `0.9999999999999999`).
        total = 0.0
        for name in names:
            total += _coerce_number(get(name))
        return total
    if kind == "multiply":
        total = 1.0
        for name in names:
            total *= _coerce_number(get(name))
        return total
    if kind == "join":
        sep = args.get("sep", " ")
        return sep.join(str(get(name)) for name in names)
    if kind == "count":
        value = get(names[0])
        return len(value) if isinstance(value, (list, tuple, str, dict)) else 0
    if kind == "format":
        template = args["template"]
        names_map = args.get("names_map", {})

        def _replace(match: "re.Match[str]") -> str:
            key = match.group(1)
            state_name = names_map.get(key)
            return str(get(state_name)) if state_name is not None else match.group(0)

        return _FORMAT_PLACEHOLDER_RE.sub(_replace, template)
    if kind == "compare":
        a, b = get(names[0]), get(names[1])
        op = args["op"]
        if op == "eq":
            return a == b
        if op == "ne":
            return a != b
        if op == "gt":
            return a > b
        if op == "lt":
            return a < b
        if op == "gte":
            return a >= b
        if op == "lte":
            return a <= b
        return False  # unreachable once Validation has run
    if kind == "subtract":
        values = [_coerce_number(get(name)) for name in names]
        total = values[0]
        for value in values[1:]:
            total -= value
        return total
    if kind == "divide":
        values = [_coerce_number(get(name)) for name in names]
        total = values[0]
        for value in values[1:]:
            # JavaScript's `x / 0` semantics (`Infinity`/`-Infinity`/
            # `NaN`, never a thrown error) rather than Python's
            # `ZeroDivisionError` -- see `arklight/ir/js_numeric.py`.
            total = js_numeric.js_divide(total, value)
        return total
    if kind == "min":
        return min(_coerce_number(get(name)) for name in names)
    if kind == "max":
        return max(_coerce_number(get(name)) for name in names)
    if kind == "uppercase":
        return str(get(names[0])).upper()
    if kind == "trim":
        return str(get(names[0])).strip()
    # `v0.064` (docs/version history/v0.064.md): the math derivations
    # catalog. Every case reads its inputs through `_coerce_number`
    # (JavaScript's `Number(x) || 0`) and reproduces `Math.*`/
    # `Number.prototype.*` via `arklight/ir/js_numeric.py`.
    if kind in _MATH_UNARY:
        return _MATH_UNARY[kind](_coerce_number(get(names[0])))
    if kind in _MATH_VARIADIC:
        return _MATH_VARIADIC[kind]([_coerce_number(get(name)) for name in names])
    if kind == "power":
        return js_numeric.js_pow(_coerce_number(get(names[0])), _coerce_number(get(names[1])))
    if kind == "clamp":
        value, low, high = (_coerce_number(get(name)) for name in names)
        return min(max(value, low), high)
    if kind == "percentage_of":
        part, whole = (_coerce_number(get(name)) for name in names)
        return js_numeric.js_divide(part, whole) * 100
    if kind == "to_fixed":
        return js_numeric.js_to_fixed(_coerce_number(get(names[0])), args["digits"])
    if kind == "to_precision":
        return js_numeric.js_to_precision(_coerce_number(get(names[0])), args["digits"])
    # `v0.065` (docs/version history/v0.065.md): the string derivations
    # catalog -- see `_STRING_UNARY`/`_STRING_WITH_ARGS` above.
    if kind in _STRING_UNARY:
        return _STRING_UNARY[kind](js_string.js_to_string(get(names[0])))
    if kind in _STRING_WITH_ARGS:
        return _STRING_WITH_ARGS[kind](js_string.js_to_string(get(names[0])), args)
    # `v0.067` (docs/version history/v0.067.md): the list-scalar
    # derivations catalog -- see `_LIST_UNARY`/`_LIST_WITH_ARGS` above.
    if kind in _LIST_UNARY:
        return _LIST_UNARY[kind](get(names[0]))
    if kind in _LIST_WITH_ARGS:
        return _LIST_WITH_ARGS[kind](get(names[0]), args)
    # `v0.068` (docs/version history/v0.068.md): JS vocabulary addendum
    # stage 8/10 -- cross-language numeric batteries, via
    # `arklight/ir/js_numeric.py`'s `js_lerp`/`js_midpoint`.
    if kind == "lerp":
        a, b, t = (_coerce_number(get(name)) for name in names)
        return js_numeric.js_lerp(a, b, t)
    if kind == "midpoint":
        a, b = (_coerce_number(get(name)) for name in names)
        return js_numeric.js_midpoint(a, b)
    if kind == "saturating_add":
        a, b = (_coerce_number(get(name)) for name in names)
        return min(max(a + b, args["min"]), args["max"])
    if kind == "saturating_subtract":
        a, b = (_coerce_number(get(name)) for name in names)
        return min(max(a - b, args["min"]), args["max"])
    if kind == "value_or":
        # Mirrors the client's `v === null || v === undefined || v === ""`:
        # JSON has no `undefined`, so `None` already stands in for both
        # `null` and a name that was never set.
        value = get(names[0])
        return args["fallback"] if value is None or value == "" else value
    if kind == "first_present":
        values = [get(name) for name in names]
        for value in values:
            if value is not None and value != "":
                return value
        return values[-1]
    # `v0.069` (docs/version history/v0.069.md): JS vocabulary addendum
    # stage 9/10 -- formatting idioms, via `arklight/ir/js_numeric.py`.
    if kind == "to_ordinal":
        return js_numeric.js_to_ordinal(_coerce_number(get(names[0])))
    if kind == "humanize_bytes":
        return js_numeric.js_humanize_bytes(_coerce_number(get(names[0])))
    if kind == "humanize_duration":
        return js_numeric.js_humanize_duration(_coerce_number(get(names[0])))
    return None  # unreachable once Validation has run


def _query_type_tag(initial: Any) -> str:
    """
    `v0.064`: the coercion tag a query-tracked `State(...)`'s `initial`
    value bakes in for the client runtime -- `bool` is checked before
    `int` since `bool` is a Python subclass of `int` (`isinstance(True,
    int)` is `True`), the same ordering pitfall
    `arklight/backend/js/derivations/` already has to account for
    wherever a value's exact type (not just its `int`-compatibility)
    matters. Anything that isn't `bool`/`int` falls back to `"str"` --
    `str(initial)` is always a safe passthrough client-side, mirroring
    the "fail open to the safe default" discipline the rest of this
    feature holds, just applied to type selection instead of a bad
    runtime read.
    """
    if isinstance(initial, bool):
        return "bool"
    if isinstance(initial, int):
        return "int"
    return "str"


def _extract_page_state(
    page: ARKNode,
) -> tuple[
    dict[str, Any],
    list[tuple[str, dict[str, Any]]],
    dict[str, Any],
    list[dict[str, Any]],
    list[str],
    list,
    list[tuple[str, str, str, str]],
]:
    """
    Split a validated Page node's children into (state, computed,
    computed_initial, watch, persist, media, query, remaining
    children). `State(...)`/`Computed(...)`/`Watch(...)` nodes are
    declarations, not renderable content -- they must never reach the
    HTML backend as a child.

    `computed` is returned in dependency order (see
    `_topological_order_computed`); `computed_initial` is each
    `Computed(...)`'s build-time-evaluated initial value, in that same
    order, computed via `_evaluate_derivation` against `state` and
    previously-evaluated entries. `watch` (`vdom-5`) is returned in
    declaration order -- see `IRPage.watch`'s docstring for why no
    sort is needed here, unlike `computed`. `persist` (`vdom-8`) is
    also declaration order, and is simply the `name` of every
    `State(...)` on this page whose `persist` prop is `True` -- no
    dependency graph, no value of its own, same reasoning as `watch`.
    `media` (`v0.063`) is declaration order too: `(name, query)` for
    every `State(...)` on this page whose `media` prop is set. `query`
    (`v0.064`) is declaration order too: `(name, param, type_tag,
    history_mode)` for every `State(...)` on this page whose `query`
    prop is set -- see `IRPage.query`'s docstring for what each field
    means.
    """
    state: dict[str, Any] = {}
    computed_defs: dict[str, dict[str, Any]] = {}
    watch: list[dict[str, Any]] = []
    persist: list[str] = []
    media: list[tuple[str, str]] = []
    query: list[tuple[str, str, str, str]] = []
    remaining: list = []
    for child in page.children:
        if isinstance(child, ARKNode) and child.type == "State":
            name = child.props["name"]
            initial = child.props.get("initial")
            state[name] = initial
            if child.props.get("persist"):
                persist.append(name)
            media_condition = child.props.get("media")
            if media_condition:
                media.append((name, media_condition))
            query_param = child.props.get("query")
            if query_param:
                history_mode = child.props.get("history") or "replace"
                query.append((name, query_param, _query_type_tag(initial), history_mode))
        elif isinstance(child, ARKNode) and child.type == "Computed":
            spec = _derivation_ref_to_spec(child.props["derive"])
            spec["deps"] = list(child.props.get("deps", ()))
            computed_defs[child.props["name"]] = spec
        elif isinstance(child, ARKNode) and child.type == "Watch":
            watch.append(
                {
                    "name": child.props["name"],
                    "then": _action_ref_to_spec(child.props["then"]),
                }
            )
        else:
            remaining.append(child)

    order = _topological_order_computed(computed_defs)
    computed_initial: dict[str, Any] = {}

    def _get(name: str) -> Any:
        if name in state:
            return state[name]
        return computed_initial.get(name)

    for name in order:
        computed_initial[name] = _evaluate_derivation(computed_defs[name], get=_get)

    computed = [(name, computed_defs[name]) for name in order]
    return state, computed, computed_initial, watch, persist, media, query, remaining


def build_website_ir(
    site_name: str,
    pages: dict[str, ARKNode],
    *,
    custom_styles: dict[str, dict[str, str]] | None = None,
    media_queries: list | None = None,
    experimental_usages: list | None = None,
    css_var_overrides: dict[str, str] | None = None,
    lang: str = "en",
    on_warning: Callable[[str], None] | None = None,
    selector_rules: list | None = None,
    keyframes: dict | None = None,
    font_faces: list | None = None,
    container_queries: list | None = None,
    supports_rules: list | None = None,
    page_rules: list | None = None,
    style_imports: list | None = None,
    app_shell: bool = False,
    raw_postprocessors: list | None = None,
    strict_csp: bool = True,
    trusted_script_origins: list | None = None,
    devtools_console_reminder: bool = True,
    provider: ProviderDeclaration | None = None,
) -> WebsiteIR:
    """
    Build the Website IR from a normalized + validated ARK AST.

    Callers are expected to have already run `normalize_ark_ast` and
    `validate_ark_ast` on `pages` before calling this. `custom_styles`
    (v0.042), `css_var_overrides` (CSS backend refactor), and `lang`
    are all optional and default to their prior stock values --
    existing callers that only pass `site_name`/`pages` are unaffected.

    `on_warning`, if given, is called once per `responsive_style={...}`
    node encountered (v0.048 Stage B) with the same inline
    "[EXPERIMENTAL FEATURE ACTIVE]" banner text `Site.media_query(...)`
    usages already print -- see `arklight.experimental.emit`. Unlike
    `Site.media_query(...)` (an author-time `Site` method call, so its
    usage is already known before this function runs), a
    `responsive_style` prop is only discovered by walking the tree
    here, so this is this feature's own detection point. Defaults to
    `None` (record the usage, but print nothing) so existing callers
    that don't pass it are unaffected; `arklight.compiler.pipeline`
    passes its stage logger.

    `selector_rules`/`keyframes`/`font_faces`/`container_queries`/
    `supports_rules`/`page_rules`/`style_imports` are the structural
    CSS addendum's registrations (`Site.style_selector`/`keyframes`/
    `font_face`/`container_query`/`supports`/`page_rule`/
    `import_style` -- see docs/Foundational/DESIGN-NOTES.md), forwarded to the
    matching `WebsiteIR` field unchanged. All default to empty/None so
    existing callers are unaffected.

    `app_shell` (htmx-4, see REFACTOR-INDEX.md row 9) is
    `Site(app_shell=...)`'s straight passthrough, same shape as
    `lang`. Defaults to `False`, unchanged output for existing callers.

    `raw_postprocessors` is `site.register_script_extension(...)`'s
    straight passthrough (docs/Foundational/EXPERIMENTAL-APIS.md; no longer fed by
    the deprecated `Site.raw_postprocess(...)`) -- a list of
    `(output_files) -> output_files` callables `arklight.compiler.
    pipeline.build` runs, in order, after every backend's own
    render()+postprocess() pass. Defaults to `None` (empty list), so
    existing callers are unaffected.

    `strict_csp`/`trusted_script_origins` are `Site(strict_csp=...,
    trusted_script_origins=...)`'s straight passthrough (runtime policy
    enforcement -- see `Site.__init__`'s comment in arklight/api.py and
    arklight/backend/html/csp.py). Note this is the one field pair in
    this function whose *default* (`strict_csp=True`) is new behavior,
    not "unchanged output for existing callers" -- see `WebsiteIR.
    strict_csp`'s own comment for why.

    `devtools_console_reminder` is the CLI's `arklight.config.py`
    (`CONFIG = {"experimental": {"devtools_console_reminder": ...}}`)
    override passthrough -- see `WebsiteIR.devtools_console_reminder`'s
    own comment for the full reasoning. Defaults to `True`, same "new
    default, not silently unchanged" note as `strict_csp` above; unlike
    `strict_csp` there's no `Site(...)` kwarg feeding this one, only
    the config file.

    `provider` is `Site(provider=...)`'s straight passthrough
    (`Provider` stage 2 of 6, `v0.066` -- see `WebsiteIR.provider`'s
    own comment). Defaults to `None`, unchanged output for existing
    callers. Callers are expected to have already run
    `arklight.ir.validate.validate_provider` on it, the same ordering
    `validate_ark_ast` already has relative to this function.
    """
    collector = _ResponsiveStyleCollector()
    ir_pages = []
    for route, page in pages.items():
        state, computed, computed_initial, watch, persist, media, query, remaining_children = (
            _extract_page_state(page)
        )
        root_page = ARKNode(type=page.type, props=page.props, children=remaining_children)
        ir_pages.append(
            IRPage(
                route=route,
                root=_ark_node_to_ir_node(root_page, collector=collector, on_warning=on_warning),
                state=state,
                computed=computed,
                computed_initial=computed_initial,
                watch=watch,
                persist=persist,
                media=media,
                query=query,
            )
        )
    return WebsiteIR(
        site_name=site_name,
        pages=ir_pages,
        custom_styles=dict(custom_styles) if custom_styles else {},
        media_queries=list(media_queries) if media_queries else [],
        experimental_usages=(list(experimental_usages) if experimental_usages else [])
        + collector.experimental_usages,
        css_var_overrides=dict(css_var_overrides) if css_var_overrides else {},
        lang=lang,
        responsive_rules=collector.rules,
        selector_rules=list(selector_rules) if selector_rules else [],
        keyframes=dict(keyframes) if keyframes else {},
        font_faces=list(font_faces) if font_faces else [],
        container_queries=list(container_queries) if container_queries else [],
        supports_rules=list(supports_rules) if supports_rules else [],
        page_rules=list(page_rules) if page_rules else [],
        style_imports=list(style_imports) if style_imports else [],
        app_shell=app_shell,
        raw_postprocessors=list(raw_postprocessors) if raw_postprocessors else [],
        strict_csp=strict_csp,
        trusted_script_origins=list(trusted_script_origins) if trusted_script_origins else [],
        devtools_console_reminder=devtools_console_reminder,
        provider=provider,
    )
