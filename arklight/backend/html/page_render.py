"""
HTML Backend refactor, Stage 5 (see
docs/Backends/HTML-BACKEND-REFACTOR.md / docs/Backends/REFACTOR-INDEX.md
row 8, `html-5`): the fifth of the six staged extractions splitting
`arklight/backend/html/render.py`'s five unrelated jobs into their own
modules.

This module owns per-page composition -- logic that runs once per
page (`_render_page`) or recursively per node within it
(`_render_bind`/`_render_children`/`_render_node`), assembling a
complete HTML document out of the pieces the other four modules
provide: `tag_map.py` (Stage 1, tag names), `routing.py` (Stage 2,
route/asset-path resolution), `attrs.py` (Stage 3, attribute strings),
and `head_meta.py` (Stage 4, `<head>` tags). With this stage done,
`render.py` is left holding only `HTMLBackend`, whose `render()`
becomes a short composition of the sibling modules -- exactly the
target shape's stated end state.

Sequenced ahead of `htmx-4` (app-shell navigation) deliberately, per
`docs/Backends/REFACTOR-INDEX.md` row 8: `_render_page` is exactly
where the shell-persistent-region audit that stage calls for has to
look, so landing this extraction first meant that audit landed
directly in `page_render.py` rather than in `render.py` a few commits
before being moved out from under it -- the same reasoning `html-3`
already applied ahead of `htmx-1`.

At the point this module was split out, that was zero behavior
change: same recursion, same tag emission, same generated HTML
byte-for-byte as before it existed. `htmx-4` (docs/Backends/
REFACTOR-INDEX.md row 9) is the first stage to actually change what
`_render_page` emits -- see `_render_page`'s own docstring below for
what `app_shell=True` adds. Every existing caller that doesn't pass
`app_shell` gets the prior byte-for-byte output, unchanged.
`render.py` re-exports `_render_bind`/`_render_children`/
`_render_node`/`_render_page` for backward compatibility with anything
that already imported them from there, same as Stages 1-4.
"""

from __future__ import annotations

import json
import math
import re
from html import escape

from arklight.ast.nodes import ActionRef, ItemIndexRef, PredicateRef
from arklight.backend.css.render import STYLESHEET_PATH
from arklight.backend.html.attrs import _attr_string
from arklight.backend.html.csp import _render_csp_meta_tag
from arklight.backend.html.head_meta import _render_head_meta
from arklight.backend.html.routing import _relative_asset_path
from arklight.backend.html.tag_map import VOID_TAGS, _tag_for
from arklight.backend.js.render import SCRIPT_PATH
from arklight.ir.build import IRNode, IRPage
from arklight.ir.js_string import from_units


_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def _render_bind(node: IRNode, *, page_state: dict) -> str:
    """
    v0.0035: `Bind("count")` renders as a `<span data-ark-bind="count">`
    pre-filled with the page's current (build-time) state value, so the
    page is fully readable with JS disabled -- the shipped reactive
    core just keeps this element's text in sync with client-side state
    changes after that.
    """
    name = node.props.get("name")
    value = page_state.get(name, "")
    # `v0.064`: a math derivation can now produce a non-finite result
    # (`Derive.sqrt` of a negative, `Derive.log` of zero). Python's
    # `str()` spells those `nan`/`inf`; the client runtime's `String()`
    # spells them `NaN`/`Infinity`, so pre-fill the JavaScript spelling.
    if isinstance(value, float) and not math.isfinite(value):
        value = "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    # `v0.065`: the string catalog's boolean kinds (`is_empty`,
    # `starts_with`, ...) make a `Computed(...)` value a `bool`, which
    # Python spells `True`/`False` and the client's `String()` spells
    # `true`/`false`.
    if isinstance(value, bool):
        value = "true" if value else "false"
    # `v0.065`: `Derive.char_at`/`slice_string` can cut an emoji in half,
    # leaving a lone surrogate -- legal in a JavaScript string, but it
    # can't be written out as UTF-8. The browser draws such a character
    # as U+FFFD, so pre-fill that. Python never merges adjacent surrogate
    # characters, but JavaScript does (`Derive.join` of a `char_at(0)` and
    # a `char_at(1)` of an emoji is the emoji again), so recombine valid
    # pairs first and only blank what is genuinely lone.
    if isinstance(value, str):
        value = _LONE_SURROGATE.sub("\ufffd", from_units(value))
    return f'<span data-ark-bind="{escape(str(name), quote=True)}">{escape(str(value))}</span>'


