"""
User-defined, reusable components -- v0.060, Stage 0.

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

    def __post_init__(self) -> None:
        if self.mode not in _VALID_MODES:
            raise ValueError(
                f"component {self.name!r}: mode={self.mode!r} is not one of "
                f"{_VALID_MODES!r}."
            )


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
) -> ComponentSpec:
    """
    Register `render_fn` under `name`. Re-registering an existing name
    overwrites the previous entry (last registration wins) -- same
    "last call wins" rule `Site.style(...)` already uses for custom CSS
    classes, so re-importing/reloading a components module during
    iterative development doesn't accumulate stale duplicates.
    """
    spec = ComponentSpec(name=name, render_fn=render_fn, props=dict(props or {}), mode=mode)
    COMPONENT_REGISTRY[name] = spec
    return spec


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
        return spec.render_fn(**resolved_props)
    elif spec.mode == "registry":
        # Option B (EXPERIMENTAL): Stage 0 does not yet give this its
        # own render path (see module docstring) -- it still resolves
        # through the component's one render function, same as Option
        # A above. A later stage that gives Option B per-backend
        # dispatch extends *this* branch, not the whole ladder.
        return spec.render_fn(**resolved_props)
    else:  # pragma: no cover -- unreachable, ComponentSpec.__post_init__ already validated this
        raise ComponentError(f"Component {spec.name!r}: unknown mode {spec.mode!r}.")


def expand_child(value: Any, stack: tuple[str, ...]) -> Any:
    """Expand one child position -- an `ARKNode`, a nested list, or a
    plain value passed through unchanged (mirrors
    `arklight.ir.normalize.normalize_children`'s own recursive shape,
    since this pass runs one stage earlier over the same kind of tree)."""
    if isinstance(value, ARKNode):
        return expand_node(value, stack)
    if isinstance(value, list):
        return [expand_child(item, stack) for item in value]
    return value


def expand_node(node: ARKNode, stack: tuple[str, ...] = ()) -> Any:
    """
    Expand `node` and everything beneath it. If `node.type` names a
    registered component, its marker is replaced by its rendered
    subtree (itself recursively expanded, in case that subtree uses
    other user components); otherwise `node` is returned with its own
    children expanded in place, unchanged in every other respect.
    """
    spec = COMPONENT_REGISTRY.get(node.type)
    if spec is None:
        return replace(node, children=[expand_child(c, stack) for c in node.children])

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

    resolved_props = _resolve_props(spec, node.props)
    rendered = _render_once(spec, resolved_props)
    return expand_child(rendered, (*stack, node.type))


def expand_ark_ast(pages: dict[str, ARKNode]) -> dict[str, ARKNode]:
    """
    Expand every page's ARK AST tree. Called between ARK-AST
    construction (`Site.build_ark_ast()`) and Normalization -- see
    `arklight.compiler.pipeline.compile_site_file`. A no-op (returns
    `pages` re-wrapped, unchanged) for a site that never registered or
    called a user component, same "purely additive" contract every
    other optional pipeline addition in this codebase follows.
    """
    return {route: expand_node(page) for route, page in pages.items()}
