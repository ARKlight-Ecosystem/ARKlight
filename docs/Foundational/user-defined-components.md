# ARKlight v0.060 — User-Defined, Reusable Components

**Status check first, since this matters:** v0.060 is listed in
`docs/Foundational/ARCHITECTURE.md`'s roadmap table as **PLANNED**,
without the "design complete in `docs/DESIGN-NOTES.md`" qualifier that
v0.054 and v0.080 carry. There is no implementation on the `alpha`
branch (`arklight/ir/schema.py` has no registry hook, `arklight/api.py`
defines no `component`/`Component` entry point, no test file mentions
it). The only design-adjacent text is one competitive-positioning
paragraph in `DESIGN-NOTES.md` (line ~169) discussing what closing this
gap would and wouldn't mean for ARKlight vs. htpy/FastHTML — it's a
"why this matters" note, not a spec. Everything below Section 3 is
therefore *my own proposed design*, reverse-engineered to fit ARKlight's
existing compiler discipline, not a transcription of an existing plan.

---

## 1. What "user-defined component" means, in general

Two genuinely different things get called "components" in web tooling,
and the distinction is the whole ballgame here:

- **Value-level reuse.** A function that builds and returns a tree of
  *already-known* primitives. The compiler/runtime never learns a new
  name — as far as it's concerned, `nav()` never existed; it only ever
  saw a `Container` holding two `Link`s. This is what plain functions,
  template `{% include %}`, and (mostly) React function components
  *without* a component-aware compiler give you.
- **Type-level reuse.** A new named node kind the compiler itself
  recognizes: it gets its own entry in whatever schema/registry drives
  validation and codegen, its own props contract, and — if the
  framework has one — its own default styling and error diagnostics
  tied to that name specifically. This is what JSX/Vue SFCs give you:
  `<UserCard />` is not sugar the compiler is oblivious to; it's a
  first-class thing the type checker, the bundler, and dev-tools all
  know about.

The difference is exactly the difference between a C preprocessor
`#define` (the compiler proper never sees the macro name, only its
expansion) and a real user-defined type registered with the compiler's
symbol table (which can be type-checked, produce a targeted error
message using its own name, and be introspected by tooling). Both
*compile down* to the same primitives eventually — the question is
whether the identity survives past the front end.

## 2. Why ARKlight specifically needs this — grounded in the actual code

ARKlight today only has value-level reuse, and it says so explicitly.
The `production` scaffold template (`arklight/cli/templates/
production.py`) ships a `components/` directory whose `__init__.py`
docstring reads, verbatim:

> "Reusable pieces shared across pages. Plain functions -- no special
> 'component' mechanism, just ordinary Python composition."

That's not an oversight — it's the accurate current state, and it's a
real ceiling once you look at what the rest of the compiler already
does for *built-in* components:

- **`arklight/ir/schema.py`** — `SCHEMA: dict[str, NodeSpec]` is a
  closed, hand-maintained table. Every built-in (`Heading`, `Button`,
  `Image`, ...) gets a `NodeSpec(required_props=..., text_only_children=...,
  allow_children=...)`. This is the single source of truth both
  Normalization and Validation consult.
- **`arklight/ir/validate.py`** — walks the AST and checks every node's
  `type` against `SCHEMA`, checks required props are present, checks
  text-only containment rules, etc. A user's `nav()` function produces
  a `Container`/`Link` subtree that gets this checking *because it's
  built entirely out of already-schema'd types* — but `nav` itself has
  no props contract. Nothing stops a caller from passing `nav(bogus=1)`
  wrong, because `nav` isn't a node type; it's just a Python function,
  checked (if at all) by nothing but Python's own call semantics.
- **`arklight/backend/html/tag_map.py`** — `TAG_MAP: dict[str, str]`
  maps a node `type` string straight to an HTML tag. Again closed;
  again keyed on the same identity Validation uses.
- **`arklight/search/feedback.py`** — `parse_undefined_component_name`
  / `record_name_error_feedback` turn a typo'd *built-in* component
  call into a targeted "did you mean `Heading`?" suggestion via
  `arklight search`. A typo'd call to `nav()` (e.g. `nva()`) just gets
  Python's own `NameError` — no ARKlight-specific help, because `nav`
  was never registered anywhere ARKlight's own tooling looks.
