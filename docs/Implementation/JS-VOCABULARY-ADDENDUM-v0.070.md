# JS Vocabulary Addendum: Staged Order, v0.061 -> v0.070

**Status:** IN PROGRESS -- stages 1-3/10 (`v0.061`-`v0.063`) have
shipped; stages 4-10 remain PLANNED. This file turns
the accepted, philosophy-compliant part of
[`docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md`](../Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md)
into a trackable, ten-rung landing order, the same role
`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md` plays for the
Android backend's staging list. It does not restate that proposal's
reasoning; it exists to turn "here's a catalog" into "here's the
order it ships in and why."

**Two other, independently accepted proposals share slots in this
range rather than getting their own:** `v0.064` also carries
`arklight search --retrieve-doc` (see
[`SEARCH-RETRIEVE-DOC-ADDENDUM.md`](SEARCH-RETRIEVE-DOC-ADDENDUM.md)),
and `v0.065`-`v0.070` also carry `Provider`'s six-rung ladder (see
[`PROVIDER-SDK-ADDENDUM.md`](PROVIDER-SDK-ADDENDUM.md)). Neither
changes this ladder's own scope or ordering below -- they're
unrelated work that happens to land in the same milestone slots, the
same precedent `v0.041` already set.

## Scope filter: what's in this ladder, and what isn't

Every rung below is a pure registry-fragment addition: one new file
(`NAME` + `JS_FRAGMENT`, mirroring `sum.py`/`compare.py`'s existing
shape) plus one registry line in `DERIVATION_REGISTRY`,
`PREDICATE_REGISTRY`, `BEHAVIOR_REGISTRY`, or `MODIFIER_REGISTRY` --
never a new IR node, never a parser, never anything that touches
`eval`/`new Function`. That's the acceptance test this ladder applied
to the source proposal:

- **In scope:** the proposal's Tier 1 (trivial gaps), Tier 2 (small
  new runtime primitives), and all of §6 (the exhaustive scalar
  derivation/predicate catalog, including §6.5's cross-language
  additions) -- everything that's genuinely *vocabulary*, addressable
  by adding registry entries to the existing four registries.
- **Out of scope, on purpose:** the proposal's Tier 3 (client-side
  data fetch, reorderable lists, sort/filter, file-upload preview --
  each needs a new IR node type, schema, and validation, the size of
  `Repeat`/`Show` when those landed) and Tier 4 (general expressions,
  WebSocket/SSE as an authored primitive, IndexedDB, client-side
  secrets -- each either reopens the `eval`-shaped non-goal or is a
  new subsystem, not a fragment). Nothing in this document authorizes
  work on either; they stay exactly where the proposal left them,
  unaccepted.

Two entries in scope by that test still need an explicit design
exception before they ship *as written* -- `random_int` isn't a pure
function of its inputs (breaks the "server-rendered `Bind` text
agrees with the client recompute" invariant `sum.py`'s docstring
calls out), and `pluralize` needs an irregular-word table, not a
suffix rule, so its first cut ships as "regular plurals only,
documented as such" rather than pretending to be exhaustive. Both are
placed last in the ladder (v0.070) for that reason, not because
they're large.

## Why ten versions, not one

ARKlight already has direct precedent for landing one capability as
many small, independently shippable stages rather than one release:
`v0.054` (JS backend reactive core) landed as 8 `vdom-N` stages, and
`v0.060` (user-defined components) landed as 5 `stage0`-`stage4`
stages, each rolled up into a single milestone summary only after
every stage in it had actually shipped. This ladder follows the same
shape, ordered **easiest to not-so-easy**:

1. Genuinely one-hour, one-file additions first (v0.061-v0.062).
2. Small new runtime modules next (v0.063).
3. The large-but-uniform scalar-derivation catalog, split by category
   so each stage stays reviewable (v0.064-v0.067).
4. Cross-language additions JS has no built-in equivalent for at all,
   which need a little more judgment about naming/edge cases
   (v0.068-v0.069).
5. The two entries that need an explicit design exception, last, so
   review attention is concentrated where it's actually needed
   (v0.070).

## The ladder

### v0.061 -- Math siblings

Same shape as `sum`/`multiply`, siblings that were simply never
written:

- `subtract`, `divide`, `min`, `max`

### v0.062 -- String-casing sibling + comparison predicates

- `uppercase`, `trim` -- siblings of `join`/`format`.
- `Show` predicates `equals`, `gt`, `lt` -- already speced alongside
  `compare`'s `eq/ne/gt/lt/gte/lte` op set, just never wired into
  `PREDICATE_REGISTRY` (today only `truthy`/`falsy`).

### v0.063 -- Small new runtime primitives

