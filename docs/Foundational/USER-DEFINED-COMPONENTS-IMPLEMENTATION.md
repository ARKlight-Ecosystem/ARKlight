# User-Defined Components Implementation: Staged Order

Status: **Stages 0-2 done**, Stages 3-4 not started. This file does not
restate the design already written in
[`docs/Foundational/user-defined-components.md`](./user-defined-components.md)
-- it exists only to turn that design's Option A / Option B discussion
into a trackable staged ladder, the same role
`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md` plays for the
Android backend, and to pin down the **hybrid** decision the design
doc itself left open.

## The hybrid decision

`user-defined-components.md` lays out Option A (macro expansion,
*recommended*) against Option B (registry-based late binding,
*rejected, but worth naming why*) and comes down on Option A as the
whole milestone's design. This implementation ladder narrows that to a
**hybrid**, rather than dropping Option B entirely:

- **Option A is the default and the only mode with real, distinct
  behavior today.** `component(...)` with no `mode=` argument (or
  `mode="macro"` explicitly) gets exactly what the design doc
  describes: a marker node, expanded away before Normalization ever
  runs, zero footprint on any downstream stage.
- **Option B is available today as an explicit, EXPERIMENTAL opt-in**
  (`component(..., mode="registry")`) for a project that genuinely
  needs per-backend rendering identity down the line -- but it is not
  yet a different *outcome*. Selecting it is a forward-compatible
  *declaration*, not a working alternate pipeline; see "What Option B
  is and isn't, right now" below.

The dispatch between the two is a literal `if`/`elif` ladder over
`ComponentSpec.mode`, in `arklight/ir/components.py`'s `_render_once`:

```python
if spec.mode == "macro":
    return spec.render_fn(**resolved_props)
elif spec.mode == "registry":
    # EXPERIMENTAL -- see below.
    return spec.render_fn(**resolved_props)
else:
    raise ComponentError(...)  # unreachable; mode is a closed vocabulary
```

Both branches currently do the same thing. That's deliberate: the
point of Stage 0 is to make the *selector* real (so a project can
write `mode="registry"` today and have that choice recorded, surfaced,
and carried forward) without pretending Option B's actual differentiator
-- identity preserved through to a per-backend render dispatch, so a
component can render differently per backend -- is implemented yet.
It isn't; that's real, larger, separate work (Stage 3 below), and
conflating "add a mode flag" with "build a second rendering pipeline"
would turn Stage 0 into the large milestone the staged approach exists
to avoid.

### What Option B is and isn't, right now

**Is:** a component can be registered with `mode="registry"`; the
registry records that choice on its `ComponentSpec`; nothing about
picking it fails the build or behaves differently from `mode="macro"`
today. A project that knows it will eventually need per-backend
identity can start using the flag now and get Stage 3's behavior later
with no call-site change.

**Isn't:** identity is *not* preserved past expansion -- a
`mode="registry"` component is spliced away by the same macro pass
Option A uses, exactly like a `mode="macro"` one. There is no
`site.register_component(...)`-style mutable per-`Site` schema yet (the
actual thing `user-defined-components.md`'s Option A/B section
describes Option B as), no per-backend render function slot, and no
change to `validate.py`/`tag_map.py`/any backend. Anyone who needs
real per-backend rendering today does not yet have it -- `mode=` is a
statement of intent, tracked for Stage 3, not a working feature.

## Staged order

