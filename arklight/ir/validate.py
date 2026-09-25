"""
Validation stage.

Once the ARK AST is normalized, ARKlight checks it against a small
schema of known node types before it's allowed to become Website IR.
This is the main guardrail that keeps ARKlight "beginner friendly": bad
trees fail loudly and specifically, at build time, in Python -- never
silently in the browser.

Checks performed:

1. The node `type` is a recognized built-in (arklight.ir.schema.SCHEMA).
2. Required props for that type are present (e.g. `Link` needs `href`,
   `Image` needs `src`).
3. Node types that require plain-text-only children (e.g. `Text`,
   `Button`) don't contain nested component nodes -- except `Bind(...)`,
   which is a value reference, not a component (see below).
4. `on_click`, if present, is either a known behavior name (paired with
   a `behavior_target` selector -- arklight.ir.schema.KNOWN_BEHAVIORS),
   an `Action.*(...)` reference (arklight.ir.schema.ACTION_REGISTRY)
   whose `state` targets a `State(...)` declared on the same page, or
   (`v0.065`) a `PlatformAPI.*(...)` reference
   (arklight.ir.platform_api.PLATFORM_API_REGISTRY) -- capability name
   and keyword arguments only; backend support is checked separately,
   per selected backend, during rendering.
5. `State(...)` may only appear as a direct child of `Page(...)` --
   state belongs to the page, not to an arbitrary nested component --
   and every `Bind(...)` anywhere on the page must name a `State(...)`
   actually declared there.
6. The tree's root is a `Page` node.
7. Recurses into every child.
8. `bind_class`, if present, is a `Bind.when(...)` reference
   (arklight.ast.nodes.ClassBindSpec) whose `state` targets a
   `State(...)` declared on the same page (Stage 2 of "Reactive-core
   vdom staging" -- see docs/Foundational/DESIGN-NOTES.md).
9. An `Action.*(...)`'s `.modifiers` (from `.with_modifiers(...)`,
   `.debounce(...)`, `.throttle(...)`) are each a known token from
   `arklight.ir.schema.MODIFIER_REGISTRY` -- `prevent`/`stop`/`once`
   bare, `debounce`/`throttle` as `"<name>:<ms>"` with a positive
   integer `ms` (Stage 3 of "Reactive-core vdom staging" -- see
   docs/Foundational/DESIGN-NOTES.md).
10. `responsive_style`, if present, is a non-empty `dict[str,
    dict[str, str]]` -- each key a non-empty media-condition string
    (e.g. `"(max-width: 600px)"`), each value a non-empty dict of
    non-empty CSS property name -> string/number value (v0.048 Stage
    B, "CSS media queries + `<head>` extension" -- see
    docs/Foundational/DESIGN-NOTES.md). Structured input only, same discipline as
    `site.style(...)`/`site.media_query(...)` -- never a raw CSS
    string.
11. `meta`/`links` on `Page(...)`, if present, are structurally
    well-formed (v0.048 Stage A, "CSS media queries + `<head>`
    extension" -- see docs/Foundational/DESIGN-NOTES.md): `meta` a non-empty
    `dict[str, str]` of name -> content pairs; `links` a non-empty
    `list[dict[str, str]]` of attribute -> value pairs, each carrying
    a `rel`. Structured input only, same "no raw HTML-injection escape
    hatch" discipline every other extension point in the project
    holds.
12. `shell_persistent`, if `True` on a node, requires that same node
    to also carry a non-empty `id` (htmx-4, see
    REFACTOR-INDEX.md [retired -- see CHANGELOG.md] row 9): `hx-preserve` -- the HTML
    backend's target for this prop, see `arklight/backend/html/attrs.py`
    -- only works if htmx can find the *same* element in both the old
    and the newly-fetched DOM to keep, and the only thing it matches
    on is a stable `id`. A node with no `id` would compile to a
    `hx-preserve="true"` attribute htmx silently can't use, so this
    fails loudly at build time instead.
13. `Computed(...)` (`vdom-4`, see REFACTOR-INDEX.md row
    12) may only appear as a direct child of `Page(...)`, same as
    `State(...)`; needs a non-empty string `name`, not already used by
    a `State(...)`/other `Computed(...)` on the same page; needs a
    non-empty `deps` tuple, every entry of which resolves to a
    `State(...)`/other `Computed(...)` declared on the same page; its
    `derive` must be a `Derive.*(...)` reference
    (`arklight.ast.nodes.DerivationRef`) whose `kind` is known
    (`arklight.ir.schema.DERIVATION_REGISTRY`), whose `names` count
    satisfies that kind's arity and is a subset of the declared
    `deps`, whose `args` carry exactly that kind's closed set of extra
    keys (`join`'s `sep`, `format`'s `template`/`names_map`,
    `compare`'s `op`, itself checked against
    `arklight.ir.schema.COMPARE_OPS`), and which does not, directly or
    transitively through other `Computed(...)` deps, depend on itself.
    `Bind(...)`/`bind_class=` may reference a `Computed(...)`'s `name`
    exactly like a `State(...)`'s; `Action.*(...)` may not -- a
    `Computed(...)` has no independent value of its own to mutate.
16. `on_reveal` (`v0.063`, JS vocabulary addendum stage 3/10), if
    present, must be a known reveal-behavior name
    (`arklight.ir.schema.KNOWN_REVEAL_BEHAVIORS`) -- unlike `on_click`,
    it never takes an `Action.*(...)` reference or a `behavior_target`
    (see `_validate_reveal_props`). `State(..., media="...")`'s
    `media` prop, if present, must be a non-empty string.
14. `Watch(...)` (`vdom-5`, see REFACTOR-INDEX.md row 13)
    may only appear as a direct child of `Page(...)`, same as
    `State(...)`/`Computed(...)`; its `name` must resolve to a
    `State(...)`/`Computed(...)` declared on the same page (the same
    bindable set `Bind(...)` checks against); its `then=` must be an
    `Action.*(...)` reference whose `action`/`state`/`modifiers` are
    valid the same way an `on_click=Action.*(...)` value already is --
    reusing `_validate_action` -- so `then` may only target a real
    `State(...)` on the page, never a `Computed(...)`.
15. `Repeat(...)`/`Show(...)` (`vdom-7`, see
    REFACTOR-INDEX.md row 15) are, unlike 13/14 above,
    real renderable content -- they may appear anywhere ordinary
    content can, not just as a direct `Page(...)` child.
    `Repeat(name, template=...)` needs a non-empty `name` resolving to
    a `State(...)`/`Computed(...)` declared on the same page, and
    exactly one child (its per-item template, built by calling
    `template()` once at compile time in `arklight.api.Repeat`) --
    that template is checked by a dedicated recursive validator
    (`_validate_repeat_template`) rather than the generic per-child
    loop below, since it's the only place an `ItemBind` node
    (`RepeatItem.value()`) is valid. `Show(predicate, ...)` needs a
    `Predicate.*(...)` reference (`arklight.ast.nodes.PredicateRef`)
    whose `kind` is known (`arklight.ir.schema.PREDICATE_REGISTRY`),
    whose `names` count matches its spec (exact, or a minimum for the
    variadic `and`/`or`), whose `args` are exactly its spec's
    `extra_args` (`v0.066`: `one_of`'s `values`, a non-empty list of
    JSON scalars), and whose `names` resolve to `State(...)`/
    `Computed(...)` declared on the same page; its children are ordinary content, validated the
    same way any other component's children are.
17. `State(..., query="...")` (`v0.064`, `docs/Proposals/
    URL-STATE-AS-PRIMITIVE-PROPOSAL.md`), if present, must be a legal
    query-parameter key (`_LEGAL_QUERY_KEY_RE`). `State(...,
    history="...")`, if present, must be a known mode
    (`arklight.ir.schema.KNOWN_QUERY_HISTORY_MODES`) and requires
    `query=` to be set alongside it.
18. An `Action.*(...)` argument that reads state (`Bind("name")`, stored
    as `{"__state__": "name"}`; `0.06503`, `docs/Foundational/DESIGN-NOTES.md`) must be an argument the
    action opts in (`ActionSpec.state_args`), be a well-formed marker,
    and name a `State(...)`/`Computed(...)` declared on the same page --
    see `_validate_action_args`. Applies wherever an `ActionRef` is
    validated: `on_click=`, a `Watch(...)`'s `then=`, a `Repeat(...)`
    template.
19. `Site(provider=...)` (`Provider` stage 2 of 6, `v0.066` -- see
    `docs/version history/v0.066.md` and `arklight/provider.py`), if
    present, is re-checked against the same finalized capability
    vocabulary (`arklight.provider.PROVIDER_CAPABILITIES` plus the
    `custom:`-prefixed escape hatch, finalized at stage 6, `v0.070`)
    `ProviderDeclaration.__post_init__` already enforces at
    construction time -- see `validate_provider`. Unlike every other
    check in this module, a `Provider` declaration is not part of the
    ARK AST tree (`Site(...)` is a build-time object, not a node), so
    `arklight.compiler.pipeline.build` calls `validate_provider`
    directly, alongside `validate_ark_ast`, rather than this function
    walking a tree to find it. An unknown capability fails the build
    the same way an unknown component prop does elsewhere in this
    module: a `ValidationError`, not the `ValueError`
    `ProviderDeclaration` itself raises -- this is defense in depth,
    not the first line of defense, since a `Provider.declare(...)`
    call already can't hold an invalid value by the time it reaches
    here.
"""

