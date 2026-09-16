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
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable

from arklight.ast.nodes import ARKNode

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


class ComponentError(RuntimeError):
    """
    Raised when a registered component is misused: an unknown prop, a
    missing required prop, or a cyclical/too-deep expansion. Caught by
    `arklight.compiler.pipeline.compile_site_file` the same way
    `ValidationError` is -- wrapped into a `CompileError` with the same
    message, never a raw traceback.
    """


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


def register_component(
    name: str,
    render_fn: RenderFn,
    *,
    props: dict[str, Prop] | None = None,
    mode: str = "macro",
    default_style: dict[str, str] | None = None,
) -> ComponentSpec:
    """
    Register `render_fn` under `name`. Re-registering an existing name
    overwrites the previous entry (last registration wins) -- same
    "last call wins" rule `Site.style(...)` already uses for custom CSS
    classes, so re-importing/reloading a components module during
    iterative development doesn't accumulate stale duplicates.

    `default_style`, if given, is expected to already be validated
    (see `arklight.api.component`) -- this function stores it verbatim,
    it doesn't re-check CSS syntax itself, same division of labor
    `props`/`mode` already have between `arklight.api.component` (the
    user-facing, validating entry point) and this lower-level registry
    function.
    """
    spec = ComponentSpec(
        name=name,
        render_fn=render_fn,
        props=dict(props or {}),
        mode=mode,
        default_style=dict(default_style) if default_style else None,
    )
    COMPONENT_REGISTRY[name] = spec
    return spec


def register_backend_render(component_name: str, backend_name: str, render_fn: RenderFn) -> ComponentSpec:
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

    Last-registration-wins per `(component_name, backend_name)` pair,
    same rule `register_component` already uses for re-registering a
    component outright -- registering `"html"` twice for the same
    component just replaces the earlier override, it doesn't error.
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
    new_backend_render_fns = dict(spec.backend_render_fns)
    new_backend_render_fns[backend_name] = render_fn
    new_spec = replace(spec, backend_render_fns=new_backend_render_fns)
    COMPONENT_REGISTRY[component_name] = new_spec
    return new_spec


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


def _render_once(spec: ComponentSpec, resolved_props: dict[str, Any]) -> Any:
    """
    The hybrid dispatch itself -- Option A vs. Option B, as an
    `if`/`elif` ladder over `spec.mode`, exactly as
    `docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`
    describes it. Every branch is required to return something
    `expand_node` can keep expanding (an `ARKNode`, a string/number, a
    list of either, or `None`/`False`) -- the same shape
    `normalize_children` already accepts from any component call.
    """
    if spec.mode == "macro":
        # Option A: plain, immediate call -- the marker is expanded
        # away right here, nothing about it survives past this pass.
        rendered = spec.render_fn(**resolved_props)
    elif spec.mode == "registry":
        # Option B: still resolves through the component's shared
        # `render_fn` here, same as Option A above -- this call always
        # produces the *default* rendering, the one every backend
        # without its own override falls back to. Stage 3 (see below)
        # is what gives a backend an actual way to supply a different
        # subtree for the *same* call site; this branch itself is
        # unchanged from Stage 0/1/2.
        rendered = spec.render_fn(**resolved_props)
    else:  # pragma: no cover -- unreachable, ComponentSpec.__post_init__ already validated this
        raise ComponentError(f"Component {spec.name!r}: unknown mode {spec.mode!r}.")

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


def expand_child(value: Any, stack: tuple[str, ...], used: set[str] | None = None) -> Any:
    """Expand one child position -- an `ARKNode`, a nested list, or a
    plain value passed through unchanged (mirrors
    `arklight.ir.normalize.normalize_children`'s own recursive shape,
    since this pass runs one stage earlier over the same kind of tree)."""
    if isinstance(value, ARKNode):
        return expand_node(value, stack, used)
    if isinstance(value, list):
        return [expand_child(item, stack, used) for item in value]
    return value


def expand_node(node: ARKNode, stack: tuple[str, ...] = (), used: set[str] | None = None) -> Any:
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
    """
    spec = COMPONENT_REGISTRY.get(node.type)
    if spec is None:
        return replace(node, children=[expand_child(c, stack, used) for c in node.children])

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
    rendered = _render_once(spec, resolved_props)
    return expand_child(rendered, (*stack, node.type), used)


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
    """
    return {route: expand_node(page, used=used) for route, page in pages.items()}


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