def _evaluate_predicate(predicate: PredicateRef, *, page_state: dict) -> bool:
    """`vdom-7`/`v0.062`: the same truthy/falsy/equals/gt/lt check
    `Predicate.*(...)` describes, evaluated at build time against the
    page's initial state -- see `arkEvalPredicate` in
    `arklight/backend/js/runtime/show.py` for the client-side twin
    that re-runs this on every state change."""
    if predicate.kind == "equals":
        return page_state.get(predicate.names[0]) == page_state.get(predicate.names[1])
    if predicate.kind == "gt":
        return page_state.get(predicate.names[0]) > page_state.get(predicate.names[1])
    if predicate.kind == "lt":
        return page_state.get(predicate.names[0]) < page_state.get(predicate.names[1])
    value = page_state.get(predicate.names[0])
    return (not value) if predicate.kind == "falsy" else bool(value)


def _render_show(
    node: IRNode, *, current_route: str, route_to_path: dict[str, str], page_state: dict
) -> str:
    """
    `vdom-7`: `Show(predicate, ...)` renders its children unconditionally
    (a `Show` that started hidden still needs its real markup available
    for `renderShow` to reveal later -- there's no way to "come back"
    from omitted HTML), wrapped in a `data-ark-show="{...}"` anchor that
    also carries a plain `hidden` attribute whenever `predicate`
    evaluates false against the page's *initial* state. `hidden` is a
    native HTML content-visibility attribute (removes the subtree from
    the accessibility tree, needs no CSS or JS to take effect) rather
    than a style toggle, so a JS-disabled visitor sees exactly the
    right thing with zero client-side help -- `renderShow`
    (`arklight/backend/js/runtime/show.py`) just keeps `hidden` in sync
    with `predicate` after that.
    """
    predicate = node.props["predicate"]
    predicate_json = escape(
        json.dumps({"kind": predicate.kind, "names": list(predicate.names)}), quote=True
    )
    visible = _evaluate_predicate(predicate, page_state=page_state)
    hidden_attr = "" if visible else " hidden"
    inner = _render_children(
        node.children, current_route=current_route, route_to_path=route_to_path, page_state=page_state
    )
    return f'<div data-ark-show="{predicate_json}"{hidden_attr}>{inner}</div>'


def _substitute_item_refs(node: IRNode, *, item, index: int) -> IRNode:
    """`vdom-7`: returns a copy of a `Repeat(...)` template `IRNode`
    with every `ItemBind` child replaced by the literal current-item
    text and every `ItemIndexRef` (`RepeatItem.index()`) inside an
    `on_click=Action.*(...)`'s args replaced by the literal current
    index -- both are only ever resolved dynamically client-side (see
    `_repeat_template_spec` below); server-rendered per-item HTML has
    no reactivity of its own, so a literal value is exactly right
    here."""
    props = dict(node.props)
    on_click = props.get("on_click")
    if isinstance(on_click, ActionRef):
        props["on_click"] = ActionRef(
            action=on_click.action,
            state=on_click.state,
            args={k: (index if isinstance(v, ItemIndexRef) else v) for k, v in on_click.args.items()},
            modifiers=on_click.modifiers,
        )
    new_children: list = []
    for child in node.children:
        if isinstance(child, IRNode):
            if child.type == "ItemBind":
                new_children.append(str(item))
            else:
                new_children.append(_substitute_item_refs(child, item=item, index=index))
        else:
            new_children.append(child)
    return IRNode(type=node.type, props=props, children=new_children)