from __future__ import annotations

import math
import re

from arklight.ast.nodes import (
    STATE_REF_KEY,
    ActionRef,
    ARKNode,
    ClassBindSpec,
    DerivationRef,
    ModelBindSpec,
    PlatformAPIRef,
    PredicateRef,
    is_state_ref,
)
from arklight.ir.platform_api import PLATFORM_API_REGISTRY
from arklight.provider import PROVIDER_CAPABILITIES, ProviderDeclaration, is_known_capability
from arklight.ir.schema import (
    ACTION_REGISTRY,
    COMPARE_OPS,
    DERIVATION_REGISTRY,
    DIGITS_RANGES,
    KNOWN_BEHAVIORS,
    KNOWN_QUERY_HISTORY_MODES,
    KNOWN_REVEAL_BEHAVIORS,
    LIST_COMPARE_KINDS,
    LIST_EQUALITY_OPS,
    LITERAL_ARG_RULES,
    LiteralArgRule,
    MODIFIER_REGISTRY,
    ONE_OF_MAX_INTEGER,
    ONE_OF_MAX_VALUES,
    PREDICATE_REGISTRY,
    SCHEMA,
)

# `v0.064`: `query=` names a real URL query-parameter key, handed
# straight to `URLSearchParams`/`history.*State(...)` client-side --
# same "fail loudly at build time, not silently in the browser"
# discipline every other check in this module holds. Deliberately
# conservative (leading letter/underscore, then letters/digits/
# underscore/hyphen/dot) rather than accepting anything
# `encodeURIComponent` could theoretically survive: a key needing
# percent-encoding to round-trip through a URL is exactly the kind of
# footgun this project's own "beginner friendly" checks exist to catch
# before it ships, not after.
_LEGAL_QUERY_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


class ValidationError(Exception):
    """Raised when an ARK AST tree fails validation.

    `component_name`, when set, names the literal `node.type` that a
    SCHEMA-backed check failed against -- either an unrecognized
    component type or a known type with a missing required prop. It is
    set *only* at those SCHEMA-lookup sites (`--narrate`'s Rei renderer
    uses its presence, not any parsing of `str(self)`, to decide
    whether to append the `arklight search <name>` pointer -- see
    `docs/Foundational/DESIGN-NOTES.md`, "Design record: Rei compiler
    narrator" §5). Every other
    `ValidationError` in this module (Bind/on_click/modifier/behavior
    checks, etc.) leaves this `None`, which is exactly how Rei knows
    *not* to print a pointer for those -- structured data reaching the
    renderer, rather than regex-scraping the formatted message back
    apart.
    """

    def __init__(self, message: str, *, component_name: str | None = None) -> None:
        super().__init__(message)
        self.component_name = component_name


def _validate_bind(node: ARKNode, *, path: str, page_state: frozenset[str]) -> None:
    name = node.props.get("name")
    if not isinstance(name, str) or not name:
        raise ValidationError(f"Bind(...) at {path} needs a non-empty string name.")
    if name not in page_state:
        known = ", ".join(sorted(page_state)) or "(none declared)"
        raise ValidationError(
            f"Bind({name!r}) at {path} references state that isn't declared "
            f"on this page. State/Computed declared on this page: {known}."
        )


def _validate_modifier_tokens(modifiers: tuple[str, ...], *, path: str, label: str) -> None:
    """Stage 3 ("Reactive-core vdom staging"), generalized at `v0.063`
    for `bind_value=Bind.model(...).debounce(...)`/`.throttle(...)`:
    check each token against `MODIFIER_REGISTRY` -- a bare name
    (`prevent`/`stop`/`once`) must take no parameter, and a
    `"<name>:<value>"` token (`debounce:300`/`throttle:300`) must both
    name a param-taking modifier and carry a positive integer value.
    `label` (`"on_click"`/`"bind_value"`) only changes the error
    message's prefix -- the check itself is identical either way."""
    for token in modifiers:
        name, sep, param = token.partition(":")
        spec = MODIFIER_REGISTRY.get(name)
        if spec is None:
            known = ", ".join(sorted(MODIFIER_REGISTRY))
            raise ValidationError(
                f"{label} at {path} uses unknown modifier {name!r} (from "
                f"{token!r}). Known modifiers are: {known}."
            )
        if spec.has_param:
            if not sep:
                raise ValidationError(
                    f"{label} at {path} uses modifier {name!r} without a "
                    f"millisecond value -- use .{name}(<ms>), e.g. .{name}(300)."
                )
            if not param.isdigit() or int(param) <= 0:
                raise ValidationError(
                    f"{label} at {path} uses modifier {token!r} with an "
                    f"invalid value -- {name!r} needs a positive integer "
                    f"millisecond count."
                )
        elif sep:
            raise ValidationError(
                f"{label} at {path} uses modifier {token!r}, but {name!r} "
                f"doesn't take a value -- use .with_modifiers({name!r}) "
                f"instead."
            )


def _validate_modifiers(action: ActionRef, *, path: str) -> None:
    """Stage 3 ("Reactive-core vdom staging"): check each token in
    `action.modifiers` against `MODIFIER_REGISTRY` -- see
    `_validate_modifier_tokens` for the shared per-token check this
    now delegates to (also used by `_validate_model_bind` below)."""
    _validate_modifier_tokens(action.modifiers, path=path, label="on_click")


def _validate_platform_api(ref: PlatformAPIRef, *, path: str) -> None:
    """
    `v0.065`: the backend-agnostic half of Platform API validation
    (Section 7/11 of `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`) --
    capability existence and argument names, checked here at
    Validation because those are compiler-owned semantic facts, true
    regardless of which backend eventually builds this site. Whether
    the *selected* backend actually implements a known-valid
    capability is a separate, later check
    (`arklight.ir.platform_api.check_backend_support`, run once per
    backend during rendering) -- Validation has no backend selected
    yet to check that against.
    """
    if ref.capability not in PLATFORM_API_REGISTRY:
        known = ", ".join(sorted(PLATFORM_API_REGISTRY))
        raise ValidationError(
            f"on_click at {path} uses unknown platform API capability "
            f"{ref.capability!r}. Known platform API capabilities are: "
            f"{known}."
        )
    spec = PLATFORM_API_REGISTRY[ref.capability]
    unknown_args = sorted(set(ref.args) - set(spec.args))
    if unknown_args:
        allowed = ", ".join(spec.args) or "(none)"
        raise ValidationError(
            f"on_click at {path} (PlatformAPI.{ref.capability}(...)) passed "
            f"unexpected keyword argument(s) {unknown_args}. Accepted "
            f"arguments for {ref.capability!r} are: {allowed}."
        )


