# Search Knowledge: State/Bind/Computed/Watch + Closed Reserved
# Keywords Addendum

**Status:** Stage 0 (plan) -- SHIPPED. Stage 1 (implementation) --
SHIPPED, unreleased (`alpha`). A capability fix to
`arklight.search.knowledge.build_knowledge_base()` and
`arklight.cli.search`, in the same spirit `ActionSpec.state_args`
(`arklight/ir/schema.py`) already calls a "capability fix" elsewhere
in this codebase: a small, additive closing of a gap in an existing
mechanism, not a new subsystem.

## Stage 0 -- Game plan

### The gap

`arklight search NAME` is backed by two independent paths:

1. **Exact match** (`arklight.cli.search.resolve_exact` /
   `_resolve_js_vocab`) -- a direct, case-insensitive lookup.
2. **Typo-tolerant "did you mean"** (`arklight.search.engine.
   SearchEngine.search`, the Stage 1-6 retrieval/ranking pipeline) --
   driven entirely by `arklight.search.knowledge.
   build_knowledge_base()`'s output.

`build_knowledge_base()` has only ever scanned two sources: the
built-in `SCHEMA` (`arklight.ir.schema`, every real `NodeSpec`) and,
optionally, a project's own `COMPONENT_REGISTRY`. Two real,
closed vocabularies were never part of it, and so were invisible to
path 2 (and, for the first, to path 1 too):

- **`State`/`Bind`/`Computed`/`Watch`** (`arklight.api`) -- the
  reactive-state declarations. These were *never* given `NodeSpec`
  entries in `SCHEMA` on purpose (`SCHEMA`'s own comment above
  `Repeat`/`Show`: unlike renderable content, they're page-scoped
  declarations Validation/IR-build pull out of the tree entirely), but
  that also meant `arklight search State` -- let alone a typo like
  `Statee` -- fell straight through to "No component named", with
  zero suggestion. Not a corner case: these four are as core to the
  language as any HTML component.
- **The six other closed, compiler-validated registries** in
  `arklight.ir.schema` (`BEHAVIOR_REGISTRY`, `REVEAL_REGISTRY`,
  `ACTION_REGISTRY`, `MODIFIER_REGISTRY`, `DERIVATION_REGISTRY`,
  `PREDICATE_REGISTRY`) plus `PLATFORM_API_REGISTRY`
  (`arklight.ir.platform_api`). `arklight.cli.search._resolve_js_vocab`
  already answers an *exact* (or dotted-prefix, e.g.
  `Action.increment`) lookup against all seven -- but that path is a
  separate function that never touched `knowledge.py`, so none of
  them were ever candidates the ranking pipeline could rank. A typo of
  `increment`, `debounce`, `toggle`, `Derive.sum`, `Predicate.truthy`,
  or `PlatformAPI.notify` got no "did you mean" of its own --
  `search_component`'s own docstring names this exact gap: "the
  suggestion fallback below is still component-only."

### The fix

1. `arklight.search.knowledge`: add `STATE_KEYWORDS` (the four
   reactive-state declarations, mapped to their required argument
   names, read off `arklight.api`'s own signatures) and fold every
   entry of both `STATE_KEYWORDS` and the seven closed registries into
   `build_knowledge_base()`'s output as `SymbolFact`s, unconditionally
   (built-in, closed vocabulary -- not opt-in the way `components=`
   is). Same "built-ins always win a name collision" rule the module
   already documents for `SCHEMA` vs. a user component: `SCHEMA` first,
   then state keywords, then each registry in
   `arklight.cli.search._JS_VOCAB_SOURCES`'s existing order, each
   skipped if the name is already claimed, then (as before) a project's
   own `components=`.
2. `arklight.cli.search`: add a small `_resolve_state_keyword` exact-
   match path (mirrors `_resolve_js_vocab`'s shape, checked in the
   same slot) plus a `_format_state_spec` formatter, so `arklight
   search State` resolves directly instead of round-tripping through
   the ranking pipeline just to find its own exact name. Update the
   module's own docstring/comments that called the fuzzy fallback
   "component-only" -- it no longer is.
3. Tests: extend `tests/test_search_knowledge.py` (the kb is now a
   strict superset of `SCHEMA`, not equal to it), add exact-match
   coverage for the four state keywords in `tests/test_search.py`, and
   add "did you mean" coverage proving a typo of a state keyword or a
   closed-registry entry now surfaces a suggestion end to end.
4. No change to `arklight.ir.schema`, `arklight.ir.platform_api`,
   `arklight.search.retrieval`, or `arklight.search.ranking` -- both
   of the latter only ever read a fact's `.tokens`, so every existing
   `SymbolFact`-shaped consumer keeps working unmodified.
5. This addendum file itself, updated in place from "Stage 0 plan" to
   "Stage 1 shipped" once the above lands -- one rung, not a ladder,
   the same single-stage shape `arklight search --retrieve-doc`'s own
   implementation entry used for its single, self-contained CLI
   addition before that entry was retired as fully rolled up.

### Explicitly out of scope

- `resolve_exact` (and therefore the CLI's `--accept` usage-stats
  flag) stays component-only, unchanged. The seven closed registries
  keep their own separate `_resolve_js_vocab` exact-match path for the
  same reason that module's docstring already gives: there's no
  `--accept` use case for JS vocabulary the way there is for
  components. This fix only adds them to the *ranking* pipeline's
  candidate pool, not to acceptance tracking.
- No new `SymbolFact`-like dataclass. Closed-registry entries reuse
  `SymbolFact` itself (`required_props=()`, `allow_children=False`,
  `text_only_children=False`) the same way `component_symbol_fact`
  already stretches it for user components -- `retrieval`/`ranking`
  only ever read `.tokens`, so a dedicated shape would add a type with
  no consumer that needs it.

## Stage 1 -- Implementation (SHIPPED, unreleased -- alpha)

Shipped exactly as planned in Stage 0, items 1-3. See the patch this
addendum accompanies for the full diff; summary below.

### What shipped

- `arklight/search/knowledge.py`: `STATE_KEYWORDS` and
  `_CLOSED_KEYWORD_REGISTRIES`, folded into `build_knowledge_base()`.
- `arklight/cli/search.py`: `_resolve_state_keyword` +
  `_format_state_spec`, wired into `search_component()` between the
  component exact-match branch and `_resolve_js_vocab`; docstrings
  updated to drop the now-inaccurate "component-only" fallback claim.
- `tests/test_search_knowledge.py`: `SCHEMA` subset assertion (was
  equality), plus new coverage for `STATE_KEYWORDS` and the closed
  registries being present, tokenized, and not shadowing `SCHEMA`.
- `tests/test_search.py`: exact-match coverage for all four state
  keywords, plus "did you mean" coverage for a typo'd state keyword
  and a typo'd closed-registry entry.
- `tests/test_user_defined_components_stage1.py`: one more pre-existing
  `set(facts) == set(SCHEMA)` equality assertion (`build_knowledge_base()`
  with no `components=`) found the same way, same subset fix.
- Full suite (`pytest -q`, `tests/`) passes: 2343 passed, 0 failed.

### Status tracking

| Stage | Covers | Status |
| --- | --- | --- |
| 0 | Game plan | SHIPPED |
| 1 | `knowledge.py` + `cli/search.py` capability fix, tests | SHIPPED (unreleased, `alpha`) |

See `PROGRESS.md`/`CHANGELOG.md` for the internal record once this is
rolled into a version-history entry; not yet given one, the same
"shipped, unreleased on `alpha`" gap `arklight search --retrieve-doc`'s
own follow-up fixes sat in before their `0.06605`/`0.06606` entries
landed.