def _repeat_template_spec(node: IRNode) -> dict:
    """`vdom-7`: converts a `Repeat(...)` template `IRNode` into a
    JSON-safe tree the client-side runtime (`arklight/backend/js/
    runtime/repeat.py`) can build brand-new items from after an
    `Action.append(...)` -- server-rendered items instead go through
    `_substitute_item_refs` + the normal `_render_node`, since they
    need no client-side construction at all. Deliberately narrower
    than full node rendering: only `class_name`/`id` and a single
    `on_click=Action.*(...)` per node are carried over (a real,
    documented limitation of this stage -- other props render
    correctly for the items the server already produced, but won't be
    reproduced for one added purely client-side; see
    docs/Backends/REFACTOR-INDEX.md row 15 for what's left for a
    future version).
    """
    tag = _tag_for(node)
    attrs: dict[str, str] = {}
    class_name = node.props.get("class_name")
    if class_name:
        attrs["class"] = str(class_name)
    node_id = node.props.get("id")
    if node_id:
        attrs["id"] = str(node_id)
    on_click_spec = None
    on_click = node.props.get("on_click")
    if isinstance(on_click, ActionRef):
        on_click_spec = {
            "action": on_click.action,
            "state": on_click.state,
            "args": {
                key: ({"__item_index__": True} if isinstance(value, ItemIndexRef) else value)
                for key, value in on_click.args.items()
            },
        }
    text = None
    children_specs: list[dict] = []
    for child in node.children:
        if isinstance(child, IRNode):
            if child.type == "ItemBind":
                text = {"item_value": True}
            else:
                children_specs.append(_repeat_template_spec(child))
        else:
            text = str(child)
    return {"tag": tag, "attrs": attrs, "on_click": on_click_spec, "text": text, "children": children_specs}


def _render_repeat(
    node: IRNode, *, current_route: str, route_to_path: dict[str, str], page_state: dict
) -> str:
    """
    `vdom-7`: `Repeat(name, template=...)` renders one real copy of its
    template per element of `name`'s current (build-time) list value --
    exactly like `Bind(...)`, this means a JS-disabled visitor sees the
    genuine current list, not an empty placeholder. The container also
    carries `data-ark-repeat-template` -- the same template compiled to
    a JSON spec (`_repeat_template_spec`) -- so `renderRepeat`
    (`arklight/backend/js/runtime/repeat.py`) can both keep these exact
    elements (rather than re-creating and duplicating them -- see that
    module's docstring) and build genuinely new ones after a later
    `Action.append(...)`.
    """
    name = node.props["name"]
    template = node.children[0]
    items = page_state.get(name) or []
    spec_json = escape(json.dumps(_repeat_template_spec(template)), quote=True)
    rendered_items = "".join(
        _render_node(
            _substitute_item_refs(template, item=item, index=index),
            current_route=current_route,
            route_to_path=route_to_path,
            page_state=page_state,
        )
        for index, item in enumerate(items)
    )
    return (
        f'<div data-ark-repeat="{escape(str(name), quote=True)}" '
        f'data-ark-repeat-template="{spec_json}">{rendered_items}</div>'
    )


def _render_children(
    children: list, *, current_route: str, route_to_path: dict[str, str], page_state: dict
) -> str:
    rendered = []
    for child in children:
        if isinstance(child, IRNode):
            rendered.append(
                _render_node(
                    child, current_route=current_route, route_to_path=route_to_path, page_state=page_state
                )
            )
        else:
            rendered.append(escape(str(child)))
    return "".join(rendered)


def _render_node(node: IRNode, *, current_route: str, route_to_path: dict[str, str], page_state: dict) -> str:
    if node.type == "Bind":
        return _render_bind(node, page_state=page_state)

    if node.type == "Repeat":
        return _render_repeat(
            node, current_route=current_route, route_to_path=route_to_path, page_state=page_state
        )

    if node.type == "Show":
        return _render_show(
            node, current_route=current_route, route_to_path=route_to_path, page_state=page_state
        )

    tag = _tag_for(node)
    attrs = _attr_string(
        node.props,
        current_route=current_route,
        route_to_path=route_to_path,
        page_state=page_state,
        node_type=node.type,
    )

    if tag in VOID_TAGS:
        return f"<{tag}{attrs} />"

    inner = _render_children(
        node.children, current_route=current_route, route_to_path=route_to_path, page_state=page_state
    )
    return f"<{tag}{attrs}>{inner}</{tag}>"