def _validate_action_args(
    action: ActionRef, *, path: str, readable_state: frozenset[str]
) -> None:
    """
    Capability fix (live-input -> action-value): checks each of an
    `ActionRef`'s arg values that reads live state
    (`Action.append("tasks", Bind("draft"))` -> `{"__state__":
    "draft"}`, see `arklight.ast.nodes.STATE_REF_KEY`). Three rules,
    each failing the build instead of misbehaving in the browser:

    - the argument must be one the action's `ActionSpec.state_args`
      opts in (a `Bind(...)` as `increment`'s `delta` would silently
      string-concatenate for input-bound state, so it's refused);
    - the marker must be well-formed -- exactly `{"__state__": <name>}`
      (`__state__` is reserved, so a literal dict that merely carries
      that key can't be mistaken for a reference by the runtime);
    - the named state must be a `State(...)`/`Computed(...)` declared
      on this page (`readable_state` -- reading needs no independent
      value to mutate, unlike an action's *target*).

    A leftover `Bind(...)` *node* in args (an `ActionRef` built by hand
    rather than through `Action.*`) gets a pointed message rather than
    a raw `TypeError` from JSON serialization at render time.
    """
    spec = ACTION_REGISTRY[action.action]
    for arg_name, value in action.args.items():
        label = f"on_click at {path} (Action.{action.action}(...), argument {arg_name!r})"
        if isinstance(value, ARKNode):
            raise ValidationError(
                f"{label} holds a {value.type!r} node, which can't be serialized "
                f"as an action argument. Build the action with Action."
                f"{action.action}(...) so Bind(\"name\") is converted, or pass "
                f"a plain value."
            )
        if not is_state_ref(value):
            continue
        name = value[STATE_REF_KEY] if len(value) == 1 else None
        if not isinstance(name, str) or not name:
            raise ValidationError(
                f"{label} uses the reserved key {STATE_REF_KEY!r} in a dict "
                f"that isn't a state reference. Use Bind(\"name\") to read "
                f"state; {STATE_REF_KEY!r} can't appear in a literal dict "
                f"argument."
            )
        if arg_name not in spec.state_args:
            accepting = sorted(
                f"{n}({', '.join(sp.state_args)})" for n, sp in ACTION_REGISTRY.items() if sp.state_args
            )
            raise ValidationError(
                f"{label} was given Bind({name!r}), but Action.{action.action}'s "
                f"{arg_name!r} argument can't be read from state. Actions that "
                f"accept Bind(...) as an argument: {', '.join(accepting)}."
            )
        if name not in readable_state:
            known = ", ".join(sorted(readable_state)) or "(none declared)"
            raise ValidationError(
                f"{label} reads Bind({name!r}), which isn't declared on this "
                f"page as State(...) or Computed(...). State/Computed declared "
                f"on this page: {known}."
            )


def _validate_action(
    action: ActionRef,
    *,
    path: str,
    mutable_state: frozenset[str],
    page_state: frozenset[str] | None = None,
) -> None:
    if action.action not in ACTION_REGISTRY:
        known = ", ".join(sorted(ACTION_REGISTRY))
        raise ValidationError(
            f"on_click at {path} uses unknown action {action.action!r}. "
            f"Known actions are: {known}."
        )
    if action.state not in mutable_state:
        known = ", ".join(sorted(mutable_state)) or "(none declared)"
        raise ValidationError(
            f"on_click at {path} ({action.action!r}) targets state "
            f"{action.state!r}, which isn't declared on this page as "
            f"State(...) (a Computed(...) name can't be an Action.*(...) "
            f"target -- it has no independent value of its own to mutate). "
            f"State declared on this page: {known}."
        )
    _validate_modifiers(action, path=path)
    # `page_state` is the wider bindable set (State + Computed). Callers
    # that haven't been threaded it fall back to `mutable_state`, which
    # is always a subset -- stricter, never looser.
    _validate_action_args(
        action, path=path, readable_state=mutable_state if page_state is None else page_state
    )


def _validate_class_bind(node: ARKNode, *, path: str, page_state: frozenset[str]) -> None:
    bind_class = node.props.get("bind_class")
    if bind_class is None:
        return
    if not isinstance(bind_class, ClassBindSpec):
        raise ValidationError(
            f"{node.type!r} at {path} has bind_class={bind_class!r}, which isn't "
            f"a Bind.when(...) reference."
        )
    if not bind_class.class_name:
        raise ValidationError(f"Bind.when(...) at {path} needs a non-empty class_name.")
    if bind_class.state not in page_state:
        known = ", ".join(sorted(page_state)) or "(none declared)"
        raise ValidationError(
            f"bind_class at {path} (Bind.when({bind_class.state!r}, ...)) "
            f"targets state {bind_class.state!r}, which isn't declared on this "
            f"page. State declared on this page: {known}."
        )


def _validate_model_bind(node: ARKNode, *, path: str, mutable_state: frozenset[str]) -> None:
    """
    `vdom-6`: `bind_value=` (a plain string, typically `Bind.model(
    "name")`, or -- `v0.063` -- a `ModelBindSpec` from `Bind.model(
    "name", debounce=...)`/`.throttle(...)`) is a two-way binding --
    the target must be a real `State(...)` name declared on the page,
    same restriction `_validate_action` already enforces for
    `Action.*(...)` targets, since a `Computed(...)` has no
    independent value for user input to write back into. A
    `ModelBindSpec`'s `modifiers` are checked against the same
    `MODIFIER_REGISTRY` `on_click=`'s modifiers already use (see
    `_validate_modifier_tokens`).
    """
    bind_value = node.props.get("bind_value")
    if bind_value is None:
        return
    if isinstance(bind_value, ModelBindSpec):
        state_name = bind_value.state
        _validate_modifier_tokens(bind_value.modifiers, path=path, label="bind_value")
    elif isinstance(bind_value, str) and bind_value:
        state_name = bind_value
    else:
        raise ValidationError(
            f"{node.type!r} at {path} has bind_value={bind_value!r}, which must "
            f"be a non-empty state name string (e.g. Bind.model(\"query\"))."
        )
    if state_name not in mutable_state:
        known = ", ".join(sorted(mutable_state)) or "(none declared)"
        raise ValidationError(
            f"bind_value at {path} (Bind.model({state_name!r})) targets state "
            f"{state_name!r}, which isn't declared on this page as State(...) "
            f"(a Computed(...) name can't be a bind_value target -- it has no "
            f"independent value of its own to write back into). State declared "
            f"on this page: {known}."
        )


def _validate_responsive_style(node: ARKNode, *, path: str) -> None:
    """
    v0.048 Stage B: `responsive_style={"(max-width: 600px)": {"display":
    "none"}}` -- a per-node prop any component may carry, extending the
    existing `style={...}` convention with a viewport-keyed variant
    (see docs/Foundational/DESIGN-NOTES.md, "v0.048: CSS media queries + `<head>`
    extension"). Validated eagerly and structurally, matching
    `Site.style()`/`Site.media_query()`'s discipline, since this
    compiles straight into the generated stylesheet rather than a
    per-page inline attribute -- a malformed entry here would otherwise
    surface as silently broken CSS instead of a clear build-time error.
    """
    responsive_style = node.props.get("responsive_style")
    if responsive_style is None:
        return
    if not isinstance(responsive_style, dict) or not responsive_style:
        raise ValidationError(
            f"{node.type!r} at {path} has responsive_style={responsive_style!r}, "
            f"which must be a non-empty dict of "
            f'{{media_condition: {{css_property: value}}}}, e.g. '
            f'{{"(max-width: 600px)": {{"display": "none"}}}}.'
        )
    for condition, rules in responsive_style.items():
        if not isinstance(condition, str) or not condition.strip():
            raise ValidationError(
                f"{node.type!r} at {path} has a responsive_style entry with an "
                f"invalid media condition key -- expected a non-empty string "
                f"like \"(max-width: 600px)\", got {condition!r}."
            )
        if not isinstance(rules, dict) or not rules:
            raise ValidationError(
                f"{node.type!r} at {path} responsive_style[{condition!r}] must "
                f"be a non-empty dict of {{css_property: value}}, got {rules!r}."
            )
        for prop, value in rules.items():
            if not isinstance(prop, str) or not prop.strip():
                raise ValidationError(
                    f"{node.type!r} at {path} responsive_style[{condition!r}] "
                    f"has a non-empty string CSS property name required, got "
                    f"{prop!r}."
                )
            if value is None or isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise ValidationError(
                    f"{node.type!r} at {path} "
                    f"responsive_style[{condition!r}][{prop!r}] needs a string "
                    f"(or plain number) CSS value, got {value!r}."
                )


