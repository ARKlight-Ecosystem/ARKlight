# User-Defined Components Implementation: Staged Order

Status: **Stage 0 done**, Stages 1-4 not started. This file does not
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
| 1 | Typo diagnostics | Extend `arklight/search/feedback.py`'s `parse_undefined_component_name` path so a typo'd call to a *registered user* component gets the same "did you mean...?" treatment a typo'd `Headign(...)` already gets -- today a typo'd user-component call is just a plain Python `NameError` with no ARKlight-specific help, since it was never in the closed built-in vocabulary `arklight search` already knows. | Stage 0 | Not started |
| 2 | Default styling hook | An optional default `Site.style(...)` block attached at `component(..., default_style={...})` registration time, expanded into the site's CSS output the same way built-in defaults are -- lets a user component ship with sane default styling instead of forcing every caller to pass `class_name=`. | Stage 0 | Not started |
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
