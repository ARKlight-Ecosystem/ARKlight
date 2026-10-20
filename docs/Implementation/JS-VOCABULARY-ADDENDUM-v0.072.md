# JS Vocabulary Addendum: Tier 3 Staged Order, v0.071/v0.072

**Status: ACCEPTED, IN PROGRESS.** Stage 1 (`list_at`) has shipped,
in the `v0.071` slot. Stages 2-4 are accepted and staged here, in the
`v0.072` slot; none have landed yet. This file turns Tier 3 (§7) of
[`docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md`](../Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md)
-- until now an unsettled follow-up finding, not covered by that
proposal's original Tier 1/Tier 2/§6 acceptance -- into a trackable
staged landing order, the same role
`JS-VOCABULARY-ADDENDUM-v0.070.md` (retired -- see `docs/Foundational/DESIGN-NOTES.md`) played for Tier 1/Tier 2/§6. It
does not restate that section's reasoning; it exists to turn "here's
a follow-up finding" into "here's the order it ships in and the slots
it ships under."

**Why two version slots for one four-stage ladder:** `list_at`
reused an already-shipped `DerivationRef` shape (`char_at`'s own) and
was ready before the `v0.072` addendum existed to track it, so it
shipped where it landed -- the `v0.071` slot, already shared by
Project Knowledge stage 1 and Input & Platform Primitives stages 2
and 6 (same "independent pieces of accepted work landing in the same
milestone slot" precedent `INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md`
cites for `v0.041`/`v0.065`). The remaining three stages are grouped
under their own `v0.072` slot rather than retro-fitted into `v0.071`,
since unlike `list_at` none of them had already shipped by the time
this ladder was written down.

## Scope filter: what's in this ladder, and what isn't

- **In scope:** all four entries of the proposal's Tier 3 (§7) --
  `list_at` (§7.3), `Derive.if_` (§7.1), `Derive.select` (§7.2), and
  date/time arithmetic (§7.4). Unlike the `v0.070` ladder's pure
  registry-fragment additions, every entry here costs a new
  `DerivationRef`/`PredicateRef` *shape*, not just a same-shape
  registry line -- that's §7's own stated reason these are a separate
  tier rather than folded into §6's catalog, and it's why this
  ladder's stages are reviewed individually rather than batched.
- **Out of scope, still:** Tier 4 (§8, client-side data fetching and
  the other IR-node-sized gaps) and Tier 5 (§9, the out-of-scope
  bucket). Nothing in this document authorizes work on either; they
  stay exactly where the proposal left them, unaccepted.
- **Accepted with a condition attached:** date/time arithmetic (§7.4,
  stage 4 below) is accepted into the ladder's *order*, not exempted
  from the sign-off its own proposal entry calls for. It is staged
  last and marked PLANNED-not-started pending that sign-off, the same
  posture the `v0.070` ladder already used for `random_int`/
  `pluralize`.

## The ladder

### v0.071, Tier 3 stage 1 -- `list_at` (DONE)

`Derive.list_at(name, index)` -- arbitrary-position read into a
list-valued `State(...)`/`Computed(...)`, the list-side counterpart
of the already-shipped `char_at(string, index)`. Reuses `char_at`'s
own `DerivationSpec`/`LiteralArgRule` shape exactly (`min_names=1,
max_names=1, extra_args=("index",)`, the same `STRING_INDEX_LIMIT`-
bounded range check); an out-of-range index, or a value that isn't a
list, reads as `None`/`null` rather than wrapping from the end.
Shipped in the `v0.071` slot -- see `CHANGELOG.md` and the `v0.071`
row in `PROGRESS.md`'s Snapshot table. Proposal: §7.3.

### v0.072, Tier 3 stage 2 -- `Derive.if_` (PLANNED)

Two-branch conditional value selection --
`Derive.if_(Predicate.gt("qty", 10), "bulk price", "regular price")`.
Ordered first among the `v0.072` stages per §10's suggested order,
since it's the one other proposals/sites are already asking for, and
the one new `DerivationRef` shape (`when_true`/`when_false`, each
either a literal or a declared `deps` name) everything else in this
tier either reuses or doesn't need. Condition is a `PredicateRef`,
already fully specified by `PREDICATE_REGISTRY` -- no new predicate
vocabulary required. Proposal: §7.1.

### v0.072, Tier 3 stage 3 -- `Derive.select` (PLANNED)

Chained `(predicate, value)` pairs plus a default -- the N-branch
follow-on to `Derive.if_`. Ships only once `Derive.if_` has real
usage to generalize the common branch count from, per the proposal's
own note against guessing it up front. Proposal: §7.2.

### v0.072, Tier 3 stage 4 -- Date/time arithmetic and formatting (PLANNED, gated)

`date_add`/`date_diff` (closed unit argument: `"days"`/`"hours"`/...,
the same closed-choice-not-raw-string shape `compare`'s `op` already
establishes) and `format_date` (closed format-token argument, never a
user-supplied strftime/ICU pattern string). **Flagged for explicit
maintainer sign-off before implementation** -- locale/timezone/
calendar-system scope risk means this could grow into its own
`Intl.DateTimeFormat`-shaped subsystem rather than stay a one-file
registry addition, and that scoping question needs settling before
any code is written. Not started pending that sign-off. Proposal:
§7.4.

## Cross-references

- `docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md` -- source
  proposal; §7 is this ladder's catalog, §10 is the suggested
  ordering this ladder follows for stages 2-4.
- `docs/Foundational/DESIGN-NOTES.md` -- design record ("JS vocabulary ladder")
  of the sibling ladder for Tier 1/Tier 2/§6, DONE as of `v0.070`; its
  staging file is retired.
- `PROGRESS.md` -- Snapshot table rows for `v0.071` (stage 1) and
  `v0.072` (stages 2-4).
- `CHANGELOG.md` -- the `list_at` entry, slotted `v0.071`.