def _validate_page_head_extensions(node: ARKNode, *, path: str) -> None:
    """
    v0.048 Stage A: `meta`/`links` on `Page(...)` -- structured `<head>`
    extension points, matching the discipline `responsive_style` (Stage
    B, above) and `Site.style(...)` already use: no raw HTML-injection
    escape hatch, validated eagerly and structurally so a malformed
    entry fails loudly at build time instead of silently producing
    broken `<head>` output. Only meaningful on `Page(...)` -- the HTML
    backend only ever reads these two props off `page.root`, matching
    `favicon`/`description`/`og_*`'s existing page-only convention (see
    `arklight/backend/html/render.py`'s `_render_head_meta`).
    """
    meta = node.props.get("meta")
    if meta is not None:
        if not isinstance(meta, dict) or not meta:
            raise ValidationError(
                f"Page(...) at {path} has meta={meta!r}, which must be a "
                f"non-empty dict of {{name: content}}, e.g. "
                f'{{"theme-color": "#0f0f0f"}}.'
            )
        for name, content in meta.items():
            if not isinstance(name, str) or not name.strip():
                raise ValidationError(
                    f"Page(...) at {path} has a meta entry with an invalid "
                    f"name key -- expected a non-empty string, got {name!r}."
                )
            if not isinstance(content, str):
                raise ValidationError(
                    f"Page(...) at {path} meta[{name!r}] needs a string "
                    f"content value, got {content!r}."
                )

    links = node.props.get("links")
    if links is not None:
        if not isinstance(links, list) or not links:
            raise ValidationError(
                f"Page(...) at {path} has links={links!r}, which must be a "
                f"non-empty list of {{attribute: value}} dicts, e.g. "
                f'[{{"rel": "preconnect", "href": "https://fonts.gstatic.com"}}].'
            )
        for i, link in enumerate(links):
            if not isinstance(link, dict) or not link:
                raise ValidationError(
                    f"Page(...) at {path} links[{i}] must be a non-empty "
                    f"dict of {{attribute: value}}, got {link!r}."
                )
            for attr, value in link.items():
                if not isinstance(attr, str) or not attr.strip():
                    raise ValidationError(
                        f"Page(...) at {path} links[{i}] has a non-string "
                        f"or empty attribute name key, got {attr!r}."
                    )
                if not isinstance(value, str):
                    raise ValidationError(
                        f"Page(...) at {path} links[{i}][{attr!r}] needs a "
                        f"string value, got {value!r}."
                    )
            if "rel" not in link:
                raise ValidationError(
                    f'Page(...) at {path} links[{i}] is missing a "rel" '
                    f"attribute -- every <link> needs one, got {link!r}."
                )

    # `Provider`, stage 4 of 6 (`v0.068` -- see
    # `docs/Foundational/PROVIDER-SDK.md` and
    # `arklight/experimental.py`'s `provider-scripts` entry): same
    # structural `{attribute: value}` discipline as `links` just above,
    # not a raw HTML-injection escape hatch. `src` is required (this
    # primitive exists to load an *external* script; an entry with no
    # `src` has nothing to load) and, unlike `links`, a bare
    # `"javascript:"` value is rejected outright -- that scheme runs as
    # inline code the moment the browser parses it, which is exactly
    # the unchecked-inline-execution surface `script-src` (no
    # `'unsafe-inline'`, see `arklight/backend/html/csp.py`) exists to
    # close, so ARKlight refuses to generate it up front rather than
    # rely on the runtime CSP to catch it.
    scripts = node.props.get("scripts")
    if scripts is not None:
        if not isinstance(scripts, list) or not scripts:
            raise ValidationError(
                f"Page(...) at {path} has scripts={scripts!r}, which must "
                f"be a non-empty list of {{attribute: value}} dicts, e.g. "
                f'[{{"src": "https://example.com/sdk.js"}}].'
            )
        for i, script in enumerate(scripts):
            if not isinstance(script, dict) or not script:
                raise ValidationError(
                    f"Page(...) at {path} scripts[{i}] must be a non-empty "
                    f"dict of {{attribute: value}}, got {script!r}."
                )
            for attr, value in script.items():
                if not isinstance(attr, str) or not attr.strip():
                    raise ValidationError(
                        f"Page(...) at {path} scripts[{i}] has a non-string "
                        f"or empty attribute name key, got {attr!r}."
                    )
                if not isinstance(value, str):
                    raise ValidationError(
                        f"Page(...) at {path} scripts[{i}][{attr!r}] needs "
                        f"a string value, got {value!r}."
                    )
            src = script.get("src")
            if not src:
                raise ValidationError(
                    f'Page(...) at {path} scripts[{i}] is missing a "src" '
                    f"attribute -- every entry needs an external URL to "
                    f"load, got {script!r}."
                )
            if src.strip().lower().startswith("javascript:"):
                raise ValidationError(
                    f"Page(...) at {path} scripts[{i}][\"src\"] can't be a "
                    f'"javascript:" URL -- Page(scripts=[...]) loads an '
                    f"external file, it isn't an inline-code escape hatch."
                )


def _validate_shell_persistent(node: ARKNode, *, path: str) -> None:
    """
    htmx-4 (REFACTOR-INDEX.md row 9): `shell_persistent`
    is inert (not just unused, but never even checked) on a site that
    never sets `Site(app_shell=True)` -- this validates the prop's own
    shape regardless, the same "fail loudly at build time, not
    silently in the browser" discipline `_validate_responsive_style`/
    `_validate_page_head_extensions` already hold for props that are
    only meaningful in combination with something else.
    """
    shell_persistent = node.props.get("shell_persistent")
    if not shell_persistent:
        return
    node_id = node.props.get("id")
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValidationError(
            f"{node.type!r} at {path} has shell_persistent=True but no "
            f"(non-empty) id -- htmx's hx-preserve, which this prop "
            f"compiles to, can only keep an element across a boosted "
            f"navigation by matching a stable id between the old and "
            f"newly-fetched page. Add id=\"...\" to this node."
        )


def _validate_behavior_props(
    node: ARKNode,
    *,
    path: str,
    mutable_state: frozenset[str],
    page_state: frozenset[str] | None = None,
) -> None:
    on_click = node.props.get("on_click")
    if on_click is None:
        return

    if isinstance(on_click, ActionRef):
        _validate_action(on_click, path=path, mutable_state=mutable_state, page_state=page_state)
        return

    if isinstance(on_click, PlatformAPIRef):
        _validate_platform_api(on_click, path=path)
        return

    if on_click not in KNOWN_BEHAVIORS:
        known = ", ".join(sorted(KNOWN_BEHAVIORS))
        raise ValidationError(
            f"{node.type!r} at {path} has on_click={on_click!r}, which isn't a "
            f"recognized behavior or Action.*(...) reference. Known behaviors "
            f"are: {known}."
        )
    if "behavior_target" not in node.props:
        raise ValidationError(
            f"{node.type!r} at {path} has on_click={on_click!r} but no "
            f"`behavior_target` prop (a CSS selector for the element(s) it "
            f"should act on)."
        )


def _validate_reveal_props(node: ARKNode, *, path: str) -> None:
    """
    `v0.063`: `on_reveal=`, unlike `on_click=`, is never click-triggered
    and never takes a `behavior_target` -- the observed element *is*
    the element that carries `on_reveal=` (see
    `arklight.ir.schema.REVEAL_REGISTRY`'s comment for why this is a
    separate prop/registry rather than reusing `on_click=`'s). Only a
    known reveal-behavior name is accepted; there's no `Action.*(...)`-
    shaped alternative the way `on_click=` has, since a reveal effect
    has no state to mutate of its own.
    """
    on_reveal = node.props.get("on_reveal")
    if on_reveal is None:
        return
    if on_reveal not in KNOWN_REVEAL_BEHAVIORS:
        known = ", ".join(sorted(KNOWN_REVEAL_BEHAVIORS))
        raise ValidationError(
            f"{node.type!r} at {path} has on_reveal={on_reveal!r}, which "
            f"isn't a recognized reveal behavior. Known reveal behaviors "
            f"are: {known}."
        )


