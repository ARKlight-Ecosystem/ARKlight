# Component-Owned Structural Styling for User-Defined Components

## Status

**Proposal -- not yet accepted, not yet staged.** Per
`docs/Proposals/README.md`'s own definition, this describes something
that does not exist yet, may never be built as written, and could be
rejected outright. Nothing below is implemented.

**Origin:** a design question -- "can a user-defined component have
independent styling, and if not, should it?" -- answered by an audit of
what `component(..., default_style={...})` does today (see "What is
already settled", including three build experiments run against
`alpha` at package version `0.070.6`) plus a survey of how other
component-based tools scope styles. The short answer to the first
half: **partly yes, already** -- a component can ship default CSS for
its own *root element*. The gap is everything below the root.

Requests no version slot. Staged as separately acceptable rungs, so a
maintainer can take Rung 1 without committing to the rest.

## What is already settled (context, not part of this proposal)

Everything in this section describes `alpha` as it is today, verified
against the code and, where marked **(verified)**, by building a small
site.

- **A component already ships styling under its own name.**
  `component(..., default_style={...})` takes a flat
  `{css-property: value}` dict, validated at registration time with the
  same rules `Site.style(...)` uses, pseudo-class shorthand included
  (`":hover:background": "#eee"`). When a build uses the component, the
  rules are folded into the stylesheet under `.{ComponentName}` and
  that class is merged onto the rendered root's `class_name`
  automatically (`arklight.ir.components._apply_default_class`),
  composing with a `class_name` the render function sets itself rather
  than replacing it. Only components a build actually uses contribute
  CSS (`collect_default_styles`). **(verified:** a component with
  `{"display": "flex", "gap": "1rem", ":hover:background": "#eee"}`
  produced `.Card { display: flex; gap: 1rem; }` and
  `.Card:hover { background: #eee; }`, and the root rendered as
  `class="inner Card"`.)