| # | Stage | What | Depends on | Status |
|---|---|---|---|---|
| 0 | Registration, props contract, macro expansion | `component(...)`/`Prop` in `arklight/api.py`; `arklight/ir/components.py` (`COMPONENT_REGISTRY`, `ComponentSpec`, `expand_ark_ast`/`expand_node`); wired into `arklight.compiler.pipeline.compile_site_file` as a new stage between ARK-AST construction and Normalization; props contract enforcement (unknown/missing/mistyped props all fail with a `ComponentError`, not a raw Python `TypeError`); cycle detection + a recursion-depth ceiling (mirrors `validate.py` check #13's `Computed`/`Derive` self-reference guard); the `mode=` selector described above. | `user-defined-components.md`'s Option A design | **Done** -- `tests/test_user_defined_components_stage0.py` |
| 1 | Typo diagnostics | Extend `arklight/search/feedback.py`'s `parse_undefined_component_name` path so a typo'd call to a *registered user* component gets the same "did you mean...?" treatment a typo'd `Headign(...)` already gets -- today a typo'd user-component call is just a plain Python `NameError` with no ARKlight-specific help, since it was never in the closed built-in vocabulary `arklight search` already knows. | Stage 0 | **Done** -- `tests/test_user_defined_components_stage1.py` |
| 2 | Default styling hook | An optional default `Site.style(...)` block attached at `component(..., default_style={...})` registration time, expanded into the site's CSS output the same way built-in defaults are -- lets a user component ship with sane default styling instead of forcing every caller to pass `class_name=`. | Stage 0 | **Done** -- `tests/test_user_defined_components_stage2.py` |
| 3 | Option B's real differentiator: per-backend render dispatch | The actual "registry-based late binding" `user-defined-components.md` describes: a `mode="registry"` component's identity survives expansion (or is preserved via a different mechanism -- open design question, not pre-decided here) far enough that the HTML backend, and eventually Android/Desktop, can each supply their own render function for the same component name, falling back to a shared default when a backend doesn't define one. This is the stage that makes Option B a real alternative outcome instead of today's same-as-Option-A placeholder. | Stage 0 (the `mode=` selector already exists to build on) | Not started |
| 4 | Component-owned state | Explicitly **out of scope** until `v0.054`'s reactive-core IR semantics have something for it to hook into (`user-defined-components.md` Section 4 already calls this out as its own, later milestone -- listed here only so this ladder doesn't silently drop it). A component today may *consume* `Bind(...)`/`ActionRef` values passed in as props from a page that already declares `State(...)`, exactly like `Container`/`Button` already do -- it just can't declare new state of its own yet. | `v0.054` (already DONE) + Stages 0-3 | Not started |

Each rung is independently useful and additive, same "later stages
extend one branch instead of retrofitting a mode switch that was never
there" shape `arklight/ir/components.py`'s own module docstring
describes for the Stage 0 -> Stage 3 relationship specifically.

## Stage 0 implementation notes

Decisions made while landing `arklight.ir.components` that weren't
already pinned down by `user-defined-components.md`:

- **Where expansion sits in the pipeline.** The design doc left this
  as "during Normalization (or a new stage immediately after ARK-AST
  construction, before Normalization)" -- Stage 0 picked the latter: a
  distinct `expand_ark_ast(...)` call in
  `arklight.compiler.pipeline.compile_site_file`, between
  `site.build_ark_ast()` and `normalize_ark_ast(...)`, rather than
  folding expansion into `normalize.py` itself. Keeps Normalization's
  own job (flatten lists, wrap bare strings, drop `None`/`False`)
  unchanged and independently testable, and gives component expansion
  its own `on_stage` log line (`"Expanding user-defined
  components..."`) for `--verbose`/`--debug` builds.
- **No children slot on a component call, yet.** `NavBar(active="home")`
  takes only keyword props, matching every example in the design doc
  -- there is no `NavBar(some_child, active="home")` positional-children
  story in Stage 0. Built-in components (`Container(*children,
  **props)`) already give a component author a way to accept children
  by taking an `ARKNode`/list as a prop value instead
  (`Card(body=Container(...))`); a dedicated children slot mirroring
  `node(...)`'s own `*children` signature is left for a later stage if
  real usage shows the prop-based workaround isn't enough.
