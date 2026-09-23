"""
User-defined, reusable components -- v0.060, Stages 0-2.

See `docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md` for
the staged rollout this belongs to, and
`docs/Foundational/user-defined-components.md` for the underlying
design (Option A vs. Option B).

This module is the **hybrid** the implementation doc commits to:

- **Option A -- macro expansion (`mode="macro"`, the default).** A
  registered component call produces a marker `ARKNode` at call time;
  `expand_components()` walks the tree *before Normalization* and
  splices each marker's rendered subtree in its place, recursively.
  By the time Normalization/Validation run, the tree contains nothing
  but already-schema'd built-in types -- zero changes required
  anywhere downstream.
- **Option B -- registry-based late binding (`mode="registry"`,
  EXPERIMENTAL).** Opt-in per component. Stage 0 does not yet give
  Option B its own defining feature (identity preserved through to a
  per-backend render dispatch) -- that is real, larger follow-on work
  (see the implementation doc's later stages). What Stage 0 *does* do
  is make the mode a first-class, selectable thing today, dispatched
  through the same `if`/`elif` ladder the design doc describes, so
  later stages extend one branch instead of retrofitting a mode switch
  that was never there. Selecting `mode="registry"` today gets you
  Option A's own expansion behavior under the hood, plus an explicit
  "EXPERIMENTAL" marker on the component's `ComponentSpec` -- it is
  not yet a different *outcome*, only a different, forward-compatible
  *declaration*.

Stage 2 adds one more, mode-independent piece: `component(...,
default_style={...})` lets a component ship default CSS under its own
name, folded into the site's stylesheet (only when the component is
actually used -- see `collect_default_styles`) and onto the rendered
subtree's root `class_name` automatically (see `_apply_default_class`),
so a caller doesn't have to pass `class_name=` by hand just to pick up
sane default styling.

Stage 3 (see
`docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s Stage
3 row) gives `mode="registry"` its own real differentiator:
`register_backend_render(name, backend_name, render_fn)` (surfaced on
the decorated component as `.register_backend(backend_name)`, see
`arklight.api.component`) lets a `mode="registry"` component ship a
*different* render function per backend, falling back to its shared
`render_fn` (the same one Stage 0-2 already call "the" render
function) wherever a backend hasn't registered its own. This module's
own job in that story is narrow: `_render_once` tags a `mode=
"registry"` component's rendered root with a `ComponentOrigin` marker
-- but only when the component actually has at least one backend
override registered, so a `mode="registry"` component with no
overrides (the whole vocabulary before Stage 3, and the common case
after it) produces byte-identical output to before this stage existed.
Everything downstream of that marker -- resolving it against a
specific backend's overrides, converting an override's own rendered
subtree back into IR -- lives in `arklight.ir.component_dispatch`,
which this module has no dependency on (component expansion runs once,
backend-agnostically, in `arklight.compiler.pipeline.compile_site_file`;
per-backend resolution runs once per backend, in `arklight.compiler.
pipeline.build`, well after this module's job is done).

Stage 4 (see the implementation doc's Stage 4 row) gives a component
its own, instance-scoped reactive state: `component(..., state={...})`
declares one or more local state names (`ComponentState`) a component's
own render function can `Bind(...)`/`Action.*(...)`/`bind_class=`/
`bind_value=` against exactly like a page-level `State(...)`. Because
`IRPage.state` (`arklight.ir.build`) is only ever extracted from a
`Page(...)` node's *direct* children, and a component's rendered
subtree can land arbitrarily deep inside the tree, this module does two
things per component *instance* (not per component -- two calls to the
same state-owning component are two independent instances) at
expansion time, in `_render_once`: hoists a real, uniquely-namespaced
`State(...)` node for each declared local name onto a page-scoped
accumulator (`_hoist_component_state`), then rewrites that instance's
own rendered subtree so every reference to a local state name points
at its hoisted, namespaced key instead (`_rewrite_component_state_refs`).
`expand_ark_ast` splices each page's accumulated hoisted `State(...)`
nodes onto that page's own direct children once the whole page finishes
expanding. By the time Normalization/Validation run, a component
instance's own state is indistinguishable from a page-level
`State(...)` -- zero changes required anywhere downstream, the same
"Option A macro expansion" property every earlier stage already
preserved.
"""

from __future__ import annotations

import inspect
import itertools
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

from arklight.ast.nodes import STATE_REF_KEY, ActionRef, ARKNode, ClassBindSpec, ModelBindSpec, is_state_ref
from arklight.ir.schema import SCHEMA

# A component render function: takes resolved keyword props, returns
# the ARKNode subtree (built entirely out of other components -- built-in
# or user-defined) that the call site's marker node expands into.
RenderFn = Callable[..., Any]

# Closed vocabulary for `component(..., mode=...)` -- see module
# docstring. Any other value fails at *registration* time (a project
# config mistake), not at build time.
_VALID_MODES = ("macro", "registry")

# Recursion-depth ceiling for component expansion, mirroring the
# self-reference guard `validate.py` check #13 already applies to
# `Computed`/`Derive` dependency cycles. A legitimate, non-cyclical
# site is exceptionally unlikely to ever nest components this deep;
# this exists to turn an accidental cycle that *isn't* caught by the
# stack-based check below (there isn't a realistic way to construct
# one, but depth is cheap insurance) into a clear build-time error
# instead of a `RecursionError` traceback.
MAX_COMPONENT_EXPANSION_DEPTH = 64

# Stage 3: the internal, never-user-visible prop key `_render_once` tags
# a `mode="registry"` component's rendered root with, when (and only
# when) that component has at least one backend override registered.
# Carried as an ordinary (if oddly-named) entry in the node's own
# `props` dict from expansion time through Normalization/Validation --
# both already tolerate an unrecognized prop key (see `validate_node`,
# which only ever checks *required* props are present, never rejects
# an extra one) -- until `arklight.ir.build._ark_node_to_ir_node` pops
# it back off and lifts it onto `IRNode.component_origin`, the same
# "pop a compile-time-only prop into its own IR field" treatment
# `responsive_style` already gets there. Never reaches a backend's own
# attribute-rendering code (`arklight/backend/html/attrs.py` et al.):
# `arklight.ir.component_dispatch.resolve_backend_dispatch` always
# clears `component_origin` (with or without a matching override) well
# before a backend ever walks the tree looking for attributes to emit.
COMPONENT_ORIGIN_PROP_KEY = "__arklight_component_origin__"