- **A site author's override is whole-rule, by name.**
  `arklight.compiler.pipeline` builds
  `custom_styles={**component_default_styles, **site.custom_styles}`, so
  `site.style("Card", {...})` replaces the component's flat rule
  entirely rather than merging property by property.
  `USER-DEFINED-COMPONENTS.md` documents this ("an explicit
  `site.style(...)` always wins").
- **The machinery for structural CSS already exists -- at site level.**
  `Site.style_selector(selector, rules)` accepts combinators, attribute
  selectors, pseudo-elements, parameterized pseudo-classes, and
  `&`-prefixed nested keys (`&:hover`, `&.active`, `& .child`,
  `& > .child`), parsed by a *closed* grammar
  (`arklight.backend.css.selectors.parse_selector_list`; a bare tag
  must be in `KNOWN_HTML_TAGS`) and resolved at author time into flat
  selectors (`Site._resolve_nested_selector`). Site-level
  `keyframes`, `font_face`, `container_query` and `supports` exist too.
  None of it is reachable from a component's own declaration.
- **The CSS backend has a fixed cascade order** (`CSSBackend.render`):
  base rules, tokens, built-in utilities, `custom_styles` (where
  component defaults land today), `media_queries`, per-node
  `responsive_rules`, and last of all `selector_rules`, "so the
  newer/more specific mechanism should get the final say."
- **Inline and per-node styling already work inside a component.**
  **(verified:** a macro-mode component whose inner `Text` carried
  `responsive_style={"(max-width: 600px)": {...}}` built, and emitted an
  `.arkgen-1` rule inside `@media`, behind the existing
  `css-media-queries` experimental gate.) What a component cannot do is
  use a pseudo-class, a descendant/child combinator, or a state-dependent
  rule on an inner element: inline `style={...}` has no pseudo-classes
  (`DESIGN-NOTES.md`, "What `style={...}` can and can't reach"), and the
  only other route is the site author registering
  `site.style_selector(".Card > img", ...)` themselves, from outside the
  component.
- **`default_style` cannot express nesting.** **(verified:**
  `default_style={"display": "flex", "& > img": {"border-radius": "8px"}}`
  fails at registration with `default_style property '& > img' needs a
  non-empty string value, got {'border-radius': '8px'}` -- a correct
  rejection, but an error message that says nothing about nesting.)
- **A `default_style` on a component with no single rendered root
  fails silently.** **(verified:** a component returning
  `[Text("a"), Text("b")]` with `default_style={"display": "flex"}`
  built without complaint and emitted a `.Pair { ... }` rule, but no
  element in the page carried the class.) `_apply_default_class` is
  documented as a no-op on a non-`ARKNode` result; the stylesheet side
  has no matching check, so the rule is dead CSS and the author is
  never told.
- **`mode="registry"` backend overrides inherit the root class.**
  `apply_default_style_class` folds `.{ComponentName}` onto an
  override's own subtree too, so a rule keyed on the component's class
  applies regardless of which render function produced the subtree.
  `USER-DEFINED-COMPONENTS.md` already records one adjacent gap:
  `responsive_style={...}` inside a registry-mode override's subtree
  does not collect into the site-wide `@media` rules.
- **Neighbouring proposal.**
  [`COMPONENT-CHILDREN-AND-PASSTHROUGH-PROPOSAL.md`](COMPONENT-CHILDREN-AND-PASSTHROUGH-PROPOSAL.md)
  covers children/slots and `class_name`/`id`/`data-*`/`aria-*`
  passthrough. This proposal does not depend on it, and does not change
  it (see Q4).

## The proposal, as stated

A component should be able to own the styling of its whole subtree, not
just its root, in the same closed, build-time, no-runtime vocabulary
the rest of ARKlight's styling already uses. Concretely: let
`default_style` accept the `&`-prefixed nested keys `Site.style_selector`
already accepts, resolved against the component's own `.{ComponentName}`
class.

```python
@component(
    props={"title": Prop(default=""), "compact": Prop(default=False)},
    default_style={
        # Unchanged: flat properties and the :pseudo:property shorthand
        # keep their current meaning, tier and output.
        "display": "flex",
        "gap": "1rem",
        ":hover:background": "#f5f5f5",
        # New: `&` is the component's own `.Card` class.
        "& > img": {"border-radius": "8px"},
        "& .title": {"font-weight": "600"},
        "&:focus-within": {"outline": "2px solid currentColor"},
        "&.compact": {"gap": "0.5rem"},
    },
)
def Card(title="", compact=False):
    return Container(
        Image(src="a.png", alt=""),
        Text(title, class_name="title"),
        class_name="compact" if compact else None,   # merges with `Card`
    )
```

Emitted, in addition to today's `.Card` / `.Card:hover`:

```css
.Card > img { border-radius: 8px; }
.Card .title { font-weight: 600; }
.Card:focus-within { outline: 2px solid currentColor; }
.Card.compact { gap: 0.5rem; }
```

The point of the design is that **a component carries everything needed
to look right wherever it is used**, instead of depending on a site
author to know which inner classes exist and register selectors for
them from `site.py`. It also gives variants a home that needs no new
mechanism: a prop that sets a root class (which `_apply_default_class`
already merges) plus an `&.variant` rule.

### Rung 1 -- `&`-nested keys in `default_style`

- **Accepted keys.** A key beginning with `&`, in exactly the shapes
  `_resolve_nested_selector` accepts today: `&:pseudo`, `&.class`,
  `&[attr]`, `& .descendant`, `& > .child`, `& + .sibling`,
  `& ~ .sibling`. Value: a flat `{property: value}` dict validated like
  `style_selector`'s rules (the `:pseudo:property` shorthand is not
  accepted *inside* a nested dict, matching `style_selector`).
- **Resolution.** `&` becomes `.{ComponentName}`, then the full
  selector goes through the same closed `parse_selector_list` grammar,
  at *registration* time, so a malformed key fails at import with the
  component's name in the message, not later in a build. Every resolved
  selector therefore begins with the component's own root class: **a
  component cannot write a rule that reaches outside its own root.**
- **One level of nesting, one base selector.** Same limits as
  `style_selector`: no `&` inside a nested dict, no grouped base list.
- **Placement in the cascade.** Flat keys and the `:pseudo:property`
  shorthand stay exactly where they are (the `custom_styles` tier,
  overridden wholesale by `site.style("Card", ...)`). Nested rules go in
  a **new tier immediately before the site's own `selector_rules`**, in
  declaration order within a component and components sorted by name
  (the determinism `render_custom_styles` already has). Consequence: a
  site author overrides a component's nested rule by registering the
  *same selector* with `site.style_selector(".Card > img", ...)` -- equal
  specificity, later tier wins -- with no `allow_redefine` needed, since
  component-owned rules are not in `site.selector_rules`.
