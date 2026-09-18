# What v1.0 Is

_A grounding, scope-defining document for `docs/Foundational/`, filed
alongside `WHAT-ARKLIGHT-IS.md`'s "The Goal" section as the answer to
the question that section raises but doesn't settle: what does
"stable" actually mean for this project, and exactly where does that
promise stop applying? Current as of **v0.0644** (latest shipped
milestone on `alpha`); cross-check `PROGRESS.md`'s Snapshot table and
`docs/Foundational/ARCHITECTURE.md`'s Milestones table -- where this
file says `v1.0 | Stable compiler | PLANNED` in one line -- before
treating any version-specific claim here as still accurate._

## 1. The one-line definition

**v1.0 is the point at which ARKlight's compiler is stable: it works,
reliably, every time, and it disappears into the background the way a
build tool is supposed to** -- not something a developer has to
actively trust, watch for regressions in, or learn to work around.
Given the same Python source and the same ARKlight version,
`arklight build` produces the same output, every time, with no
surprise breakage between one project and the next.

That is a narrower claim than "1.0" usually signals. It is **not** a
claim that every planned capability exists by then -- Section 6 of
`WHAT-ARKLIGHT-IS.md` already lists real, open gaps (no fetch/HTTP
primitive, no slot/children-passing model for user-defined components)
and nothing here promises they close before `v1.0` ships. It is a
claim about the *reliability of what already exists*, not the
*completeness of what could exist*. A compiler with fewer features
that never surprises anyone is closer to `v1.0` than one with more
features that sometimes does.

## 2. What "reliably" and "disappears into the background" mean, concretely

Four concrete properties, not a mood:

- **Deterministic.** The same `entry.py` compiled with the same
  ARKlight version produces the same `index.html`/`styles.css`/
  `arklight.js`, every time, on every machine. No hidden
  environment-dependent branching in the pipeline.
- **Fails loudly, at build time, or not at all.** `docs/README.md`'s
  Philosophy section already states this as a project-wide rule
  (`ir/validate.py`, `config.py`, `experimental.py` all raise a
  `ValidationError` in Python rather than letting something wrong
  reach the browser silently). v1.0 is the point where that rule has
  no known exceptions left inside the scope drawn in Section 3 below --
  not "mostly fails loudly," but does, full stop, for the surface that
  scope covers.
- **No breaking changes to the closed vocabulary without a
  deprecation path.** `State`, `Action.*`, `Derive.*`, `Predicate.*`,
  `Watch`, and the built-in component set are the public contract a
  v1.0-built site is written against. Renaming or removing one of
  those outright, post-`v1.0`, without a documented migration path, is
  exactly the kind of surprise Section 1 says a stable compiler
  shouldn't produce.
- **A developer stops thinking about the compiler and starts thinking
  about their site.** This is the "disappears like a shadow" framing
  stated operationally: the compiler earns silence. If a developer has
  to remember which version introduced a quirk, or keep a mental list
  of "don't do X, it breaks the build," the compiler hasn't
  disappeared yet -- it's still visibly present as a thing to manage
  around.

### Capability fixes are the mechanism, and the evidence, for this

