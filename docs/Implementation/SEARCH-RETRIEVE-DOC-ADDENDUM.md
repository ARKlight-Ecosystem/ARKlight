# Search Retrieve-Doc Addendum: Single-Version Entry, v0.064

**Status:** SHIPPED, `v0.064`. This file turns the accepted
[`docs/Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md`](../Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md)
into a trackable entry, the same role every other file in this folder
plays for its own proposal -- filed retrospectively, since the feature
itself landed at `v0.064` ahead of this writeup ever existing. See
`docs/version history/v0.064.md`'s own note: the feature "landed ahead
of its own planned `docs/Implementation/SEARCH-RETRIEVE-DOC-ADDENDUM.md`
staging writeup, which was never actually filed." This file closes
that gap -- the dangling reference existed in
[`docs/Proposals/README.md`](../Proposals/README.md),
[`docs/Implementation/README.md`](README.md), and
`docs/version history/v0.064.md` for longer than it should have, with
nothing behind the filename any of them pointed at.

Only one rung, not a ladder, because the accepted proposal was already
a single, self-contained CLI addition -- a new mode on an existing
subcommand, not a multi-piece capability needing its own landing order
the way `JS-VOCABULARY-ADDENDUM-v0.070.md`'s ten rungs or
`PROVIDER-SDK-ADDENDUM.md`'s six do.

## v0.064 -- `arklight search --retrieve-doc` (SHIPPED)

Proposal, in full. A doc-tree retrieval mode on the existing
`arklight search` subcommand, switching it from component-schema
lookup into doc-tree retrieval: read-only, unsynthesized, exact and
unmodified file bytes from `docs/`, nothing invented or summarized.

### What shipped

- **Bare `arklight search --retrieve-doc`** prints the root
  `docs/README.md` index verbatim.
- **A per-folder flag** (`--foundational`, `--proposals`,
  `--backends`, `--implementation`, and the rest of the top-level
  `docs/` folders) prints that folder's own `README.md` index instead
  of the root one.
- **`--file NAME`** appended to either form prints one file's full,
  unmodified contents rather than just its index row -- the only mode
  that returns more than a `README.md`.
- Every mode is read-only against files already in the repository's
  `docs/` tree; nothing is generated, synthesized, or paraphrased on
  the way out.

### Tests

`tests/test_search.py` gained coverage for: bare `--retrieve-doc`
against the root index, each per-folder flag against its own
`README.md`, `--file NAME` against a real file in that folder, and the
error path for a folder flag with no matching `README.md` or a
`--file` name that doesn't exist in it.

## Status tracking

| Stage | Covers | Status |
| --- | --- | --- |
| 1 of 1 | `arklight search --retrieve-doc` (root/folder index + `--file` retrieval) | SHIPPED (`v0.064`) |

See `docs/version history/v0.064.md` for this version's forward-looking,
user-facing summary, and `PROGRESS.md`/`CHANGELOG.md` for the internal
record.