def _validate_state_declaration(node: ARKNode, *, path: str, parent_is_page: bool) -> None:
    if not parent_is_page:
        raise ValidationError(
            f"State(...) at {path} may only be declared as a direct child of "
            f"Page(...) -- state belongs to the page, not to a nested "
            f"component. Move it up to the top level of Page(...)."
        )
    name = node.props.get("name")
    if not isinstance(name, str) or not name:
        raise ValidationError(f"State(...) at {path} needs a non-empty string name.")
    # `vdom-8` (REFACTOR-INDEX.md row 16): `persist`
    # defaults to `False` (unset is fine, mirroring every other
    # optional bool prop in this module) but a value that *is*
    # provided must actually be a bool -- a truthy non-bool (e.g. a
    # stray string) would otherwise silently opt a key into
    # `localStorage` persistence without the caller meaning to.
    persist = node.props.get("persist", False)
    if not isinstance(persist, bool):
        raise ValidationError(
            f"State(...) at {path} has persist={persist!r}, which must be a bool."
        )
    # `v0.063`: `media` defaults to `None` (unset, plain state --
    # unchanged behavior) but a value that *is* provided must be a
    # non-empty string -- the raw text ARKlight hands straight to
    # `window.matchMedia(...)` client-side, so an empty/non-string
    # value would silently become a useless (or throwing) media query
    # at runtime instead of failing loudly here at build time, same
    # discipline `persist`'s bool check above already holds.
    media = node.props.get("media")
    if media is not None and (not isinstance(media, str) or not media.strip()):
        raise ValidationError(
            f"State(...) at {path} has media={media!r}, which must be a "
            f'non-empty media condition string, e.g. "(min-width: 768px)".'
        )
    # `v0.064` (docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md):
    # `query` defaults to `None` (unset, plain state -- unchanged
    # behavior) but a value that *is* provided must be a legal query-
    # parameter key -- same "fail loudly at build time" discipline
    # `media`'s check just above already holds, now against
    # `_LEGAL_QUERY_KEY_RE` instead of a bare non-empty-string check,
    # since an illegal key would silently mis-round-trip through
    # `URLSearchParams` client-side rather than failing anywhere
    # visible.
    query = node.props.get("query")
    if query is not None and (not isinstance(query, str) or not _LEGAL_QUERY_KEY_RE.match(query)):
        raise ValidationError(
            f"State(...) at {path} has query={query!r}, which must be a "
            f"legal query-parameter key (letters, digits, underscore, "
            f'hyphen, or dot, starting with a letter or underscore), e.g. "page".'
        )
    # `history` defaults to `None` (the unmarked "replace" default --
    # see `arklight.ir.schema.KNOWN_QUERY_HISTORY_MODES`'s docstring
    # for why this is its own small registry rather than a reuse of
    # `MODIFIER_REGISTRY`). A value that *is* provided must be a known
    # mode, and only ever makes sense alongside `query=` -- a
    # `history=` with no `query=` would silently do nothing at
    # runtime, so this is caught here instead.
    history = node.props.get("history")
    if history is not None:
        if not isinstance(history, str) or history not in KNOWN_QUERY_HISTORY_MODES:
            known = ", ".join(sorted(KNOWN_QUERY_HISTORY_MODES))
            raise ValidationError(
                f"State(...) at {path} has history={history!r}, which isn't "
                f"a recognized history mode. Known history modes are: {known}."
            )
        if query is None:
            raise ValidationError(
                f"State(...) at {path} has history={history!r} but no "
                f"query=... -- history= only affects how a query-tracked "
                f"key's writes hit the browser history stack, so it needs "
                f"a query= alongside it."
            )


def _validate_derive_ref(
    derive: DerivationRef, *, path: str, deps: tuple[str, ...]
) -> None:
    """
    `vdom-4`: structural checks for a `Computed(...)`'s `derive=`
    value, mirroring `_validate_action`'s discipline for `ActionRef`.
    Checked once `deps` itself is known to be a non-empty tuple of
    strings (`_validate_computed_declaration` checks that first), so
    `deps` here is trusted shape, just not yet cross-checked against
    the page's declared state -- that cross-check
    (`_collect_page_reactive_names`) happens after every page's
    `State(...)`/`Computed(...)` names are known, to allow a
    `Computed(...)` to depend on another `Computed(...)` declared
    later in `Page(...)`'s children.
    """
    if not isinstance(derive, DerivationRef):
        raise ValidationError(
            f"Computed(...) at {path} has derive={derive!r}, which isn't a "
            f"Derive.*(...) reference."
        )
    spec = DERIVATION_REGISTRY.get(derive.kind)
    if spec is None:
        known = ", ".join(sorted(DERIVATION_REGISTRY))
        raise ValidationError(
            f"Computed(...) at {path} uses unknown derivation {derive.kind!r}. "
            f"Known derivations are: {known}."
        )
    count = len(derive.names)
    if count < spec.min_names or (spec.max_names is not None and count > spec.max_names):
        arity = (
            f"exactly {spec.min_names}"
            if spec.max_names == spec.min_names
            else f"at least {spec.min_names}"
            if spec.max_names is None
            else f"between {spec.min_names} and {spec.max_names}"
        )
        raise ValidationError(
            f"Computed(...) at {path} uses Derive.{derive.kind}(...) with "
            f"{count} name(s) ({derive.names!r}), but Derive.{derive.kind}(...) "
            f"needs {arity}."
        )
    missing_from_deps = [name for name in derive.names if name not in deps]
    if missing_from_deps:
        raise ValidationError(
            f"Computed(...) at {path} uses Derive.{derive.kind}(...) reading "
            f"{missing_from_deps!r}, which isn't in this Computed(...)'s own "
            f"deps={deps!r}. Every name Derive.*(...) reads must also be "
            f"listed in deps."
        )
    unknown_args = set(derive.args) - set(spec.extra_args)
    if unknown_args:
        raise ValidationError(
            f"Computed(...) at {path} passes unexpected argument(s) "
            f"{sorted(unknown_args)!r} to Derive.{derive.kind}(...). Known "
            f"arguments for Derive.{derive.kind}(...) are: {spec.extra_args!r}."
        )
    missing_args = [name for name in spec.extra_args if name not in derive.args]
    if missing_args:
        raise ValidationError(
            f"Computed(...) at {path} is missing required argument(s) "
            f"{missing_args!r} for Derive.{derive.kind}(...)."
        )
    if derive.kind == "compare":
        op = derive.args.get("op")
        if op not in COMPARE_OPS:
            known = ", ".join(sorted(COMPARE_OPS))
            raise ValidationError(
                f"Computed(...) at {path} uses Derive.compare(...) with "
                f"unknown op {op!r}. Known ops are: {known}."
            )
    if derive.kind == "list_includes" or derive.kind in LIST_COMPARE_KINDS:
        _validate_list_derivation_args(derive, path=path)
    if derive.kind == "value_or":
        fallback = derive.args["fallback"]
        if not _is_json_scalar_literal(fallback):
            raise ValidationError(
                f"Computed(...) at {path} uses Derive.value_or(...) with "
                f"fallback={fallback!r}, which isn't a str, bool, None, "
                f"finite number, or integer within +/-2**53."
            )
    if derive.kind in ("saturating_add", "saturating_subtract"):
        low, high = derive.args.get("min"), derive.args.get("max")
        if isinstance(low, int) and isinstance(high, int) and low > high:
            raise ValidationError(
                f"Computed(...) at {path} uses Derive.{derive.kind}(...) with "
                f"min={low!r} above max={high!r}. min must not be above max."
            )
    if derive.kind in DIGITS_RANGES:
        low, high = DIGITS_RANGES[derive.kind]
        digits = derive.args.get("digits")
        if isinstance(digits, bool) or not isinstance(digits, int) or not low <= digits <= high:
            raise ValidationError(
                f"Computed(...) at {path} uses Derive.{derive.kind}(...) with "
                f"digits={digits!r}, but digits must be an integer from {low} "
                f"to {high}."
            )
    for arg_name, rule in LITERAL_ARG_RULES.get(derive.kind, {}).items():
        _validate_literal_arg(
            derive.args[arg_name], rule, kind=derive.kind, arg_name=arg_name, path=path
        )