# v0.060, Stage 4 ("Component-owned state" -- see
# docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md). The
# namespaced key format a `state=`-declaring component's local state
# names are rewritten into -- see `_namespaced_state_name`. Prefixed
# the same way `COMPONENT_ORIGIN_PROP_KEY` is (an internal, dunder-
# wrapped name no hand-written `State(...)`/`Bind(...)` call would
# plausibly collide with), and includes both the component's own name
# and a per-page instance counter so two call sites of the same
# component -- or two different components that both happen to declare
# a local state name like `"count"` -- never collide once hoisted onto
# the same page (see `expand_ark_ast`).
_COMPONENT_STATE_NAME_PREFIX = "__arklight_component_state__"


class ComponentError(RuntimeError):
    """
    Raised when a registered component is misused: an unknown prop, a
    missing required prop, or a cyclical/too-deep expansion. Caught by
    `arklight.compiler.pipeline.compile_site_file` the same way
    `ValidationError` is -- wrapped into a `CompileError` with the same
    message, never a raw traceback.
    """


class DuplicateComponentError(ComponentError):
    """
    Raised by `register_component(...)`/`register_backend_render(...)`
    when the call would silently replace an existing registration --
    a component name, or a `(component_name, backend_name)` per-backend
    override, that's already present in `COMPONENT_REGISTRY`. Both
    functions used to store the new entry over the old one
    unconditionally ("last call wins"), which quietly hid the common
    project mistake of two components accidentally sharing a name (or
    the same backend override registered twice) behind an outcome that
    looked fine at import time and only surfaced -- if at all -- as
    wrong rendered output much later, with no error pointing at either
    registration site.

    Pass `allow_redefine=True` to either function (surfaced as
    `allow_redefine=True` on `@component(...)` and
    `.register_backend(backend_name, allow_redefine=True)`) for the one
    legitimate case last-call-wins used to serve unconditionally:
    re-importing/reloading a components module during iterative
    development, where the replacement really is deliberate. That
    escape hatch is opt-in and per call site, not a global switch --
    a project turns it on exactly where it re-registers on purpose,
    everywhere else keeps the safety net.
    """


def positional_call_message(
    name: str,
    args: tuple[Any, ...],
    declared_props: "list[str]",
    *,
    caller: str | None = None,
) -> str:
    """
    v0.06506 (issue-register #5/#32): the message a user-defined
    component's call-site marker raises when it is called with
    positional arguments.

    A component's call site is keyword-only -- `Stat(label="a")`, never
    `Stat("a")` -- because props are matched by *name* against the
    `props=` contract, and built-in components' positional *children*
    have no equivalent on a user-defined one. Before this message
    existed, the marker's own `**call_props` signature made Python
    itself refuse the call with `Stat() takes 0 positional arguments
    but 2 were given`: accurate about Python, silent about ARKlight's
    actual rule and about what the component does accept.

    `declared_props` is the component's `props=` keys in declared
    order (empty when it declares none). `caller` is an optional
    `"file:line"` for the offending call site.
    """
    count = len(args)
    plural = "" if count == 1 else "s"
    head = (
        f"Component {name!r} was called with {count} positional "
        f"argument{plural}, but user-defined components accept keyword "
        "props only."
    )
    if not declared_props:
        detail = (
            f" {name!r} declares no props, so it takes no arguments at "
            f"all: call it as {name}()."
        )
    elif count <= len(declared_props):
        example = ", ".join(f"{p}=..." for p in declared_props[:count])
        detail = (
            f" Declared props: {declared_props!r}. Pass each value by "
            f"name instead, e.g. {name}({example})."
        )
    else:
        detail = (
            f" It declares only {len(declared_props)} prop(s): "
            f"{declared_props!r}."
        )
    tail = (
        " Positional children are not supported on a user-defined "
        "component; pass content through a declared prop."
    )
    where = f" (called at {caller})" if caller else ""
    return head + detail + tail + where


def call_render_fn(
    name: str,
    render_fn: Callable[..., Any],
    resolved_props: dict[str, Any],
    *,
    what: str = "render function",
) -> Any:
    """
    v0.06506 (issue-register #32): call `render_fn(**resolved_props)`,
    but check first that the keyword arguments actually *bind* to its
    signature, so a `props=` contract that disagrees with the function
    it belongs to fails as a `ComponentError` naming both sides instead
    of a raw `TypeError` from two frames down.

    Only argument binding is checked (`inspect.Signature.bind`, which
    never runs the function), so this cannot reject a call that would
    have succeeded: every prop the contract declares is passed by
    keyword, so a declared prop the function has no parameter for -- or
    a required parameter no prop supplies -- was always going to raise
    `TypeError`. A function whose signature can't be introspected
    (`ValueError`/`TypeError` from `inspect.signature`) is called as
    before, unchecked. Errors raised *inside* the function are never
    touched.
    """
    try:
        signature = inspect.signature(render_fn)
    except (TypeError, ValueError):
        return render_fn(**resolved_props)
    try:
        signature.bind(**resolved_props)
    except TypeError as exc:
        raise ComponentError(
            f"Component {name!r}: props= and the {what}'s signature "
            f"disagree -- {exc}. Declared props: "
            f"{sorted(resolved_props)!r}; {what} parameters: "
            f"{list(signature.parameters)!r}. Every declared prop is "
            "passed by keyword, so each must be a parameter (or the "
            "function must accept **kwargs), and every required "
            "parameter must be declared in props=."
        ) from exc
    return render_fn(**resolved_props)


