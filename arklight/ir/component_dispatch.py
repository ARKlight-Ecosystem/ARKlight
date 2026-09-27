"""
User-defined components, Stage 3: per-backend render dispatch.

See `USER-DEFINED-COMPONENTS-IMPLEMENTATION.md` [retired -- see CHANGELOG.md]'s
Stage 3 row for the milestone this belongs to, and
`arklight.ir.components`'s module docstring for how a `mode="registry"`
component call ends up tagged with a `ComponentOrigin` in the first
place (`_render_once`/`_tag_component_origin`, only when the component
has at least one backend override registered at all).

This module is where that identity actually gets *used*. Component
expansion (`arklight.ir.components.expand_ark_ast`) runs exactly once,
backend-agnostically, in `arklight.compiler.pipeline.compile_site_file`
-- it produces one `WebsiteIR` every backend renders from. Per-backend
dispatch can't happen there: two different backends legitimately want
two different subtrees for the same `mode="registry"` call site, and
`compile_site_file` has no idea which backends `arklight.compiler.
pipeline.build` is even going to run. So this resolves *after* the
shared `WebsiteIR` exists, once per backend, right before that
backend's own `render()` walks the tree:

    ir = compile_site_file(...)                      # once, shared
    for backend in backends:
        backend_ir = resolve_backend_dispatch(ir, backend.name)
        backend.render(backend_ir)                    # per backend

`resolve_backend_dispatch` returns a *new* `WebsiteIR` (`ir` itself,
and any node with no `component_origin` anywhere beneath it, is never
mutated) so that running it once for `"html"` and once for `"css"`
never lets one backend's resolution bleed into another's.

`arklight.backend.html.render.HTMLBackend` is the one backend that
calls this today, in its own `render()` -- see that module. A future
Android/Desktop backend that implements `arklight.backend.base.Backend`
and walks the same `IRNode` tree can opt in the exact same one-line
way; `CSSBackend`/`JSBackend` don't need to, since neither one walks
a page's node tree looking for markup to emit (see their own `render()`
bodies) -- calling this before either one's `render()` would be a
harmless no-op, just a wasted tree walk, not a behavior change.
"""

from __future__ import annotations

from dataclasses import replace

from arklight.ast.nodes import ARKNode
from arklight.ir.build import IRNode, WebsiteIR, ark_node_to_ir_node
from arklight.ir.components import (
    COMPONENT_REGISTRY,
    MAX_COMPONENT_EXPANSION_DEPTH,
    ComponentError,
    apply_default_style_class,
    call_render_fn,
    expand_node,
)
from arklight.ir.normalize import normalize_node

# Mirrors `arklight.ir.components.MAX_COMPONENT_EXPANSION_DEPTH` --
# same insurance-against-a-cycle reasoning, applied to *this* pass
# instead: a backend override that (directly or by returning another
# `mode="registry"` call with yet another override for this same
# backend) re-renders itself without end would otherwise recurse until
# a raw `RecursionError`, same failure mode `MAX_COMPONENT_EXPANSION_DEPTH`
# exists to turn into a clear build-time error one stage earlier.
MAX_BACKEND_DISPATCH_DEPTH = MAX_COMPONENT_EXPANSION_DEPTH