def _render_page(
    page: IRPage,
    site_name: str,
    route_to_path: dict[str, str],
    *,
    site_lang: str,
    app_shell: bool = False,
    strict_csp: bool = True,
    trusted_script_origins: list[str] | None = None,
) -> str:
    """
    `app_shell` (htmx-4, docs/Backends/REFACTOR-INDEX.md row 9):
    `Site(app_shell=True)` -- defaults to `False`, unchanged output
    (same byte-for-byte HTML this function always produced). Set, two
    things change:

    1. `<body hx-boost="true">` -- htmx's own mechanism for turning
       same-origin link clicks into an in-place AJAX swap instead of a
       full document reload. See `arklight/backend/js/render.py` for
       the matching JS-side change (`needs_htmx` now also ships HTMX
       for a site with this flag set, even on a page with no
       behaviors or State(...) of its own).
    2. **The state marker moves.** Per htmx's own docs, `hx-boost`'s
       default swap replaces `<body>`'s *innerHTML* only -- never the
       `<body>` tag's own attributes. A `data-ark-state="..."`
       attribute placed directly on `<body>` (the non-app_shell
       branch below, unchanged) would therefore freeze at whatever
       page first loaded and never update across a boosted
       navigation, silently breaking every State(...) page's
       hydration the moment app-shell navigation reached it. Instead,
       for an app_shell page with state, the JSON blob is emitted as
       a hidden marker element (`<div id="ark-state" ...>`) that's
       part of `body_inner` -- and therefore *is* replaced, with the
       new page's own state, on every boosted swap. `initState()`
       (see `arklight/backend/js/runtime/state.py`) checks for this
       marker first and falls back to the `<body>` attribute, so it
       handles both shapes without needing to know `app_shell` was
       set.

    `strict_csp`/`trusted_script_origins` (runtime policy enforcement,
    `arklight/backend/html/csp.py`): `Site(strict_csp=..., trusted_
    script_origins=...)`'s straight passthrough. `strict_csp` defaults
    to `True` -- unlike every other default in this docstring, that is
    new output for an unconfigured site (one more `<head>` `<meta>`
    tag), not a byte-for-byte-unchanged default; see `WebsiteIR.
    strict_csp`'s comment (arklight/ir/build.py) for why.
    """
    title = page.root.props.get("title", site_name)
    lang = page.root.props.get("lang", site_lang)
    # `vdom-4` (docs/Backends/REFACTOR-INDEX.md row 12): `Bind(...)`/
    # `bind_class=` may reference a Computed(...) name exactly like a
    # State(...)'s, so both build-time text-fill (_render_bind) and
    # build-time truthiness checks (attrs.py's bind_class rendering)
    # need to see computed's initial values too -- merged only for
    # this read-only rendering pass, never written back into
    # `page.state` itself (see `state_marker` below for why the two
    # stay separate in the JSON hydration blob).
    render_state = {**page.state, **page.computed_initial}
    body_inner = _render_children(
        page.root.children, current_route=page.route, route_to_path=route_to_path, page_state=render_state
    )
    stylesheet_href = _relative_asset_path(
        STYLESHEET_PATH, current_route=page.route, route_to_path=route_to_path
    )
    script_src = _relative_asset_path(SCRIPT_PATH, current_route=page.route, route_to_path=route_to_path)
    head_meta = _render_head_meta(page, title, current_route=page.route, route_to_path=route_to_path)
    # v0.0035: pages that declare State(...) hydrate the client-side
    # store from here -- a JSON blob of the same initial values the
    # page was rendered with, so client and server never disagree.
    # `vdom-4`: `page.computed` (dependency-ordered `(name, spec)`
    # pairs) rides along as its own `data-ark-computed` attribute,
    # never folded into `data-ark-state` itself -- `data-ark-state`
    # seeds the client store's *mutable* values, and a Computed(...)
    # has none of its own to seed (the runtime derives it fresh on
    # init, from `state`, via `initState()` -- see
    # `arklight/backend/js/runtime/state.py`). A page can only ever
    # have `page.computed` non-empty when `page.state` is too (every
    # Computed(...) dependency chain bottoms out at a real State(...),
    # enforced by Validation), so it's always safe to place both
    # attributes on the same marker.
    body_attr_parts: list[str] = []
    state_marker = ""
    if page.state:
        state_json = escape(json.dumps(page.state), quote=True)
        computed_attr = ""
        if page.computed:
            computed_json = escape(json.dumps(page.computed), quote=True)
            computed_attr = f' data-ark-computed="{computed_json}"'
        # `vdom-5` (docs/Backends/REFACTOR-INDEX.md row 13): `page.watch`
        # rides along as its own `data-ark-watch` attribute, same
        # reasoning as `data-ark-computed` above -- it carries no
        # value of its own to hydrate, just the (name, then) pairs the
        # JS runtime's `wireWatchers` (`arklight/backend/js/runtime/
        # watch.py`) wires up as extra `store.subscribe` callbacks
        # once `initState()` has a store to hand it. A page can only
        # ever have `page.watch` non-empty when `page.state` is too
        # (`Watch(...)`'s `name` must resolve to a `State(...)`/
        # `Computed(...)` declared on the page, and any `Computed(...)`
        # chain itself bottoms out at a real `State(...)`, both
        # enforced by Validation), so it's always safe to place all
        # three attributes on the same marker.
        watch_attr = ""
        if page.watch:
            watch_json = escape(json.dumps(page.watch), quote=True)
            watch_attr = f' data-ark-watch="{watch_json}"'
        # `vdom-8` (docs/Backends/REFACTOR-INDEX.md row 16): `page.persist`
        # rides along as its own `data-ark-persist` attribute, same
        # reasoning as `data-ark-watch`/`data-ark-computed` above -- a
        # plain list of `State(...)` names, no value of its own, read
        # by `initState()` (`arklight/backend/js/runtime/state.py`) to
        # decide which keys get a `localStorage` override/write-back.
        # A page can only ever have `page.persist` non-empty when
        # `page.state` is too (`persist=True` only exists as a prop on
        # a `State(...)` node), so it's always safe to place all four
        # attributes on the same marker.
        persist_attr = ""
        if page.persist:
            persist_json = escape(json.dumps(page.persist), quote=True)
            persist_attr = f' data-ark-persist="{persist_json}"'
        # `v0.063` (docs/version history/v0.063.md): `page.media` rides
        # along as its own `data-ark-media` attribute, same reasoning
        # as `data-ark-persist` above -- `[name, query]` pairs, no
        # value of their own (`state_json` above already carries this
        # key's server-rendered-guess initial value), read by
        # `initState()` (`arklight/backend/js/runtime/state.py`) to
        # override that guess with the real `matchMedia(query).matches`
        # and keep it live after that. A page can only ever have
        # `page.media` non-empty when `page.state` is too (`media=`
        # only exists as a prop on a `State(...)` node), so it's always
        # safe to place all five attributes on the same marker.
        media_attr = ""
        if page.media:
            media_json = escape(json.dumps(page.media), quote=True)
            media_attr = f' data-ark-media="{media_json}"'
        # `v0.064` (docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md):
        # `page.query` rides along as its own `data-ark-query`
        # attribute, same reasoning as `data-ark-media` above --
        # `[name, param, type_tag, history_mode]` tuples, no value of
        # their own (`state_json` above already carries this key's
        # server-rendered initial value), read by `initState()`
        # (`arklight/backend/js/runtime/state.py`) to override that
        # value from `URLSearchParams(location.search)`, keep it live
        # across `popstate` (`arklight/backend/js/runtime/query.py`),
        # and write it back out via `history.replaceState`/
        # `pushState` on every change. A page can only ever have
        # `page.query` non-empty when `page.state` is too (`query=`
        # only exists as a prop on a `State(...)` node), so it's
        # always safe to place all six attributes on the same marker.
        query_attr = ""
        if page.query:
            query_json = escape(json.dumps(page.query), quote=True)
            query_attr = f' data-ark-query="{query_json}"'
        if app_shell:
            state_marker = (
                f'<div id="ark-state" data-ark-state="{state_json}"'
                f"{computed_attr}{watch_attr}{persist_attr}{media_attr}{query_attr} hidden></div>\n"
            )
        else:
            body_attr_parts.append(
                f' data-ark-state="{state_json}"{computed_attr}{watch_attr}'
                f"{persist_attr}{media_attr}{query_attr}"
            )
    if app_shell:
        body_attr_parts.append(' hx-boost="true"')
    body_attrs = "".join(body_attr_parts)
    # Runtime policy enforcement (arklight/backend/html/csp.py):
    # charset stays the very first <head> tag (browsers sniff it before
    # anything else), so CSP is the very next one -- applied as early as
    # possible, before the stylesheet link or any other tag. Empty
    # string when `strict_csp=False` (Site(strict_csp=False), the
    # general escape valve -- see csp.py's module docstring), so a
    # site that opts out gets exactly today's tag set back, byte for
    # byte.
    csp_meta = _render_csp_meta_tag(trusted_script_origins) if strict_csp else ""
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{escape(str(lang), quote=True)}">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"{csp_meta}"
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{escape(str(title))}</title>\n"
        f'  <link rel="stylesheet" href="{escape(stylesheet_href, quote=True)}">\n'
        f"{head_meta}"
        "</head>\n"
        f"<body{body_attrs}>\n{state_marker}{body_inner}\n"
        f'<script src="{escape(script_src, quote=True)}" defer></script>\n'
        "</body>\n"
        "</html>\n"
    )