@dataclass(frozen=True)
class Prop:
    """
    One entry in a component's props contract -- the `NodeSpec`-shaped
    declaration `docs/Foundational/user-defined-components.md` (Section
    3, "What this needs that ARKlight doesn't have yet") calls for.

        @component(props={"active": Prop(default=None)})
        def NavBar(active=None):
            ...

    `default`: use the `_REQUIRED` sentinel (the default) to mean "this
    prop must be supplied at every call site"; any other value
    (including `None`) makes the prop optional with that default.
    `type`: optional; if given, the resolved value is checked with
    `isinstance()` and a mismatch fails the build with a Validation-
    quality message instead of a raw `TypeError` inside the render
    function two frames down the stack.
    """

    type: type | tuple[type, ...] | None = None
    default: Any = "__ARKLIGHT_REQUIRED_PROP__"

    @property
    def required(self) -> bool:
        return self.default == "__ARKLIGHT_REQUIRED_PROP__"


@dataclass(frozen=True)
class ComponentState:
    """
    One entry in a component's `state={...}` declaration -- v0.060,
    Stage 4 ("Component-owned state", see
    docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md).

        @component(state={"open": ComponentState(False)})
        def Accordion(label=""):
            return Container(
                Button(label, on_click=Action.toggle_bool("open")),
                Show(Predicate.truthy("open"), Container(...)),
            )

    Mirrors `State(...)`'s own two knobs: `initial` is the value a
    *fresh instance* of this component's local state starts at (every
    call site gets its own independent copy, never a value shared
    across instances -- see `_namespaced_state_name`); `persist`
    mirrors `State(..., persist=True)`, opting that one instance's key
    into `localStorage` under its own instance-namespaced key,
    independent of any other instance of the same component.

    A bare initial value (`state={"open": False}`) is accepted too --
    `arklight.api._validate_component_state` normalizes it into
    `ComponentState(initial=False)` at registration time. This
    dataclass only needs to be spelled out explicitly when a component
    wants `persist=True`, the same "usually just the bare value,
    sometimes a small structured object" ergonomics `Prop` already has
    for `type=`.
    """

    initial: Any = None
    persist: bool = False