- **Props contract is closed, not partial.** An unknown prop at a call
  site fails the build (`_resolve_props`'s `unknown` check) rather than
  being silently passed through or ignored -- matches
  `validate.py`'s own "closed vocabulary, no arbitrary code path"
  discipline the design doc's Option B write-up calls out approvingly
  for Option A.
- **Re-registration is last-call-wins**, not append-only or an error --
  same rule `Site.style(...)` already uses for custom CSS classes, so
  reloading a components module during iterative development doesn't
  accumulate stale duplicate entries in `COMPONENT_REGISTRY`.
- **`MAX_COMPONENT_EXPANSION_DEPTH = 64`.** A generous, arbitrary
  ceiling -- no real site should ever nest components 64 deep on
  purpose. Exists as cheap insurance alongside the stack-based cycle
  check, not because the stack check alone was found to miss cases.

## Explicitly out of scope for Stage 0

Same boundary `user-defined-components.md` Section 4 already draws,
repeated here only so this table doesn't imply any of it landed
alongside Stage 0: typo-suggestion integration with `arklight search`
(Stage 1), default component styling (Stage 2), any per-backend
rendering distinction between `mode="macro"` and `mode="registry"`
(Stage 3), and component-owned reactive state (Stage 4, blocked on
nothing further from `v0.054`'s side but still a materially separate
problem). No change to `arklight/ir/schema.py`, `tag_map.py`, or any
backend was needed for Stage 0 -- exactly the "zero changes required"
property Option A promised.

## Stage 1 implementation notes

`arklight/search/feedback.py` itself needed **no changes** --
`parse_undefined_component_name`/`record_name_error_feedback` already
did exactly the right thing; they just never had a registered user
component to find, because `SearchEngine.knowledge` was built purely
from `arklight.ir.schema.SCHEMA`. Stage 1 is entirely a knowledge-base
change:

- **`arklight/search/knowledge.py`.** `build_knowledge_base()` gained
  an optional `components:` parameter (default `None`, so every
  pre-Stage-1 caller is unaffected) that merges a
  `{name: SymbolFact}` entry per registered `ComponentSpec` alongside
  the built-in `SCHEMA` facts, via the new `component_symbol_fact`.
- **Built-ins always win a name collision.** If a user component ever
  reuses a built-in's name, `build_knowledge_base` silently keeps
  `SCHEMA`'s own facts for that name rather than letting the user
  registration shadow them -- `SCHEMA` stays the one closed, canonical
  vocabulary every other compiler stage already agrees on; this only
  concerns what the search/typo-feedback layer sees, not the registry
  itself (`arklight.ir.components.expand_node` still looks a call's
  `node.type` up in `COMPONENT_REGISTRY` exactly as before, unchanged
  by anything in this file).
- **A user component's `SymbolFact` always has `allow_children=False`,
  `text_only_children=False`.** Reflects Stage 0's "no children slot
  on a component call, yet" decision (see above) -- there's no
  children position for a "did you mean...?" hint to describe, unlike
  a built-in `Container`/`Heading`.
- **`SearchEngine.knowledge` merges live, not once.** The built-in
  `SCHEMA` scan is still cached exactly as before Stage 1
  (`self._builtin_knowledge`, built once per engine instance) --  but
  the *merge* with `arklight.ir.components.COMPONENT_REGISTRY` runs on
  every `.knowledge` access instead of being folded into that same
  cached snapshot. Registration is a live global mutated as a site
  module executes (`@component(...)`'s decorator runs at import time,
  before `Site.build_ark_ast()` -- and therefore before the `NameError`
  a *typo'd* call raises -- ever runs), so caching a merged snapshot
  from whenever `.knowledge` first happened to be accessed could
  permanently miss components registered afterward. See
  `SearchEngine.knowledge`'s own docstring for the one known
  consequence this trades away: `_search_uncached`'s
  `functools.lru_cache` is keyed on `(query, limit, near, now)`, not
  on registry contents, so a long-lived engine (the Stage 9 endpoint)
  answering the exact same query twice, with a registration in
  between, could still return a stale cached result the second time.
  Doesn't affect the real path this stage exists for -- a one-shot
  `compile_site_file` call never repeats a query against a changing
  registry within its own process lifetime.
- **The usage graph/PageRank importance signal is untouched.**
  `SearchEngine.graph`/`._importance` still build off `set(self.
  knowledge)` (now including user components) the same way they
  always did, and `arklight.search.ranking._normalized_importance`
  already defaults any name absent from the PageRank dict to `0.0` --
  so a user component that was registered *after* `.graph` was first
  computed and cached just ranks with no structural-importance boost
  rather than erroring, exactly like any other guaranteed-to-be-0
  candidate that has never appeared in a scanned usage example.

## Explicitly out of scope for Stage 1

Default component styling (Stage 2), the per-backend render dispatch
that gives `mode="registry"` its real differentiator (Stage 3), and
component-owned reactive state (Stage 4) -- none of them touched by
this stage. `arklight/cli/search.py`'s `_format_spec` (the *exact-match*
schema-summary printer for `arklight search <name>`) also still reads
`SCHEMA` directly and was left alone: it has no equivalent for a user
component yet (a `ComponentSpec` isn't a `NodeSpec`), so an exact-name
`arklight search NavBar` still won't print a schema summary the way
`arklight search Heading` does -- only the *typo* path
(`_suggest`/the Stage 8 feedback hook) was in Stage 1's scope, per the
table above.

## Stage 2 implementation notes

`component(..., default_style={...})` (`arklight/api.py`) validates the
`rules` dict with the exact same rule set `Site.style(name, rules)`
already enforces -- non-empty dict, non-empty string values, the same
CSS-property/pseudo-class-shorthand syntax check, the same
`CSSSyntaxError`. That shared check used to live only as a `Site`
method (`_validate_css_syntax`); Stage 2 pulled its body out into a
free function, `_check_css_syntax(context, prop, value)`, that both
`Site._validate_css_syntax` (now a one-line wrapper) and the new
`_validate_component_default_style(component_name, rules)` call --
`component(...)` registers independently of any `Site` instance, so it
has no `self` to call a method on. Validation happens once, at
registration/import time, not on every build.

- **Two effects from one registration, both mode-independent.**
  `ComponentSpec.default_style` feeds two separate things, both wired
  into `_render_once` right after a component's render function runs
  (outside the `mode="macro"`/`"registry"` `if`/`elif`, since neither
  branch does anything different here -- default styling isn't part of
  the Option A/B split):
  1. **The rendered subtree's root gets `.{ComponentName}` folded into
     its `class_name`** (`_apply_default_class`), merged with -- not
     overwriting -- any `class_name` the render function already set,
     and skipped entirely if that class is already present (so
     re-expansion can't duplicate it). A component whose render
     function returns something other than a single `ARKNode` (a bare
     list of siblings, a string, `None`) has no single root to attach
     a class to -- `_apply_default_class` is a no-op for those shapes,
     same as any other prop that only makes sense on one node.
  2. **The rules are folded into the site's stylesheet** under that
     same `.{ComponentName}` class, exactly like a `site.style(name,
     rules)` registration -- reusing `render_custom_styles` completely
     unchanged; Stage 2 needed zero new CSS-rendering code.
- **Usage-keyed, not registry-keyed.** `COMPONENT_REGISTRY` is a
  process-global dict -- several unrelated site files can register
  components in the same test run or long-lived process. Emitting
  every *registered* component's `default_style` would leak one
  site's component CSS into an unrelated build's stylesheet. Instead,
  `expand_ark_ast(pages, used=...)`/`expand_node(..., used=...)` now
  optionally collect the name of every component *actually expanded*
  into a `set[str]`, and `arklight.compiler.pipeline.compile_site_file`
  passes that set to the new `collect_default_styles(used)`, which
  only returns `default_style` for names in it. A component that's
  registered but never called in a given build contributes nothing to
  that build's CSS -- see
  `test_end_to_end_unused_component_default_style_is_not_emitted`.
- **An explicit `site.style(name, ...)` wins on a name collision.**
  `compile_site_file` merges `{**component_default_styles,
  **site.custom_styles}` before handing the result to
  `build_website_ir` as `custom_styles=` -- dict-literal unpacking
  means a key present in both wins from the *second* dict, so a site
  author who explicitly calls `site.style("NavBar", {...})` (matching
  a component's own name) always overrides that component's own
  default, the same "more specific/explicit wins" cascade reasoning
  the rest of the CSS backend's ordering already follows (see
  `arklight/backend/css/render.py`'s own comment on cascade order).
  This is also, incidentally, the only realistic way a name collision
  happens at all: a component's default class is always named after
  the component itself, and component names are PascalCase Python
  identifiers by convention, same charset `Site.style(...)` class
  names already accept.
- **No class-name validation needed for the class itself.** Unlike
  `Site.style(name, rules)`, which validates `name` against
  `_CSS_CLASS_NAME_RE`, `_validate_component_default_style` doesn't
  re-check the component's own name -- it's already a valid Python
  identifier (it's a decorated function's `__name__`), and every valid
  Python identifier ARKlight would see here already matches
  `_CSS_CLASS_NAME_RE`.
- **`register_component(..., default_style=...)` stores, doesn't
  validate.** Same division of labor Stage 0 already established for
  `props`/`mode`: `arklight.api.component` is the validating,
  user-facing entry point; `arklight.ir.components.register_component`
  is the lower-level registry function that trusts its caller. A test
  or internal caller that goes around `component(...)` and calls
  `register_component` directly with an unvalidated `default_style`
  gets exactly that -- stored verbatim, checked nowhere.

## Explicitly out of scope for Stage 2

The per-backend render dispatch that gives `mode="registry"` its real
differentiator (Stage 3) and component-owned reactive state (Stage 4)
-- neither touched by this stage. Also out of scope, deliberately: any
way to opt a component *out* of its own default class once
`default_style` is set (there isn't one -- if a component registers a
`default_style`, every call site gets the class; a caller who doesn't
want it should register the component without `default_style` and
apply a class manually via its own `class_name=` prop plumbing
instead), and any interaction with `responsive_style={...}`/`@media`
-- a component's `default_style` is always a flat, non-responsive
`{property: value}` dict, the same shape `Site.style(...)` accepts,
not the richer per-node `responsive_style` shape from v0.048 Stage B.