- **CSS backend** (`Site.style(...)`, the default stylesheet) — styling
  is keyed to component/class names ARKlight knows about.
  `DESIGN-NOTES.md` calls "beautiful with zero CSS written" out
  explicitly as ARKlight's one clearly unclaimed differentiator versus
  `htpy`/FastHTML. A user's `nav()` gets none of that default styling
  benefit *as a named thing* — only its constituent built-ins do,
  individually.

So the gap isn't "users can't reuse markup" — they clearly can, via
plain functions, right now. The gap is that reuse is invisible to the
compiler: no props contract enforced at the call site, no participation
in the typo-correction/search tooling, no default styling hook, and no
way for `arklight search <name>` or any future dev-tool to say
anything about a project's own vocabulary. `v0.060` is the milestone
that promotes "a Python function that returns a tree" into "a real
node type the compiler's schema, validator, and backends all know by
name" — closing exactly the gap the `DESIGN-NOTES.md` note about
htpy/FastHTML calls out, without touching ARKlight's harder
differentiator (no client-side reactivity runtime), which is a
separate, later concern (`v0.054`/the vdom staging work).

## 3. Where this has to sit in the pipeline — a compiler-design question, not a styling one

ARKlight's pipeline (from `arklight/compiler/pipeline.py`) is:

```
Python Source
  -> Python AST        (arklight.parser.discover)
  -> ARK AST           (page functions executed, return ARKNode trees)
  -> Normalization     (arklight.ir.normalize)
  -> Validation        (arklight.ir.validate)
  -> Website IR        (arklight.ir.build)
  -> Backends          (html / css / js)
```

Every stage after Normalization is written against the closed
`SCHEMA`/`TAG_MAP` vocabulary. That constraint is a feature, not
incidental — it's what lets Validation give beginner-friendly, build-time
errors instead of "silently wrong in the browser" (`validate.py`'s own
module docstring says this outright), and it's what the CSS/JS/Android
backends all lean on. Any component design that makes Validation or a
backend consult something *other than* the static dict at runtime adds
real complexity to every one of those consumers.

There are two structurally different ways to introduce a user
component, and they map exactly onto two well-known compiler
strategies:

### Option A — Macro expansion / inlining (recommended)

A user component call is expanded into its constituent built-in
subtree **before Validation ever runs** — as an extra step during
Normalization (or a new stage immediately after ARK-AST construction,
before Normalization). Concretely:

```python
from arklight import component, Container, Link

@component(
    props={"active": Prop(str, default=None)},
)
def NavBar(active=None):
    return Container(
        Link("Home", href="/", class_name="active" if active == "home" else None),
        Link("About", href="/about", class_name="active" if active == "about" else None),
        class_name="nav",
    )
```

`NavBar(active="home")` produces an `ARKNode(type="NavBar", props={...},
children=[])` marker at call time (so the *call site* is inspectable —
this is what lets diagnostics/search know the name exists at all), and
a new pipeline stage walks the tree, finds every `NavBar`-typed node,
calls its registered render function with its props, and **splices the
result in place of the marker** — recursively, since an expanded
component may itself contain other user components. By the time
Validation runs, the tree contains nothing but `Container`/`Link`/etc.
— the exact same types Validation and every backend already understand.
Zero changes required to `validate.py`, `tag_map.py`, or any backend.

