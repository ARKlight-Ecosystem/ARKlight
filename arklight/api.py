"""
Public ARKlight API.

`from arklight import *` gives users:

- `Site`       -- the app object, holds page registrations
- `Page`       -- the root node every page function must return
- Built-in components: `Heading`, `Text`, `Button`, `Container`, `Link`, `Image`, `List`, `Item`,
  plus the v0.003 vocabulary extension and its "even more vocabulary" addendum below.

Everything a user calls here returns an `ARKNode` (see arklight.ast.nodes),
except `Site`, which is a small registry object.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from arklight import experimental
from arklight.ast.nodes import (
    ActionRef,
    ARKNode,
    ClassBindSpec,
    DerivationRef,
    ItemIndexRef,
    ModelBindSpec,
    PlatformAPIRef,
    PredicateRef,
    node,
    state_ref,
)
from arklight.backend.css import selectors as css_selectors

# v0.042: custom CSS class names must look like a real, single CSS class
# identifier -- letters/digits/hyphens/underscores, not starting with a
# digit. Deliberately conservative (no escaped Unicode class names,
# no leading '.', no combinators) since this becomes a literal `.name {`
# selector in generated CSS with no further validation downstream.
_CSS_CLASS_NAME_RE = re.compile(r"^-?[A-Za-z_][A-Za-z0-9_-]*$")

# CSS Backend, pseudo-class shorthand (see docs/CSS-BACKEND-REFACTOR.md
# "Stage 2"): a `site.style(...)` rules key is either a plain property
# ("background") or a pseudo-class-scoped property (":hover:background"),
# letting a class express a simple interactive state without opening up
# raw CSS/selector strings. Plain property names allow a leading "--"
# (custom properties) or a single leading "-" (vendor prefixes, e.g.
# "-webkit-appearance"); pseudo names are letters/hyphens only and must
# be one of `ALLOWED_PSEUDO_CLASSES` below.
_CSS_PROPERTY_NAME_RE = re.compile(r"^(--[A-Za-z0-9-]+|-?[A-Za-z][A-Za-z0-9-]*)$")
_CSS_PSEUDO_RULE_RE = re.compile(
    r"^:(?P<pseudo>[A-Za-z-]+):(?P<prop>--[A-Za-z0-9-]+|-?[A-Za-z][A-Za-z0-9-]*)$"
)

# Deliberately a fixed, curated set rather than "any :whatever the user
# types" -- same reasoning as `_CSS_CLASS_NAME_RE`: this becomes a
# literal `.name:pseudo { ... }` selector with no further validation
# downstream, so an open-ended pseudo name would reopen the "no
# arbitrary CSS/selector strings" boundary `site.style(...)` otherwise
# holds. Extend this set (not the regex) if a new pseudo-class is
# needed later.
ALLOWED_PSEUDO_CLASSES = frozenset(
    {
        "hover",
        "focus",
        "focus-visible",
        "focus-within",
        "active",
        "visited",
        "link",
        "target",
        "disabled",
        "enabled",
        "checked",
        "indeterminate",
        "default",
        "required",
        "optional",
        "valid",
        "invalid",
        "in-range",
        "out-of-range",
        "read-only",
        "read-write",
        "placeholder-shown",
        "root",
        "empty",
        "first-child",
        "last-child",
        "only-child",
        "first-of-type",
        "last-of-type",
        "only-of-type",
    }
)

# Characters that would let a "value" break out of its declaration and
# inject a second declaration, a new selector, or close/reopen a rule
# block (e.g. {"color": "red; } .evil { color"}). `site.style(...)`
# rules are meant to be one property/value pair each, not a raw CSS
# string, so any of these in a value is a syntax error, not something
# to pass through.
_CSS_VALUE_INJECTION_CHARS = frozenset("{};\n")


# Recognized `@page` pseudo-classes for `Site.page_rule(..., pseudo=...)`
# -- same fixed-set discipline as `ALLOWED_PSEUDO_CLASSES` above.
ALLOWED_PAGE_PSEUDOS = frozenset({"first", "left", "right", "blank"})

# Recognized `src` formats for `Site.font_face(...)` -- matches the
# `format(...)` keywords browsers actually recognize in an `@font-face`
# `src` descriptor.
ALLOWED_FONT_FACE_FORMATS = frozenset(
    {"woff2", "woff", "truetype", "opentype", "embedded-opentype", "svg"}
)

# `@keyframes` stop keys: `from`/`to` or a percentage like "50%".
_KEYFRAME_STOP_RE = re.compile(r"^(from|to|\d{1,3}(\.\d+)?%)$")

# `Site.container_query(..., name=...)`'s optional container-name --
# a CSS custom-ident, same charset as `_CSS_CLASS_NAME_RE` (no leading
# digit).
_CSS_IDENT_RE = re.compile(r"^-?[A-Za-z_][A-Za-z0-9_-]*$")


class CSSSyntaxError(ValueError):
    """
    Raised by `Site.style(...)` when a rules key or value isn't valid
    CSS syntax for the shape ARKlight accepts -- an unknown pseudo-class
    in a ":pseudo:property" key, a malformed property name, or a value
    that would break out of its declaration. Subclasses `ValueError` so
    existing `except ValueError` call sites keep working unchanged; this
    exists as its own type so callers that want to distinguish "bad CSS
    syntax" from other `Site.style(...)` argument errors (bad class
    name, wrong dict shape) can catch it specifically.
    """


class DuplicateStyleNameError(ValueError):
    """
    Raised by `Site.style(...)` when `name` is already registered in
    `self.custom_styles`. This used to be silent, unconditional "last
    call wins" -- the same rule `register_component(...)` used to
    apply -- which hid two unrelated `site.style(...)` calls
    accidentally reusing the same class name behind whichever one
    happened to run last, no error at either call site. Subclasses
    `ValueError` for the same reason `CSSSyntaxError` does (existing
    `except ValueError` handling for `Site.style(...)` keeps working),
    while staying its own type so a caller can distinguish "this name
    is already taken" from "the CSS in this call is malformed"
    (`CSSSyntaxError`). Pass `allow_redefine=True` to `Site.style(...)`
    for the one legitimate case last-call-wins used to serve:
    deliberately redefining a class as a site file is built up.
    """

# ---------------------------------------------------------------------------
# Built-in components
#
# Each of these is a plain Python function. Calling one does not render
# anything -- it just builds an ARKNode. The real rendering happens later,
# in the compiler pipeline, once every page has been collected.
# ---------------------------------------------------------------------------

Page = node("Page")
Heading = node("Heading")
Text = node("Text")
Button = node("Button")
Container = node("Container")
Link = node("Link")
Image = node("Image")
List = node("List")
Item = node("Item")

# ---------------------------------------------------------------------------
# v0.003 vocabulary extension.
#
# Same mechanism as everything above -- each is `node("SomeType")`, a thin
# ARKNode-building wrapper, nothing more. Grouped to match arklight.ir.schema:
# semantic layout, text-level semantics, forms, tables, media. See
# arklight.ir.schema.SCHEMA for the authoritative list of what each one
# allows (required props, text-only-children, etc.) and
# docs/DESIGN-NOTES.md for why these specifically.
# ---------------------------------------------------------------------------

# Semantic page/section layout.
Header = node("Header")
Footer = node("Footer")
Main = node("Main")
Nav = node("Nav")
Section = node("Section")
Article = node("Article")
Aside = node("Aside")
Figure = node("Figure")
FigCaption = node("FigCaption")
Details = node("Details")
Summary = node("Summary")

# Text-level semantics.
Strong = node("Strong")
Em = node("Em")
Small = node("Small")
Mark = node("Mark")
Code = node("Code")
Cite = node("Cite")
Abbr = node("Abbr")
Sub = node("Sub")
Sup = node("Sup")
Span = node("Span")
Time = node("Time")
HorizontalRule = node("HorizontalRule")
LineBreak = node("LineBreak")
Pre = node("Pre")
Blockquote = node("Blockquote")

# Forms.
Form = node("Form")
Input = node("Input")
Textarea = node("Textarea")
Select = node("Select")
Option = node("Option")
OptGroup = node("OptGroup")
Label = node("Label")
FieldSet = node("FieldSet")
Legend = node("Legend")

# Tables.
Table = node("Table")
TableHead = node("TableHead")
TableBody = node("TableBody")
TableFoot = node("TableFoot")
TableRow = node("TableRow")
TableHeaderCell = node("TableHeaderCell")
TableCell = node("TableCell")
Caption = node("Caption")

# Media.
Video = node("Video")
Audio = node("Audio")
Source = node("Source")

# ---------------------------------------------------------------------------
# v0.003 second vocabulary extension addendum ("even more vocabulary").
#
# Same mechanism as everything above -- each is `node("SomeType")`. See
# arklight.ir.schema.SCHEMA for what each one allows and CHANGELOG.md /
# docs/DESIGN-NOTES.md for why these specifically.
# ---------------------------------------------------------------------------

# Lists.
OrderedList = node("OrderedList")
DescriptionList = node("DescriptionList")
DescriptionTerm = node("DescriptionTerm")
DescriptionDetails = node("DescriptionDetails")

# Responsive images.
Picture = node("Picture")
PictureSource = node("PictureSource")

# Native widgets.
Progress = node("Progress")
Meter = node("Meter")
Datalist = node("Datalist")
Output = node("Output")

# Dialog.
Dialog = node("Dialog")

# More text-level semantics.
Kbd = node("Kbd")
Samp = node("Samp")
Var = node("Var")
Data = node("Data")
Ins = node("Ins")
Del = node("Del")
Q = node("Q")
Dfn = node("Dfn")
Address = node("Address")
Wbr = node("Wbr")
Bdi = node("Bdi")
Bdo = node("Bdo")

# Ruby annotations.
Ruby = node("Ruby")
Rt = node("Rt")
Rp = node("Rp")

# Table extras.
ColGroup = node("ColGroup")
Col = node("Col")

# Media.
Track = node("Track")

# Image maps.
Map = node("Map")
Area = node("Area")

# Embeds.
IFrame = node("IFrame")

# Fallback content for no-JS visitors.
NoScript = node("NoScript")

# ---------------------------------------------------------------------------
# v0.060, Stage 0: user-defined, reusable components.
#
# `component(...)` promotes a plain Python render function into a real,
# named node type the compiler's own tooling knows about -- see
# docs/Foundational/user-defined-components.md ("Option A -- macro
# expansion") and docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md
# for the staged rollout this belongs to. Re-exported here from
# arklight.ir.components so `from arklight import *` gives users
# `component`/`Prop` alongside every built-in component.
# ---------------------------------------------------------------------------

from arklight.ir.components import (  # noqa: E402
    ALLOW_REDEFINE_MARKER,
    ComponentState,
    Prop,
    register_backend_render,
    register_component,
)


def component(
    *,
    props: dict[str, Prop] | None = None,
    mode: str = "macro",
    default_style: dict[str, str] | None = None,
    state: dict[str, Any] | None = None,
    allow_redefine: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., ARKNode]]:
    """
    Decorator that registers a render function as a named, reusable
    component:

        @component(
            props={"active": Prop(default=None)},
            default_style={"display": "flex", "gap": "1rem"},
        )
        def NavBar(active=None):
            return Container(
                Link("Home", href="/"),
                Link("About", href="/about"),
            )

    The decorated name (`NavBar`) becomes callable exactly like a
    built-in component (`NavBar(active="home")`) -- but instead of
    building its subtree immediately, the call produces a marker
    `ARKNode(type="NavBar", ...)` that `arklight.ir.components.
    expand_ark_ast` splices the real, rendered subtree into, before
    Normalization ever runs. Props are checked against `props=` at
    expansion time -- an unknown prop or a missing required one fails
    the build with a clear message instead of a raw Python `TypeError`
    inside `NavBar` itself.

    `mode="macro"` (the default, Option A) never has a distinct
    rendering behavior beyond its shared `render_fn`. `mode="registry"`
    (Option B) is EXPERIMENTAL, and is the only mode that can register
    a per-backend override -- via `.register_backend(backend_name)` on
    the value this decorator returns (v0.060, Stage 3; see
    `arklight.ir.components`'s module docstring and the implementation
    doc for the full design). A `mode="registry"` component with no
    backend override registered behaves exactly like `mode="macro"` --
    it always falls back to its one shared `render_fn`.

    `default_style`, if given (v0.060, Stage 2), is a `{css-property:
    value}` dict -- the same shape and syntax `Site.style(...)` accepts
    (pseudo-class shorthand like `":hover:background"` included),
    validated here up front so a bad rule fails at *registration* time
    (import time), not buried inside a later build. When the build
    actually uses this component, its rules are folded into the site's
    stylesheet under a `.{ComponentName}` class, and that class is
    folded onto the rendered subtree's own root `class_name`
    automatically -- see `arklight.ir.components.
    _apply_default_class`/`collect_default_styles`. A component that
    never sets `default_style` behaves exactly as it did in Stage 0/1:
    no class is added, nothing is emitted for it, `class_name=` (if the
    render function sets one itself) is left completely alone.

    `state`, if given (v0.060, Stage 4 -- see
    `docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`),
    declares this component's own local, instance-scoped reactive
    state: `{local_name: initial_value}` (the common case, mirroring
    `State("name", initial)`'s own ergonomics), or
    `{local_name: ComponentState(initial=..., persist=True)}` when an
    instance needs `persist=True`. The render function references a
    declared name exactly like a page-level `State(...)` -- `Bind(...)`,
    `on_click=Action.*(...)`, `bind_class=Bind.when(...)`,
    `bind_value=Bind.model(...)` -- and every call site gets its own
    independent copy: two `Accordion(...)` calls on the same page never
    share one `"open"` value. A component that never sets `state=`
    behaves exactly as it did in Stage 0-3: it may still *consume*
    `Bind(...)`/`ActionRef` values a caller passes in as ordinary props
    from a page that already declares its own `State(...)`, exactly
    like `Container`/`Button` already do -- it just can't declare new
    state of its own. Not yet supported inside a `mode="registry"`
    component's own per-backend override subtree (v0.060 Stage 3) --
    see `arklight.ir.components.expand_node`'s docstring for the
    `ComponentError` that use raises today.

    `allow_redefine` (default `False`) -- decorating a name that's
    already registered raises
    `arklight.ir.components.DuplicateComponentError` unless this is
    `True`. This used to be silent, unconditional "last call wins":
    two components accidentally sharing a name would just have the
    second one win, with nothing pointing at either `@component(...)`
    site. Pass `allow_redefine=True` for the one legitimate case that
    served: re-importing/reloading a components module during
    iterative development, where redefining `NavBar` really is the
    point. See `arklight.ir.components.register_component`.
    """
    def decorator(render_fn: Callable[..., Any]) -> Callable[..., ARKNode]:
        name = render_fn.__name__
        validated_default_style = (
            _validate_component_default_style(name, default_style)
            if default_style is not None
            else None
        )
        validated_state = (
            _validate_component_state(name, state) if state is not None else None
        )
        register_component(
            name,
            render_fn,
            props=props,
            mode=mode,
            default_style=validated_default_style,
            state=validated_state,
            allow_redefine=allow_redefine,
        )

        def marker(**call_props: Any) -> ARKNode:
            return ARKNode(type=name, props=call_props, children=[])

        marker.__name__ = name
        marker.__qualname__ = name
        marker.__doc__ = render_fn.__doc__
        # Read by the site loader's namespace-shadowing check -- see
        # `arklight.ir.components.ALLOW_REDEFINE_MARKER`.
        setattr(marker, ALLOW_REDEFINE_MARKER, allow_redefine)

        def register_backend(
            backend_name: str, *, allow_redefine: bool = False
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            """
            v0.060, Stage 3. Decorator factory that registers the
            function it decorates as `name`'s render function for
            `backend_name` (e.g. `"html"`):

                @component(mode="registry")
                def NavBar(active=None):
                    return Container(...)  # shared default

                @NavBar.register_backend("html")
                def _(active=None):
                    return Container(..., class_name="html-only-navbar")

            Only available on a `mode="registry"` component -- see
            `arklight.ir.components.register_backend_render`, which
            this delegates to (and whose `ComponentError` this raises
            unchanged for a `mode="macro"` component, matching this
            decorator's "fail at the registration call, not three
            stages later" contract with every other decorator here).
            The decorated function's own name is irrelevant (`_` above
            is conventional, not required) -- unlike `component(...)`
            itself, nothing here derives an identity from it.

            `allow_redefine` (default `False`) -- registering a second
            override for the same `backend_name` on this component
            raises `arklight.ir.components.DuplicateComponentError`
            unless this is `True`; see that function's docstring for
            why this is no longer silent last-registration-wins.
            """
            def decorator(backend_render_fn: Callable[..., Any]) -> Callable[..., Any]:
                register_backend_render(
                    name, backend_name, backend_render_fn, allow_redefine=allow_redefine
                )
                return backend_render_fn

            return decorator

        marker.register_backend = register_backend
        return marker

    return decorator


# ---------------------------------------------------------------------------
# v0.0035: stateful JS -- capability, not vocabulary.
#
# `State`/`Bind`/`Action` are the reactivity primitives: a page declares
# state, components read it via `Bind`, and `on_click=` mutates it via a
# closed, described set of `Action.*` helpers (never an arbitrary JS/Python
# string -- see arklight.ir.schema.ACTION_REGISTRY and
# docs/DESIGN-NOTES.md, "v0.0035: stateful JS -- capability, not
# vocabulary", for the full design).
# ---------------------------------------------------------------------------


def State(
    name: str,
    initial: Any = None,
    persist: bool = False,
    media: str | None = None,
    query: str | None = None,
    history: str | None = None,
) -> ARKNode:
    """
    Declare page-scoped reactive state: `State("count", 0)`.

    Must appear as a direct child of `Page(...)` -- state belongs to the
    page, the same way `title=` does -- and is compiled into the
    Website IR's `IRPage.state`, never rendered as an HTML element
    itself. Validation checks every `Bind(...)`/`Action.*(...)` on the
    page references a `name` declared here.

    `persist=True` (`vdom-8`, docs/Backends/REFACTOR-INDEX.md row 16)
    opts this one key into `localStorage` persistence: the shipped
    runtime overrides the server-rendered initial value with whatever
    was last saved under `localStorage["ark:<page-path>:<name>"]` (if
    present and JSON-parseable), and saves the current value back out
    under that key on every change. Read/write failures (private
    browsing, quota, a hand-edited non-JSON value) degrade to "this key
    just doesn't persist" -- never a page-breaking error. Off by
    default, unchanged behavior for existing `State(...)` calls.

    `media="(min-width: 768px)"` (`v0.063`) opts this key into
    `matchMedia`-driven boolean state: as soon as the shipped runtime
    initializes, it overrides `initial` with
    `window.matchMedia(media).matches` (the value given here is only
    ever what a JS-disabled visitor sees -- pick a reasonable
    server-rendered guess, e.g. `False` for a "wide viewport" query),
    and attaches one `MediaQueryList` "change" listener per declared
    media state that keeps writing `State(name)` as the viewport
    crosses the query's breakpoint, exactly like a window resize
    listener but native and debounced by the browser itself.

        State("is_wide", False, media="(min-width: 768px)")
        Show(Predicate.truthy("is_wide"), Text("Desktop layout"))

    A `media=` key is still an ordinary `State(...)` in every other
    respect -- `Bind(...)`/`bind_class=`/`Show(...)` all read it the
    same way -- it just also has a second, non-`Action.*(...)` writer.
    Mutually independent of `persist=True` (both may be set at once,
    though a media-driven value re-derives itself every load, making
    persistence for it a no-op in practice). `None` (the default)
    means this key is plain, non-media-driven state, unchanged
    behavior for existing `State(...)` calls.

    `query="page"` (`v0.064`, `docs/Proposals/URL-STATE-AS-PRIMITIVE-
    PROPOSAL.md`) opts this key into two-way URL query-parameter
    syncing, the primitive this project previously had no authored
    answer for at all:

        State("page", initial=1, query="page")
        Text(Bind("page"))
        Button("Next", on_click=Action.increment("page", 1))

    An extension of the exact same shape `persist=True` already
    established (a value the compiler can't know at build time,
    corrected from an external source at runtime, with the same
    fail-open safety property), just sourced from
    `new URLSearchParams(location.search)` instead of `localStorage`:

    - *Read*, at page-init (and again on every browser back/forward
      navigation -- `popstate`, the one genuinely new runtime surface
      this feature adds, since ARKlight ships no SPA router and
      nothing before this listened for that event): if the query
      string carries this key's `query=` parameter, its value
      overrides `initial`, coerced by `initial`'s own Python type
      (`int` -> `parseInt`, `bool` -> a `"true"`/`"false"` mapping,
      `str` -> passthrough -- the same type-carrying mechanism that
      already lets `Computed(...)` be evaluated at build time). A
      missing or malformed value silently falls back to the baked
      `initial`, never a thrown error -- the same "every external-
      input read in this runtime fails open" invariant `persist`
      already holds, now a confirmed convention rather than a one-off.
    - *Write*, on every change (through `Action.*(...)`, exactly as
      `persist`'s `localStorage` write already does): the shipped
      runtime calls `history.replaceState(...)` with the updated
      search string, by default -- never a network request or page
      navigation. `State`, `Computed`, `Derive`, and every `Action` in
      this vocabulary are synchronous, in-memory primitives with no
      navigation step anywhere in them; a query-tagged `State` update
      stays that way rather than triggering a full reload or an
      `hx-boost` swap of a document that would, by construction, be
      byte-for-byte identical to the one already on screen (the
      compiler never sees the query string -- static file resolution
      strips it before ARKlight's output is even in the picture).

    `query=` names exactly one flat parameter key -- no nested
    objects, no array encodings. `None` (the default) means this key
    is plain, non-query-tracked state, unchanged behavior for existing
    `State(...)` calls. Mutually independent of `persist=`/`media=`
    (any combination may be set at once).

    `history="push"` (opt-in; the unmarked default is `"replace"`)
    gives this key's changes a real, back-button-worthy history entry
    instead of the default `history.replaceState(...)` -- for e.g. a
    paginated list, where landing back on an earlier page via the
    back button is expected, unlike a live-updating search box where
    every keystroke firing `replaceState` is correct. Only meaningful
    alongside `query=`; raises at build time if given without it. This
    is deliberately *not* threaded through `arklight.ir.schema.
    MODIFIER_REGISTRY` (the `prevent`/`stop`/`once`/`debounce`/
    `throttle` tokens `.with_modifiers(...)`/`.debounce(...)` attach
    to an `on_click=`/`bind_value=`) -- that registry describes
    per-*event* timing/dispatch modifiers on an `ActionRef`, not a
    per-*State-declaration* property with no event of its own to
    attach to, so reusing it here would be forcing an unrelated shape
    onto a different kind of knob rather than genuinely sharing one.
    """
    return ARKNode(
        type="State",
        props={
            "name": name,
            "initial": initial,
            "persist": persist,
            "media": media,
            "query": query,
            "history": history,
        },
        children=[],
    )


def Bind(name: str) -> ARKNode:
    """
    Reference a `State(...)` value from wherever a literal value is
    accepted today, e.g. `Text(Bind("count"))`. Compiled to a small
    `data-ark-bind="<name>"` element the shipped runtime keeps in sync
    with state -- never a template string evaluated at runtime.
    """
    return ARKNode(type="Bind", props={"name": name}, children=[])


def _bind_when(state: str, class_name: str) -> ClassBindSpec:
    """
    Reactive class binding (Stage 2 of "Reactive-core vdom staging" --
    see docs/DESIGN-NOTES.md): `bind_class=Bind.when("active", "is-active")`
    toggles `class_name` on/off as `state`'s truthiness changes,
    without ever touching the element's other static classes. A small
    structured `ClassBindSpec`, not a string -- validated against the
    page's declared `State(...)` names at compile time, same discipline
    `Action.*(...)` already established for `on_click=`.

        State("active", False)
        Container(class_name="card", bind_class=Bind.when("active", "is-active"))
    """
    return ClassBindSpec(state=state, class_name=class_name)


Bind.when = _bind_when


def _bind_model(name: str, *, debounce: int | None = None, throttle: int | None = None) -> Any:
    """
    Two-way input binding (`vdom-6`): `bind_value=Bind.model("query")`
    keeps an `Input`'s `value` in sync with `State("query", ...)` in
    both directions -- the element's initial `value` is pre-filled from
    state (same as `bind_class`), and the shipped runtime writes the
    user's keystrokes back into state on every `input` event. Unlike
    `bind_class=`, this is just the state name itself (no second
    value to pair it with), so `Bind.model(...)` is a thin, explicit
    spelling for "this is a two-way reference," not a distinct spec
    type -- `bind_value=` also accepts a plain string directly.

        State("query", "")
        Input(bind_value=Bind.model("query"))

    Only a `State(...)` name is a valid target (mirrors `Action.*(...)`
    's own restriction) -- a `Computed(...)` has no independent value
    of its own for user input to write back into.

    `v0.063`: pass `debounce=<ms>` or `throttle=<ms>` to wait for a
    pause in typing (or cap the write rate) before a keystroke is
    written back into state -- reuses the same `debounce`/`throttle`
    tokens `Action.*(...).debounce(...)`/`.throttle(...)` already
    validate against `arklight.ir.schema.MODIFIER_REGISTRY`, wired
    into the shipped `wireModelBinding` instead of the click
    dispatcher. With neither given, returns the same plain string as
    before -- only requesting a modifier changes the return type.

        Input(bind_value=Bind.model("query", debounce=300))
    """
    if debounce is None and throttle is None:
        return name
    modifiers: list[str] = []
    if debounce is not None:
        modifiers.append(f"debounce:{debounce}")
    if throttle is not None:
        modifiers.append(f"throttle:{throttle}")
    return ModelBindSpec(state=name, modifiers=tuple(modifiers))


Bind.model = _bind_model


def _action_arg(value: Any) -> Any:
    """
    A `Bind(name)` handed to an `Action.*(...)` as an argument means
    "the value `name` holds when the action runs", not a literal --
    the same reading `Text(Bind("count"))` already gives it wherever a
    literal value is accepted. Converted here, at construction, to the
    JSON-safe `{"__state__": name}` marker
    (`arklight.ast.nodes.state_ref`) so every later stage carries it
    like any other arg value. Anything else passes through untouched.
    Whether a given action's argument may take one is decided in
    Validation (`ActionSpec.state_args`), not here.
    """
    if isinstance(value, ARKNode) and value.type == "Bind":
        return state_ref(value.props["name"])
    return value


class Action:
    """
    A closed vocabulary of state-mutating actions for `on_click=`,
    alongside today's named behaviors (`on_click="toggle"`). Each
    returns a small structured `ActionRef` -- validated against
    `arklight.ir.schema.ACTION_REGISTRY` at compile time -- never a
    string of JavaScript or Python.

        Button("+1", on_click=Action.increment("count"))
        Button("-1", on_click=Action.decrement("count"))
        Button("Reset", on_click=Action.reset("count"))
        Button("Toggle", on_click=Action.toggle_bool("is_open"))

    v0.0035 vocabulary addendum: `decrement` and `reset` fill the two
    gaps most sites hit right away -- a counter's `-1` counterpart to
    `increment`, and "put this state back the way it started" without
    hardcoding the initial value again at every call site (`reset`
    reads the store's own captured initial value). Only the most
    commonly needed additions; see docs/DESIGN-NOTES.md for what's
    deliberately left for a future version.

    Capability fix (live-input -> action-value): `set`'s and
    `append`'s `value` may be a `Bind("name")` instead of a literal --
    "whatever `name` holds when the click happens". Paired with
    `bind_value=Bind.model("draft")` on an `Input`, that is the
    conventional `[type a task] [Add]` workflow:

        State("draft", "")
        State("tasks", [])
        Input(bind_value=Bind.model("draft"))
        Button("Add", on_click=Action.append("tasks", Bind("draft")))
        Watch("tasks", then=Action.reset("draft"))   # clear after adding

    Still closed vocabulary: the target must be a `State(...)` or
    `Computed(...)` declared on the same page (checked at build time),
    and it is read by name from the store -- never evaluated as an
    expression. Other actions' arguments (`increment`'s `delta`,
    `remove`'s `index`) reject a `Bind(...)` at build time. See
    `docs/Proposals/ACTION-VALUE-FROM-STATE-PROPOSAL.md`.
    """

    @staticmethod
    def set(name: str, value: Any) -> ActionRef:
        return ActionRef(action="set", state=name, args={"value": _action_arg(value)})

    @staticmethod
    def increment(name: str, delta: Any = 1) -> ActionRef:
        return ActionRef(action="increment", state=name, args={"delta": _action_arg(delta)})

    @staticmethod
    def decrement(name: str, delta: Any = 1) -> ActionRef:
        return ActionRef(action="decrement", state=name, args={"delta": _action_arg(delta)})

    @staticmethod
    def toggle_bool(name: str) -> ActionRef:
        return ActionRef(action="toggle_bool", state=name, args={})

    @staticmethod
    def reset(name: str) -> ActionRef:
        return ActionRef(action="reset", state=name, args={})

    @staticmethod
    def append(name: str, value: Any) -> ActionRef:
        """Appends `value` to a list-valued `State(...)`."""
        return ActionRef(action="append", state=name, args={"value": _action_arg(value)})

    @staticmethod
    def remove(name: str, index: Any) -> ActionRef:
        """Removes the element at `index` from a list-valued `State(...)`."""
        return ActionRef(action="remove", state=name, args={"index": _action_arg(index)})

    @staticmethod
    def geolocate(name: str) -> ActionRef:
        """
        `v0.063`: on click, asks the browser for the visitor's current
        location (`navigator.geolocation.getCurrentPosition`) and, once
        the browser's own permission prompt resolves, writes a plain
        `{"lat": ..., "lng": ...}` object into `State(name)`.

            State("here", None)
            Button("Find me", on_click=Action.geolocate("here"))
            Text(Bind("here"))

        Unlike every other action, this one is asynchronous: the write
        happens some time after the click, not before this dispatch
        returns -- see `arklight/backend/js/actions/geolocate.py` for
        why that's safe with the existing "fire and forget" dispatcher.
        If geolocation isn't available (unsupported browser, insecure
        context, permission denied), `name`'s value is simply never
        updated and a small notice is shown -- never a thrown error.
        """
        return ActionRef(action="geolocate", state=name, args={})


class PlatformAPI:
    """
    A closed vocabulary of platform-supplied capabilities (`v0.065`,
    accepted from `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`), for
    `on_click=`, alongside named behaviors and `Action.*(...)`. Each
    returns a small structured `PlatformAPIRef` -- validated against
    `arklight.ir.platform_api.PLATFORM_API_REGISTRY` at compile time,
    and against the selected backend's own declared support at build
    time -- never a string of JavaScript/Kotlin/C.

        Button("Notify me", on_click=PlatformAPI.notify("Saved!", body="Your changes were saved."))
        Button("Copy link", on_click=PlatformAPI.clipboard_write("https://example.com"))

    Unlike `Action.*(...)`, a `PlatformAPI.*(...)` call never targets a
    declared `State(...)` name -- it asks the *execution platform* to
    do something (show a notification, touch the clipboard), not the
    page's own reactive store. See `docs/Foundational/
    PLATFORM-APIS.md` Section 6 for where this boundary is drawn and
    why `Action.geolocate` stayed an `Action` rather than becoming the
    first `PlatformAPI.*(...)` entry.

    Deliberately a small, closed catalogue at acceptance (Section 23
    of the proposal, "Initial scope"): two capabilities, both
    implemented today by the Web backend (the reference/default
    implementation, Section 5) and by neither the Android nor the
    Linux Desktop backend yet (Section 6/22 -- earned progressively,
    not granted because the backend exists). Requesting either of
    these against `android`/`desktop` fails the build with a named
    diagnostic rather than silently doing nothing -- see
    `arklight.ir.platform_api.check_backend_support`.
    """

    @staticmethod
    def notify(title: str, body: str | None = None) -> PlatformAPIRef:
        """
        On click, asks the browser to show a user-visible notification
        with the given `title` and optional `body` -- the Web
        implementation of the `notify` platform API interface
        (`arklight/backend/js/platform_apis/notify.py`), falling back
        to ARKlight's own in-page notice (`arkNotify`) if the
        `Notification` API isn't available, and requesting permission
        the first time it's needed rather than assuming it's already
        granted.
        """
        args: dict[str, Any] = {"title": title}
        if body is not None:
            args["body"] = body
        return PlatformAPIRef(capability="notify", args=args)

    @staticmethod
    def clipboard_write(text: str) -> PlatformAPIRef:
        """
        On click, writes `text` to the system clipboard -- the Web
        implementation (`arklight/backend/js/platform_apis/
        clipboard_write.py`) uses `navigator.clipboard.writeText`,
        showing ARKlight's own in-page notice if clipboard access
        isn't available rather than failing silently.
        """
        return PlatformAPIRef(capability="clipboard_write", args={"text": text})


# ---------------------------------------------------------------------------
# `vdom-4` (docs/Backends/REFACTOR-INDEX.md row 12): computed/derived state.
#
# `Computed`/`Derive` close the "derived/computed state" gap named in the
# `v0.0035` addenda -- a page-scoped value derived from other `State(...)`/
# `Computed(...)` values, recomputed automatically whenever a dependency
# changes, without ever handing the runtime an expression string to
# evaluate. See arklight.ir.schema.DERIVATION_REGISTRY and
# docs/Foundational/DESIGN-NOTES.md ("Computed/derived state") for the
# full design.
# ---------------------------------------------------------------------------


def Computed(name: str, *, deps: tuple[str, ...] = (), derive: "DerivationRef | None" = None) -> ARKNode:
    """
    Declare a page-scoped derived value: `Computed("total",
    deps=("price", "qty"), derive=Derive.multiply("price", "qty"))`.

    Must appear as a direct child of `Page(...)`, same as `State(...)`
    -- a `Computed(...)` is a declaration, not renderable content, and
    is compiled into the Website IR rather than reaching any backend
    as a component. `deps` names every `State(...)`/other
    `Computed(...)` this value depends on (Validation checks each one
    resolves to something actually declared on the page, and rejects a
    dependency cycle); `Bind(...)`/`bind_class=` may reference a
    `Computed(...)`'s `name` exactly like a `State(...)`'s. Unlike
    `State(...)`, a `Computed(...)` is never a valid `Action.*(...)`
    target -- it has no independent value of its own to mutate, only
    the `derive` recomputation the runtime re-runs after every state
    change.
    """
    return ARKNode(
        type="Computed",
        props={"name": name, "deps": tuple(deps), "derive": derive},
        children=[],
    )


class Derive:
    """
    A closed vocabulary of derivations for `Computed(..., derive=...)`.
    Each returns a small structured `DerivationRef` -- validated
    against `arklight.ir.schema.DERIVATION_REGISTRY` at compile time --
    never a string of JavaScript or Python.

        Computed("total", deps=("price", "qty"), derive=Derive.multiply("price", "qty"))
        Computed("full_name", deps=("first", "last"),
                  derive=Derive.join("first", "last", sep=" "))
        Computed("item_count", deps=("items",), derive=Derive.count("items"))
        Computed("greeting", deps=("name",),
                  derive=Derive.format("Hello, {n}!", n="name"))
        Computed("is_over_limit", deps=("count", "limit"),
                  derive=Derive.compare("count", "limit", "gt"))
        Computed("shout", deps=("name",), derive=Derive.uppercase("name"))
        Computed("clean_input", deps=("raw",), derive=Derive.trim("raw"))
    """

    @staticmethod
    def sum(*names: str) -> DerivationRef:
        return DerivationRef(kind="sum", names=tuple(names))

    @staticmethod
    def multiply(*names: str) -> DerivationRef:
        return DerivationRef(kind="multiply", names=tuple(names))

    @staticmethod
    def join(*names: str, sep: str = " ") -> DerivationRef:
        return DerivationRef(kind="join", names=tuple(names), args={"sep": sep})

    @staticmethod
    def count(name: str) -> DerivationRef:
        """Reads a list-valued `State(...)`/`Computed(...)`'s length."""
        return DerivationRef(kind="count", names=(name,))

    @staticmethod
    def format(template: str, **names: str) -> DerivationRef:
        """
        Fixed `{name}`-style substitution over named state values only
        -- `str.format`-shaped, never a general string-eval. Each
        keyword maps a `{placeholder}` in `template` to the state/
        computed name whose value fills it, e.g.
        `Derive.format("Hello, {n}!", n="name")`.
        """
        return DerivationRef(
            kind="format",
            names=tuple(names.values()),
            args={"template": template, "names_map": dict(names)},
        )

    @staticmethod
    def compare(a: str, b: str, op: str) -> DerivationRef:
        """
        `op` is itself a closed choice (see
        `arklight.ir.schema.COMPARE_OPS`: `"eq"`/`"ne"`/`"gt"`/`"lt"`/
        `"gte"`/`"lte"`), never a raw operator string executed as
        code.
        """
        return DerivationRef(kind="compare", names=(a, b), args={"op": op})

    @staticmethod
    def subtract(*names: str) -> DerivationRef:
        """
        `v0.061`: `names[0]` minus every later name, in declared
        order -- `Derive.subtract("total", "discount")` reads as
        `total - discount`. Not associative like `sum`, so needs at
        least two names.
        """
        return DerivationRef(kind="subtract", names=tuple(names))

    @staticmethod
    def divide(*names: str) -> DerivationRef:
        """
        `v0.061`: `names[0]` divided by every later name, in declared
        order -- `Derive.divide("total", "count")` reads as
        `total / count`. Not associative like `sum`, so needs at
        least two names.
        """
        return DerivationRef(kind="divide", names=tuple(names))

    @staticmethod
    def min(*names: str) -> DerivationRef:
        """`v0.061`: the smallest of one or more state/computed values."""
        return DerivationRef(kind="min", names=tuple(names))

    @staticmethod
    def max(*names: str) -> DerivationRef:
        """`v0.061`: the largest of one or more state/computed values."""
        return DerivationRef(kind="max", names=tuple(names))

    @staticmethod
    def uppercase(name: str) -> DerivationRef:
        """`v0.062`: the named state/computed value, coerced to a
        string and upper-cased -- a string-casing sibling of
        `Derive.join`/`Derive.format`."""
        return DerivationRef(kind="uppercase", names=(name,))

    @staticmethod
    def trim(name: str) -> DerivationRef:
        """`v0.062`: the named state/computed value, coerced to a
        string with leading/trailing whitespace stripped -- a sibling
        of `Derive.join`/`Derive.format`."""
        return DerivationRef(kind="trim", names=(name,))


# ---------------------------------------------------------------------------
# `vdom-5` (docs/Backends/REFACTOR-INDEX.md row 13): watch effects.
#
# `Watch(...)` closes the "when X changes, also do Y" side-effect gap
# `Computed(...)` deliberately leaves open (a `Computed(...)` only ever
# *derives* a value -- it can't dispatch an `Action.*(...)` of its own).
# See docs/Foundational/DESIGN-NOTES.md ("Watch effects") for the full
# design. No new dispatch mechanism: a `Watch(...)`'s `then=` is the
# exact same `ActionRef` `on_click=Action.*(...)` already uses, just
# invoked from a state-change subscription instead of a click listener
# -- see `arklight/backend/js/runtime/watch.py`.
# ---------------------------------------------------------------------------


def Watch(name: str, *, then: "ActionRef") -> ARKNode:
    """
    Declare a page-scoped side effect: whenever the `State(...)`/
    `Computed(...)` named `name` changes value, run `then` -- an
    `Action.*(...)` reference, exactly like an `on_click=` value.

        State("celsius", 0)
        State("fahrenheit", 32)
        Watch("celsius", then=Action.set("fahrenheit", ...))

    Must appear as a direct child of `Page(...)`, same as `State(...)`/
    `Computed(...)` -- a `Watch(...)` is a declaration, not renderable
    content, and is compiled into the Website IR rather than reaching
    any backend as a component. `name` may be a `State(...)` or a
    `Computed(...)` (anything `Bind(...)` could reference); `then`
    must target a real `State(...)` on the same page, the same
    restriction `Action.*(...)` already has when used as `on_click=` --
    a `Computed(...)` has no independent value of its own to mutate.
    """
    return ARKNode(
        type="Watch",
        props={"name": name, "then": then},
        children=[],
    )


# ---------------------------------------------------------------------------
# `vdom-7` (docs/Backends/REFACTOR-INDEX.md row 15): per-item list
# rendering (`Repeat`) + conditional show/hide (`Show`).
#
# Both are real, renderable content (unlike `State(...)`/`Computed(...)`/
# `Watch(...)`, which are page-scoped declarations extracted out of the
# tree entirely) -- `Repeat(...)`/`Show(...)` appear exactly where their
# rendered output should go, the same as `Container(...)`/`List(...)`.
# See `docs/new js backend proposal/ARCHITECTURE-VDOM.md` SS6.2-6.3 for
# the design this follows, and `arklight/backend/js/runtime/repeat.py`/
# `show.py` for the client-side half.
# ---------------------------------------------------------------------------


class RepeatItem:
    """
    References to the *current* item inside a `Repeat(...)`'s
    `template=` callable -- meaningful only there (Validation rejects
    either one used anywhere else).

        Repeat("todos", template=lambda: Container(
            Text(RepeatItem.value()),
            Button("x", on_click=Action.remove("todos", RepeatItem.index())),
        ))
    """

    @staticmethod
    def value() -> ARKNode:
        """
        The current item's own value, wherever a literal value/
        `Bind(...)` is accepted, e.g. `Text(RepeatItem.value())`. Compiles to
        a small marker element the shipped runtime substitutes with
        that item's value -- never a template string evaluated at
        runtime, same discipline `Bind(...)` already holds for
        `State(...)`.
        """
        return ARKNode(type="ItemBind", props={}, children=[])

    @staticmethod
    def index() -> ItemIndexRef:
        """
        The current item's *live* position -- only valid as an
        `Action.*(...)` arg, e.g. `Action.remove(name, RepeatItem.index())`.
        Unlike a literal index, this is re-resolved on every render, so
        a `Button(on_click=Action.remove(...))` inside a repeated item
        keeps removing *that* item even after an earlier
        `Action.remove(...)` shifted every later item's position.
        """
        return ItemIndexRef()


def Repeat(name: str, *, template: Callable[[], ARKNode]) -> ARKNode:
    """
    Per-item list rendering: `Repeat("todos", template=lambda: ...)`
    renders one copy of `template()`'s returned `ARKNode` per element
    of the list-valued `State(...)`/`Computed(...)` named `name`,
    re-rendered (added/removed/reordered, keyed by each item's own
    value -- see `Repeat`'s docstring on the JS side for why not by
    index) through the vendored snabbdom `patch()`
    (`arklight/backend/js/vdom.py`) whenever `name` changes.

        State("todos", ["Buy milk", "Walk the dog"])
        Repeat("todos", template=lambda: Container(
            Text(RepeatItem.value()),
            Button("Remove", on_click=Action.remove("todos", RepeatItem.index())),
        ))

    `template` is called exactly once, at compile time, to build the
    per-item markup -- it never receives the actual item values (those
    only exist once the page runs, server-rendered per current item or
    client-rendered per the JS runtime's own copy of `name`); reference
    the current item via `RepeatItem.value()`/`RepeatItem.index()` inside it
    instead. The returned template stays closed-vocabulary, built from
    the same `NodeSpec`/schema nodes every other page-facing construct
    uses -- never an arbitrary JS render function.

    Deliberately scoped to a *single* dynamic value per item (whatever
    `name`'s list elements themselves are, typically a string/number),
    not per-field access into a list of records -- see
    docs/Backends/REFACTOR-INDEX.md row 15 for what's left for a future
    version.
    """
    return ARKNode(type="Repeat", props={"name": name}, children=[template()])


class Predicate:
    """
    A closed vocabulary of predicates for `Show(..., ...)`'s first
    argument. Each returns a small structured `PredicateRef` --
    validated against `arklight.ir.schema.PREDICATE_REGISTRY` at
    compile time -- never a string of JavaScript or Python.

        Show(Predicate.truthy("is_open"), Text("Details go here"))
        Show(Predicate.falsy("is_open"), Text("Click to expand"))
        Show(Predicate.equals("role", "admin_role"), Text("Welcome, admin"))
        Show(Predicate.gt("score", "threshold"), Text("You passed!"))
    """

    @staticmethod
    def truthy(name: str) -> PredicateRef:
        return PredicateRef(kind="truthy", names=(name,))

    @staticmethod
    def falsy(name: str) -> PredicateRef:
        return PredicateRef(kind="falsy", names=(name,))

    @staticmethod
    def equals(a: str, b: str) -> PredicateRef:
        """`v0.062`: true when the two named state/computed values are
        `===` equal, mirroring `Derive.compare(a, b, "eq")`'s own
        semantics but as a standalone predicate kind (no `op=` arg)."""
        return PredicateRef(kind="equals", names=(a, b))

    @staticmethod
    def gt(a: str, b: str) -> PredicateRef:
        """`v0.062`: true when `a`'s value is greater than `b`'s,
        mirroring `Derive.compare(a, b, "gt")`."""
        return PredicateRef(kind="gt", names=(a, b))

    @staticmethod
    def lt(a: str, b: str) -> PredicateRef:
        """`v0.062`: true when `a`'s value is less than `b`'s,
        mirroring `Derive.compare(a, b, "lt")`."""
        return PredicateRef(kind="lt", names=(a, b))


def Show(predicate: PredicateRef, *children: Any) -> ARKNode:
    """
    Conditional rendering: mounts `children` in the page exactly when
    `predicate` (a `Predicate.*(...)` reference) is true against the
    page's current `State(...)`/`Computed(...)`, re-evaluated on every
    state change.

        State("is_open", False)
        Show(Predicate.truthy("is_open"), Text("Now you see me"))

    `children` renders server-side (with JS disabled, the page shows
    exactly what `predicate` evaluates to against `State(...)`'s
    *initial* values -- there's no client-only content) and is toggled
    via the HTML `hidden` attribute client-side, a content-visibility
    semantic, not a style declaration -- see
    `arklight/backend/js/runtime/show.py`'s module docstring for why
    this is `Show`'s actual mechanism rather than the vnode-swap
    `docs/new js backend proposal/ARCHITECTURE-VDOM.md` SS6.3 proposes.
    """
    return ARKNode(type="Show", props={"predicate": predicate}, children=list(children))


BUILTIN_COMPONENTS = {
    "Page": Page,
    "Heading": Heading,
    "Text": Text,
    "Button": Button,
    "Container": Container,
    "Link": Link,
    "Image": Image,
    "List": List,
    "Item": Item,
    "Repeat": Repeat,
    "Show": Show,
    "Header": Header,
    "Footer": Footer,
    "Main": Main,
    "Nav": Nav,
    "Section": Section,
    "Article": Article,
    "Aside": Aside,
    "Figure": Figure,
    "FigCaption": FigCaption,
    "Details": Details,
    "Summary": Summary,
    "Strong": Strong,
    "Em": Em,
    "Small": Small,
    "Mark": Mark,
    "Code": Code,
    "Cite": Cite,
    "Abbr": Abbr,
    "Sub": Sub,
    "Sup": Sup,
    "Span": Span,
    "Time": Time,
    "HorizontalRule": HorizontalRule,
    "LineBreak": LineBreak,
    "Pre": Pre,
    "Blockquote": Blockquote,
    "Form": Form,
    "Input": Input,
    "Textarea": Textarea,
    "Select": Select,
    "Option": Option,
    "OptGroup": OptGroup,
    "Label": Label,
    "FieldSet": FieldSet,
    "Legend": Legend,
    "Table": Table,
    "TableHead": TableHead,
    "TableBody": TableBody,
    "TableFoot": TableFoot,
    "TableRow": TableRow,
    "TableHeaderCell": TableHeaderCell,
    "TableCell": TableCell,
    "Caption": Caption,
    "Video": Video,
    "Audio": Audio,
    "Source": Source,
    "OrderedList": OrderedList,
    "DescriptionList": DescriptionList,
    "DescriptionTerm": DescriptionTerm,
    "DescriptionDetails": DescriptionDetails,
    "Picture": Picture,
    "PictureSource": PictureSource,
    "Progress": Progress,
    "Meter": Meter,
    "Datalist": Datalist,
    "Output": Output,
    "Dialog": Dialog,
    "Kbd": Kbd,
    "Samp": Samp,
    "Var": Var,
    "Data": Data,
    "Ins": Ins,
    "Del": Del,
    "Q": Q,
    "Dfn": Dfn,
    "Address": Address,
    "Wbr": Wbr,
    "Bdi": Bdi,
    "Bdo": Bdo,
    "Ruby": Ruby,
    "Rt": Rt,
    "Rp": Rp,
    "ColGroup": ColGroup,
    "Col": Col,
    "Track": Track,
    "Map": Map,
    "Area": Area,
    "IFrame": IFrame,
    "NoScript": NoScript,
}


def _check_css_syntax(context: str, prop: str, value: str) -> None:
    """
    Free-function core of `Site._validate_css_syntax` -- syntax-checks
    one (property, value) pair against the same rules `site.style(...)`
    has always enforced. `context` is the human-readable prefix an
    error message opens with (e.g. `"site.style('nav', ...)"`); it's
    never re-validated itself. Split out (v0.060 Stage 2) so
    `component(..., default_style=...)` -- registered independently of
    any `Site` instance, so it has no `self` to call a method on -- can
    share this exact validation instead of a second, easily-drifting
    copy of it. `Site._validate_css_syntax` is now a thin wrapper
    around this.
    """
    if prop.startswith(":"):
        match = _CSS_PSEUDO_RULE_RE.match(prop)
        if not match:
            raise CSSSyntaxError(
                f"{context} has an invalid pseudo-class "
                f"rule key {prop!r} -- expected the form "
                f"':pseudo:property', e.g. ':hover:background'."
            )
        pseudo = match.group("pseudo")
        if pseudo not in ALLOWED_PSEUDO_CLASSES:
            raise CSSSyntaxError(
                f"{context} uses unsupported pseudo-class "
                f"{pseudo!r} in {prop!r}. Supported: "
                f"{', '.join(sorted(ALLOWED_PSEUDO_CLASSES))}."
            )
    elif not _CSS_PROPERTY_NAME_RE.match(prop):
        raise CSSSyntaxError(
            f"{context} has an invalid CSS property name "
            f"{prop!r} -- letters, digits, and hyphens only (or a "
            f"'--custom-property'), and it can't start with a digit."
        )

    if any(ch in value for ch in _CSS_VALUE_INJECTION_CHARS):
        raise CSSSyntaxError(
            f"{context} property {prop!r} has a value "
            f"{value!r} containing '{{', '}}', or a newline -- that would "
            f"break out of its declaration. Use one property/value pair "
            f"per key instead of a raw CSS block."
        )


def _validate_component_default_style(
    component_name: str, default_style: dict[str, str]
) -> dict[str, str]:
    """
    v0.060, Stage 2: validate `component(..., default_style={...})` the
    same way `Site.style(name, rules)` validates its own `rules` --
    same non-empty-dict/non-empty-string-value checks, same
    `_check_css_syntax` (pseudo-class shorthand included), same
    `CSSSyntaxError` on a bad pair. Returns a clean, plain `dict` copy
    on success (never the caller's own dict by reference); raises
    `ValueError`/`CSSSyntaxError` otherwise. There's no class-name
    check here the way `Site.style(name, ...)` checks `name` -- a
    component's name is already a valid Python identifier (it's a
    function name), and `_CSS_CLASS_NAME_RE` accepts every valid
    Python identifier ARKlight would ever see here.
    """
    if not isinstance(default_style, dict) or not default_style:
        raise ValueError(
            f"component {component_name!r}: default_style needs a "
            f"non-empty dict of {{css-property: value}}, e.g. "
            f"{{'color': 'red'}}, got {default_style!r}."
        )
    clean: dict[str, str] = {}
    for prop, value in default_style.items():
        if not isinstance(prop, str) or not prop.strip():
            raise ValueError(
                f"component {component_name!r}: default_style has a "
                f"non-string or empty CSS property name: {prop!r}."
            )
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"component {component_name!r}: default_style property "
                f"{prop!r} needs a non-empty string value, got {value!r}."
            )
        _check_css_syntax(f"component {component_name!r}: default_style", prop, value)
        clean[prop] = value
    return clean


def _validate_component_state(
    component_name: str, state: dict[str, Any]
) -> dict[str, ComponentState]:
    """
    v0.060, Stage 4: validate/normalize `component(..., state={...})`.
    Each entry is either a bare initial value (`{"open": False}` -- the
    common case, mirroring `State("open", False)`'s own two-positional-
    arg ergonomics) or an explicit `ComponentState(initial=False,
    persist=True)` for the less-common `persist=True` case. Returns a
    clean `{local_name: ComponentState}` dict (never the caller's own
    dict by reference) -- same "validate/normalize once, at
    registration time, so a mistake here is a clear error at import
    time rather than a ComponentError three build stages later"
    contract `_validate_component_default_style` already established
    for `default_style`.
    """
    if not isinstance(state, dict) or not state:
        raise ValueError(
            f"component {component_name!r}: state needs a non-empty dict of "
            f"{{local_name: initial_value}} (or {{local_name: "
            f"ComponentState(initial=..., persist=True)}} for persist=True), "
            f"got {state!r}."
        )
    clean: dict[str, ComponentState] = {}
    for local_name, value in state.items():
        if not isinstance(local_name, str) or not local_name:
            raise ValueError(
                f"component {component_name!r}: state has a non-string or "
                f"empty local state name: {local_name!r}."
            )
        clean[local_name] = value if isinstance(value, ComponentState) else ComponentState(initial=value)
    return clean


class Site:
    """
    The application object.

    Usage:

        site = Site()

        @site.page("/")
        def home():
            return Page(Heading("Hello"))

    `site.page(route)` is a decorator that registers a page function
    under a route. Nothing is executed or compiled at registration time
    -- the compiler pipeline calls each registered function later, when
    it builds the ARK AST for the whole site.
    """

    def __init__(
        self,
        name: str = "arklight-site",
        *,
        max_width: str | None = None,
        bg: str | None = None,
        font_family: str | None = None,
        button_text: str | None = None,
        lang: str = "en",
        stack_space: str | None = None,
        cluster_space: str | None = None,
        sidebar_space: str | None = None,
        sidebar_width: str | None = None,
        switcher_space: str | None = None,
        switcher_threshold: str | None = None,
        grid_min: str | None = None,
        grid_space: str | None = None,
        center_gutter: str | None = None,
        reel_space: str | None = None,
        app_shell: bool = False,
        strict_csp: bool = True,
        trusted_script_origins: list[str] | None = None,
    ) -> None:
        self.name = name
        # <html lang="..."> for every page this site builds, unless a
        # page overrides it with its own Page(lang=...). Previously
        # hardcoded to "en" in the HTML backend with no override path
        # at all -- see WebsiteIR.lang's comment in arklight/ir/build.py.
        if not isinstance(lang, str) or not lang.strip():
            raise ValueError(f"Site(lang=...) needs a non-empty language tag string, got {lang!r}.")
        self.lang = lang
        # route -> page function
        self.routes: dict[str, Callable[[], ARKNode]] = {}
        # v0.042: name -> {css-property: value}, registered via
        # `site.style(...)`. Structured input only -- see `style()` below
        # for why this isn't a raw CSS string.
        self.custom_styles: dict[str, dict[str, str]] = {}
        # Experimental (docs/EXPERIMENTAL-APIS.md): (condition, class_name,
        # rules) triples registered via `site.media_query(...)`, kept
        # separate from `custom_styles` above rather than overloading
        # `style()`'s key syntax -- an experimental escape hatch gets its
        # own explicit opt-in surface, not a silently-expanded standard one.
        self.custom_media_queries: list[tuple[str, str, dict[str, str]]] = []
        # Every `ExperimentalUsage` recorded by an opt-in call
        # (`media_query()` so far) on this Site, in call order --
        # `arklight.compiler.pipeline` drains this to print the inline
        # "[EXPERIMENTAL FEATURE ACTIVE]" banner and, deduplicated, the
        # end-of-build summary block.
        self.experimental_usages: list = []
        # EXPERIMENTAL (docs/EXPERIMENTAL-APIS.md): user-supplied
        # `(output_files: dict[str, str]) -> dict[str, str]` callables
        # registered via `site.raw_postprocess(...)`, run in
        # registration order over the *combined* output of every
        # backend's own render()+postprocess() pass -- see
        # `arklight.compiler.pipeline.build`. Empty for sites that
        # never call `site.raw_postprocess(...)`.
        self.raw_postprocessors: list[Callable[[dict[str, str]], dict[str, str]]] = []
        # CSS backend refactor: `max_width`/`bg` override two of the
        # `:root`-declared `--ark-*` custom properties that `CSSBackend`
        # used to bake in as constants. Both are read by `body`'s *own*
        # rule (`max-width: var(--ark-max-width)`, `background:
        # var(--ark-bg)`) -- see docs/CONTAINER-WIDTH-BUG.md and the CSS
        # backend architecture notes for why that specifically makes them
        # unreachable from any wrapper/descendant override: a CSS custom
        # property only cascades *downward*, and `body` resolves its own
        # rule before any site-authored wrapper div exists to override it
        # on. `Site(max_width=..., bg=...)` is the fix -- these become
        # real constructor kwargs, threaded through Website IR to
        # `CSSBackend`, which now generates `:root` instead of hardcoding
        # it (see `arklight/backend/css/render.py`). Both stay `None` by
        # default, so a site that doesn't pass either gets ARKlight's
        # stock defaults, unchanged.
        self.css_var_overrides: dict[str, str] = {}
        if max_width is not None:
            self._set_css_var_override("max_width", "--ark-max-width", max_width)
        if bg is not None:
            self._set_css_var_override("bg", "--ark-bg", bg)
        if font_family is not None:
            # Same unreachable-value bug class `max_width`/`bg` above
            # already fix -- see design_tokens.py's `--ark-font-family`
            # comment. `body` reads this directly, so before this a
            # site author had no way to change the font at all.
            self._set_css_var_override("font_family", "--ark-font-family", font_family)
        if button_text is not None:
            # Fixes the button-text-color/accent-color decoupling --
            # see design_tokens.py's `--ark-button-text` comment.
            self._set_css_var_override("button_text", "--ark-button-text", button_text)

        # Layout-primitive tokens (Stack/Cluster/Sidebar/Switcher/Grid/
        # Reel spacing + Sidebar's fixed-column width + Switcher's
        # stack/row breakpoint). These already had a `var(--ark-x,
        # fallback)` fallback at their point of use in BASE_CSS, so a
        # *per-instance* wrapper `style=` override already worked --
        # what was missing was a sitewide path, same shape as
        # `max_width`/`bg` above. All default to `None` (unset), so a
        # site passing none of these gets ARKlight's stock per-use
        # defaults, unchanged.
        for kwarg_name, var_name, value in (
            ("stack_space", "--ark-stack-space", stack_space),
            ("cluster_space", "--ark-cluster-space", cluster_space),
            ("sidebar_space", "--ark-sidebar-space", sidebar_space),
            ("sidebar_width", "--ark-sidebar-width", sidebar_width),
            ("switcher_space", "--ark-switcher-space", switcher_space),
            ("switcher_threshold", "--ark-switcher-threshold", switcher_threshold),
            ("grid_min", "--ark-grid-min", grid_min),
            ("grid_space", "--ark-grid-space", grid_space),
            ("center_gutter", "--ark-center-gutter", center_gutter),
            ("reel_space", "--ark-reel-space", reel_space),
        ):
            if value is not None:
                self._set_css_var_override(kwarg_name, var_name, value)

        # Structural addendum (see docs/DESIGN-NOTES.md "CSS selector
        # algebra + at-rule vocabulary"): storage for the new
        # `Site.style_selector`/`keyframes`/`font_face`/
        # `container_query`/`supports`/`page_rule`/`import_style`
        # registrations. Each is its own list/dict, same "don't
        # overload one structure with several unrelated shapes"
        # reasoning `custom_media_queries` already documents against
        # `custom_styles` above -- a selector rule, a keyframes
        # definition, and an `@import` url are different enough shapes
        # that folding them together would just move the type-checking
        # into the reader instead of the type system.
        self.selector_rules: list[tuple[str, dict[str, str]]] = []
        self.custom_keyframes: dict[str, dict[str, dict[str, str]]] = {}
        self.font_faces: list[dict[str, str]] = []
        self.container_queries: list[tuple[str | None, str, str, dict[str, str]]] = []
        self.supports_rules: list[tuple[str, str, dict[str, str]]] = []
        self.page_rules: list[tuple[str | None, dict[str, str]]] = []
        self.style_imports: list[str] = []

        # htmx-4 (docs/Backends/REFACTOR-INDEX.md row 9 /
        # docs/Backends/JS-BACKEND-REFACTOR-PLAN.md "The app-illusion
        # problem, stated precisely"): opt-in app-shell navigation for
        # sites that get wrapped in a packaging-backend shell (Android/
        # KaiOS/Desktop) where a full document reload on every internal
        # link defeats the point of shipping it as an installable app.
        # Naming placeholder, per the design doc. Defaults to `False`
        # -- unset, ARKlight's output is byte-for-byte what it always
        # was: real multi-page navigation, no `hx-boost` anywhere. Set,
        # the HTML backend emits `hx-boost="true"` on `<body>` (see
        # `arklight/backend/html/page_render.py`) and the JS backend
        # ships HTMX on every page of the site, not just ones that
        # already needed it for a named behavior or `State(...)` (see
        # `arklight/backend/js/render.py`'s `needs_htmx`). No
        # validation needed -- a plain bool, same as every other
        # `Site(...)` feature flag.
        self.app_shell = bool(app_shell)

        # Runtime policy enforcement (docs/Foundational/RUNTIME-POLICY.md):
        # closed-vocabulary/no-eval was already a *compile-time* guarantee
        # (nothing ARKlight's own compiler emits ever constructs a
        # function from a string -- see WHAT-ARKLIGHT-IS.md's "Closed-
        # vocabulary" point). That says nothing about *runtime*: nothing
        # stopped an injected/compromised script (a browser extension, a
        # supply-chain-compromised CDN dependency, a future bug) from
        # calling eval/Function/innerHTML-with-untrusted-content/
        # document.write once the page is loaded. A strict
        # Content-Security-Policy meta tag is the browser-enforced
        # backstop for that gap -- see `arklight/backend/html/csp.py` for
        # what it declares and, importantly, what it deliberately leaves
        # alone (style-src is never touched: inline `style="..."` is a
        # first-class, already-documented escape hatch --
        # docs/Foundational/CONFIGURABILITY.md -- and restricting it here
        # would be an unrelated regression, not hardening).
        #
        # `strict_csp` defaults to `True` (new default behavior, not
        # gated behind an opt-in kwarg -- same precedent as htmx-5's
        # unconditional `htmx.config.allowEval = false`, see
        # arklight/backend/js/render.py). Per CONFIGURABILITY.md, the
        # *disallowal* of eval/inline-script itself stays a "safety-
        # critical, deliberately fixed" non-option -- there's no kwarg
        # that reintroduces 'unsafe-eval' or 'unsafe-inline'. What a real
        # site can legitimately need instead:
        #   - `trusted_script_origins`: additive script-src origins for
        #     a genuinely trusted external script (an analytics snippet,
        #     a third-party embed SDK) -- reachability-rule-qualifying,
        #     since nothing today lets a site add a CSP source at all.
        #   - `strict_csp=False`: the escape valve for a site whose
        #     `Site.raw_postprocess(...)` step (EXPERIMENTAL-APIS.md)
        #     injects inline <script> content the default policy would
        #     otherwise silently block -- see raw-postprocess's own
        #     warning text in arklight/experimental.py for why this
        #     can't be solved with a nonce (ARKlight ships static files;
        #     a nonce baked into a static build is publicly readable and
        #     provides no actual protection, unlike a real per-request
        #     server-rendered nonce), so an explicit opt-out is the
        #     honest mechanism here, matching how raw_postprocess itself
        #     is already an explicit, warned, all-or-nothing escape
        #     hatch rather than a partial one.
        self.strict_csp = bool(strict_csp)
        if trusted_script_origins is not None:
            if not isinstance(trusted_script_origins, list) or not all(
                isinstance(origin, str) and origin.strip() for origin in trusted_script_origins
            ):
                raise ValueError(
                    "Site(trusted_script_origins=...) needs a list of non-empty strings "
                    f"(script-src origins), got {trusted_script_origins!r}."
                )
            # Bugfix: each origin is spliced verbatim, space-separated,
            # straight into the `script-src` directive's value
            # (csp.py::_render_csp_meta_tag) -- so an origin containing
            # whitespace or a `;` doesn't stay a single script-src
            # source the way the kwarg's own docs (above) promise it
            # will. Whitespace silently splits one entry into what
            # *looks* like two origins; a `;` terminates the `script-src`
            # directive early and starts an entirely new CSP directive
            # this module never intended to emit (e.g.
            # `["evil.example.com; frame-ancestors *"]` adds a
            # `frame-ancestors` directive from a kwarg that is only
            # supposed to add script-src origins). Separately, this
            # comment block states directly that "there's no kwarg that
            # reintroduces 'unsafe-eval' or 'unsafe-inline'" -- but
            # nothing enforced that until now, so
            # `trusted_script_origins=["'unsafe-inline'"]` silently did
            # exactly that. All three are the same class of bug: a
            # contract this docstring/comment already makes, that the
            # code didn't actually keep. Caught here, at Site()
            # construction (build time), per this project's
            # fails-loudly-at-build-time-or-not-at-all rule
            # (docs/README.md's Philosophy section) -- not deferred to
            # a broken/weakened CSP discovered later in a real browser.
            for origin in trusted_script_origins:
                if any(ch.isspace() for ch in origin) or ";" in origin:
                    raise ValueError(
                        "Site(trusted_script_origins=...) entries must be a single "
                        "script-src source with no whitespace or ';' -- "
                        f"{origin!r} would split into multiple sources or inject a "
                        "new CSP directive when rendered."
                    )
                if origin.strip("'\"").lower() in {"unsafe-inline", "unsafe-eval"}:
                    raise ValueError(
                        "Site(trusted_script_origins=...) can't include "
                        f"{origin!r} -- ARKlight's strict CSP deliberately has no "
                        "kwarg that reintroduces 'unsafe-inline'/'unsafe-eval' "
                        "into script-src."
                    )
        self.trusted_script_origins: list[str] = list(trusted_script_origins or [])

    def _set_css_var_override(self, kwarg_name: str, var_name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Site({kwarg_name}=...) needs a non-empty CSS value string, "
                f"got {value!r}."
            )
        self.css_var_overrides[var_name] = value

    def style(self, name: str, rules: dict[str, str], *, allow_redefine: bool = False) -> None:
        """
        Register a real, named, reusable CSS class -- `class_name="name"`
        anywhere in the site then picks up `rules` from the generated
        stylesheet, instead of repeating a `style={...}` dict on every
        node that needs it.

        `rules` is a plain `{css-property: value}` dict, the same shape
        already used for the per-node `style={...}` prop -- deliberately
        not a raw CSS string, so this doesn't reopen the "no arbitrary
        CSS/HTML strings" boundary the rest of ARKlight holds. Calling
        this again with a name that's already registered raises
        `DuplicateStyleNameError` unless `allow_redefine=True` is
        passed -- this used to be silent, unconditional "last call
        wins", which hid two unrelated `site.style(...)` calls
        accidentally colliding on the same class name behind whichever
        one happened to run last. Pass `allow_redefine=True` for the
        one legitimate case that served: deliberately redefining a
        class as a site is built up, without needing a separate
        "update" method.

        A key may also be a pseudo-class-scoped property, written
        ":<pseudo>:<property>" (e.g. ":hover:background"), to reach a
        simple interactive state -- `site.style("btn", {"background":
        "blue", ":hover:background": "red"})` renders both `.btn { ... }`
        and `.btn:hover { background: red; }`. `<pseudo>` must be one of
        `ALLOWED_PSEUDO_CLASSES`; anything else raises `CSSSyntaxError`.
        """
        if not isinstance(name, str) or not _CSS_CLASS_NAME_RE.match(name):
            raise ValueError(
                f"site.style({name!r}, ...) needs a valid CSS class name -- "
                f"letters, digits, hyphens, and underscores only, and it "
                f"can't start with a digit."
            )
        if name in self.custom_styles and not allow_redefine:
            raise DuplicateStyleNameError(
                f"site.style({name!r}, ...) is already registered. "
                "Registering it again would silently replace the "
                "earlier rules -- if that's deliberate, pass "
                f"allow_redefine=True: site.style({name!r}, rules, "
                "allow_redefine=True). Otherwise two different calls "
                f"are colliding on the class name {name!r}; pick a "
                "different name for one of them."
            )
        if not isinstance(rules, dict) or not rules:
            raise ValueError(
                f"site.style({name!r}, rules) needs a non-empty dict of "
                f"{{css-property: value}}, e.g. {{'color': 'red'}}."
            )
        for prop, value in rules.items():
            if not isinstance(prop, str) or not prop.strip():
                raise ValueError(
                    f"site.style({name!r}, ...) has a non-string or empty "
                    f"CSS property name: {prop!r}."
                )
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"site.style({name!r}, ...) property {prop!r} needs a "
                    f"non-empty string value, got {value!r}."
                )
            self._validate_css_syntax(name, prop, value)
        self.custom_styles[name] = dict(rules)

    def media_query(self, condition: str, class_name: str, rules: dict[str, str]) -> None:
        """
        EXPERIMENTAL (see `docs/EXPERIMENTAL-APIS.md`) -- register a
        `@media` block: `.class_name { ... }` rendered inside
        `@media (condition) { ... }` in the generated stylesheet.

        This is a deliberate, opt-in escape hatch from ARKlight's
        intrinsic layout model, not a peer of `style()` -- viewport-
        keyed rules are exactly the thing `.stack`/`.cluster`/
        `.switcher`/`.grid`/`.sidebar` exist to make unnecessary, and
        they're markedly less reliable on Android's device spread
        (foldables, OEM WebViews, non-standard aspect ratios) than the
        "phone vs desktop" case breakpoint intuition is usually built
        around. Every call is flagged: an `[EXPERIMENTAL FEATURE
        ACTIVE]` banner prints the moment the build detects it, and a
        summary block prints again at the end of the build. Prefer an
        intrinsic layout primitive first; reach for this only when the
        design genuinely cannot be expressed without a viewport-keyed
        rule.

        `condition` is the raw text that goes inside `@media (...)`
        (e.g. `"max-width: 600px"` or `"orientation: landscape"`) --
        not validated beyond "non-empty string", since the space of
        valid media-feature syntax is large; a malformed condition
        surfaces as broken generated CSS, the same failure mode
        hand-written `@media` would have. `class_name`/`rules` are
        validated exactly like `style()`.
        """
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(
                f"site.media_query(condition, ...) needs a non-empty media "
                f"condition string, e.g. 'max-width: 600px', got {condition!r}."
            )
        if not isinstance(class_name, str) or not _CSS_CLASS_NAME_RE.match(class_name):
            raise ValueError(
                f"site.media_query(..., {class_name!r}, ...) needs a valid CSS "
                f"class name -- letters, digits, hyphens, and underscores "
                f"only, and it can't start with a digit."
            )
        if not isinstance(rules, dict) or not rules:
            raise ValueError(
                f"site.media_query(..., {class_name!r}, rules) needs a "
                f"non-empty dict of {{css-property: value}}, e.g. "
                f"{{'flex-direction': 'column'}}."
            )
        for prop, value in rules.items():
            if not isinstance(prop, str) or not prop.strip() or prop.startswith(":"):
                raise ValueError(
                    f"site.media_query(..., {class_name!r}, ...) has an "
                    f"invalid CSS property name: {prop!r} (pseudo-class keys "
                    f"aren't supported inside a media query block)."
                )
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"site.media_query(..., {class_name!r}, ...) property "
                    f"{prop!r} needs a non-empty string value, got {value!r}."
                )
            self._validate_css_syntax(class_name, prop, value)

        self.custom_media_queries.append((condition.strip(), class_name, dict(rules)))
        self.experimental_usages.append(
            experimental.emit("css-media-queries")
        )

    def _validate_css_syntax(self, name: str, prop: str, value: str) -> None:
        """
        Syntax-check one `site.style(...)` (property, value) pair --
        called after the non-empty/is-a-string checks in `style()`
        above, so `prop`/`value` are already known to be non-empty
        strings here. Raises `CSSSyntaxError` (a `ValueError` subclass)
        on anything that isn't valid CSS syntax for the shape ARKlight
        accepts; returns `None` on a valid pair.

        Thin wrapper around the free function `_check_css_syntax` below
        -- kept as a method (rather than inlined) so every existing
        `self._validate_css_syntax(...)` call site in this class is
        unaffected; the free function exists so `component(...,
        default_style=...)` (registered independently of any `Site`
        instance) can reuse the exact same rules -- see
        `_validate_component_default_style`.
        """
        _check_css_syntax(f"site.style({name!r}, ...)", prop, value)

    def _validate_plain_rules(self, context: str, rules: dict[str, str]) -> dict[str, str]:
        """
        Shared validation for the "flat `{property: value}` dict, no
        pseudo-class shorthand" shape used by `container_query`,
        `supports`, and `page_rule` below (`style_selector` needs its
        own variant, since it also has to recognize `&`-nested dict
        values -- see `_expand_style_selector_rules`). `context` is a
        short description used in error messages (e.g. the selector or
        `"@page"`), not re-validated itself.
        """
        if not isinstance(rules, dict) or not rules:
            raise ValueError(
                f"{context} needs a non-empty dict of {{css-property: value}}, "
                f"e.g. {{'color': 'red'}}."
            )
        clean: dict[str, str] = {}
        for prop, value in rules.items():
            if not isinstance(prop, str) or not prop.strip() or prop.startswith(":"):
                raise ValueError(
                    f"{context} has an invalid CSS property name {prop!r} "
                    f"(pseudo-class shorthand keys aren't supported here -- "
                    f"put the pseudo-class in the selector itself)."
                )
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{context} property {prop!r} needs a non-empty string "
                    f"value, got {value!r}."
                )
            self._validate_css_syntax(context, prop, value)
            clean[prop] = value
        return clean

    def _expand_style_selector_rules(
        self, selector_text: str, selector_ast, rules: dict
    ) -> list[tuple[str, dict[str, str]]]:
        """
        Validate `rules` for `style_selector(selector_text, rules)` and
        expand any `&`-nested dict values into their own fully-resolved
        (selector, rules) pairs -- see `style_selector`'s docstring for
        the nesting shapes accepted. Recurses for multi-level nesting.
        """
        if not isinstance(rules, dict) or not rules:
            raise ValueError(
                f"site.style_selector({selector_text!r}, rules) needs a "
                f"non-empty dict of {{css-property: value}} (values may "
                f"also be a nested '&'-prefixed rules dict), got {rules!r}."
            )

        plain: dict[str, str] = {}
        nested: list[tuple[str, dict]] = []
        for key, value in rules.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    f"site.style_selector({selector_text!r}, ...) has a "
                    f"non-string or empty rule key: {key!r}."
                )
            if key.startswith("&"):
                if not isinstance(value, dict) or not value:
                    raise ValueError(
                        f"site.style_selector({selector_text!r}, ...) "
                        f"nested key {key!r} needs a non-empty rules dict, "
                        f"got {value!r}."
                    )
                nested.append((key, value))
                continue
            if key.startswith(":"):
                raise CSSSyntaxError(
                    f"site.style_selector({selector_text!r}, ...) doesn't "
                    f"support the ':pseudo:property' shorthand -- put the "
                    f"pseudo-class in the selector itself, e.g. "
                    f"style_selector({selector_text!r} + ':hover', ...)."
                )
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"site.style_selector({selector_text!r}, ...) property "
                    f"{key!r} needs a non-empty string value, got {value!r}."
                )
            self._validate_css_syntax(selector_text, key, value)
            plain[key] = value

        results: list[tuple[str, dict[str, str]]] = []
        if plain:
            results.append((selector_text, plain))
        for key, nested_rules in nested:
            nested_selector_text = self._resolve_nested_selector(selector_text, selector_ast, key)
            try:
                nested_ast = css_selectors.parse_selector_list(nested_selector_text)
            except css_selectors.CSSSelectorSyntaxError as exc:
                raise CSSSyntaxError(str(exc)) from exc
            results.extend(
                self._expand_style_selector_rules(nested_selector_text, nested_ast, nested_rules)
            )
        return results

    @staticmethod
    def _resolve_nested_selector(selector_text: str, selector_ast, key: str) -> str:
        """
        Resolve one `&`-prefixed nested key (e.g. `"&:hover"`,
        `"& .child"`, `"& > .child"`) against `selector_text` into a
        fully-written selector string -- desugared at author time into
        a flat selector, not emitted as real CSS nesting syntax (`&`),
        so the generated stylesheet stays readable in browsers that
        predate CSS nesting support. Only defined for a single base
        selector (not a grouped `a, b` list): a group would make "the
        parent" ambiguous, so a grouped base selector must be nested
        against one branch at a time via separate `style_selector` calls.
        """
        if len(selector_ast) != 1:
            raise CSSSyntaxError(
                f"site.style_selector({selector_text!r}, ...) nested key "
                f"{key!r} needs a single base selector, not a grouped "
                f"selector list -- register each branch of the group with "
                f"its own style_selector(...) call."
            )
        remainder = key[1:]
        if not remainder:
            raise CSSSyntaxError(
                "site.style_selector(...) nested key '&' needs something "
                "after '&', e.g. '&:hover' or '& .child'."
            )
        first = remainder[0]
        if first in (">", "+", "~"):
            return f"{selector_text} {first} {remainder[1:].strip()}"
        if first.isspace():
            return f"{selector_text} {remainder.strip()}"
        if first in (":", ".", "["):
            return f"{selector_text}{remainder}"
        raise CSSSyntaxError(
            f"site.style_selector(...) nested key {key!r} isn't a "
            f"recognized '&'-nesting shape -- expected '&:pseudo', "
            f"'&.class', '&[attr]', '& .child' (descendant), or "
            f"'& > .child' / '& + .child' / '& ~ .child' (combinator)."
        )

    def style_selector(self, selector: str, rules: dict) -> None:
        """
        Register CSS rules against an arbitrary *structural* selector --
        combinators (`.a > .b`), grouped selectors (`h1, h2`), a bare
        tag override (`blockquote`, no `class_name=` needed on every
        node), attribute selectors (`[type="email"]`), pseudo-elements
        (`::before`), and parameterized pseudo-classes (`:not(.a)`,
        `:has(> .icon)`, `:is(...)`, `:where(...)`, `:nth-child(2n+1)`)
        -- everything `Site.style(...)`'s single flat `.name { }` block
        can't reach. See docs/DESIGN-NOTES.md ("CSS selector algebra +
        at-rule vocabulary") for why this is a separate method rather
        than widening `style()` itself.

        `selector` is parsed by `arklight.backend.css.selectors
        .parse_selector_list` -- a closed grammar, not a raw CSS
        string: anything outside pseudo-classes/pseudo-elements/
        attribute operators this module recognizes raises
        `CSSSyntaxError` rather than being passed through. A bare tag
        selector must be a real HTML tag ARKlight's HTML backend can
        emit (`arklight.backend.css.selectors.KNOWN_HTML_TAGS`).

        `rules` is normally a flat `{css-property: value}` dict, same
        shape as `style()`/`style={...}`. A key may also be a
        `&`-prefixed nested rules dict to reach a related selector
        without re-typing the base selector -- `&:hover` (pseudo-class
        on the same element), `&.active` / `&[data-open]` (compound
        extension), `& .child` (descendant), `& > .child` / `&
        + .child` / `& ~ .child` (combinator). Nesting is resolved at
        author time into a fully-written selector (see
        `_resolve_nested_selector`), not emitted as real CSS `&`
        nesting syntax, and only supported against a single base
        selector (not a grouped `a, b` list -- register each branch
        separately). The `:pseudo:property` shorthand `style()` uses
        isn't accepted here; put the pseudo-class in the selector
        string (or a `&`-nested key) instead.

        Example:

            site.style_selector(".card", {
                "padding": "1rem",
                "&:hover": {"box-shadow": "0 2px 8px rgba(0,0,0,.15)"},
                "& > img": {"border-radius": "8px 8px 0 0"},
            })
            site.style_selector("blockquote", {"font-style": "italic"})
            site.style_selector("h1, h2, h3", {"font-family": "var(--ark-font-family)"})
            site.style_selector('[data-state="open"] .panel', {"display": "block"})
        """
        if not isinstance(selector, str) or not selector.strip():
            raise ValueError(
                f"site.style_selector(selector, ...) needs a non-empty "
                f"selector string, got {selector!r}."
            )
        try:
            selector_ast = css_selectors.parse_selector_list(selector)
        except css_selectors.CSSSelectorSyntaxError as exc:
            raise CSSSyntaxError(str(exc)) from exc
        canonical_selector = css_selectors.render_selector_list(selector_ast)

        expanded = self._expand_style_selector_rules(canonical_selector, selector_ast, rules)
        self.selector_rules.extend((sel, dict(r)) for sel, r in expanded)

    def keyframes(self, name: str, frames: dict[str, dict[str, str]]) -> None:
        """
        Register a real `@keyframes name { ... }` block -- one of the
        gaps explicitly deferred in earlier design notes ("not silently
        dropped", see docs/DESIGN-NOTES.md). `transition` itself
        already worked (it's just a property value inside `style=`),
        but there was no way to *define* a keyframe sequence to
        transition/animate through.

        `name` is a CSS custom-ident (letters/digits/hyphens/
        underscores, no leading digit) -- referenced from any node's
        `style={"animation": "name 2s ease infinite"}` the same way any
        other `animation-name` value would be, since inline `style=` is
        already unrestricted for property *values*.

        `frames` is `{stop: {property: value}}`, where each `stop` is
        `"from"`, `"to"`, or a percentage like `"50%"` -- structured
        data, not a raw `@keyframes` block string. Stops are re-sorted
        (from -> ascending percentages -> to) regardless of the dict's
        insertion order, so `{"100%": ..., "0%": ...}` and `{"0%":
        ..., "100%": ...}` produce identical output.

        Example:

            site.keyframes("fade-in", {
                "from": {"opacity": "0"},
                "to": {"opacity": "1"},
            })
        """
        if not isinstance(name, str) or not _CSS_IDENT_RE.match(name):
            raise ValueError(
                f"site.keyframes({name!r}, ...) needs a valid animation "
                f"name -- letters, digits, hyphens, and underscores only, "
                f"and it can't start with a digit."
            )
        if not isinstance(frames, dict) or not frames:
            raise ValueError(
                f"site.keyframes({name!r}, frames) needs a non-empty dict "
                f"of {{stop: {{property: value}}}}, e.g. {{'from': "
                f"{{'opacity': '0'}}, 'to': {{'opacity': '1'}}}}."
            )

        normalized: dict[str, dict[str, str]] = {}
        for stop, rules in frames.items():
            if not isinstance(stop, str) or not _KEYFRAME_STOP_RE.match(stop.strip()):
                raise CSSSyntaxError(
                    f"site.keyframes({name!r}, ...) has an invalid stop "
                    f"{stop!r} -- expected 'from', 'to', or a percentage "
                    f"like '50%'."
                )
            normalized[stop.strip()] = self._validate_plain_rules(
                f"site.keyframes({name!r}, ...) stop {stop!r}", rules
            )

        def _sort_key(stop: str) -> float:
            if stop == "from":
                return -1.0
            if stop == "to":
                return 101.0
            return float(stop[:-1])

        self.custom_keyframes[name] = {
            stop: normalized[stop] for stop in sorted(normalized, key=_sort_key)
        }

    def font_face(
        self, family: str, src: str | list[dict[str, str]], **descriptors: str
    ) -> None:
        """
        Register a real `@font-face { ... }` block -- the other gap
        explicitly deferred in earlier design notes. Previously a
        self-hosted webfont was entirely unreachable; an external one
        was only reachable indirectly via `Page(links=[{"rel":
        "stylesheet", "href": "https://fonts.googleapis.com/..."}])`.

        `family` becomes the `font-family` descriptor (quoted
        automatically). `src` is either a single url string, or a list
        of `{"url": ..., "format": "woff2"}` dicts for a multi-format
        fallback chain (`format` is optional; when given, it must be
        one of `ALLOWED_FONT_FACE_FORMATS`). Extra keyword arguments
        become other `@font-face` descriptors (`font_weight="700"` ->
        `font-weight: 700;`, `font_display="swap"`, `font_style=...`,
        `unicode_range=...`, etc.) -- underscores convert to hyphens,
        same convention `style={...}`/`responsive_style={...}` already
        use for prop names.

        Example:

            site.font_face(
                "Inter",
                [
                    {"url": "/assets/inter.woff2", "format": "woff2"},
                    {"url": "/assets/inter.woff", "format": "woff"},
                ],
                font_weight="400 700",
                font_display="swap",
            )
        """
        if not isinstance(family, str) or not family.strip():
            raise ValueError(
                f"site.font_face(family, ...) needs a non-empty font "
                f"family name string, got {family!r}."
            )
        if any(ch in family for ch in _CSS_VALUE_INJECTION_CHARS) or '"' in family:
            raise CSSSyntaxError(
                f"site.font_face({family!r}, ...) has a family name that "
                f"isn't safe to emit -- quotes, braces, semicolons, and "
                f"newlines aren't allowed."
            )

        if isinstance(src, str):
            src_entries: list[dict[str, str]] = [{"url": src}]
        elif isinstance(src, list) and src:
            src_entries = src
        else:
            raise ValueError(
                f"site.font_face({family!r}, src, ...) needs `src` to be a "
                f"non-empty url string or a non-empty list of "
                f"{{'url': ..., 'format': ...}} dicts, got {src!r}."
            )

        src_parts: list[str] = []
        for entry in src_entries:
            if not isinstance(entry, dict) or "url" not in entry:
                raise ValueError(
                    f"site.font_face({family!r}, ...) has a src entry that "
                    f"isn't a dict with at least a 'url' key: {entry!r}."
                )
            url = entry["url"]
            if (
                not isinstance(url, str)
                or not url.strip()
                or any(ch in url for ch in _CSS_VALUE_INJECTION_CHARS)
                or '"' in url
            ):
                raise CSSSyntaxError(
                    f"site.font_face({family!r}, ...) has a src url that "
                    f"isn't safe to emit: {url!r}."
                )
            fmt = entry.get("format")
            if fmt is None:
                src_parts.append(f'url("{url}")')
            else:
                if fmt not in ALLOWED_FONT_FACE_FORMATS:
                    raise CSSSyntaxError(
                        f"site.font_face({family!r}, ...) has unsupported "
                        f"src format {fmt!r}. Supported: "
                        f"{', '.join(sorted(ALLOWED_FONT_FACE_FORMATS))}."
                    )
                src_parts.append(f'url("{url}") format("{fmt}")')

        descriptor_rules: dict[str, str] = {
            "font-family": f'"{family}"',
            "src": ", ".join(src_parts),
        }
        for desc_name, desc_value in descriptors.items():
            css_desc_name = desc_name.replace("_", "-")
            if not isinstance(desc_value, str) or not desc_value.strip():
                raise ValueError(
                    f"site.font_face({family!r}, ...) descriptor "
                    f"{desc_name!r} needs a non-empty string value, got "
                    f"{desc_value!r}."
                )
            self._validate_css_syntax(family, css_desc_name, desc_value)
            descriptor_rules[css_desc_name] = desc_value

        self.font_faces.append(descriptor_rules)

    def container_query(
        self, condition: str, selector: str, rules: dict, *, name: str | None = None
    ) -> None:
        """
        Register a real `@container (condition) { selector { ... } }`
        block (optionally `@container name (condition) { ... }` when a
        specific named container is targeted) -- one of the structural
        gaps `site.media_query(...)` can't reach, since a container
        query is keyed to an ancestor element's size, not the viewport.

        Unlike `site.media_query(...)`, this isn't flagged as an
        ARKlight "viewport-keyed, prefer intrinsic layout" EXPERIMENTAL
        escape hatch: a container query is compatible with (and often
        used alongside) intrinsic layout, since it reacts to an actual
        ancestor's size rather than assuming a "phone vs desktop"
        breakpoint intuition about the whole viewport.

        A site declares the container context itself via the existing,
        unrestricted `style={...}` prop -- `style={"container-type":
        "inline-size", "container-name": "sidebar"}` on the ancestor
        node -- no new mechanism needed there.

        `condition` is the raw text inside the required parentheses
        (e.g. `"min-width: 400px"`), validated the same
        non-empty/no-injection-characters way `site.media_query(...)`'s
        `condition` already is. `selector`/`rules` go through the same
        grammar/validation as `style_selector(...)`.
        """
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(
                f"site.container_query(condition, ...) needs a non-empty "
                f"container condition string, e.g. 'min-width: 400px', "
                f"got {condition!r}."
            )
        if any(ch in condition for ch in _CSS_VALUE_INJECTION_CHARS):
            raise CSSSyntaxError(
                f"site.container_query({condition!r}, ...) has a "
                f"condition that isn't safe to emit -- braces, "
                f"semicolons, and newlines aren't allowed."
            )
        if name is not None and (not isinstance(name, str) or not _CSS_IDENT_RE.match(name)):
            raise ValueError(
                f"site.container_query(..., name={name!r}) needs a valid "
                f"container name -- letters, digits, hyphens, and "
                f"underscores only, and it can't start with a digit."
            )
        try:
            selector_ast = css_selectors.parse_selector_list(selector)
        except css_selectors.CSSSelectorSyntaxError as exc:
            raise CSSSyntaxError(str(exc)) from exc
        canonical_selector = css_selectors.render_selector_list(selector_ast)
        clean_rules = self._validate_plain_rules(
            f"site.container_query(..., {canonical_selector!r}, ...)", rules
        )
        self.container_queries.append((name, condition.strip(), canonical_selector, clean_rules))

    def supports(self, condition: str, selector: str, rules: dict) -> None:
        """
        Register a real `@supports (condition) { selector { ... } }`
        feature-query block -- a progressive-enhancement gate ARKlight
        previously had no authoring surface for at all.

        `condition` is the raw text inside the required parentheses
        (e.g. `"display: grid"`, or a compound condition like
        `"(display: grid) and (gap: 1rem)"`), validated the same
        non-empty/no-injection-characters way `site.media_query(...)`'s
        `condition` is -- the space of valid feature-query syntax is
        large, so (like `media_query`) this doesn't parse it beyond
        that; a malformed condition surfaces as broken generated CSS,
        the same failure mode hand-written `@supports` would have.
        `selector`/`rules` go through the same grammar/validation as
        `style_selector(...)`.
        """
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(
                f"site.supports(condition, ...) needs a non-empty feature "
                f"condition string, e.g. 'display: grid', got {condition!r}."
            )
        if any(ch in condition for ch in _CSS_VALUE_INJECTION_CHARS):
            raise CSSSyntaxError(
                f"site.supports({condition!r}, ...) has a condition that "
                f"isn't safe to emit -- braces, semicolons, and newlines "
                f"aren't allowed."
            )
        try:
            selector_ast = css_selectors.parse_selector_list(selector)
        except css_selectors.CSSSelectorSyntaxError as exc:
            raise CSSSyntaxError(str(exc)) from exc
        canonical_selector = css_selectors.render_selector_list(selector_ast)
        clean_rules = self._validate_plain_rules(
            f"site.supports(..., {canonical_selector!r}, ...)", rules
        )
        self.supports_rules.append((condition.strip(), canonical_selector, clean_rules))

    def page_rule(self, rules: dict, *, pseudo: str | None = None) -> None:
        """
        Register a real `@page { ... }` (or `@page :pseudo { ... }`)
        print-layout rule. `pseudo`, if given, must be one of
        `ALLOWED_PAGE_PSEUDOS` (`"first"`, `"left"`, `"right"`,
        `"blank"`) -- same fixed-set discipline as
        `ALLOWED_PSEUDO_CLASSES`. `rules` goes through the same plain
        `{property: value}` validation `container_query`/`supports` use.

        Example:

            site.page_rule({"margin": "2cm"})
            site.page_rule({"margin-top": "4cm"}, pseudo="first")
        """
        if pseudo is not None and pseudo not in ALLOWED_PAGE_PSEUDOS:
            raise CSSSyntaxError(
                f"site.page_rule(..., pseudo={pseudo!r}) isn't supported. "
                f"Supported: {', '.join(sorted(ALLOWED_PAGE_PSEUDOS))}."
            )
        clean_rules = self._validate_plain_rules("site.page_rule(...)", rules)
        self.page_rules.append((pseudo, clean_rules))

    def import_style(self, url: str) -> None:
        """
        EXPERIMENTAL (see `docs/EXPERIMENTAL-APIS.md`) -- register a
        sitewide `@import url("...");` statement, emitted first in
        the generated stylesheet (required -- `@import` must precede
        every other rule per the CSS spec, aside from `@charset`).
        Mainly useful for an external stylesheet/webfont host that
        isn't reachable via `Page(links=[...])` for some reason;
        prefer `links=` for the common case (it doesn't block the CSS
        Object Model the way `@import` does).

        Flagged because the imported file's contents can't be
        validated by ARKlight the way every other generated rule is --
        it's fetched and applied by the browser at request time, from
        whatever the URL happens to resolve to then. Every call is
        flagged: an `[EXPERIMENTAL FEATURE ACTIVE]` banner prints the
        moment the build detects it, and a summary block prints again
        at the end of the build.
        """
        if not isinstance(url, str) or not url.strip():
            raise ValueError(
                f"site.import_style(url) needs a non-empty url string, "
                f"got {url!r}."
            )
        if any(ch in url for ch in _CSS_VALUE_INJECTION_CHARS) or '"' in url:
            raise CSSSyntaxError(
                f"site.import_style({url!r}) isn't safe to emit -- quotes, "
                f"braces, semicolons, and newlines aren't allowed."
            )
        self.style_imports.append(url.strip())
        self.experimental_usages.append(experimental.emit("css-import"))

    def raw_postprocess(
        self, fn: Callable[[dict[str, str]], dict[str, str]]
    ) -> Callable[[dict[str, str]], dict[str, str]]:
        """
        \u26a0\ufe0f EXPERIMENTAL -- ADVANCED, UNCHECKED ESCAPE HATCH (see
        `docs/EXPERIMENTAL-APIS.md`). Register a raw postprocessing
        function that runs directly over the site's *final* output
        files -- the same combined `{relative_path: contents}` dict
        every `Backend.postprocess()` gets (see
        `arklight.backend.base.Backend.postprocess`), except this one
        is authored by you, not a backend, and runs last: after every
        backend's own render() + postprocess() pass, in the order
        `site.raw_postprocess(...)` was called. Whatever `fn` returns
        replaces the output dict entirely and is written to disk
        as-is -- add, remove, or rewrite any file, in any way.

        This is an advanced experimental feature. It is recommended to
        use it wisely: because nothing about `fn`'s output is
        validated, normalized, or checked against ARKlight's layout
        model the way every other generated file is, it hands you a
        million different ways to shoot yourself in the foot -- a
        stray string replace can silently corrupt every page in the
        site with no error at build time. Proceed with caution. Every
        call is flagged: an `[EXPERIMENTAL FEATURE ACTIVE]` banner
        prints the moment the build detects it, and a summary block
        prints again at the end of the build.

        Can be used directly (`site.raw_postprocess(my_fn)`) or as a
        bare decorator (`@site.raw_postprocess`) -- either way `fn` is
        returned unchanged, so decorating doesn't shadow the name.

        Prefer a real `Backend` subclass overriding `postprocess()`
        instead whenever the transformation is reusable across
        projects or depends on what another backend already produced
        -- it gets the exact same second pass with none of the
        unchecked-arbitrary-code risk. Reach for this only for a
        genuine one-off that can't be expressed that way.
        """
        if not callable(fn):
            raise TypeError(
                f"site.raw_postprocess(fn) needs a callable taking and "
                f"returning a dict[str, str], got {fn!r}."
            )
        self.raw_postprocessors.append(fn)
        self.experimental_usages.append(experimental.emit("raw-postprocess"))
        return fn

    def page(self, route: str) -> Callable[[Callable[[], ARKNode]], Callable[[], ARKNode]]:
        if not route.startswith("/"):
            raise ValueError(f"Route {route!r} must start with '/'")

        def decorator(fn: Callable[[], ARKNode]) -> Callable[[], ARKNode]:
            if route in self.routes:
                raise ValueError(f"Route {route!r} is already registered")
            self.routes[route] = fn
            return fn

        return decorator

    def build_ark_ast(self) -> dict[str, ARKNode]:
        """
        Call every registered page function and collect the resulting
        ARK AST, keyed by route. This is the moment the "Python source"
        actually turns into "ARK AST" objects.
        """
        ark_ast: dict[str, ARKNode] = {}
        for route, fn in self.routes.items():
            result = fn()
            if not isinstance(result, ARKNode):
                raise TypeError(
                    f"Page function for route {route!r} must return a Page(...) node, "
                    f"got {type(result).__name__!r} instead."
                )
            ark_ast[route] = result
        return ark_ast