def _is_json_scalar_literal(value: object) -> bool:
    """`v0.066`/`v0.067`: a literal the build-time mirror and the client
    are guaranteed to read the same way -- a str, bool, `None`, a finite
    number, or an integer within +/-2**53 (`nan`/`inf` can't be written
    in JSON at all, and a larger integer isn't exactly representable as a
    JavaScript number). Shared by `Predicate.one_of(...)`'s `values` and
    `Derive.list_includes/list_any/list_all(...)`'s `value`."""
    if value is None or isinstance(value, (bool, str)):
        return True
    if isinstance(value, int):
        return abs(value) <= ONE_OF_MAX_INTEGER
    return isinstance(value, float) and math.isfinite(value)


def _validate_list_derivation_args(derive: DerivationRef, *, path: str) -> None:
    """`v0.067`: the literal arguments of the list-scalar catalog's
    `list_includes`/`list_any`/`list_all`. `op` is a member of
    `COMPARE_OPS`, never a raw operator string executed as code (same
    rule as `Derive.compare`). `eq`/`ne` accept any JSON scalar `value`;
    the four relational operators compare the element read as a number,
    so their `value` must be a number too -- a string there would ask
    JavaScript's type-coercing `<` to order text, which the build-time
    mirror deliberately does not reproduce."""
    where = f"Computed(...) at {path} uses Derive.{derive.kind}(...)"
    value = derive.args["value"]
    scalar_message = (
        f"{where} with value={value!r}, which isn't a str, bool, None, "
        f"finite number, or integer within +/-2**53."
    )
    if derive.kind == "list_includes":
        if not _is_json_scalar_literal(value):
            raise ValidationError(scalar_message)
        return
    op = derive.args["op"]
    if not isinstance(op, str) or op not in COMPARE_OPS:
        known = ", ".join(sorted(COMPARE_OPS))
        raise ValidationError(f"{where} with unknown op {op!r}. Known ops are: {known}.")
    if op in LIST_EQUALITY_OPS:
        if not _is_json_scalar_literal(value):
            raise ValidationError(scalar_message)
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not _is_json_scalar_literal(value)
    ):
        raise ValidationError(
            f"{where} with op={op!r} and value={value!r}, but {op!r} compares "
            f"numbers, so value must be a finite number (an integer within "
            f"+/-2**53)."
        )


def _validate_literal_arg(
    value: object, rule: LiteralArgRule, *, kind: str, arg_name: str, path: str
) -> None:
    """`v0.065`: one literal `Derive.*(...)` argument against its
    `LITERAL_ARG_RULES` entry (see `arklight.ir.schema`). Named
    `Derive.<kind>(..., <arg>=...)` in the message so the author can go
    straight to the offending call."""
    where = f"Computed(...) at {path} uses Derive.{kind}(...) with {arg_name}={value!r}"
    if value is None and rule.nullable:
        return
    if rule.kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(f"{where}, but {arg_name} must be an integer.")
        if not rule.low <= value <= rule.high:
            raise ValidationError(
                f"{where}, but {arg_name} must be an integer from {rule.low} to {rule.high}."
            )
        return
    if not isinstance(value, str):
        raise ValidationError(f"{where}, but {arg_name} must be a string.")
    if rule.non_empty and value == "":
        raise ValidationError(f"{where}, but {arg_name} must be a non-empty string.")


def _validate_computed_declaration(node: ARKNode, *, path: str, parent_is_page: bool) -> None:
    if not parent_is_page:
        raise ValidationError(
            f"Computed(...) at {path} may only be declared as a direct child "
            f"of Page(...) -- like State(...), it belongs to the page, not "
            f"to a nested component. Move it up to the top level of "
            f"Page(...)."
        )
    name = node.props.get("name")
    if not isinstance(name, str) or not name:
        raise ValidationError(f"Computed(...) at {path} needs a non-empty string name.")
    deps = node.props.get("deps")
    if not isinstance(deps, tuple) or not deps or not all(isinstance(d, str) and d for d in deps):
        raise ValidationError(
            f"Computed({name!r}) at {path} needs a non-empty deps=(...) tuple "
            f"of non-empty state/computed names, got {deps!r}."
        )
    _validate_derive_ref(node.props.get("derive"), path=path, deps=deps)


def _validate_watch_declaration(
    node: ARKNode,
    *,
    path: str,
    parent_is_page: bool,
    page_state: frozenset[str],
    mutable_state: frozenset[str],
) -> None:
    """
    `vdom-5`: structural + cross-reference checks for `Watch(...)`.
    Mirrors `_validate_computed_declaration`'s "must be a direct child
    of Page(...)" rule, then reuses `_validate_bind`'s bindable-name
    check for `name` (a `Watch(...)` can observe anything `Bind(...)`
    could render -- `State(...)` or `Computed(...)`) and
    `_validate_action`'s existing checks for `then` (an
    `Action.*(...)` reference is only ever valid against a real
    `State(...)`, never a `Computed(...)` -- the same restriction
    `on_click=Action.*(...)` already enforces).
    """
    if not parent_is_page:
        raise ValidationError(
            f"Watch(...) at {path} may only be declared as a direct child of "
            f"Page(...) -- like State(...)/Computed(...), it belongs to the "
            f"page, not to a nested component. Move it up to the top level "
            f"of Page(...)."
        )
    name = node.props.get("name")
    if not isinstance(name, str) or not name:
        raise ValidationError(f"Watch(...) at {path} needs a non-empty string name.")
    if name not in page_state:
        known = ", ".join(sorted(page_state)) or "(none declared)"
        raise ValidationError(
            f"Watch({name!r}) at {path} watches state that isn't declared on "
            f"this page. State/Computed declared on this page: {known}."
        )
    then = node.props.get("then")
    if not isinstance(then, ActionRef):
        raise ValidationError(
            f"Watch({name!r}) at {path} has then={then!r}, which isn't an "
            f"Action.*(...) reference."
        )
    _validate_action(then, path=path, mutable_state=mutable_state, page_state=page_state)


def _validate_one_of_values(values: object, *, path: str) -> None:
    """`v0.066`: `Predicate.one_of(...)`'s literal `values` list -- a
    non-empty list of JSON scalars, so the build-time membership test and
    the client's `indexOf` always see the same literals. `nan`/`inf`
    can't be written in JSON at all; integers past 2**53 aren't exactly
    representable as a JavaScript number."""
    if not isinstance(values, list) or not values:
        raise ValidationError(
            f"Show(...) at {path} needs Predicate.one_of(...) values to be a "
            f"non-empty list, got {values!r}."
        )
    if len(values) > ONE_OF_MAX_VALUES:
        raise ValidationError(
            f"Show(...) at {path} gives Predicate.one_of(...) {len(values)} "
            f"values; the limit is {ONE_OF_MAX_VALUES}."
        )
    for value in values:
        if _is_json_scalar_literal(value):
            continue
        raise ValidationError(
            f"Show(...) at {path} gives Predicate.one_of(...) the value "
            f"{value!r}, which isn't a str, bool, None, finite number, or "
            f"integer within +/-2**53."
        )