- **Usage-keyed emission.** Same rule as the flat dict: only components
  a build actually uses contribute CSS, via a sibling of
  `collect_default_styles` (name to be settled).
- **Better error for the rejected shape.** Independent of whether the
  rest is accepted, the existing failure for a non-string value under a
  non-`&` key should say that nested rules need an `&`-prefixed key.
  (Today it reports `needs a non-empty string value, got {...}`.)

### Rung 2 -- diagnose a `default_style` that can never apply

When a component declares `default_style` (flat or nested) but a call
expands to something with no single `ARKNode` root -- a list of
siblings, a bare string -- emit a **build-time warning** naming the
component and the call site, instead of silently emitting a dead rule.
This is a warning, not an error, because today's builds with this shape
succeed and a new hard failure would be a breaking change for any
project already shipping one by accident. Whether it later becomes an
error is Q3. This rung has no dependency on Rung 1 and is worth
landing on its own.

### Rung 3 -- component-owned responsive rules (separately stageable)

Let a component declare breakpoint rules alongside its other styling,
e.g. a `default_responsive_style={"(max-width: 600px)": {...}}` keyed
like the existing per-node `responsive_style`, resolved against
`.{ComponentName}`, emitted through the existing `media_queries` tier,
and gated by the existing `css-media-queries` experimental feature
(same banner, same end-of-build summary). Nested `&` keys inside it
follow Rung 1's rules.

This rung is kept separate because it is the one most likely to be
*replaced* rather than built as written: a component's natural
breakpoint is usually the size of its *container*, not the viewport.
`Site.media_query`'s own docstring calls viewport-keyed rules a
deliberate, opt-in escape hatch from the intrinsic layout model, and
`Site.container_query` exists because a container query is keyed to an
ancestor's size instead. See Q2 -- a
component-owned `@container` rung may be the better fit.

### What "scoped" means here, and what it deliberately doesn't

This proposal gives components **rooting, not isolation.** Every
component-owned rule is anchored under the component's own class, so a
component cannot style outside itself and two components cannot collide
on an inner class name like `.title` (each writes `.Card .title` /
`.Panel .title`). It does **not** stop other CSS from reaching in: a
site's `site.style_selector(...)`, an inline `style=`, or a built-in
utility rule can still affect a component's inner elements, and a
component's descendant selector can still match a *nested component's*
elements. That is the same trade-off native CSS `@scope` makes -- scoped
rules limit where *your* selectors apply, not what else may override
them -- and it is deliberate: ARKlight's override story (a site author
can always win by writing the same selector later) depends on there being
no hard boundary.

### Why staged, not built outright

Rung 1 is a validation-and-emission change that reuses a parser, a
resolver and a rendering function that already exist, behind an
unchanged default (a component with no `&` key is byte-identical).
Rung 2 is a diagnostic. Rung 3 touches an experimental gate and an
open design question (viewport vs container), and should not hold up
the other two.

## Prior art

How other component-based tools scope a component's CSS, summarized
(sources at the end of this section):

- **Svelte** compiles a component's `<style>` so each affected element
  gets a class derived from a hash of the component's styles; each
  scoped selector gains `0-1-0` of specificity from that class, with
  `:where()` used on repeats to avoid compounding it. Component
  `@keyframes` names are hashed the same way.
- **Astro** scopes a component's `<style>` by default, and exposes the
  specificity trade-off as a setting (`scopedStyleStrategy`:
  `where`, `class`, or `attribute`) -- i.e. even a mature scoping
  implementation treats "does scoping raise specificity" as a knob, not a
  given. Scoped styles do not apply to other components nested inside.
- **Vue** (`<style scoped>`) rewrites selectors to carry a generated
  `data-v-*` attribute. The well-known gotcha: a rule like `.card h2`
  does not reach markup inside a *child component* or a slot, because
  that markup carries a different attribute -- a boundary the author did
  not ask for and often does not expect.
- **CSS Modules / styled-components** generate unique class names --
  per file at build time for CSS Modules, per component for
  styled-components.