This isn't an aspiration stated without a track record. Since
`v0.0431`, this project has recognized two categories of out-of-band,
priority-interrupt patch, both numbered *inside* the normal milestone
sequence (`v0.064` -> `v0.065`'s gap) rather than waiting for whichever
numbered version was already in flight to finish first:

- A **bug fix** (`v0.0431`) closes a place where the compiler broke a
  contract it had already made -- `ROUTE_AWARE_ATTRS` silently letting
  route-shaped `srcset`/`poster`/`action`/`formaction` values 404
  outside the domain root. A broken promise.
- A **capability fix** (`v0.0641`, the first of the category; see
  `docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md`) closes a place
  where the compiler shipped *no* authored answer at all for something
  every other primitive in the reactive vocabulary implied it should
  have -- `State`'s `persist=`/`media=` two-way-sync precedent existing
  with no `query=` sibling, confirmed by an exhaustive grep of
  `arklight/` for `location.search`/`URLSearchParams` turning up
  nothing. Not a broken promise -- a missing one. `PROGRESS.md`'s
  `v0.0641` entry states the priority reasoning directly: *"a contract
  violation caps how wrong the tool can be, but a capability gap caps
  how useful it can be, and the latter has no ceiling on how much it's
  costing every site built against this compiler until it's closed."*
  The category's second instance is already identified and staged --
  the Platform API IR work filed as a proposal at `v0.0642` and shipped
  as `v0.065`'s Stage 1 (`docs/Foundational/PLATFORM-APIS.md`).

Both categories exist because this project decided, explicitly, that
"ship it eventually, on the numbered schedule" is the wrong response
to a real gap or a real broken contract sitting in the compiler right
now. Every capability fix landed is direct, checkable evidence that
the compiler is getting more reliable over time in exactly the sense
Section 1 means -- each one closes a specific way `arklight build`
could otherwise surprise, block, or silently under-serve a real site,
ahead of schedule rather than on it. `v1.0`, in that light, isn't a
single milestone that arrives from nowhere -- it's the point at which
the supply of capability fixes (and, ideally, bug fixes) for the
in-scope surface below has run dry, not the point at which someone
decides to stop looking for them.

## 3. Scope: the Web Developing parts, and nothing wider

**The v1.0 promise applies to one thing: the Web Developing parts of
ARKlight** -- the compiler pipeline that takes Python source and
produces a static HTML/CSS/vanilla-JS site, the thing the root
`README.md`'s opening paragraph describes and
`WHAT-ARKLIGHT-IS.md` Section 3 diagrams stage by stage:

```
Python Source -> Python AST -> ARK AST -> Normalization -> Validation
-> Website IR -> HTML / CSS / JS Backends
-> index.html / styles.css / arklight.js
```

Concretely, in scope for the v1.0 stability promise:

| In scope | Where it lives |
| --- | --- |
| Parsing and the AST stage | `arklight/parser/`, `arklight/ast/` |
| Normalization and Validation | `arklight/ir/` |
| The Website IR and its closed action/derivation/component registries | `arklight/ir/schema.py` |
| The HTML backend | `arklight/backend/html/` |
| The CSS backend (default stylesheet, `Site.style(...)`, `responsive_style`/`@media` compilation) | `arklight/backend/css/` |
| The stateful JS runtime backend -- the closed `State`/`Action.*`/`Derive.*`/`Predicate.*`/`Watch` vocabulary, as it exists when `v1.0` ships | `arklight/backend/js/` |
| `arklight build` itself, the one CLI entry point that exercises everything above | `arklight/cli/` |

That list is the whole of "the Web Developing parts": what it takes to
go from a Python site definition to a working, deployable static
website. That is the whole of ARKlight's v1.0 stability promise --
not a soft default that happens to cover more, and not a promise that
widens automatically as other parts of the project mature.

## 4. What v1.0 explicitly does not cover

Named individually, not left to be inferred from Section 3's silence:

- **The Android backend** (`arklight android`,
  `arklight/backend/android/`) and **the Desktop backend**
  (`arklight desktop`, `arklight/backend/desktop/`). Both are still
  `IN PROGRESS` per `ARCHITECTURE.md`'s own Milestones table, both wrap
  the Web target's output rather than replacing it, and each is
  earning its own maturity independently (see
  `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md` and
  `docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`). A packaging
  backend reaching its own "stable" bar is a separate, later claim --
  not something `v1.0`'s Web-scoped promise makes on its behalf.
- **CLI conveniences beyond `build`** -- `arklight search`,
  `arklight pack`/`unpack`, `arklight pwa`, `arklight new`,
  `arklight live-streaming`. These should also work well, but `v1.0`
  specifically certifies the *build pipeline*, not every subcommand
  the CLI happens to ship.
- **Anything behind `arklight/experimental.py`'s registry** -- `@media`
  queries, `raw-postprocess`, `css-import`, and any future entry in
  that gate. `docs/Foundational/EXPERIMENTAL-APIS.md` already labels
  these unstable and opt-in by design; a feature that prints its own
  "you are stepping outside the philosophy" warning on every use
  cannot simultaneously be part of a "just works, reliably" claim.
- **`Provider`** (`docs/Proposals/PROVIDER-SDK-PROPOSAL.md`), **Rei**
  (`docs/Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md`),
  **Project Knowledge** (`docs/Implementation/
  PROJECT-KNOWLEDGE-ADDENDUM.md`), and **`arklight assistant`**
  (Miko/Raeliana, `docs/Proposals/ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`).
  All four are explicitly experimental, staged, or provisional as of
  this writing -- useful, in-flight work, but not "the compiler" in
  the sense Section 1 uses the word.
- **ARKlight Component Collections.** Named on its own in Section 5,
  not folded into the list above, because it is the one item this
  boundary has to be *most* explicit about excluding.

## 5. ARKlight Component Collections: named here specifically because it is excluded

**ARKlight Component Collections** (no design doc yet -- defined here
for the first time, and only for the purpose of drawing this
boundary correctly) is the working name for curated, distributable
bundles of ready-to-use, `@component`-registered components, built on
top of the User-Defined Components system
(`docs/Foundational/USER-DEFINED-COMPONENTS.md`, `v0.060`) rather than
inside the compiler itself. The idea: a Python-Community or
Education-Community author should be able to `import` a collection --
an "Education" collection of quiz widgets, flashcard components, and
lesson-navigation shells; a general "Starter UI" collection of
buttons, cards, and common form patterns -- and call its components
the same way they call any built-in one, without designing the
macro-expansion, default styling, or props contract themselves. This
is the concrete, product-shaped answer to "The Goal" in
`WHAT-ARKLIGHT-IS.md`: it's what makes the Python and Education
communities productive *fast*, on top of a compiler that stays small
and closed.

The reason it is excluded from v1.0's promise, deliberately and by
name, rather than simply not-yet-covered:

- **It is content built on the compiler, not code inside it.** A
  Collection is a package of Python source that calls `component(...)`
  the same way any project's own code does -- it compiles through
  exactly the same macro-expansion path `USER-DEFINED-COMPONENTS.md`
  already documents, with zero special-cased compiler support. Nothing
  about shipping, updating, or removing a Collection touches
  `arklight/parser/`, `arklight/ir/`, or any backend listed in
  Section 3.
- **Its release cadence and quality bar are independent of the
  compiler's.** A Collection can be versioned, expanded, split,
  renamed, deprecated, or pruned on its own schedule -- far faster and
  looser than a compiler earning a `v1.0` stability claim should ever
  move. None of that is "the compiler broke," and it must never be
  read as one. The parallel worth drawing explicitly: the JavaScript
  language and engine being stable has never meant every npm package
  built on top of it is equally stable, and a stable ARKlight compiler
  should not be expected to imply anything about the maturity of a
  given Collection sitting on top of it.
- **Curation is an editorial judgment, not a compiler guarantee.**
  Whether a given quiz-widget component is well-designed, accessible,
  or a good teaching example is a question about that component, not
  about whether `arklight build` behaved correctly. Folding that
  judgment into "the compiler is stable" would conflate two entirely
  different kinds of promise.
- **It stays pre-1.0-shaped even after `v1.0` ships.** Collections are
  expected to keep expanding, splitting, and getting pruned well after
  the compiler itself has stopped needing that kind of churn -- that
  difference in churn rate is exactly why the two need separate
  stability claims in the first place, not a sign that Collections are
  somehow behind schedule.

This section is a scope note, not a proposal. Per `docs/README.md`'s
own lifecycle rule (`docs/Far Future Concern/` -> `docs/Proposals/` ->
`docs/Implementation/` -> `docs/Foundational/`), a real ARKlight
Component Collections feature -- registries, distribution mechanism,
versioning policy, a curation process -- would need its own proposal
filed in `docs/Proposals/` before any of it is real. Nothing here
authorizes that work; this section exists only so the exclusion isn't
left to be inferred later, after some Collection-shaped feature has
already started drifting into "the compiler," the way
`docs/README.md`'s own "why this section exists" postmortem describes
happening to other undocumented boundaries in this project's history.

## 6. Why the boundary is drawn this way

`SYSTEM-DESIGN-AGREEMENTS.md`'s "Compiler First, Runtime Last" rule is
about where *behavior* should live -- compiler vs. runtime. This
boundary is the same instinct applied to where a *stability guarantee*
should live: the compiler is the once-per-project trust boundary every
site built with ARKlight passes through, so it is the compiler's job
to earn "stable" first and alone. A Collection, an experimental flag,
or a packaging backend sitting on top of or beside that trust boundary
does not get to borrow its stability claim for free just by being
part of the same repository -- each one earns its own, on its own
schedule, the same way `docs/Backends/`'s own README already treats
Android and Desktop as maturing independently of each other and of the
Web target underneath both.

## 7. What changes if this boundary moves

- If **ARKlight Component Collections** graduates from this section's
  scope-note into a real, accepted proposal, this section should be
  trimmed to a pointer and the real definition should live in
  `docs/Proposals/` (then `docs/Implementation/`, then its own
  `docs/Foundational/` entry) -- not be expanded in place here, per
  the same "single canonical copy" discipline `docs/README.md`
  enforces everywhere else.
- If **Android** or **Desktop** later earns its own explicit stability
  milestone, that is a new, separately-named milestone
  (`ARCHITECTURE.md`'s Milestones table gets a new row) -- not a
  silent widening of what "`v1.0`" itself means. This file's Section 3
  stays Web-only for as long as `v1.0` itself refers only to the Web
  target.
- If a future capability fix or bug fix reveals that something listed
  in Section 3 as "in scope" isn't actually reliable yet, that is
  exactly the kind of gap Section 2's capability-fix mechanism exists
  to surface and close -- it delays `v1.0`, it doesn't redefine it.