Each extends `arklight/backend/js/runtime/*.py` with one small new
module; no new IR node:

- `reveal`/`lazy` behavior via `IntersectionObserver` (mirrors
  `scroll-to`'s shape).
- Debounced two-way binding -- wires the existing
  `MODIFIER_REGISTRY` debounce/throttle tokens into
  `wireModelBinding`.
- Clipboard **paste** behavior (`navigator.clipboard.readText()`,
  mirrors `copy.py`).
- Geolocation one-shot action (`Action.geolocate(name)` ->
  `{lat, lng}`).
- `matchMedia`-driven boolean state
  (`State(..., media="(min-width: 768px)")`).

### v0.064 -- Math derivations catalog

Everything from the proposal's §6.1 except `random_int` (deferred to
v0.070 -- see "Scope filter" above):

- `absolute`, `ceiling`, `floor`, `truncate_number`, `sign`, `sqrt`,
  `cbrt`, `power`, `exp`, `log`, `log2`, `log10`, `hypot`, `clamp`,
  `average`/`mean`, `median`, `gcd`, `lcm`, `percentage_of`,
  `to_fixed`, `to_precision`

### v0.065 -- String derivations catalog

Everything from §6.2. `replace_first`/`replace_all` ship with the
proposal's caveat as a hard requirement, not a suggestion: literal
substring argument only, never a regex pattern string passed through
`new RegExp(...)`.

- `capitalize`, `title_case`, `trim_start`, `trim_end`, `pad_start`,
  `pad_end`, `repeat`, `slice_string`, `char_at`, `replace_first`,
  `replace_all`, `split_count`, `reverse_string`, `string_length`,
  `includes_substring`, `starts_with`, `ends_with`, `is_empty`

### v0.066 -- Predicates catalog

Everything from §6.3:

- `and`, `or`, `not`, `in_range`, `one_of`, `is_empty`/
  `is_not_empty`, `is_null`

### v0.067 -- List-scalar derivations catalog

Everything from §6.4 -- list-typed `State` reduced to a scalar, still
no new "list-in, list-out" registry (that stays with Tier 3's
sort/filter, out of scope here):

- `list_length`, `list_min`, `list_max`, `list_average`,
  `list_first`, `list_last`, `list_includes`, `list_any`, `list_all`

### v0.068 -- Cross-language numeric batteries

Everything from §6.5's numeric rows -- things JS's own `Math` has no
built-in for at all:

- `lerp` (C++20 `std::lerp`), `midpoint` (C++20 `std::midpoint`),
  `saturating_add`/`saturating_subtract` (Rust
  `saturating_add`/`saturating_sub`), `value_or` (Rust
  `Option::unwrap_or`), `first_present` (Rust `Option::or`
  chains/SQL `COALESCE`)

### v0.069 -- Cross-language formatting/case batteries

Everything from §6.5's formatting/case rows:

- `to_ordinal`, `humanize_bytes`, `humanize_duration`,
  `to_snake_case`, `to_camel_case`, `to_kebab_case`, `to_title_case`

### v0.070 -- Capstone: the two design-exception entries

The two §6.1/§6.5 rows the "Scope filter" section above flags as
needing sign-off before they ship as written:

- **`pluralize`** -- ships with a small irregular-noun table plus a
  documented regular-plural-only fallback (`+s`/`+es`), not a claim
  of exhaustive English pluralization.
- **`random_int`** -- ships with an explicit written exception to the
  "server-rendered `Bind` text agrees with the client recompute"
  contract: excluded from build-time pre-rendering entirely, always
  resolved client-side only, documented in the fragment's own
  docstring so a future contributor doesn't assume it follows
  `sum.py`'s usual dual-implementation shape.

## Status tracking

| Stage | Covers | Status |
| --- | --- | --- |
| v0.061 | Math siblings (`subtract`/`divide`/`min`/`max`) | SHIPPED |
| v0.062 | String-casing sibling + comparison predicates | SHIPPED |
| v0.063 | Small new runtime primitives | SHIPPED |
| v0.064 | Math derivations catalog | PLANNED |
| v0.065 | String derivations catalog | PLANNED |
| v0.066 | Predicates catalog | PLANNED |
| v0.067 | List-scalar derivations catalog | PLANNED |
| v0.068 | Cross-language numeric batteries | PLANNED |
| v0.069 | Cross-language formatting/case batteries | PLANNED |
| v0.070 | Capstone: `pluralize` + `random_int` | PLANNED |

See `docs/version history/v0.061.md` through `v0.070.md` for each
stage's forward-looking, user-facing summary (updated to reflect
actual shipped behavior once a stage lands), and `PROGRESS.md`/
`CHANGELOG.md` for the internal record once work on a stage begins.
