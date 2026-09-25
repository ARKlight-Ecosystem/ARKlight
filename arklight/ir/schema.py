"""
Shared component schema.

A small, single source of truth for facts about each built-in component
type that more than one pipeline stage needs to agree on. Right now
that's just "does this component only ever hold plain text?" -- both
Normalization (should a bare string become a Text node, or stay a plain
string?) and Validation (is a nested component here even allowed?) need
to agree on the answer, so it lives here instead of being duplicated.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NodeSpec:
    required_props: tuple[str, ...] = field(default_factory=tuple)
    text_only_children: bool = False
    allow_children: bool = True


# v0.001 built-in component schema. Extending this dict is how future
# milestones add new component types without touching normalize/validate
# logic.
SCHEMA: dict[str, NodeSpec] = {
    "Page": NodeSpec(),
    "Container": NodeSpec(),
    "Heading": NodeSpec(text_only_children=True),
    "Text": NodeSpec(text_only_children=True),
    "Button": NodeSpec(text_only_children=True),
    "Link": NodeSpec(required_props=("href",), text_only_children=True),
    "Image": NodeSpec(required_props=("src",), allow_children=False),
    "List": NodeSpec(),
    "Item": NodeSpec(text_only_children=True),
    # ------------------------------------------------------------------
    # v0.003: vocabulary extension. These don't change how the compiler
    # pipeline *works* -- normalize/validate/build/backends are all
    # driven entirely off this dict and TEXT_ONLY_TYPES below -- they
    # just give users more of standard HTML to reach for. Grouped by
    # what they're commonly used for in a real static site; see
    # docs/Foundational/DESIGN-NOTES.md for how this addresses the v0.003 ceiling.
    # ------------------------------------------------------------------
    # Semantic page/section layout (HTML5 sectioning + grouping content).
    "Header": NodeSpec(),
    "Footer": NodeSpec(),
    "Main": NodeSpec(),
    "Nav": NodeSpec(),
    "Section": NodeSpec(),
    "Article": NodeSpec(),
    "Aside": NodeSpec(),
    "Figure": NodeSpec(),
    "FigCaption": NodeSpec(text_only_children=True),
    # <details>/<summary>: a native, browser-built disclosure widget --
    # an accordion/expand-collapse that needs *zero* JS, not even the
    # `toggle` behavior. `Details` takes an optional `open=True` prop.
    "Details": NodeSpec(),
    "Summary": NodeSpec(text_only_children=True),
    # Text-level semantics.
    "Strong": NodeSpec(text_only_children=True),
    "Em": NodeSpec(text_only_children=True),
    "Small": NodeSpec(text_only_children=True),
    "Mark": NodeSpec(text_only_children=True),
    "Code": NodeSpec(text_only_children=True),
    "Cite": NodeSpec(text_only_children=True),
    "Abbr": NodeSpec(text_only_children=True),
    "Sub": NodeSpec(text_only_children=True),
    "Sup": NodeSpec(text_only_children=True),
    "Span": NodeSpec(text_only_children=True),
    "Time": NodeSpec(text_only_children=True),
    "HorizontalRule": NodeSpec(allow_children=False),
    "LineBreak": NodeSpec(allow_children=False),
    # `Pre` is a real container (not text-only) so the standard
    # `Pre(Code("..."))` pairing works -- a code block is a `<pre>`
    # wrapping a `<code>`, not raw text.
    "Pre": NodeSpec(),
    "Blockquote": NodeSpec(),
    # Forms.
    "Form": NodeSpec(),
    "Input": NodeSpec(allow_children=False),
    "Textarea": NodeSpec(text_only_children=True),
    "Select": NodeSpec(),
    "Option": NodeSpec(text_only_children=True),
    "OptGroup": NodeSpec(),
    "Label": NodeSpec(text_only_children=True),
    "FieldSet": NodeSpec(),
    "Legend": NodeSpec(text_only_children=True),
    # Tables. Cells are left as real containers (not text-only) since
    # real table cells routinely hold a `Link`, `Strong`, etc., not
    # just plain text.
    "Table": NodeSpec(),
    "TableHead": NodeSpec(),
    "TableBody": NodeSpec(),
    "TableFoot": NodeSpec(),
    "TableRow": NodeSpec(),
    "TableHeaderCell": NodeSpec(),
    "TableCell": NodeSpec(),
    "Caption": NodeSpec(text_only_children=True),
    # Media.
    "Video": NodeSpec(),
    "Audio": NodeSpec(),
    "Source": NodeSpec(required_props=("src",), allow_children=False),
    # ------------------------------------------------------------------
    # v0.003: second vocabulary addendum ("even more vocabulary"). Same
    # deal as the addendum above -- pure data in SCHEMA (+ TAG_MAP/
    # PASSTHROUGH_ATTRS/VOID_TAGS in the HTML backend), no compiler
    # logic touched. This batch fills in the "long tail" of standard,
    # production-grade static-site HTML that the first addendum left
    # out: numbered/description lists, art-directed responsive images,
    # native form/progress widgets, a zero-JS dialog, the rest of
    # HTML's text-level semantics (including bidi + ruby), table
    # column grouping, video captions, image maps, iframes, and a
    # <noscript> fallback. See docs/Foundational/DESIGN-NOTES.md and CHANGELOG.md
    # for the full rationale per group.
    # ------------------------------------------------------------------
    # Lists: v0.003's first pass only ever produced <ul> (via `List`).
    # `OrderedList` is a genuine gap, not a niche one -- there was no
    # numbered list at all. `DescriptionList` covers key/value and
    # glossary content (specs, FAQs, metadata blocks) that a <ul> can't
    # express semantically.
    "OrderedList": NodeSpec(),
    "DescriptionList": NodeSpec(),
    # Short, like `Item` -- a term is a label, not a place for a
    # nested Container/Figure/etc.
    "DescriptionTerm": NodeSpec(text_only_children=True),
    # Real container (like `TableCell`) -- a definition routinely holds
    # a `Link`, `Strong`, or multiple `Text` paragraphs, not just a
    # bare string.
    "DescriptionDetails": NodeSpec(),
    # Responsive images: art-direction (a different crop/format per
    # viewport, via `<source media=... srcset=...>`), the image half of
    # "responsive design" that the first addendum's CSS-only utilities
    # didn't touch at all.
    "Picture": NodeSpec(),
    # Distinct from the existing `Source` (which is for Video/Audio and
    # requires `src`) -- a <picture>'s <source> takes `srcset`/`sizes`/
    # `media`/`type` instead, so it gets its own required prop.
    "PictureSource": NodeSpec(required_props=("srcset",), allow_children=False),
    # Native, zero-JS widgets: progress bars, gauges, autocomplete lists,
    # and calculation output are all built into the browser already.
    "Progress": NodeSpec(text_only_children=True),
    "Meter": NodeSpec(text_only_children=True),
    "Datalist": NodeSpec(),
    "Output": NodeSpec(text_only_children=True),
    # <dialog open>: renders open with zero JS, and
    # `Form(method="dialog")` closes it natively (a browser behavior,
    # not a script) -- genuinely clever within the "no arbitrary JS"
    # constraint for a static confirmation/FAQ modal. Programmatically
    # opening it from an arbitrary trigger would need JS and stays out
    # of scope, same as the rest of v0.003.
    "Dialog": NodeSpec(),
    # More text-level semantics.
    "Kbd": NodeSpec(text_only_children=True),
    "Samp": NodeSpec(text_only_children=True),
    "Var": NodeSpec(text_only_children=True),
    "Data": NodeSpec(required_props=("value",), text_only_children=True),
    # `Ins`/`Del` are real containers (not text-only): HTML5 allows them
    # to wrap block content (e.g. a whole edited paragraph), same
    # reasoning as `Blockquote`.
    "Ins": NodeSpec(),
    "Del": NodeSpec(),
    "Q": NodeSpec(text_only_children=True),
    "Dfn": NodeSpec(text_only_children=True),
    # Real container -- postal/contact info commonly mixes plain text
    # with a `Link` (mailto:) or `LineBreak`s.
    "Address": NodeSpec(),
    "Wbr": NodeSpec(allow_children=False),
    # Bidirectional text isolation/override -- a real, production i18n
    # need (mixed LTR/RTL content: names, prices, or user-generated
    # text embedded in an RTL page, or vice versa), not just theory.
    "Bdi": NodeSpec(text_only_children=True),
    "Bdo": NodeSpec(text_only_children=True),
    # Ruby annotations (furigana/pinyin-style glosses) -- a real,
    # standard part of production East-Asian-language typography, and
    # a genuine gap: nothing above could express it at all.
    "Ruby": NodeSpec(),
    "Rt": NodeSpec(text_only_children=True),
    "Rp": NodeSpec(text_only_children=True),
    # Table extras: column-level styling/grouping without repeating a
    # style on every cell in the column.
    "ColGroup": NodeSpec(),
    "Col": NodeSpec(allow_children=False),
    # Media: caption/subtitle tracks -- accessibility, not decoration.
    "Track": NodeSpec(required_props=("src",), allow_children=False),
    # Image maps: multiple clickable regions on one image.
    "Map": NodeSpec(required_props=("name",)),
    "Area": NodeSpec(allow_children=False),
    # Embeds: the single most common "extra functionality" a static
    # site reaches for that plain markup can't provide on its own --
    # embedding a map, a video host player, or another site's widget --
    # while still being pure declarative HTML (no JS involved in the
    # embed itself).
    "IFrame": NodeSpec(required_props=("src",), allow_children=False),
    # Fallback content for the (rare, but real) visitor with JavaScript
    # disabled -- pairs naturally with ARKlight's own small JS runtime:
    # anything gated behind a `toggle`/`copy`/`dismiss` behavior can
    # have a `NoScript` sibling explaining what's missing.
    "NoScript": NodeSpec(),
    # vdom-7 (REFACTOR-INDEX.md [retired -- see CHANGELOG.md] row 15): per-item list
    # rendering + conditional show/hide. Both are real, renderable
    # content -- unlike `State`/`Computed`/`Watch` below, which are
    # page-scoped declarations Validation/IR-build pull out of the tree
    # entirely, `Repeat`/`Show` stay in place and go through the normal
    # recursive node conversion, so they need SCHEMA entries the same
    # as any other component. Their one/many children are validated by
    # dedicated logic in `arklight.ir.validate` rather than the generic
    # per-child loop below (a `Repeat`'s child is a *template*, not
    # ordinary content -- see `_validate_repeat_declaration`), but still
    # need an entry here so unrelated generic lookups (e.g. tag mapping)
    # find them like any other node type.
    "Repeat": NodeSpec(required_props=("name",)),
    "Show": NodeSpec(required_props=("predicate",)),
}

# Types whose raw string children should stay raw strings during
# normalization rather than being auto-wrapped in a Text node.
TEXT_ONLY_TYPES = frozenset(
    type_name for type_name, spec in SCHEMA.items() if spec.text_only_children
)

# v0.003 (+v0.003): named client-side behaviors any component may opt
# into via `on_click="<name>"` (plus `behavior_target="<css selector>"`
# and, for `toggle`, an optional `toggle_class`). Named `behavior_target`
# rather than `target` on purpose: `target` is already a real HTML
# attribute (`<a target="_blank">`), and reusing it for a CSS selector
# would be a silent footgun the moment someone wanted both on the same
# element.
#
# This is a closed set on purpose -- ARKlight ships a tiny vanilla-JS
# runtime that implements exactly these behaviors (see
# arklight.backend.js), rather than letting users embed arbitrary JS
# strings. That keeps "the browser never executes Python" true in
# spirit (it never executes anything ARKlight didn't ship) and keeps to
# "one obvious way": there's a fixed, discoverable vocabulary instead
# of a new ad-hoc DSL per site.
#
# v0.003 added `copy` and `dismiss` -- both still stateless in the same
# sense as `toggle`/`scroll-to`: each is a pure function of the DOM at
# click time (clipboard write, or a one-way class add), with no value
# retained in JS across events. Nothing here introduces app state.
#
# This lives here (not in arklight.backend.js) so the Validation stage
# can check `on_click` values against it without importing a backend --
# ir/ stays backend-agnostic; arklight.backend.js imports FROM here to
# stay in sync instead of the other way around.
# v0.0035: behaviors are a registry, not a hardcoded dispatch table.
#
# `BehaviorSpec` documents what a behavior needs the same way `NodeSpec`
# documents what an HTML component needs: `extra_props` are optional
# extra props (beyond the universal `on_click`/`behavior_target` pair)
# a behavior reads -- e.g. `toggle`'s `toggle_class`.
@dataclass
class BehaviorSpec:
    extra_props: tuple[str, ...] = field(default_factory=tuple)


BEHAVIOR_REGISTRY: dict[str, BehaviorSpec] = {
    "toggle": BehaviorSpec(extra_props=("toggle_class",)),
    "scroll-to": BehaviorSpec(),
    "copy": BehaviorSpec(),
    "dismiss": BehaviorSpec(extra_props=("toggle_class",)),
    # `v0.063` (docs/version history/v0.063.md): clipboard **paste** --
    # mirrors `copy` almost exactly (same `behavior_target` selector,
    # same clipboard-availability guard), just reading instead of
    # writing: `navigator.clipboard.readText()` into `target`'s
    # `.value` (an `Input`/`Textarea`) or `.textContent` otherwise.
    "paste": BehaviorSpec(),
}

# Derived, not hand-maintained -- Validation's existing
# `on_click in KNOWN_BEHAVIORS` check doesn't need to change shape.
KNOWN_BEHAVIORS = frozenset(BEHAVIOR_REGISTRY)


# `v0.063` (docs/version history/v0.063.md): `reveal`/`lazy` behavior
# via `IntersectionObserver` -- deliberately its own small registry,
# not folded into `BEHAVIOR_REGISTRY` above, because it needs its own
# prop (`on_reveal=`, not `on_click=`): every existing named behavior
# is click-triggered (wired through `wireClickInterceptor`'s delegated
# `click` listener), but a reveal-on-scroll-into-view effect has no
# click to hook -- it has to be wired from a *mount-time* pass instead
# (`wireReveal`, `arklight/backend/js/runtime/reveal.py`), observing
# every `data-ark-on-reveal`-carrying element once at page init (and
# again after an app-shell boosted swap). Reusing `on_click=`'s
# registry/prop for a mechanism that isn't click-triggered at all
# would be a silent footgun the moment a site tried to combine the
# two (`on_click="toggle"` + a reveal effect) on the same element --
# same reasoning `behavior_target` vs. `target` already documents in
# `arklight/api.py`. One kind so far: `reveal` adds `toggle_class`
# (default `"is-visible"`, reusing the same prop/attribute name
# `toggle`/`dismiss` already use) to the element itself, once, the
# first time it enters the viewport, then stops observing it -- a
# one-shot scroll-reveal, the same "lazy"/"reveal-on-scroll" pattern
# most sites reach for hand-rolled JS for.
@dataclass
class RevealSpec:
    extra_props: tuple[str, ...] = field(default_factory=tuple)


REVEAL_REGISTRY: dict[str, RevealSpec] = {
    "reveal": RevealSpec(extra_props=("toggle_class",)),
}

KNOWN_REVEAL_BEHAVIORS = frozenset(REVEAL_REGISTRY)


# v0.0035: a real `State` primitive with a closed *action* vocabulary,
# on top of (not instead of) the named-behavior vocabulary above.
# `State("count", 0)` declared inside `Page(...)` and `Bind("count")`
# used wherever a literal value is accepted give components a way to
# read reactive state; `Action.set/increment/toggle_bool` (structured
# `ActionRef` objects, see arklight.ast.nodes) give them a closed way
# to *change* it from `on_click=`. `ActionSpec.args` documents the
# keyword arguments a given action's `ActionRef.args` dict is expected
# to carry (e.g. `increment`'s `delta`), the same role `extra_props`
# plays for `BehaviorSpec` above.
#
# Still a closed, described vocabulary, same discipline as
# `BEHAVIOR_REGISTRY`: adding a new action later is a new registry
# entry plus a new JS fragment in `arklight/backend/js/actions/`, never
# a string of JS or Python handed to the browser to execute.
@dataclass
class ActionSpec:
    args: tuple[str, ...] = field(default_factory=tuple)
    # Capability fix (live-input -> action-value): the subset of `args`
    # that may be fed from live state instead of a compile-time
    # literal -- `Action.append("tasks", Bind("draft"))` reads
    # `State("draft")`'s current value when the click happens. Empty
    # by default: an action opts a given argument in explicitly, so
    # `Bind(...)` in any other position (e.g. `increment`'s `delta`,
    # where an input-bound *string* would silently concatenate rather
    # than add) is a build-time error, not a runtime surprise. See
    # `arklight.ast.nodes.STATE_REF_KEY` for the wire shape and
    # `arklight/backend/js/runtime/action_args.py` for the resolution.
    state_args: tuple[str, ...] = field(default_factory=tuple)


ACTION_REGISTRY: dict[str, ActionSpec] = {
    "set": ActionSpec(args=("value",), state_args=("value",)),
    "increment": ActionSpec(args=("delta",)),
    "toggle_bool": ActionSpec(),
    # ------------------------------------------------------------------
    # v0.0035: stateful-JS vocabulary addendum. Same discipline as the
    # v0.003 HTML vocabulary addendum above -- these fill in the two
    # gaps real usage hits almost immediately (a counter needs a `-1`
    # as much as a `+1`; a form/counter/toggle demo needs a "put it
    # back the way it started" control), rather than every site
    # re-deriving them from `set`/`increment` by hand. Only the most
    # commonly needed additions land here; see docs/Foundational/DESIGN-NOTES.md
    # ("v0.0035: stateful JS vocabulary addendum") for the rest of the
    # candidates (list append/remove, derived/computed state, debounced
    # actions, input-bound `set`) deliberately left for a future
    # version instead of growing this addendum further.
    # ------------------------------------------------------------------
    "decrement": ActionSpec(args=("delta",)),
    "reset": ActionSpec(),
    # ------------------------------------------------------------------
    # v0.0035: stateful-JS vocabulary addendum II. The first actions
    # that assume a list-valued `State(...)` rather than a scalar one
    # -- deliberately just the two minimal list mutations (append one
    # value, remove by index), not a full list-editing vocabulary. See
    # docs/Foundational/DESIGN-NOTES.md for what's still left for a future version.
    # ------------------------------------------------------------------
    "append": ActionSpec(args=("value",), state_args=("value",)),
    "remove": ActionSpec(args=("index",)),
    # ------------------------------------------------------------------
    # `v0.063` (docs/version history/v0.063.md): JS vocabulary addendum
    # stage 3/10. `geolocate` is a one-shot, argument-less write --
    # `navigator.geolocation.getCurrentPosition` writes a plain
    # `{lat, lng}` object into the target State(...) once the browser's
    # location prompt resolves (see
    # arklight/backend/js/actions/geolocate.py). Async/"fire and
    # forget", same shape a debounced action's deferred setTimeout
    # callback already relies on -- `wireClickInterceptor` calls
    # `action(store, key, args)` and moves on without waiting for a
    # return value.
    # ------------------------------------------------------------------
    "geolocate": ActionSpec(),
}

KNOWN_ACTIONS = frozenset(ACTION_REGISTRY)


# Stage 3 of "Reactive-core vdom staging" (see docs/Foundational/DESIGN-NOTES.md):
# event modifiers -- a timing/dispatch concern orthogonal to what an
# action does, so it's solved once as a wrapper around the click
# dispatcher rather than duplicated into every `ACTION_REGISTRY` entry.
# `Action.set(...).with_modifiers("prevent", "stop", "once")` and
# `Action.set(...).debounce(300)` / `.throttle(300)` attach these to an
# `ActionRef` (see `ActionRef.modifiers` in arklight.ast.nodes); the
# Validation stage checks each token here the same way it checks
# `action.action` against `ACTION_REGISTRY` above.
#
# `has_param` distinguishes plain boolean modifiers (`prevent`, `stop`,
# `once`) from ones that carry a millisecond value serialized as
# `"<name>:<ms>"` (`debounce`, `throttle`) -- same shape distinction
# `ActionSpec.args` draws for actions, just for the modifier token
# itself rather than the action's argument dict.
@dataclass
class ModifierSpec:
    has_param: bool = False


MODIFIER_REGISTRY: dict[str, ModifierSpec] = {
    "prevent": ModifierSpec(),
    "stop": ModifierSpec(),
    "once": ModifierSpec(),
    "debounce": ModifierSpec(has_param=True),
    "throttle": ModifierSpec(has_param=True),
}

KNOWN_MODIFIERS = frozenset(MODIFIER_REGISTRY)


# `v0.064` (docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md, `docs/
# version history/v0.064.md`): `State(..., query=..., history=...)`'s
# `history` prop names how a query-tracked key's writes affect the
# browser history stack -- `"replace"` (the unmarked default, `State
# (..., query=...)` with `history` left `None`) calls
# `history.replaceState(...)`, `"push"` calls `history.pushState(...)`
# instead, giving that key's changes a real back-button-worthy entry.
# A small, closed set, same discipline `KNOWN_MODIFIERS` above holds
# for event-modifier tokens -- but deliberately its own registry, not
# a reuse of `MODIFIER_REGISTRY`: that one describes per-*event*
# timing/dispatch tokens attached to an `ActionRef`
# (`.with_modifiers(...)`/`.debounce(...)`/`.throttle(...)`), which
# `history=` isn't -- it's a per-*State-declaration* property with no
# event of its own, so it gets a small dedicated set instead of
# stretching an unrelated one to fit.
KNOWN_QUERY_HISTORY_MODES = frozenset({"replace", "push"})


# `vdom-4` (REFACTOR-INDEX.md row 12; docs/Foundational/
# DESIGN-NOTES.md "Computed/derived state"): closed-vocabulary derived
# state, the same shape discipline as `ACTION_REGISTRY`/
# `BEHAVIOR_REGISTRY` above -- a new `*Spec` dataclass, a new
# `*_REGISTRY` dict, and `arklight.api.Derive.*` producing structured
# `DerivationRef` objects (arklight.ast.nodes), never a parsed/executed
# expression string.
#
#     State("price", 9.99)
#     State("qty", 3)
#     Computed("total", deps=("price", "qty"), derive=Derive.multiply("price", "qty"))
#     Text(Bind("total"))
#
# `min_names`/`max_names` bound how many state/computed names a given
# `kind` accepts (`None` for `max_names` means unlimited) -- e.g.
# `count` takes exactly one, `compare` takes exactly two, `sum`/
# `multiply`/`join`/`format` take one or more. `extra_args` documents
# the closed set of extra keyword data (beyond `names`) a `kind`'s
# `DerivationRef.args` dict is expected to carry, the same role
# `ActionSpec.args` plays for actions -- `join`'s `sep`, `format`'s
# `template`/`names_map`, `compare`'s `op`.
@dataclass
class DerivationSpec:
    min_names: int = 1
    max_names: int | None = None
    extra_args: tuple[str, ...] = field(default_factory=tuple)


DERIVATION_REGISTRY: dict[str, DerivationSpec] = {
    "sum": DerivationSpec(min_names=1, max_names=None),
    "multiply": DerivationSpec(min_names=1, max_names=None),
    "join": DerivationSpec(min_names=1, max_names=None, extra_args=("sep",)),
    "count": DerivationSpec(min_names=1, max_names=1),
    "format": DerivationSpec(min_names=1, max_names=None, extra_args=("template", "names_map")),
    "compare": DerivationSpec(min_names=2, max_names=2, extra_args=("op",)),
    # `v0.061` (docs/version history/v0.061.md): math siblings of
    # `sum`/`multiply`. `subtract`/`divide` aren't associative, so
    # they need at least two names (the first is the starting value,
    # every later one applies against it in order); `min`/`max` are
    # associative like `sum`, so one name is already meaningful.
    "subtract": DerivationSpec(min_names=2, max_names=None),
    "divide": DerivationSpec(min_names=2, max_names=None),
    "min": DerivationSpec(min_names=1, max_names=None),
    "max": DerivationSpec(min_names=1, max_names=None),
    # `v0.062` (docs/version history/v0.062.md): JS vocabulary
    # addendum stage 2/10 -- string-casing siblings of `join`/
    # `format`. Both are single-value transforms, same fixed arity as
    # `count`.
    "uppercase": DerivationSpec(min_names=1, max_names=1),
    "trim": DerivationSpec(min_names=1, max_names=1),
    # `v0.064` (docs/version history/v0.064.md): JS vocabulary
    # addendum stage 4/10 -- the math derivations catalog. Unary
    # transforms take exactly one name; `power`/`percentage_of` are
    # ordered pairs and `clamp` an ordered triple (value, low, high);
    # `hypot`/`average`/`median`/`gcd`/`lcm` are variadic; `to_fixed`/
    # `to_precision` take one name plus a literal `digits` argument
    # (range-checked in `arklight.ir.validate`).
    "absolute": DerivationSpec(min_names=1, max_names=1),
    "ceiling": DerivationSpec(min_names=1, max_names=1),
    "floor": DerivationSpec(min_names=1, max_names=1),
    "truncate_number": DerivationSpec(min_names=1, max_names=1),
    "sign": DerivationSpec(min_names=1, max_names=1),
    "sqrt": DerivationSpec(min_names=1, max_names=1),
    "cbrt": DerivationSpec(min_names=1, max_names=1),
    "power": DerivationSpec(min_names=2, max_names=2),
    "exp": DerivationSpec(min_names=1, max_names=1),
    "log": DerivationSpec(min_names=1, max_names=1),
    "log2": DerivationSpec(min_names=1, max_names=1),
    "log10": DerivationSpec(min_names=1, max_names=1),
    "hypot": DerivationSpec(min_names=1, max_names=None),
    "clamp": DerivationSpec(min_names=3, max_names=3),
    "average": DerivationSpec(min_names=1, max_names=None),
    "median": DerivationSpec(min_names=1, max_names=None),
    "gcd": DerivationSpec(min_names=1, max_names=None),
    "lcm": DerivationSpec(min_names=1, max_names=None),
    "percentage_of": DerivationSpec(min_names=2, max_names=2),
    "to_fixed": DerivationSpec(min_names=1, max_names=1, extra_args=("digits",)),
    "to_precision": DerivationSpec(min_names=1, max_names=1, extra_args=("digits",)),
    # `v0.065` (docs/version history/v0.065.md): JS vocabulary addendum
    # stage 5/10 -- the string derivations catalog. Every kind reads
    # exactly one name, coerced the way `String(x)` coerces it; the
    # literal parameters (`length`, `fill`, `search`, ...) ride in `args`
    # and are checked by `LITERAL_ARG_RULES` below. `is_empty`,
    # `includes_substring`, `starts_with` and `ends_with` return a
    # boolean (the source proposal files them as predicates; they ship
    # here as derivations, per the addendum's `v0.065` section, so a
    # `Computed(...)` result can feed `Show(Predicate.truthy(...))`).
    "capitalize": DerivationSpec(min_names=1, max_names=1),
    "title_case": DerivationSpec(min_names=1, max_names=1),
    "trim_start": DerivationSpec(min_names=1, max_names=1),
    "trim_end": DerivationSpec(min_names=1, max_names=1),
    "pad_start": DerivationSpec(min_names=1, max_names=1, extra_args=("length", "fill")),
    "pad_end": DerivationSpec(min_names=1, max_names=1, extra_args=("length", "fill")),
    "repeat": DerivationSpec(min_names=1, max_names=1, extra_args=("count",)),
    "slice_string": DerivationSpec(min_names=1, max_names=1, extra_args=("start", "end")),
    "char_at": DerivationSpec(min_names=1, max_names=1, extra_args=("index",)),
    "replace_first": DerivationSpec(min_names=1, max_names=1, extra_args=("search", "replacement")),
    "replace_all": DerivationSpec(min_names=1, max_names=1, extra_args=("search", "replacement")),
    "split_count": DerivationSpec(min_names=1, max_names=1, extra_args=("sep",)),
    "reverse_string": DerivationSpec(min_names=1, max_names=1),
    "string_length": DerivationSpec(min_names=1, max_names=1),
    "includes_substring": DerivationSpec(min_names=1, max_names=1, extra_args=("substring",)),
    "starts_with": DerivationSpec(min_names=1, max_names=1, extra_args=("substring",)),
    "ends_with": DerivationSpec(min_names=1, max_names=1, extra_args=("substring",)),
    "is_empty": DerivationSpec(min_names=1, max_names=1),
    # `v0.067` (docs/version history/v0.067.md): JS vocabulary addendum
    # stage 7/10 -- the list-scalar derivations catalog. Every kind reads
    # exactly one name, a list-valued `State(...)`/`Computed(...)`
    # (anything that isn't a list reads as an empty one), and reduces it
    # to one scalar. `list_includes` takes a literal `value`;
    # `list_any`/`list_all` take one of `COMPARE_OPS` plus a literal
    # `value` (checked in `arklight.ir.validate`, not a callback).
    # `list_includes`, `list_any` and `list_all` return a boolean, so
    # their result can feed `Show(Predicate.truthy(...))`.
    "list_length": DerivationSpec(min_names=1, max_names=1),
    "list_min": DerivationSpec(min_names=1, max_names=1),
    "list_max": DerivationSpec(min_names=1, max_names=1),
    "list_average": DerivationSpec(min_names=1, max_names=1),
    "list_first": DerivationSpec(min_names=1, max_names=1),
    "list_last": DerivationSpec(min_names=1, max_names=1),
    "list_includes": DerivationSpec(min_names=1, max_names=1, extra_args=("value",)),
    "list_any": DerivationSpec(min_names=1, max_names=1, extra_args=("op", "value")),
    "list_all": DerivationSpec(min_names=1, max_names=1, extra_args=("op", "value")),
    # `v0.068` (docs/version history/v0.068.md): JS vocabulary addendum
    # stage 8/10 -- cross-language numeric batteries, things JS's own
    # `Math` has no built-in for at all. `lerp` is an ordered triple
    # (value `a`, value `b`, weight `t`), same shape as `clamp`;
    # `midpoint` is an ordered pair. `saturating_add`/`saturating_subtract`
    # read two state names and take their fixed clamp bounds as literal
    # `min`/`max` args (checked in `arklight.ir.validate`, `min <= max`).
    # `value_or` reads one name plus a literal `fallback`. `first_present`
    # is variadic like `sum`, but needs at least two names -- one name
    # would just be `value_or` with a fallback of `None`.
    "lerp": DerivationSpec(min_names=3, max_names=3),
    "midpoint": DerivationSpec(min_names=2, max_names=2),
    "saturating_add": DerivationSpec(min_names=2, max_names=2, extra_args=("min", "max")),
    "saturating_subtract": DerivationSpec(min_names=2, max_names=2, extra_args=("min", "max")),
    "value_or": DerivationSpec(min_names=1, max_names=1, extra_args=("fallback",)),
    "first_present": DerivationSpec(min_names=2, max_names=None),
    # `v0.069` (docs/version history/v0.069.md): JS vocabulary addendum
    # stage 9/10 -- cross-language formatting/case batteries (Rails-style
    # inflection and human-readable byte/duration strings). Each reads one
    # name and takes no literal arguments.
    "to_ordinal": DerivationSpec(min_names=1, max_names=1),
    "humanize_bytes": DerivationSpec(min_names=1, max_names=1),
    "humanize_duration": DerivationSpec(min_names=1, max_names=1),
    "to_snake_case": DerivationSpec(min_names=1, max_names=1),
    "to_camel_case": DerivationSpec(min_names=1, max_names=1),
    "to_kebab_case": DerivationSpec(min_names=1, max_names=1),
    "to_title_case": DerivationSpec(min_names=1, max_names=1),
}

KNOWN_DERIVATIONS = frozenset(DERIVATION_REGISTRY)

# `Derive.compare(a, b, op)`'s `op` is itself a closed choice, never a
# raw operator string executed as code -- mirrors why `on_click`/
# `action` are closed vocabularies rather than arbitrary strings.
COMPARE_OPS = frozenset({"eq", "ne", "gt", "lt", "gte", "lte"})

# `v0.067`: `Derive.list_any(...)`/`Derive.list_all(...)` reuse
# `COMPARE_OPS` as their whole comparison vocabulary. `eq`/`ne` compare
# an element strictly (`===`) against any JSON scalar literal; the four
# relational operators compare the element read as a number against a
# *numeric* literal, so a list of strings is never ordered by JavaScript's
# type-coercing `<`.
LIST_COMPARE_KINDS = frozenset({"list_any", "list_all"})
LIST_EQUALITY_OPS = frozenset({"eq", "ne"})

# `v0.064`: `Derive.to_fixed(...)`/`Derive.to_precision(...)`'s `digits`
# is a literal, range-checked at build time to exactly the range
# JavaScript's own `Number.prototype.toFixed`/`toPrecision` accept --
# outside it the browser would throw a `RangeError` on every recompute
# instead of the build failing once, loudly.
DIGITS_RANGES: dict[str, tuple[int, int]] = {
    "to_fixed": (0, 100),
    "to_precision": (1, 100),
}


# `v0.065`: the string catalog's literal parameters. Each is checked once
# at build time against a rule, so a bad one fails the build instead of
# throwing on every client recompute (`"x".repeat(-1)` is a `RangeError`)
# or silently doing something else (`charAt(-1)` is `""`, never a wrap).
#
# * `int` rules are exact-integer only (`bool` is rejected) and inclusive
#   `low`/`high`; `nullable` additionally allows `None` (`slice_string`'s
#   open-ended `end`).
# * `str` rules take any string; `non_empty` rejects `""`. `search` must
#   be non-empty because `"abc".replace("", x)` and `"abc".split("")`
#   are per-code-unit operations nobody means by "replace this text".
# * `repeat`/`pad_*` are capped (`STRING_SIZE_LIMIT`) so a typo can't ask
#   the compiler, or a visitor's browser, for a gigabyte string.
#
# `replace_first`/`replace_all` take a *literal* `search`/`replacement`,
# never a pattern: see `arklight/backend/js/derivations/replace_first.py`.
STRING_SIZE_LIMIT = 1000
STRING_INDEX_LIMIT = 2**31 - 1


@dataclass(frozen=True)
class LiteralArgRule:
    kind: str  # "int" or "str"
    low: int | None = None
    high: int | None = None
    nullable: bool = False
    non_empty: bool = False


_SIZE = LiteralArgRule("int", 0, STRING_SIZE_LIMIT)
_SIGNED_INDEX = LiteralArgRule("int", -STRING_INDEX_LIMIT, STRING_INDEX_LIMIT)
_ANY_STR = LiteralArgRule("str")
_NON_EMPTY_STR = LiteralArgRule("str", non_empty=True)

LITERAL_ARG_RULES: dict[str, dict[str, LiteralArgRule]] = {
    "pad_start": {"length": _SIZE, "fill": _ANY_STR},
    "pad_end": {"length": _SIZE, "fill": _ANY_STR},
    "repeat": {"count": _SIZE},
    "slice_string": {
        "start": _SIGNED_INDEX,
        "end": LiteralArgRule("int", -STRING_INDEX_LIMIT, STRING_INDEX_LIMIT, nullable=True),
    },
    "char_at": {"index": LiteralArgRule("int", 0, STRING_INDEX_LIMIT)},
    "replace_first": {"search": _NON_EMPTY_STR, "replacement": _ANY_STR},
    "replace_all": {"search": _NON_EMPTY_STR, "replacement": _ANY_STR},
    "split_count": {"sep": _NON_EMPTY_STR},
    "includes_substring": {"substring": _ANY_STR},
    "starts_with": {"substring": _ANY_STR},
    "ends_with": {"substring": _ANY_STR},
}

# `v0.068`: `Derive.saturating_add(...)`/`Derive.saturating_subtract(...)`'s
# `min`/`max` -- literal integer bounds, same `+/-2**53` ceiling
# `ONE_OF_MAX_INTEGER` gives `Predicate.one_of(...)`'s values (an
# arbitrarily wide float bound isn't meaningfully different for a UI
# clamp, and staying integer-only keeps this table's `LiteralArgRule`
# shape instead of inventing a float-capable one). `min > max` is
# checked separately in `arklight.ir.validate` -- it isn't expressible
# as a single-argument `LiteralArgRule`.
_SATURATING_BOUND = LiteralArgRule("int", -(2**53), 2**53)
LITERAL_ARG_RULES["saturating_add"] = {"min": _SATURATING_BOUND, "max": _SATURATING_BOUND}
LITERAL_ARG_RULES["saturating_subtract"] = {"min": _SATURATING_BOUND, "max": _SATURATING_BOUND}


# `vdom-7` (REFACTOR-INDEX.md row 15): `Show(...)`'s
# closed-vocabulary predicate, the same shape discipline as
# `DERIVATION_REGISTRY` above but scaled down.
#
# `names` is the exact number of state/computed names a kind takes --
# or, when `variadic` is true (`v0.066`: `and`/`or`), the *minimum*,
# with no upper bound. `extra_args` documents the closed set of extra
# literal data (beyond `names`) a kind's `PredicateRef.args` dict must
# carry, the same role `DerivationSpec.extra_args` plays (`v0.066`:
# `one_of`'s `values`).
@dataclass
class PredicateSpec:
    names: int = 1
    variadic: bool = False
    extra_args: tuple[str, ...] = field(default_factory=tuple)


PREDICATE_REGISTRY: dict[str, PredicateSpec] = {
    "truthy": PredicateSpec(names=1),
    "falsy": PredicateSpec(names=1),
    # `v0.062` (docs/version history/v0.062.md): JS vocabulary
    # addendum stage 2/10 -- comparison predicates already speced
    # alongside `Derive.compare`'s `eq/ne/gt/lt/gte/lte` op set, just
    # never wired into this registry. Each is its own fixed-arity
    # `kind` (mirrors `truthy`/`falsy`'s shape) rather than one
    # `compare`-style kind plus an `op` extra arg.
    "equals": PredicateSpec(names=2),
    "gt": PredicateSpec(names=2),
    "lt": PredicateSpec(names=2),
    # `v0.066` (docs/version history/v0.066.md): JS vocabulary
    # addendum stage 6/10 -- the predicates catalog. `and`/`or` are the
    # only variadic kinds (2+ names); `in_range` reads three names in
    # `Derive.clamp`'s order (value, low, high); `one_of` is the only
    # kind with an extra arg, a literal `values` list.
    "and": PredicateSpec(names=2, variadic=True),
    "or": PredicateSpec(names=2, variadic=True),
    "not": PredicateSpec(names=1),
    "in_range": PredicateSpec(names=3),
    "one_of": PredicateSpec(names=1, extra_args=("values",)),
    "is_empty": PredicateSpec(names=1),
    "is_not_empty": PredicateSpec(names=1),
    "is_null": PredicateSpec(names=1),
}

KNOWN_PREDICATES = frozenset(PREDICATE_REGISTRY)

# `v0.066`: `Predicate.one_of(...)`'s `values` is a literal list, range-
# checked once at build time (see `arklight.ir.validate`): at most this
# many entries, each a JSON scalar. Integers are held to +/-2**53 so the
# build-time membership test and the browser's `indexOf` (which sees a
# double) can never disagree about which number a literal is.
ONE_OF_MAX_VALUES = 1000
ONE_OF_MAX_INTEGER = 2**53