__all__ = [
    "Site",
    "Page",
    "Heading",
    "Text",
    "Button",
    "Container",
    "Link",
    "Image",
    "List",
    "Item",
    "Header",
    "Footer",
    "Main",
    "Nav",
    "Section",
    "Article",
    "Aside",
    "Figure",
    "FigCaption",
    "Details",
    "Summary",
    "Strong",
    "Em",
    "Small",
    "Mark",
    "Code",
    "Cite",
    "Abbr",
    "Sub",
    "Sup",
    "Span",
    "Time",
    "HorizontalRule",
    "LineBreak",
    "Pre",
    "Blockquote",
    "Form",
    "Input",
    "Textarea",
    "Select",
    "Option",
    "OptGroup",
    "Label",
    "FieldSet",
    "Legend",
    "Table",
    "TableHead",
    "TableBody",
    "TableFoot",
    "TableRow",
    "TableHeaderCell",
    "TableCell",
    "Caption",
    "Video",
    "Audio",
    "Source",
    "OrderedList",
    "DescriptionList",
    "DescriptionTerm",
    "DescriptionDetails",
    "Picture",
    "PictureSource",
    "Progress",
    "Meter",
    "Datalist",
    "Output",
    "Dialog",
    "Kbd",
    "Samp",
    "Var",
    "Data",
    "Ins",
    "Del",
    "Q",
    "Dfn",
    "Address",
    "Wbr",
    "Bdi",
    "Bdo",
    "Ruby",
    "Rt",
    "Rp",
    "ColGroup",
    "Col",
    "Track",
    "Map",
    "Area",
    "IFrame",
    "NoScript",
    "component",
    "Prop",
    "State",
    "Bind",
    "Action",
    "ActionRef",
    "Computed",
    "Watch",
    "Derive",
    "DerivationRef",
    # `vdom-7`/`v0.062` (docs/Backends/REFACTOR-INDEX.md row 15): these
    # were defined in this module but missing from `__all__` --
    # reachable via `arklight.api.Repeat` etc., but not via `from
    # arklight.api import *`, the same gap `test_package_exports.py`
    # already found and fixed once for the v0.003 second vocabulary
    # addendum. `arklight/__init__.py` re-exports all of these too, so
    # `from arklight import *` (the documented way users are told to
    # import everything) reaches them as well.
    "Repeat",
    "RepeatItem",
    "Show",
    "Predicate",
    "PredicateRef",
    "ItemIndexRef",
    "ClassBindSpec",
    "ModelBindSpec",
    "ARKNode",
]