def _validate_predicate_ref(
    predicate: PredicateRef | None, *, path: str, page_state: frozenset[str]
) -> None:
    """`vdom-7`: checks for a `Show(...)`'s `predicate=Predicate.*(...)`
    reference -- mirrors `_validate_derive_ref`'s registry-driven
    arity check, scaled down to `PREDICATE_REGISTRY`'s simpler
    fixed-arity predicates."""
    if not isinstance(predicate, PredicateRef):
        raise ValidationError(
            f"Show(...) at {path} needs predicate=Predicate.truthy(...)/"
            f"Predicate.falsy(...)/Predicate.equals(...)/Predicate.gt(...)/"
            f"Predicate.lt(...)/or another Predicate.*(...) kind "
            f"({', '.join(sorted(PREDICATE_REGISTRY))}), got {predicate!r}."
        )
    spec = PREDICATE_REGISTRY.get(predicate.kind)
    if spec is None:
        known = ", ".join(sorted(PREDICATE_REGISTRY))
        raise ValidationError(
            f"Show(...) at {path} uses unknown predicate {predicate.kind!r}. "
            f"Known predicates are: {known}."
        )
    count = len(predicate.names)
    if count < spec.names or (count > spec.names and not spec.variadic):
        arity = f"at least {spec.names}" if spec.variadic else f"exactly {spec.names}"
        raise ValidationError(
            f"Show(...) at {path} uses Predicate.{predicate.kind}(...) with "
            f"{count} name(s); it takes {arity}."
        )
    unknown_args = set(predicate.args) - set(spec.extra_args)
    if unknown_args:
        raise ValidationError(
            f"Show(...) at {path} passes unexpected argument(s) "
            f"{sorted(unknown_args)!r} to Predicate.{predicate.kind}(...). "
            f"Known arguments for Predicate.{predicate.kind}(...) are: "
            f"{spec.extra_args!r}."
        )
    missing_args = [name for name in spec.extra_args if name not in predicate.args]
    if missing_args:
        raise ValidationError(
            f"Show(...) at {path} is missing required argument(s) "
            f"{missing_args!r} for Predicate.{predicate.kind}(...)."
        )
    if predicate.kind == "one_of":
        _validate_one_of_values(predicate.args["values"], path=path)
    for name in predicate.names:
        if name not in page_state:
            known = ", ".join(sorted(page_state)) or "(none declared)"
            raise ValidationError(
                f"Show(...) at {path} references state {name!r}, which isn't "
                f"declared on this page. State/Computed declared on this "
                f"page: {known}."
            )


def _validate_show_declaration(
    node: ARKNode,
    *,
    path: str,
    page_state: frozenset[str],
    mutable_state: frozenset[str],
) -> None:
    """`vdom-7`: unlike `Computed`/`Watch` above, `Show(...)` is real
    content, so -- after checking its own `predicate=` -- this still
    recurses into its children exactly the way `validate_node`'s
    generic tail does for any other component."""
    _validate_predicate_ref(node.props.get("predicate"), path=path, page_state=page_state)
    for i, child in enumerate(node.children):
        if isinstance(child, ARKNode):
            validate_node(
                child,
                path=f"{path}/{child.type}[{i}]",
                page_state=page_state,
                mutable_state=mutable_state,
                parent_is_page=False,
            )
        elif not isinstance(child, str):
            raise ValidationError(
                f"Show(...) at {path} has an unexpected child of type "
                f"{type(child).__name__!r}."
            )


def _validate_repeat_template(
    node: ARKNode,
    *,
    path: str,
    mutable_state: frozenset[str],
    page_state: frozenset[str] | None = None,
) -> None:
    """`vdom-7`: validates a `Repeat(...)`'s per-item template --
    structurally the same as `validate_node`'s generic path (unknown
    types/missing required props/`on_click` still get checked), except
    an `ItemBind` node (`RepeatItem.value()`) is recognized here
    instead of rejected as an unknown component, since it's only
    meaningful inside this one context. `RepeatItem.index()`
    (`arklight.ast.nodes.ItemIndexRef`) isn't separately checked here:
    it can only ever appear as an `Action.*(...)` arg value, which
    `_validate_action` doesn't inspect the *values* of -- same as a
    literal int index wouldn't be."""
    if node.type == "ItemBind":
        return
    spec = SCHEMA.get(node.type)
    if spec is None:
        known = ", ".join(sorted(SCHEMA))
        raise ValidationError(
            f"Unknown component type {node.type!r} at {path} (inside a "
            f"Repeat(...) template). Known component types are: {known}.",
            component_name=node.type,
        )
    for prop_name in spec.required_props:
        if prop_name not in node.props:
            raise ValidationError(
                f"{node.type!r} at {path} is missing required prop {prop_name!r}.",
                component_name=node.type,
            )
    on_click = node.props.get("on_click")
    if isinstance(on_click, ActionRef):
        _validate_action(on_click, path=path, mutable_state=mutable_state, page_state=page_state)
    elif isinstance(on_click, PlatformAPIRef):
        _validate_platform_api(on_click, path=path)
    elif isinstance(on_click, str) and on_click not in KNOWN_BEHAVIORS:
        known = ", ".join(sorted(KNOWN_BEHAVIORS))
        raise ValidationError(
            f"on_click at {path} uses unknown behavior {on_click!r}. "
            f"Known behaviors are: {known}."
        )
    if not spec.allow_children and node.children:
        raise ValidationError(f"{node.type!r} at {path} must not have children.")
    for i, child in enumerate(node.children):
        if isinstance(child, ARKNode):
            _validate_repeat_template(
                child,
                path=f"{path}/{child.type}[{i}]",
                mutable_state=mutable_state,
                page_state=page_state,
            )
        elif not isinstance(child, str):
            raise ValidationError(
                f"{node.type!r} at {path} has an unexpected child of type "
                f"{type(child).__name__!r}."
            )


def _validate_repeat_declaration(
    node: ARKNode,
    *,
    path: str,
    page_state: frozenset[str],
    mutable_state: frozenset[str],
) -> None:
    """`vdom-7`: structural checks for `Repeat(name, template=...)`,
    then hands its one child (the compiled template, built by calling
    `template()` once in `arklight.api.Repeat`) to
    `_validate_repeat_template` rather than the generic per-child loop
    in `validate_node`."""
    name = node.props.get("name")
    if not isinstance(name, str) or not name:
        raise ValidationError(f"Repeat(...) at {path} needs a non-empty string name.")
    if name not in page_state:
        known = ", ".join(sorted(page_state)) or "(none declared)"
        raise ValidationError(
            f"Repeat({name!r}) at {path} references state that isn't declared "
            f"on this page. State/Computed declared on this page: {known}."
        )
    if len(node.children) != 1 or not isinstance(node.children[0], ARKNode):
        raise ValidationError(
            f"Repeat({name!r}) at {path} needs exactly one item template -- "
            f"pass template=lambda: ... to Repeat(...)."
        )
    _validate_repeat_template(
        node.children[0],
        path=f"{path}/template",
        mutable_state=mutable_state,
        page_state=page_state,
    )


def validate_node(
    node: ARKNode,
    *,
    path: str = "root",
    page_state: frozenset[str] = frozenset(),
    mutable_state: frozenset[str] = frozenset(),
    parent_is_page: bool = False,
) -> None:
    """
    `page_state` is the *bindable* set -- every `State(...)`/
    `Computed(...)` name declared on the page -- used for `Bind(...)`/
    `bind_class=` validation. `mutable_state` is the narrower `vdom-4`
    restriction of that set to `State(...)` names only, used for
    `Action.*(...)` validation: a `Computed(...)` name is readable
    (bindable) but never a valid mutation target.
    """
    if node.type == "Bind":
        _validate_bind(node, path=path, page_state=page_state)
        return

    if node.type == "State":
        _validate_state_declaration(node, path=path, parent_is_page=parent_is_page)
        return

    if node.type == "Computed":
        _validate_computed_declaration(node, path=path, parent_is_page=parent_is_page)
        return

    if node.type == "Watch":
        _validate_watch_declaration(
            node,
            path=path,
            parent_is_page=parent_is_page,
            page_state=page_state,
            mutable_state=mutable_state,
        )
        return

    if node.type == "Repeat":
        _validate_repeat_declaration(
            node, path=path, page_state=page_state, mutable_state=mutable_state
        )
        return

    if node.type == "Show":
        _validate_show_declaration(
            node, path=path, page_state=page_state, mutable_state=mutable_state
        )
        return

    spec = SCHEMA.get(node.type)
    if spec is None:
        known = ", ".join(sorted(SCHEMA))
        raise ValidationError(
            f"Unknown component type {node.type!r} at {path}. "
            f"Known component types are: {known}.",
            component_name=node.type,
        )

    for prop_name in spec.required_props:
        if prop_name not in node.props:
            raise ValidationError(
                f"{node.type!r} at {path} is missing required prop {prop_name!r}.",
                component_name=node.type,
            )

    _validate_behavior_props(node, path=path, mutable_state=mutable_state, page_state=page_state)
    _validate_reveal_props(node, path=path)
    _validate_class_bind(node, path=path, page_state=page_state)
    _validate_model_bind(node, path=path, mutable_state=mutable_state)
    _validate_responsive_style(node, path=path)
    _validate_shell_persistent(node, path=path)
    if node.type == "Page":
        _validate_page_head_extensions(node, path=path)

    if not spec.allow_children and node.children:
        raise ValidationError(f"{node.type!r} at {path} must not have children.")

    if spec.text_only_children:
        for i, child in enumerate(node.children):
            if isinstance(child, ARKNode):
                if child.type == "Bind":
                    _validate_bind(child, path=f"{path}/children[{i}]", page_state=page_state)
                    continue
                raise ValidationError(
                    f"{node.type!r} at {path} can only contain text (or "
                    f"Bind(...)), but found a nested {child.type!r} component "
                    f"at {path}/children[{i}]. Move the {child.type!r} outside "
                    f"of {node.type!r}."
                )
            if not isinstance(child, str):
                raise ValidationError(
                    f"{node.type!r} at {path} expected a string child, got "
                    f"{type(child).__name__!r}."
                )
        return

    for i, child in enumerate(node.children):
        if isinstance(child, ARKNode):
            validate_node(
                child,
                path=f"{path}/{child.type}[{i}]",
                page_state=page_state,
                mutable_state=mutable_state,
                parent_is_page=(node.type == "Page"),
            )
        elif not isinstance(child, str):
            raise ValidationError(
                f"{node.type!r} at {path} has an unexpected child of type "
                f"{type(child).__name__!r} at position {i}."
            )