This is precisely C's `#define`/inline-function-at-the-call-site model,
or C++ template instantiation: the abstraction exists for the author
and for tooling, but it's fully resolved — "compiled away" — before the
stages that care about final shape ever see it. It costs nothing at
runtime (there is no runtime; ARKlight's own stated non-goal), and it
means `v0.060` is additive to every existing stage rather than invasive.

**What this needs that ARKlight doesn't have yet:**
- A `component`/`Component` registration API in `arklight/api.py`,
  parallel to `node(type_name)`.
- A props-schema mechanism per user component — a `NodeSpec`-shaped
  declaration (required/optional props, defaults, maybe a type check)
  so a bad call produces a Validation-quality error instead of a raw
  Python `TypeError` two frames deep in the user's own render function.
  This should reuse `validate.py`'s existing error-reporting shape, not
  invent a second one.
- A new "component expansion" pass, with **cycle detection and a
  recursion-depth ceiling** — a user component that (directly or
  transitively) expands into itself needs to fail at build time with a
  clear message, the same way `Computed(...)` dependency cycles already
  do (`validate.py` check #13 already implements exactly this kind of
  self-reference check for `Derive.*`; the same pattern applies here).
- An extension to `arklight/search/feedback.py`'s
  `parse_undefined_component_name` path so a typo'd call to a
  *registered user* component gets the same "did you mean...?"
  treatment a typo'd `Headign(...)` already gets — this is the payoff
  for `arklight search` becoming project-aware, not just
  builtin-aware.
- A styling hook — most naturally, an optional default `Site.style(...)`
  block attached at registration time, expanded into the site's CSS
  output the same way built-in defaults are, so a user component can
  ship with sane default styling instead of forcing every caller to
  pass `class_name=`.

### Option B — Registry-based late binding (rejected, but worth naming why)

The alternative is to make `SCHEMA`/`TAG_MAP` **per-`Site`, mutable
dictionaries** that a project populates at startup (`site.register_component(...)`),
and have `validate.py`/each backend consult the project's registry
instead of (or in addition to) the static global one. This is the
v-table / dynamic-dispatch approach: identity is preserved *all the
way to the backend*, which means a component could render differently
per backend (different markup for the Android WebView shell vs. plain
HTML, say) — a real capability Option A doesn't give you, since Option
A has already erased the component's identity by the time a backend
runs.

The cost: every stage that currently trusts a static, import-time-known
dict now has to thread a per-build registry through instead, and
multiple backends (HTML today; Android and, eventually, alternate
targets per the roadmap) would each need their own render function per
custom component or fall back to some default — meaningfully more
surface area for a v0.060-sized milestone, and it cuts against the
"closed vocabulary, no arbitrary code path" discipline `validate.py`
and `arklight/api.py`'s CSS-input handling both lean on hard (see the
`CSSSyntaxError` / `_CSS_VALUE_INJECTION_CHARS` discipline in `api.py`
— ARKlight is visibly allergic to open-ended, backend-specific
behavior hooks). Per-backend component rendering is a real, legitimate
future need (especially once Android/Desktop backends mature), but
it's more honestly a *follow-on* milestone once Option A's simpler
form has shipped and the multi-backend story around it is better
understood — not something to build into v0.060's first cut.

## 4. Scope boundary worth being explicit about

`v0.054` (JS backend capability expansion / the "reactive-core vdom
staging" work already IN PROGRESS) is where ARKlight is adding
`State`/`Computed`/two-way binding as first-class IR concepts. `v0.060`
should **not** try to let a user-defined component own its own
reactive state — that's a materially harder problem (props flowing
into a closed-registry reactive system, re-render scoping, etc.) and
conflating it with "give reusable markup a name and a props contract"
risks turning a medium milestone into a large one. A clean v0.060
should let a user component *consume* `Bind(...)`/`ActionRef` values
passed in as props from a page that already has `State(...)` declared
— just like `Container`/`Button` do today — without the component
itself declaring new state. State-owning components are a reasonable
`v0.061`-or-later extension once `v0.054` has actually landed and the
IR has real state semantics to hook into.

## 5. Summary

| | Today (plain functions) | Proposed v0.060 |
|---|---|---|
| Reuse mechanism | Ordinary Python function call | Registered component, own `ARKNode` type |
| Props contract | None — Python's own call semantics only | `NodeSpec`-style schema, checked in Validation |
| Compiler visibility | Invisible — erased before Normalization even starts | Visible marker node, expanded (inlined) before Validation |
| Typo diagnostics | Plain Python `NameError` | Integrated into `arklight search` / `parse_undefined_component_name` |
| Default styling | None (must compose already-styled built-ins) | Optional default `Site.style(...)` attached at registration |
| Backend-specific rendering | N/A | Out of scope for v0.060 (would require Option B; deferred) |
| Component-owned state | N/A | Explicitly out of scope for v0.060; depends on `v0.054` landing first |

The one-sentence version: ARKlight already lets you *reuse markup*;
`v0.060`'s job is to let you *name a piece of markup* in a way the
compiler, not just Python, understands — and the cleanest way to do
that without disturbing anything downstream is to treat a user
component the way a compiler treats an inline macro: expand it away
before Validation, so every stage that already trusts the closed
built-in vocabulary keeps trusting it unchanged.