@dataclass(frozen=True)
class ComponentSpec:
    """Everything the expansion pass needs to know about one registered
    user component. Built by `component(...)`/`register_component(...)`,
    never constructed by hand in a site file."""

    name: str
    render_fn: RenderFn
    props: dict[str, Prop] = field(default_factory=dict)
    mode: str = "macro"
    # v0.060, Stage 2 ("Default styling hook" -- see
    # docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md). An
    # optional `{css-property: value}` dict, same shape `Site.style(...)`
    # already accepts (pseudo-class shorthand included), registered at
    # `component(..., default_style={...})` time and validated by
    # `arklight.api.component` the same way `Site.style()` validates its
    # own `rules` -- by the time it lands here it's already known-good
    # CSS. `None` (the default) means this component ships no default
    # styling at all, unchanged from Stage 0/1 behavior.
    default_style: dict[str, str] | None = None
    # v0.060, Stage 3 ("Option B's real differentiator" -- see
    # docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md).
    # `backend_name -> render_fn`, populated by
    # `register_backend_render(...)`/`.register_backend(...)` --
    # never at `component(...)`/`register_component(...)` registration
    # time itself, since a project registers its backend overrides
    # (if any) as separate, later declarations, same "the component
    # exists first, extras attach to it after" ordering `default_style`
    # already established for Stage 2. Empty for every component before
    # Stage 3, and for any `mode="registry"` component that never opts
    # in -- both behave exactly as Stage 0-2 already do (see
    # `_render_once`).
    backend_render_fns: dict[str, RenderFn] = field(default_factory=dict)
    # v0.060, Stage 4 ("Component-owned state" -- see
    # docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md).
    # `local_name -> ComponentState`, registered at `component(...,
    # state={...})` time and validated by `arklight.api.component` the
    # same way `default_style` already is. Empty for every component
    # before Stage 4, and for any component that never declares its
    # own state -- both behave exactly as Stage 0-3 already do (see
    # `_render_once`, which only does any extra work here when this is
    # non-empty).
    state: dict[str, ComponentState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in _VALID_MODES:
            raise ValueError(
                f"component {self.name!r}: mode={self.mode!r} is not one of "
                f"{_VALID_MODES!r}."
            )


@dataclass(frozen=True)
class ComponentOrigin:
    """
    Stage 3: what `COMPONENT_ORIGIN_PROP_KEY` carries -- which
    component instance a rendered root node came from, and the exact
    resolved props it was rendered with, so a backend override can be
    called with the same arguments the shared `render_fn` already was.
    Constructed once, by `_render_once`, immediately after resolving
    `resolved_props`; never mutated afterward (`ARKNode`/`IRNode`
    props dicts are copied whole on every transform this codebase
    already does, so this rides along by value).
    """

    name: str
    resolved_props: dict[str, Any] = field(default_factory=dict)


# Populated by `component(...)`/`register_component(...)` as a project's
# site file imports and decorates its own render functions -- a plain
# module-level dict, not `arklight.ir.schema.SCHEMA`: user components are
# per-project vocabulary, never a shared global one, so they never touch
# the closed built-in schema (see the design doc's Option A writeup).
COMPONENT_REGISTRY: dict[str, ComponentSpec] = {}

# Attribute `arklight.api.component` sets on the callable it returns,
# recording whether the author passed `allow_redefine=True`. The site
# loader's namespace-shadowing check (`arklight.parser.preamble.
# check_namespace_shadowing`) reads it, so a *deliberate* override of a
# name a preamble already bound isn't flagged as an accident -- the
# same explicit opt-in `register_component` itself honors.
ALLOW_REDEFINE_MARKER = "__ark_allow_redefine__"


def register_component(
    name: str,
    render_fn: RenderFn,
    *,
    props: dict[str, Prop] | None = None,
    mode: str = "macro",
    default_style: dict[str, str] | None = None,
    state: dict[str, ComponentState] | None = None,
    allow_redefine: bool = False,
) -> ComponentSpec:
    """
    Register `render_fn` under `name`.

    Re-registering an existing name raises `DuplicateComponentError`
    unless `allow_redefine=True` is passed -- this used to be silent,
    unconditional "last call wins" (the same rule `Site.style(...)`
    used to apply to custom CSS classes), which hid an accidental name
    collision between two unrelated components behind output that
    looked correct at import time. Pass `allow_redefine=True` for the
    one case that rule was actually protecting: re-importing/reloading
    a components module during iterative development, where the
    replacement is deliberate and the previous entry is known-stale.

    `default_style`, if given, is expected to already be validated
    (see `arklight.api.component`) -- this function stores it verbatim,
    it doesn't re-check CSS syntax itself, same division of labor
    `props`/`mode` already have between `arklight.api.component` (the
    user-facing, validating entry point) and this lower-level registry
    function. `state` (v0.060, Stage 4) is the same story: expected
    already-normalized into `{local_name: ComponentState}` by
    `arklight.api._validate_component_state`, stored verbatim here.
    """
    if name in SCHEMA and not allow_redefine:
        # `expand_ark_ast` resolves a node by `COMPONENT_REGISTRY.get(
        # node.type)` *before* anything consults the built-in schema,
        # so a user component named after a built-in (`Button`,
        # `Card`, ...) used to silently take over every node of that
        # type in the whole site -- including ones the site's own
        # vocabulary produced -- with no diagnostic anywhere. Same
        # "fail loudly, opt in explicitly" rule as the duplicate-
        # registration check just below.
        raise DuplicateComponentError(
            f"A component named {name!r} would shadow the built-in "
            f"{name!r} component: every {name}(...) in the site, "
            "including ARKlight's own, would silently be replaced by "
            "yours. Rename it, or if overriding the built-in is "
            "deliberate, pass allow_redefine=True: @component(..., "
            "allow_redefine=True)."
        )
    if name in COMPONENT_REGISTRY and not allow_redefine:
        raise DuplicateComponentError(
            f"A component named {name!r} is already registered. "
            "Registering it again would silently replace the earlier "
            "definition -- if that's deliberate (e.g. re-importing a "
            "components module during iterative development), pass "
            f"allow_redefine=True: register_component({name!r}, ..., "
            "allow_redefine=True) or @component(..., "
            "allow_redefine=True). Otherwise, two different components "
            f"are colliding on the name {name!r}; rename one of them."
        )
    spec = ComponentSpec(
        name=name,
        render_fn=render_fn,
        props=dict(props or {}),
        mode=mode,
        default_style=dict(default_style) if default_style else None,
        state=dict(state) if state else {},
    )
    COMPONENT_REGISTRY[name] = spec
    return spec


def register_backend_render(
    component_name: str,
    backend_name: str,
    render_fn: RenderFn,
    *,
    allow_redefine: bool = False,
) -> ComponentSpec:
    """
    Stage 3: register `render_fn` as `component_name`'s override for
    `backend_name` (e.g. `"html"` -- `Backend.name` on whichever
    `arklight.backend.base.Backend` subclass this is for). Surfaced to
    site/component authors as `.register_backend(backend_name)` on the
    callable `component(...)` returns -- see `arklight.api.component`
    -- this lower-level entry point exists for the same reason
    `register_component` does: something a test or an advanced caller
    can reach directly, without going through the decorator.

    Only a `mode="registry"` component can take a backend override --
    per-backend dispatch is Option B's own defining feature (see this
    module's docstring); a `mode="macro"` component has no `identity`
    for a backend to look up an override *by*, since its marker is
    already fully spliced away before this registry is ever consulted
    again. Raises `ComponentError` for an unregistered `component_name`
    or a `mode="macro"` one -- both are project mistakes caught at
    registration time, the same "fail where the mistake was made, not
    three stages later" discipline `_resolve_props` already applies to
    a bad prop.

    Re-registering an override for a `(component_name, backend_name)`
    pair that already has one raises `DuplicateComponentError` unless
    `allow_redefine=True` is passed -- same reasoning and same escape
    hatch `register_component` uses for re-registering a component
    outright: this used to be silent last-registration-wins, which hid
    an accidental double registration of the same backend override
    behind output that looked fine until the wrong render function
    turned out to be the one that stuck.
    """
    spec = COMPONENT_REGISTRY.get(component_name)
    if spec is None:
        raise ComponentError(
            f"Cannot register a {backend_name!r} render function for "
            f"{component_name!r}: no component with that name is "
            "registered yet. Register the component with @component(...) "
            "first."
        )
    if spec.mode != "registry":
        raise ComponentError(
            f"Cannot register a {backend_name!r} render function for "
            f"{component_name!r}: only mode=\"registry\" components support "
            f"per-backend rendering (this component was registered with "
            f"mode={spec.mode!r}). Register it with "
            "@component(mode=\"registry\") to opt in."
        )
    if not backend_name:
        raise ComponentError(
            f"Cannot register a backend render function for "
            f"{component_name!r}: backend_name must be a non-empty string."
        )
    if backend_name in spec.backend_render_fns and not allow_redefine:
        raise DuplicateComponentError(
            f"{component_name!r} already has a {backend_name!r} backend "
            "render function registered. Registering it again would "
            "silently replace the earlier override -- if that's "
            "deliberate, pass allow_redefine=True: "
            f"register_backend_render({component_name!r}, "
            f"{backend_name!r}, ..., allow_redefine=True) or "
            f"@{component_name}.register_backend({backend_name!r}, "
            "allow_redefine=True). Otherwise this is likely two "
            f"unrelated registrations for {backend_name!r} colliding by "
            "mistake."
        )
    new_backend_render_fns = dict(spec.backend_render_fns)
    new_backend_render_fns[backend_name] = render_fn
    new_spec = replace(spec, backend_render_fns=new_backend_render_fns)
    COMPONENT_REGISTRY[component_name] = new_spec
    return new_spec


def _component_source_file(render_fn: RenderFn) -> str | None:
    """Best-effort absolute path to the file `render_fn` was defined
    in, or `None` if it can't be determined (a builtin, a function
    built dynamically with no real file, ...). Used only by
    `unregister_components_under` below -- never anything that affects
    a component's actual behavior."""
    try:
        return str(Path(inspect.getfile(render_fn)).resolve())
    except (TypeError, OSError):
        return None


def unregister_components_under(directory: str) -> None:
    """Remove every `COMPONENT_REGISTRY` entry whose render function
    was defined in a file under `directory`.

    Exists for the site loader (`arklight.parser.loader._project_imports`),
    which evicts a project's own modules from `sys.modules` after each
    `load_site()` call so a dev-server rebuild re-imports them fresh
    instead of reusing a stale cached module -- see that function's
    docstring. `COMPONENT_REGISTRY` is a plain module-level dict here,
    not part of that eviction, so without this a rebuilt project's
    `components/` module re-running its `@component(...)` decorators
    used to collide with the *previous* build's still-registered
    entries and raise `DuplicateComponentError`, even though nothing
    about the component actually changed -- `allow_redefine=True`
    could silence it, but that also silences a genuine same-name
    collision between two unrelated components, which is exactly what
    `DuplicateComponentError` exists to catch. Called with the site's
    own directory right after the module eviction it mirrors, so only
    that project's components are dropped: a component a project pulls
    in from an installed package (ACC or otherwise) lives outside
    `directory` and is left alone, same as those modules are left out
    of the `sys.modules` eviction.
    """
    directory = str(Path(directory).resolve())
    stale = [
        name
        for name, spec in COMPONENT_REGISTRY.items()
        if (source := _component_source_file(spec.render_fn)) is not None
        and (source == directory or source.startswith(directory + os.sep))
    ]
    for name in stale:
        del COMPONENT_REGISTRY[name]


def _resolve_props(spec: ComponentSpec, call_props: dict[str, Any]) -> dict[str, Any]:
    """
    Check `call_props` (the kwargs a call site passed) against
    `spec.props`, filling in defaults for anything omitted. Raises
    `ComponentError` for an unknown prop, a missing required prop, or a
    type mismatch -- the "Validation-quality error instead of a raw
    Python TypeError" the design doc asks for.
    """
    unknown = sorted(set(call_props) - set(spec.props))
    if unknown:
        raise ComponentError(
            f"Component {spec.name!r} received unexpected prop(s) "
            f"{unknown!r}. Declared props: {sorted(spec.props) or '(none)'}."
        )

    resolved: dict[str, Any] = {}
    for prop_name, prop_spec in spec.props.items():
        if prop_name in call_props:
            value = call_props[prop_name]
            if prop_spec.type is not None and not isinstance(value, prop_spec.type):
                expected = prop_spec.type
                raise ComponentError(
                    f"Component {spec.name!r}, prop {prop_name!r}: expected "
                    f"{expected!r}, got {type(value).__name__!r} ({value!r})."
                )
            resolved[prop_name] = value
        elif prop_spec.required:
            raise ComponentError(
                f"Component {spec.name!r} is missing required prop {prop_name!r}."
            )
        else:
            resolved[prop_name] = prop_spec.default
    return resolved


def _apply_default_class(rendered: Any, class_name: str) -> Any:
    """
    Stage 2: fold `class_name` onto `rendered`'s root, the mechanism
    behind "a user component can ship with sane default styling
    instead of forcing every caller to pass `class_name=`"
    (`user-defined-components.md`, Option A's requirements list).

    Only applies when `rendered` is itself an `ARKNode` -- a component
    whose render function returns a list (multiple top-level siblings)
    or a bare string/number has no single root to attach a class to,
    so this is a no-op for those shapes, same as every other prop
    that's meaningless on a non-`ARKNode` child. If the render function
    already gave its root an explicit `class_name` (as the design
    doc's own `NavBar` example does, with `class_name="nav"`), the
    component's own name is appended rather than overwriting it --
    same "merge, don't clobber" convention `Bind.when(...)`'s
    pre-fill already uses for `bind_class` (see
    `arklight/backend/html/attrs.py`) -- and it's a no-op if that
    class is already present, so re-expansion (a component nested
    inside itself's own default-style path, or repeated compiles)
    can't keep appending duplicates.
    """
    if not isinstance(rendered, ARKNode):
        return rendered
    existing = rendered.props.get("class_name")
    classes = existing.split() if isinstance(existing, str) and existing else []
    if class_name not in classes:
        classes.append(class_name)
    new_props = dict(rendered.props)
    new_props["class_name"] = " ".join(classes)
    return replace(rendered, props=new_props)


def apply_default_style_class(component_name: str, rendered: Any) -> Any:
    """
    Public wrapper around `_apply_default_class`, keyed by component
    name rather than a bare class-name string -- Stage 3's own reason
    for this existing: `arklight.ir.component_dispatch` needs the exact
    same "fold `.{ComponentName}` onto the rendered root, merge rather
    than clobber, no-op on a non-`ARKNode` result" treatment for a
    backend override's own rendered subtree that `_render_once` already
    gives the shared `render_fn`'s output below -- `default_style` is
    mode-independent *and* backend-independent, a registration-time
    property of the component itself, not of which render function
    happened to produce a given subtree.
    """
    return _apply_default_class(rendered, component_name)


def _tag_component_origin(rendered: Any, name: str, resolved_props: dict[str, Any]) -> Any:
    """
    Stage 3: stamp `rendered`'s root with a `ComponentOrigin`, under
    `COMPONENT_ORIGIN_PROP_KEY` -- see that constant's own docstring
    for the full trip this takes through Normalization/Validation/IR-
    build before `arklight.ir.component_dispatch` reads it back off.
    Same "no single root, no-op" shape as `_apply_default_class` above,
    for the same reason: a component whose render function returns a
    list of siblings (or a bare string) has nothing to tag identity
    onto, so a backend override is simply unreachable for that call --
    unchanged, Option-A-shaped behavior for it, exactly as if this
    component had never registered any backend overrides at all.
    """
    if not isinstance(rendered, ARKNode):
        return rendered
    new_props = dict(rendered.props)
    new_props[COMPONENT_ORIGIN_PROP_KEY] = ComponentOrigin(
        name=name, resolved_props=dict(resolved_props)
    )
    return replace(rendered, props=new_props)


def _namespaced_state_name(component_name: str, instance_id: int, local_name: str) -> str:
    """
    v0.060, Stage 4: the page-level `State(...)` name one component
    instance's local state name (`local_name`, whatever the component's
    own render function called it, e.g. `"open"`) is rewritten into --
    unique per `(component_name, instance_id)` pair, so two call sites
    of the same component (or two different components that both
    happen to pick the same local name) never collide once hoisted
    onto the same page. `instance_id` comes from a per-page counter
    `expand_ark_ast` threads through expansion -- see that function's
    own docstring.
    """
    return f"{_COMPONENT_STATE_NAME_PREFIX}{component_name}__{instance_id}__{local_name}"


def _hoist_component_state(
    spec: ComponentSpec, instance_id: int, hoisted: list[ARKNode]
) -> dict[str, str]:
    """
    v0.060, Stage 4: for one instance of a `state=`-declaring
    component, append a real `State(...)` `ARKNode` (in declaration
    order) onto `hoisted` for every locally-declared name, under that
    name's instance-namespaced key -- see `_namespaced_state_name`.
    `hoisted` is a page-scoped, mutable accumulator `expand_ark_ast`
    splices onto the owning page's own direct children once expansion
    of that whole page finishes, the same "declared where the design
    doc says state belongs -- directly on `Page(...)`" place a
    hand-written `State(...)` call already occupies (`_extract_page_state`
    only ever looks at a Page node's *direct* children).

    Returns the `{local_name: namespaced_name}` map
    `_rewrite_component_state_refs` needs to retarget this instance's
    own `Bind(...)`/`Action.*(...)`/`bind_class=`/`bind_value=`
    references onto the state this just hoisted, so that by the time
    Normalization/Validation run, this instance's component-owned
    state is indistinguishable from a page-level `State(...)` --
    because it now *is* one.
    """
    name_map: dict[str, str] = {}
    for local_name, comp_state in spec.state.items():
        namespaced = _namespaced_state_name(spec.name, instance_id, local_name)
        name_map[local_name] = namespaced
        hoisted.append(
            ARKNode(
                type="State",
                props={
                    "name": namespaced,
                    "initial": comp_state.initial,
                    "persist": comp_state.persist,
                },
                children=[],
            )
        )
    return name_map


def _rewrite_component_state_refs(value: Any, name_map: dict[str, str]) -> Any:
    """
    v0.060, Stage 4: recursively rewrite every reference to one of
    `name_map`'s local component-state names -- a `Bind(name)` node, an
    `on_click=Action.*(...)` (`ActionRef.state`, and any arg fed from
    state via `Bind(name)`, i.e. a `{"__state__": name}` marker), a
    `bind_class=Bind.when(...)` (`ClassBindSpec.state`), or a
    `bind_value=Bind.model(...)` (a plain string prop) -- into that
    name's instance-namespaced page-state key. Runs once, on a
    `state=`-declaring component's own freshly rendered subtree, before
    Normalization/Validation ever see it (same pipeline position every
    other expansion-time transform in this module already runs at) --
    so every downstream check (`validate.py`'s Bind/Action/bind_class/
    bind_value-against-declared-`State(...)` rules, the JS runtime's
    own hydration blob) treats a component-owned state name exactly
    like an ordinary page-level `State(...)`, with zero special-casing
    anywhere past this point.

    A name *not* in `name_map` (a prop value the caller passed in from
    the page's own `State(...)`, e.g. `Card(count_state=Bind("total"))`
    -- see the module docstring's "consume `Bind(...)`/`ActionRef`
    values passed in as props" carve-out `user-defined-components.md`
    Section 4 already established as in-scope before this stage even
    existed) is left completely untouched; only a component's *own*
    locally-declared state names are ever rewritten here.
    """
    if isinstance(value, list):
        return [_rewrite_component_state_refs(item, name_map) for item in value]
    if not isinstance(value, ARKNode):
        return value

    if value.type == "Bind":
        name = value.props.get("name")
        if name in name_map:
            new_props = dict(value.props)
            new_props["name"] = name_map[name]
            return replace(value, props=new_props)
        return value

    new_props = value.props
    props_changed = False

    on_click = new_props.get("on_click")
    if isinstance(on_click, ActionRef):
        # The action's *target* (`state`) and, for the live-input ->
        # action-value capability fix, any arg that *reads* state
        # (`Action.append("tasks", Bind("draft"))` ->
        # `{"__state__": "draft"}`) both name component-local state
        # that has to move to its namespaced page key together -- a
        # target renamed while its value-source wasn't would read a
        # name that no longer exists on the page.
        rewritten_args = {
            key: (
                {STATE_REF_KEY: name_map[val[STATE_REF_KEY]]}
                if is_state_ref(val) and val[STATE_REF_KEY] in name_map
                else val
            )
            for key, val in on_click.args.items()
        }
        args_changed = rewritten_args != on_click.args
        if on_click.state in name_map or args_changed:
            if not props_changed:
                new_props = dict(new_props)
                props_changed = True
            new_props["on_click"] = replace(
                on_click,
                state=name_map.get(on_click.state, on_click.state),
                args=rewritten_args,
            )

    bind_class = new_props.get("bind_class")
    if isinstance(bind_class, ClassBindSpec) and bind_class.state in name_map:
        if not props_changed:
            new_props = dict(new_props)
            props_changed = True
        new_props["bind_class"] = replace(bind_class, state=name_map[bind_class.state])

    bind_value = new_props.get("bind_value")
    if isinstance(bind_value, str) and bind_value in name_map:
        if not props_changed:
            new_props = dict(new_props)
            props_changed = True
        new_props["bind_value"] = name_map[bind_value]
    elif isinstance(bind_value, ModelBindSpec) and bind_value.state in name_map:
        if not props_changed:
            new_props = dict(new_props)
            props_changed = True
        new_props["bind_value"] = replace(bind_value, state=name_map[bind_value.state])

    new_children = [_rewrite_component_state_refs(c, name_map) for c in value.children]
    children_changed = new_children != value.children

    if not props_changed and not children_changed:
        return value
    return replace(
        value,
        props=new_props if props_changed else value.props,
        children=new_children if children_changed else value.children,
    )


def _render_once(
    spec: ComponentSpec,
    resolved_props: dict[str, Any],
    *,
    instance_id: int | None = None,
    hoisted: list[ARKNode] | None = None,
) -> Any:
    """
    The hybrid dispatch itself -- Option A vs. Option B, as an
    `if`/`elif` ladder over `spec.mode`, exactly as
    `docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`
    describes it. Every branch is required to return something
    `expand_node` can keep expanding (an `ARKNode`, a string/number, a
    list of either, or `None`/`False`) -- the same shape
    `normalize_children` already accepts from any component call.

    `instance_id`/`hoisted` (v0.060, Stage 4) are only ever consulted
    when `spec.state` is non-empty -- see `expand_node`, the only real
    caller, for how they're produced and threaded through. Every
    component before Stage 4, and every Stage-4-aware component that
    simply never declares `state=`, ignores both entirely.
    """
    if spec.mode == "macro":
        # Option A: plain, immediate call -- the marker is expanded
        # away right here, nothing about it survives past this pass.
        rendered = call_render_fn(spec.name, spec.render_fn, resolved_props)
    elif spec.mode == "registry":
        # Option B: still resolves through the component's shared
        # `render_fn` here, same as Option A above -- this call always
        # produces the *default* rendering, the one every backend
        # without its own override falls back to. Stage 3 (see below)
        # is what gives a backend an actual way to supply a different
        # subtree for the *same* call site; this branch itself is
        # unchanged from Stage 0/1/2.
        rendered = call_render_fn(spec.name, spec.render_fn, resolved_props)
    else:  # pragma: no cover -- unreachable, ComponentSpec.__post_init__ already validated this
        raise ComponentError(f"Component {spec.name!r}: unknown mode {spec.mode!r}.")

    # Stage 4: only a `state=`-declaring component does any extra work
    # here -- hoist one `State(...)` per locally-declared name (under
    # this call's own `instance_id`), then retarget every reference to
    # one of those local names inside `rendered` onto its hoisted,
    # namespaced key. A component with no `state=` declared (every
    # component before Stage 4, and most components after it too)
    # skips this entirely -- `rendered` passes through unchanged.
    if spec.state:
        assert instance_id is not None and hoisted is not None, (
            "expand_node is required to supply instance_id/hoisted for a "
            "state=-declaring component; see expand_node's own ComponentError "
            "for the caller-facing message when it can't."
        )
        name_map = _hoist_component_state(spec, instance_id, hoisted)
        rendered = _rewrite_component_state_refs(rendered, name_map)

    # Stage 2: both branches above get the same default-class
    # treatment -- `default_style` isn't mode-specific, it's a
    # registration-time property of the component itself.
    if spec.default_style:
        rendered = _apply_default_class(rendered, spec.name)

    # Stage 3: only a `mode="registry"` component that actually has at
    # least one backend override registered gets tagged -- a component
    # with none (every component before Stage 3, and most
    # mode="registry" components after it too) produces the exact same
    # `ARKNode` it always did, with no extra prop riding along for
    # `arklight.ir.component_dispatch` to strip back out later.
    if spec.mode == "registry" and spec.backend_render_fns:
        rendered = _tag_component_origin(rendered, spec.name, resolved_props)
    return rendered


def expand_child(
    value: Any,
    stack: tuple[str, ...],
    used: set[str] | None = None,
    hoisted: list[ARKNode] | None = None,
    counter: "itertools.count[int] | None" = None,
) -> Any:
    """Expand one child position -- an `ARKNode`, a nested list, or a
    plain value passed through unchanged (mirrors
    `arklight.ir.normalize.normalize_children`'s own recursive shape,
    since this pass runs one stage earlier over the same kind of tree).

    `hoisted`/`counter` (v0.060, Stage 4) are threaded straight through
    to `expand_node` unchanged -- see that function's own docstring."""
    if isinstance(value, ARKNode):
        return expand_node(value, stack, used, hoisted, counter)
    if isinstance(value, list):
        return [expand_child(item, stack, used, hoisted, counter) for item in value]
    return value


def expand_node(
    node: ARKNode,
    stack: tuple[str, ...] = (),
    used: set[str] | None = None,
    hoisted: list[ARKNode] | None = None,
    counter: "itertools.count[int] | None" = None,
) -> Any:
    """
    Expand `node` and everything beneath it. If `node.type` names a
    registered component, its marker is replaced by its rendered
    subtree (itself recursively expanded, in case that subtree uses
    other user components); otherwise `node` is returned with its own
    children expanded in place, unchanged in every other respect.

    `used`, if given, collects the name of every component actually
    expanded (not just registered) -- Stage 2's own reason for
    threading this through: `arklight.compiler.pipeline` needs to know
    which components a build *actually called* before it can decide
    which `default_style`s belong in that build's stylesheet, the same
    "purely additive, opt into it by passing the set" shape `on_stage`
    already uses elsewhere in this codebase. `None` (the default)
    keeps every pre-Stage-2 call site -- including direct test calls to
    this function -- unaffected; expansion behaves identically either
    way, this only controls whether usage is recorded anywhere.

    `hoisted`/`counter` (v0.060, Stage 4) exist for exactly one reason:
    a `state=`-declaring component. `counter` (an `itertools.count()`,
    fresh per page -- see `expand_ark_ast`) hands out this call's
    unique `instance_id`; `hoisted` is where this call's own
    `State(...)` node(s) get appended (see `_hoist_component_state`),
    to later be spliced onto the *page's* own direct children once
    that whole page finishes expanding -- a component's rendered
    subtree can land arbitrarily deep inside the tree, but `State(...)`
    is only ever meaningful as a direct child of `Page(...)`
    (`_extract_page_state` only ever looks there). Both default to
    `None`: a component that never declares `state=` never touches
    either, so every pre-Stage-4 call site here -- including direct
    test calls to this function with no `hoisted=`/`counter=` at all --
    is completely unaffected. Calling `expand_node`/`expand_child`
    directly (skipping `expand_ark_ast`) on a tree that *does* contain
    a `state=`-declaring component's call site without supplying both
    raises `ComponentError` below, rather than silently dropping that
    component's state -- this is what happens today, for instance, if
    a `mode="registry"` backend override (`arklight.ir.
    component_dispatch`, which calls `expand_node(rendered)` bare) uses
    a state-owning component: not supported yet, see this module's own
    docstring and `docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s
    Stage 4 "explicitly out of scope" note.
    """
    spec = COMPONENT_REGISTRY.get(node.type)
    if spec is None:
        return replace(
            node,
            children=[expand_child(c, stack, used, hoisted, counter) for c in node.children],
        )

    if node.type in stack:
        chain = " -> ".join((*stack, node.type))
        raise ComponentError(
            f"Cyclical component expansion detected: {chain}. A component "
            "cannot (directly or transitively) expand into itself."
        )
    if len(stack) >= MAX_COMPONENT_EXPANSION_DEPTH:
        raise ComponentError(
            f"Component expansion exceeded the maximum nesting depth "
            f"({MAX_COMPONENT_EXPANSION_DEPTH}) while expanding {node.type!r}. "
            "This almost always means an unintended cycle."
        )

    if used is not None:
        used.add(node.type)

    resolved_props = _resolve_props(spec, node.props)

    instance_id: int | None = None
    if spec.state:
        if hoisted is None or counter is None:
            raise ComponentError(
                f"Component {spec.name!r} declares its own state "
                f"(state={{...}}) but is being expanded somewhere that can't "
                "hoist that state onto a page -- either a bare expand_node()/"
                "expand_child() call outside expand_ark_ast(...), or a "
                "mode=\"registry\" backend override's own rendered subtree "
                "(v0.060 Stage 3). A state-owning component used inside a "
                "backend override is not supported yet; use expand_ark_ast(...) "
                "for a normal page build."
            )
        instance_id = next(counter)

    rendered = _render_once(spec, resolved_props, instance_id=instance_id, hoisted=hoisted)
    return expand_child(rendered, (*stack, node.type), used, hoisted, counter)


def expand_ark_ast(
    pages: dict[str, ARKNode], *, used: set[str] | None = None
) -> dict[str, ARKNode]:
    """
    Expand every page's ARK AST tree. Called between ARK-AST
    construction (`Site.build_ark_ast()`) and Normalization -- see
    `arklight.compiler.pipeline.compile_site_file`. A no-op (returns
    `pages` re-wrapped, unchanged) for a site that never registered or
    called a user component, same "purely additive" contract every
    other optional pipeline addition in this codebase follows.

    `used`, if given, is populated (in place) with the name of every
    component actually expanded across every page -- see
    `expand_node`'s own docstring. Defaults to `None`, so this
    function's return value and side effects on `pages` are unchanged
    from Stage 0/1; passing a set is purely additive.

    v0.060, Stage 4: this is the one expansion entry point that can
    actually finish a `state=`-declaring component's trip onto the
    page. Each page gets its own fresh `hoisted` accumulator and
    `instance_id` counter (an `itertools.count()`, so instance ids are
    unique *within* a page -- there's no need for cross-page
    uniqueness, since each page's own `IRPage.state` is independent).
    After a page's tree finishes expanding, every `State(...)` node
    `hoisted` collected along the way (declaration order, i.e. the
    order component instances were encountered depth-first) is
    appended onto that page's own direct children -- the exact place
    `_extract_page_state` (`arklight.ir.build`) looks for `State(...)`,
    so by the time Normalization/Validation run, a component instance's
    own state is a completely ordinary page-level `State(...)`, with
    zero special-casing anywhere downstream of this function. A page
    that never uses a `state=`-declaring component gets an empty
    `hoisted` list and its children are left byte-for-byte as
    `expand_node` already produced them -- unchanged from Stage 0-3.
    """
    result: dict[str, ARKNode] = {}
    for route, page in pages.items():
        hoisted: list[ARKNode] = []
        counter = itertools.count()
        expanded = expand_node(page, used=used, hoisted=hoisted, counter=counter)
        if hoisted:
            expanded = replace(expanded, children=[*expanded.children, *hoisted])
        result[route] = expanded
    return result


def collect_default_styles(used: set[str]) -> dict[str, dict[str, str]]:
    """
    Stage 2: `{component_name: rules}` for every name in `used` that's
    both still registered (it may have been expanded by an earlier
    build in the same process and since deregistered/overwritten --
    unlikely, but `COMPONENT_REGISTRY` is a plain global dict, not
    build-scoped) and actually carries a `default_style`. Returns a
    fresh dict each call (never the registry's own `default_style`
    dicts by reference), ready to merge into `Site.custom_styles`
    shaped input -- see `arklight.compiler.pipeline.compile_site_file`,
    which is the only real caller.

    Deliberately keyed on *usage*, not on everything in
    `COMPONENT_REGISTRY`: the registry is a per-process global (several
    unrelated site files can register components in the same test run
    or long-lived process), so blindly emitting every registered
    component's CSS would leak one site's component styling into
    another's stylesheet. Only components an `expand_ark_ast(...,
    used=...)` call actually saw for *this* build belong in *this*
    build's output.
    """
    styles: dict[str, dict[str, str]] = {}
    for name in used:
        spec = COMPONENT_REGISTRY.get(name)
        if spec is not None and spec.default_style:
            styles[name] = dict(spec.default_style)
    return styles