- **Native CSS `@scope`** limits a rule's reach to a subtree, with an
  optional lower boundary ("donut scope"). Support is now broad but
  uneven: Chromium 118+, Firefox 146+, Safari 17.4+ (with a partial-support
  window reported around Safari 26.0-26.3). A browser without it drops the whole block rather
  than falling back, so using it would mean an unscoped duplicate or
  accepting that older browsers lose the styling. It also does not
  protect scoped elements from higher-specificity outside rules.

What this proposal takes from that, and what it doesn't:

- **Take:** styling is declared with the component and is only
  emitted when the component is used (already true for ARKlight's flat
  `default_style`).
- **Don't take: hashed or attribute-based scoping.** ARKlight
  components are already identified by a stable, human-readable class
  (`.Card`) that is part of the design -- a site author overrides it by
  name. Replacing it with `.Card-a1b2c3` would break
  `site.style("Card", ...)` and make output hard to read.
- **Don't take: `@scope`.** ARKlight is a compiler that already
  resolves `&` nesting into flat selectors "so the generated stylesheet
  stays readable in browsers that predate CSS nesting support"
  (`Site._resolve_nested_selector`'s own docstring). Prefixing at
  compile time gives the same rooting with no browser dependency and no
  fallback problem.
- **Don't take: Vue's accidental boundary.** Because ARKlight expands
  components into plain trees before validation, a descendant selector
  matches nested components' elements too. That is a more predictable
  default than a hidden attribute boundary, but it is a decision worth
  stating -- Q1.

Sources consulted (October 2026): Svelte docs, "Scoped styles"
(`https://svelte.dev/docs/svelte/scoped-styles`); Astro docs, "Styles and
CSS" (`docs.astro.build`, guides/styling); Netguru, "Vue scoped styles vs
CSS Modules" (`https://www.netguru.com/codestories/vue.js-scoped-styles-vs-css-modules`);
OpenReplay, "Native CSS @scope" (`https://blog.openreplay.com/native-css-scope/`);
CoderCops, "CSS @scope explained: style isolation"
(`https://blog.codercops.com/blog/css-scope-explained-style-isolation-2026`).
Browser-support figures vary between these sources and move quickly;
re-check before relying on any of them.

## Acceptance criteria

1. A component whose `default_style` contains no `&`-prefixed key
   produces **byte-identical** output to today, including its flat
   `.Name` and `:pseudo:property` rules and their position in the
   stylesheet.
2. `&:pseudo`, `&.class`, `&[attr]`, `& .descendant` and the three
   combinator forms in `default_style` emit the corresponding rule
   rooted at `.{ComponentName}`, only when the build uses the
   component.
3. A malformed or out-of-grammar nested key fails at **registration
   time**, naming the component and the key, using the same closed
   grammar as `Site.style_selector`. A `&` key can never produce a
   selector that does not begin with the component's own class.
4. Nested rules are emitted after `custom_styles`, `media_queries` and
   `responsive_rules`, and before the site's own `selector_rules`; a
   site's `site.style_selector(<same selector>, ...)` overrides a
   component's nested rule without `allow_redefine=True`.
5. `site.style("Card", {...})` keeps its current meaning: it replaces
   the component's *flat* rule wholesale. (Whether it should also affect
   nested rules is Q5.)
6. Registry-mode override subtrees pick up nested rules the same way
   they already pick up the root class.
7. A component with `default_style` whose call expands to no single
   root produces a build-time warning naming the component (Rung 2),
   and still builds.
8. Nothing here adds a compiler stage, a runtime, or a way to emit an
   arbitrary CSS string: every rule still passes through the closed
   selector grammar and the same property/value validation as
   `Site.style`.

## Open questions