def _render_backend_override(
    component_name: str,
    backend_name: str,
    render_fn,
    resolved_props: dict,
    *,
    depth: int,
) -> IRNode:
    """
    Call a backend override, then walk its output back down to
    `IRNode` through the same shape every other component render
    function's output already goes through -- component expansion
    (for any nested `mode="macro"`/`mode="registry"` call the override
    itself makes), Normalization, then IR conversion -- before handing
    the result back to `_resolve_node` for its own (recursive) dispatch
    pass, in case the override's subtree contains further
    `mode="registry"` calls with overrides of their own.
    """
    rendered = call_render_fn(
        component_name,
        render_fn,
        resolved_props,
        what=f"{backend_name!r} backend override",
    )

    if isinstance(rendered, list):
        # Same top-level-single-root requirement `expand_ark_ast` (via
        # `Site.build_ark_ast`) already has for a whole page -- a
        # backend override stands in for exactly one call site's one
        # rendered root, so it can't hand back multiple siblings with
        # nowhere on the existing tree to attach the second one.
        raise ComponentError(
            f"Backend override for {component_name!r} ({backend_name!r}) "
            "must render a single root node, not a list of siblings."
        )
    if not isinstance(rendered, ARKNode):
        raise ComponentError(
            f"Backend override for {component_name!r} ({backend_name!r}) "
            f"must return an ARKNode, got {type(rendered).__name__!r}."
        )

    # `expand_node` is called bare here -- no `hoisted`/`counter` (v0.060,
    # Stage 4) -- because there is no page-level accumulator to hoist a
    # component-owned `State(...)` onto at this point in the pipeline
    # (`WebsiteIR` already exists; see `_render_backend_override`'s own
    # caller). A backend override subtree that itself calls a `state=`-
    # declaring component raises `ComponentError` here, same as any
    # other bare `expand_node()` call would -- not supported yet, see
    # `USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s
    # Stage 4 "explicitly out of scope" note.
    rendered = expand_node(rendered)
    spec = COMPONENT_REGISTRY.get(component_name)
    if spec is not None and spec.default_style:
        # `default_style` is mode- *and* backend-independent (see
        # `arklight.ir.components.apply_default_style_class`) -- an
        # override's own rendered root gets the same `.{ComponentName}`
        # class the shared `render_fn`'s output already would have.
        rendered = apply_default_style_class(component_name, rendered)
    rendered = normalize_node(rendered)

    ir_node = ark_node_to_ir_node(rendered)
    return _resolve_node(ir_node, backend_name, depth=depth + 1)


def _resolve_node(node: IRNode, backend_name: str, *, depth: int = 0) -> IRNode:
    origin = node.component_origin
    if origin is not None:
        if depth >= MAX_BACKEND_DISPATCH_DEPTH:
            raise ComponentError(
                f"Per-backend render dispatch for {origin.name!r} "
                f"({backend_name!r}) exceeded the maximum nesting depth "
                f"({MAX_BACKEND_DISPATCH_DEPTH}). This almost always means "
                "a backend override's own output keeps re-triggering "
                "another override for the same backend."
            )
        spec = COMPONENT_REGISTRY.get(origin.name)
        backend_fn = spec.backend_render_fns.get(backend_name) if spec is not None else None
        if backend_fn is not None:
            return _render_backend_override(
                origin.name, backend_name, backend_fn, origin.resolved_props, depth=depth
            )
        # No override for this backend -- fall back to the default
        # subtree `_render_once` already rendered with the shared
        # `render_fn` (Option A's own behavior). Just clear the marker
        # so a resolved node's shape is indistinguishable from one that
        # was never tagged at all, for anything downstream of this
        # function that inspects `component_origin` later (there is no
        # such reader today, but keeping a `WebsiteIR` this pass has
        # already run over free of stale internal markers is one less
        # thing for a future reader -- of this IR or of this module --
        # to have to reason about).
        node = replace(node, component_origin=None)

    return replace(
        node,
        children=[
            _resolve_node(child, backend_name, depth=depth) if isinstance(child, IRNode) else child
            for child in node.children
        ],
    )


def resolve_backend_dispatch(ir: WebsiteIR, backend_name: str) -> WebsiteIR:
    """
    Stage 3's actual "the HTML backend ... can supply their own render
    function for the same component name" behavior. Returns a new
    `WebsiteIR` (same `ir`, but with every page's `root` walked and any
    `mode="registry"` component instance carrying a `backend_name`
    override resolved to that override's own rendered subtree) --
    `ir` itself is never mutated, so calling this once per backend
    (see `arklight.compiler.pipeline.build`) never lets one backend's
    resolution affect another's.

    A no-op in the only sense that matters for every site before Stage
    3, and most sites after it: if no node anywhere carries a
    `component_origin` (true whenever nothing on the site uses
    `mode="registry"` with a backend override registered), every page's
    `root` comes back unchanged.
    """
    resolved_pages = [
        replace(page, root=_resolve_node(page.root, backend_name)) for page in ir.pages
    ]
    return replace(ir, pages=resolved_pages)