def _find_computed_cycle(computed_deps: dict[str, tuple[str, ...]]) -> list[str] | None:
    """
    DFS cycle detection over the `Computed(...) -> Computed(...)` edges
    of a page's dependency graph (edges to a `State(...)` name are
    leaves -- state has no further deps to walk). Returns the cycle as
    a list of names (first repeated last) if one exists, else `None`.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in computed_deps}
    stack: list[str] = []

    def visit(name: str) -> list[str] | None:
        color[name] = GRAY
        stack.append(name)
        for dep in computed_deps[name]:
            if dep not in computed_deps:
                continue  # a State(...) dependency -- not part of this graph
            if color[dep] == GRAY:
                cycle_start = stack.index(dep)
                return stack[cycle_start:] + [dep]
            if color[dep] == WHITE:
                found = visit(dep)
                if found is not None:
                    return found
        stack.pop()
        color[name] = BLACK
        return None

    for name in computed_deps:
        if color[name] == WHITE:
            found = visit(name)
            if found is not None:
                return found
    return None


def _collect_page_reactive_names(page: ARKNode, route: str) -> tuple[frozenset[str], frozenset[str]]:
    """
    Walk `page`'s direct children once, gathering every `State(...)`/
    `Computed(...)` declaration. Returns `(bindable, mutable_state)`:
    `bindable` is every name `Bind(...)`/`bind_class=` may reference
    (`State(...)` + `Computed(...)`); `mutable_state` is the narrower
    `State(...)`-only set `Action.*(...)` may target (`vdom-4` --
    see this module's docstring, point 13).

    Also performs the cross-declaration checks that can only happen
    once every name on the page is known: a `Computed(...)`'s `deps`
    must each resolve to a `State(...)`/other `Computed(...)`
    declared on this same page (forward references allowed -- a
    `Computed(...)` may depend on one declared later in `Page(...)`'s
    children), and the resulting dependency graph must not contain a
    cycle.
    """
    state_names: set[str] = set()
    computed_specs: dict[str, tuple[tuple[str, ...], ARKNode]] = {}

    for child in page.children:
        if not isinstance(child, ARKNode):
            continue
        if child.type == "State":
            name = child.props.get("name")
            if not isinstance(name, str) or not name:
                raise ValidationError(
                    f"State(...) on page {route!r} needs a non-empty string name."
                )
            if name in state_names or name in computed_specs:
                raise ValidationError(
                    f"State {name!r} is declared more than once on page {route!r}."
                )
            state_names.add(name)
        elif child.type == "Computed":
            name = child.props.get("name")
            if not isinstance(name, str) or not name:
                raise ValidationError(
                    f"Computed(...) on page {route!r} needs a non-empty string name."
                )
            if name in state_names or name in computed_specs:
                raise ValidationError(
                    f"State/Computed {name!r} is declared more than once on "
                    f"page {route!r}."
                )
            deps = child.props.get("deps")
            if not isinstance(deps, tuple):
                deps = ()
            computed_specs[name] = (deps, child)

    known = frozenset(state_names) | frozenset(computed_specs)

    for name, (deps, child) in computed_specs.items():
        unknown_deps = [d for d in deps if d not in known]
        if unknown_deps:
            raise ValidationError(
                f"Computed({name!r}) on page {route!r} depends on "
                f"{unknown_deps!r}, which isn't declared on this page. "
                f"State/Computed declared on this page: "
                f"{', '.join(sorted(known)) or '(none declared)'}."
            )

    cycle = _find_computed_cycle({name: deps for name, (deps, _child) in computed_specs.items()})
    if cycle is not None:
        raise ValidationError(
            f"Computed(...) dependency cycle on page {route!r}: "
            f"{' -> '.join(cycle)}."
        )

    return known, frozenset(state_names)


def validate_page(route: str, page: ARKNode) -> None:
    if page.type != "Page":
        raise ValidationError(
            f"Page function for route {route!r} must return Page(...) as its "
            f"root node, got {page.type!r} instead."
        )
    page_state, mutable_state = _collect_page_reactive_names(page, route)
    validate_node(
        page,
        path=f"page:{route}",
        page_state=page_state,
        mutable_state=mutable_state,
        parent_is_page=False,
    )


def validate_ark_ast(pages: dict[str, ARKNode]) -> None:
    """Validate every page. Raises ValidationError on the first problem found."""
    for route, page in pages.items():
        validate_page(route, page)


def validate_provider(provider: ProviderDeclaration | None) -> None:
    """
    Re-check a declared `Site(provider=...)` against the finalized
    capability vocabulary -- the four well-known names plus the
    `custom:`-prefixed escape hatch (`Provider` stage 2 of 6, `v0.066`,
    re-checked here; the vocabulary itself finalized at stage 6,
    `v0.070` -- see this module's docstring, check 19, and
    `arklight/provider.py`).

    A no-op when `provider` is `None` (the common case -- most sites
    never declare a Provider). `ProviderDeclaration.__post_init__`
    already validates `capabilities` against
    `arklight.provider.PROVIDER_CAPABILITIES` at construction time, so
    in the ordinary `Provider.declare(...)` path this check can never
    actually fire -- an invalid declaration is rejected long before it
    could reach `Site(provider=...)`, let alone this function. This
    exists anyway for the same reason `arklight.ir.validate` re-checks
    other build-time-constructed values instead of trusting the
    object that produced them: the officially designated validation
    stage (`arklight.compiler.pipeline.build`'s "Running validation..."
    step) is where every build-time schema violation is supposed to
    surface as this module's `ValidationError`, not a `ValueError`
    raised earlier from somewhere else in the pipeline. It also covers
    the one case `ProviderDeclaration`'s own `__post_init__` can't: a
    frozen dataclass built by going around its own constructor (e.g.
    `object.__setattr__`), which is possible in Python but not
    something ARKlight itself does.

    Not part of `validate_ark_ast`/`validate_page`'s tree walk --
    `Site(provider=...)` isn't a node in the ARK AST, so
    `arklight.compiler.pipeline.build` calls this directly, right
    alongside `validate_ark_ast`, rather than this module discovering
    it by recursing into a tree that never contains it.
    """
    if provider is None:
        return
    unknown = sorted({cap for cap in provider.capabilities if not is_known_capability(cap)})
    if unknown:
        raise ValidationError(
            f"Site(provider=...) declares unknown capabilit{'y' if len(unknown) == 1 else 'ies'} "
            f"{unknown!r}. Known capabilities are: {', '.join(PROVIDER_CAPABILITIES)}."
        )