**Q1. Should a component's descendant rules reach into a nested
component?** As proposed, `.Card .title` matches any `.title` below the
card, including one rendered by a component placed inside it, because
expansion is complete before styling is resolved. The alternative is a
lower boundary (a `to` limit like `@scope`'s) so a component's rules
stop at a nested component's root. Rooting-without-isolation is simpler and matches how
`style_selector` already behaves; isolation is closer to what Vue/Svelte
users expect. Needs a decision before Rung 1's acceptance criteria are
final.

**Q2. Viewport or container for Rung 3?** A component-owned
`default_responsive_style` reuses the experimental, viewport-keyed
`css-media-queries` path. A component-owned `@container` rule reuses
`Site.container_query`'s shape and keys the breakpoint to the thing the
component actually controls. Which, or both, and does a container-query
rung need the component to declare itself a container (a root
`container-type`)?

**Q3. Warning or error for a `default_style` that can never apply
(Rung 2)?** Warning-only is non-breaking; an error is honest. Should the
severity change in a later version, and should the dead `.Name` rule
still be emitted when the warning fires?

**Q4. Interaction with prop passthrough.** If
`COMPONENT-CHILDREN-AND-PASSTHROUGH-PROPOSAL.md`'s `class_name`
passthrough is accepted, a call site can add a class to a component's
root (`Card(class_name="compact")`), which makes `&.compact` a
caller-controlled variant with no `Prop` at all. Does that make a
first-class `variant` concept unnecessary, or is a declared, validated
variant prop still worth having so a typo'd variant fails the build?

**Q5. Does `site.style("Card", ...)` also suppress nested defaults?**
Today it replaces the flat rule only. Leaving nested rules in place is
the least surprising reading of "the site overrode the root"; but an
author who wants to take over a component's look entirely has no single
switch. Options: leave as is and document the override recipe, or add
an explicit opt-out.

**Q6. Declaration order and merging across the two forms.** If a
component declares both `":hover:background"` and `"&:hover"`, both are
emitted (different tiers). Is that acceptable, or should one be
rejected as redundant?

**Q7. Component-scoped `@keyframes` / `@font-face`.** Site-level
`Site.keyframes` and `font_face` exist, but a component-owned animation
raises a name-collision question Svelte answers with hashing, which this
proposal has just declined for class names. Out of scope here (see
below); recorded so the question is not lost.

## If accepted -- a sketch, not a commitment

- **`arklight/api.py` (`component`)** -- split `default_style` at
  registration into flat entries (existing validation, unchanged) and
  `&`-keyed entries, validated by a shared, module-level form of
  `_resolve_nested_selector` (currently a `Site` static method) plus the
  existing property validation. Store the nested part on a new
  `ComponentSpec` field rather than widening `default_style`'s type, so
  `collect_default_styles` and acceptance criterion 1 are untouched.
- **`arklight/ir/components.py`** -- a sibling of
  `collect_default_styles` returning `[(selector, rules)]` for used
  components; the Rung 2 diagnostic next to `_apply_default_class`'s
  existing no-op branch.
- **`arklight/compiler/pipeline.py` / `arklight/ir/build.py`** -- thread
  the new list into `WebsiteIR` as a new field (name to be settled),
  next to `selector_rules`.
- **`arklight/backend/css/render.py`** -- render the new tier through
  `render_selector_rules` immediately before the site's own
  `selector_rules`.
- **Docs** -- `docs/Foundational/USER-DEFINED-COMPONENTS.md`'s "Default
  styling" section and `AUTHORING-GUIDE.md`; a Capability Matrix row if
  accepted. Tests following `tests/test_user_defined_components_stage1.py`'s
  pattern (per-layer unit coverage plus an end-to-end build), including
  the byte-identical regression for a component with no `&` key.
- Nothing staged; this would graduate to `docs/Implementation/` only
  once accepted, per `docs/Proposals/README.md`'s own graduation path.

## Not in scope

- **Hashed, attribute-based or otherwise generated scoping classes.**
  See "Prior art" -- components keep their stable, overridable name.
- **Native `@scope` output.** Not needed once selectors are rooted at
  compile time.
- **Hard style isolation** (Shadow DOM-style encapsulation). Rooting
  only; see "What 'scoped' means here".
- **Component-owned `@keyframes`, `@font-face`, `@supports` or
  `@import`.** Site-level APIs exist; the collision and ordering
  questions (Q7) are a separate design.
- **A runtime or JavaScript-driven styling mechanism, and any raw CSS
  string.** The closed-vocabulary, no-`eval` boundary is unchanged.
- **Instance-level style overrides at the call site** (`Card(style=...)`).
  That is prop passthrough, covered by
  `COMPONENT-CHILDREN-AND-PASSTHROUGH-PROPOSAL.md`.
- **Changes to `mode="macro"` vs. `mode="registry"`, or to how
  `site.style("Name", ...)` overrides the flat rule**, beyond Q5.
