# `arklight search --retrieve-doc`: Doc-Tree Retrieval From the Existing Search Command

## Status

**Accepted -- shipped as `v0.064`; see `docs/version history/v0.064.md`.**
Follows the format and conventions of
[`docs/Proposals/ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`](ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md).
The content below is left as filed -- it's the design record this
proposal was accepted on -- and is not rewritten to reflect
in-progress implementation detail; see the addendum above for the
current landing order and status.

**A version-number note, kept for history:** this proposal originally
disclaimed targeting `v0.064` (the currently installed version at
filing time was `0.062`, and `v0.064` was already reserved for JS
vocabulary addendum stage 4). At acceptance, a maintainer chose to
interleave this proposal into `v0.064` anyway rather than push every
later reserved slot down by one -- the same "two pieces of work, one
milestone" precedent `v0.041` already set. The JS vocabulary addendum
stage 4 work `v0.064` was already reserved for is unaffected; the two
are independent and simply share a slot. See §6.

**Origin:** a request to add a way for `arklight search` to return
project documentation -- starting from the doc tree's own index, and
drilling into a specific folder and then a specific file from there --
without leaving the terminal or knowing `docs/`'s folder layout by
heart.

## TL;DR

A new `--retrieve-doc` flag on the existing `arklight search`
subcommand (`arklight/cli/search.py`, wired in `arklight/cli/main.py`)
that switches `search` from component-schema lookup into **doc-tree
retrieval** mode. Three flags, stackable, each narrowing the previous:

```bash
arklight search --retrieve-doc                        # docs/README.md (the root index)
arklight search --retrieve-doc index                   # same as above, explicit
arklight search --retrieve-doc --foundational           # docs/Foundational/README.md (that folder's index)
arklight search --retrieve-doc --foundational --file architecture   # + docs/Foundational/ARCHITECTURE.md, appended
```

- No dir flag, no `--file` -> prints the **root** `docs/README.md`,
  plus a short "how to go deeper" footer listing the available `--<dir>`
  flags. This is the "readme plus extra how to get them" behavior.
- A dir flag alone (`--foundational`, `--proposals`, etc.) -> prints
  that folder's own `README.md` index, plus a footer listing the
  `--file` names available inside it.
- A dir flag **and** `--file NAME` -> prints the folder's index *and*
  the named file's full contents, in one scrollable output, separated
  by a rule -- "appended... and prints \[it\] in the terminal as
  \[the\] output," per the request that prompted this.

Nothing here touches the compiler, the IR, or generated output -- like
`arklight search`'s existing component-lookup mode and
`ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`'s `assistant` subcommand, this is
a dev-time CLI convenience, entirely read-only over files already in
the repo.

## 1. Why this belongs on `search`, not a new subcommand

`arklight search <name>` is already ARKlight's "look something up
without opening a file" command -- read-only reflection over
`SCHEMA`, typo-tolerant ranking, no side effects unless `--accept` is
passed (`arklight/cli/search.py`'s own module docstring). Doc
retrieval is the same shape of task pointed at a different corpus:
instead of `SCHEMA` (component names -> `NodeSpec`), it reflects over
`docs/` (folder names -> `README.md` index -> individual files). Reusing
`search` means:

- One mental model ("`arklight search` is where I look things up"),
  not two commands that both mean "find me something."
- The existing `--limit`/typo-tolerant machinery
  (`arklight.search.engine.default_engine()`) is *right there* to
  reuse for "did you mean" on a mistyped `--file` value (§4.3) --
  standing up a second, parallel fuzzy-matcher for docs would
  duplicate what `_suggest()` already does for component names.
- It matches the precedent `ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`
  already set for *not* reflexively reaching for a new subcommand: that
  proposal's `arklight assistant` is a genuinely different
  interaction shape (an open-ended conversational session). Doc
  retrieval isn't -- it's one deterministic lookup per invocation,
  exactly like today's `arklight search Picture`, so it belongs next
  to that, not next to `assistant`.

This proposal is deliberately scoped narrower than
`ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`: Raeliana (if built) answers
open-ended questions by drawing from the doc tree and synthesizing;
`--retrieve-doc` does no synthesis at all -- it prints exact,
unmodified file contents, nothing invented, nothing summarized. The
two are complementary, not competing: `--retrieve-doc` is a fast,
deterministic "just show me the file" path that would remain useful
even if `arklight assistant` is later built and accepted.

## 2. Command surface

```bash
arklight search --retrieve-doc
arklight search --retrieve-doc index
arklight search --retrieve-doc --foundational
arklight search --retrieve-doc --proposals
arklight search --retrieve-doc --foundational --file architecture
arklight search --retrieve-doc --proposals --file url-state-as-primitive
```

- `--retrieve-doc` -- the mode switch. Mutually exclusive with the
  existing `name` positional (component lookup) and `--serve`, the
  same way `--serve` is already mutually exclusive with `name`
  (`_cmd_search`'s existing check in `arklight/cli/main.py`). The only
  positional value accepted alongside it is the literal `index` (§3),
  reserved for future full-tree lookups (§7).
- One **directory flag**, optional, choosing which lifecycle folder to
  look in -- mutually exclusive with each other (`argparse`
  `add_mutually_exclusive_group`), mirroring `docs/README.md`'s own
  Folder Guide one-for-one:

  | Flag | Folder |
  | --- | --- |
  | `--foundational` | `docs/Foundational/` |
  | `--backends` | `docs/Backends/` |
  | `--proposals` | `docs/Proposals/` |
  | `--implementation` | `docs/Implementation/` |
  | `--js-backend` | `docs/new js backend proposal/` (removed later, along with its folder) |
  | `--far-future` | `docs/Far Future Concern/` |
  | `--version-history` | `docs/version history/` |

- `--file NAME`, optional, **requires** a directory flag (§4.4) --
  selects one file inside that folder by its filename stem, matched
  case-insensitively with spaces/hyphens/underscores normalized (so
  `--file architecture`, `--file Architecture`, and
  `--file ARCHITECTURE` all resolve to `ARCHITECTURE.md`; see §4.3 for
  why this is a value flag and not one boolean flag per file).

`--limit`, `--near`, and `--accept` are component-lookup-only flags
and have no meaning here; passed alongside `--retrieve-doc` they print
a short stderr notice that they were ignored, the same "explain what
happened, don't silently drop it" posture `_cmd_search` already uses
for `--accept` on a non-exact match.

## 3. Root retrieval: `--retrieve-doc` alone, or with `index`

```
$ arklight search --retrieve-doc
```

Prints `docs/README.md` verbatim, followed by a footer block:

```
---
Go deeper with a folder flag:
  --foundational      permanent design record (architecture, design notes, ...)
  --backends          per-backend staging docs (desktop, android, neutralino, ...)
  --proposals         unsettled proposals awaiting a decision
  --implementation    staged implementation ladders for accepted proposals
  --js-backend        competing new-JS-backend architecture proposals
  --far-future        speculative/backlog backend material
  --version-history   per-milestone shipped-feature summaries

Then add --file NAME to print one file from that folder in full.
Example: arklight search --retrieve-doc --foundational --file architecture
```

`arklight search --retrieve-doc index` is defined to be **identical**
to the bare form above -- `index` is accepted as an explicit,
self-documenting way to say "the root index," for scripts or muscle
memory that prefer not to rely on an implicit default. Any other
positional value alongside `--retrieve-doc` (without a dir flag) is
rejected for now (§7 covers why this is deliberately left for a
follow-up rather than accepted silently).

## 4. Folder retrieval: a directory flag, with or without `--file`

### 4.1 Directory flag alone

```
$ arklight search --retrieve-doc --foundational
```

Prints that folder's own `README.md` (`docs/Foundational/README.md`)
verbatim -- every lifecycle folder in `docs/` already has one, per
`docs/README.md`'s Folder Guide ("Each subfolder now has its own
`README.md` with a fuller overview and index"), so this needs no new
content, only a lookup table from flag to path. Followed by the same
kind of footer as §3, scoped to that folder's own files:

```
---
Files in docs/Foundational/ (use --file NAME):
  architecture              High-level system design: parsing, IR, backend rendering.
  configurability           The "reachability rule" for constant -> kwarg/CLI-flag growth.
  deployment-cli             The arklight CLI: build/deploy workflows and commands.
  design-notes               Rationale and trade-offs behind key design decisions.
  experimental-apis          Unstable/opt-in APIs and their stability guarantees.
  system-design-agreements   The "compiler first, runtime last" design agreement.
  user-defined-components    User-defined components: props, styling, registry modes.
```

The right-hand descriptions are the same "Covers" column text already
in each folder's `README.md` index table -- reused, not
re-authored, so there is exactly one place (the `README.md` itself)
that has to stay accurate, matching the "every fact should live in
exactly one of them" rule `docs/README.md`'s "Adding a new doc"
section already states for the doc tree generally.

### 4.2 Directory flag + `--file`

```
$ arklight search --retrieve-doc --foundational --file architecture
```

Prints `docs/Foundational/README.md`, then a visual separator, then
the full contents of `docs/Foundational/ARCHITECTURE.md` -- both to
stdout, in one output, in that order:

```
<... docs/Foundational/README.md contents ...>

================================================================================
docs/Foundational/ARCHITECTURE.md
================================================================================

<... docs/Foundational/ARCHITECTURE.md contents ...>
```

No footer after the file body -- once a specific file has been
printed, there's nothing further to "go deeper" into; the person has
what they asked for. (Whether a file that itself links to others, like
`ARCHITECTURE.md`'s cross-references, should surface those links as
suggested next `--file` values is an open question, §7.)

### 4.3 Why `--file NAME` is one value flag, not one boolean flag per file

The request that prompted this proposal used `--architecture` as the
example spelling. That reads naturally for one file, but doesn't scale
as written: `docs/Foundational/` alone has seven files, and the full
tree (§2's table) has more than thirty non-`README.md` files today,
growing every time a proposal is accepted and graduates into
`Implementation/` or `Foundational/`. A dedicated boolean per file
means every new doc file requires an `argparse` change in
`arklight/cli/main.py` just to become reachable -- the same "grows
without bound" problem `docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md`
flags for other unbounded catalogs. `--file NAME` is the one-flag
equivalent of the same idea: the *directory* flags stay as named
booleans because that set is small and stable (it's the lifecycle
folder list, which changes rarely and deliberately, per
`docs/README.md`'s own Folder Guide), while the *file* selector inside
a folder stays a value flag because that set is neither small nor
stable.

### 4.4 Why `--file` requires a directory flag

Filenames are not guaranteed unique across folders forever (nothing
stops two future docs in different folders from both being named, say,
`DESIGN-NOTES.md`), and resolving `--file` against the whole tree
without a folder to scope it to would mean silently picking one on a
collision -- exactly the kind of implicit, unannounced tie-break this
project's "fail loudly, stay inspectable" posture
(`docs/README.md`'s Philosophy section) argues against. `--file`
without a preceding directory flag is a hard error:

```
$ arklight search --retrieve-doc --file architecture
arklight search: --file requires a folder flag (--foundational, --proposals, ...). ARCHITECTURE.md lives in docs/Foundational/ -- try --foundational --file architecture.
```

The error message names the folder(s) a case-insensitive match for
`NAME` was actually found in (reusing the same lookup table `--file`
itself resolves against), so the fix is one copy-paste away rather
than a guessing game.

## 5. Relationship to the existing typo-tolerant search pipeline

`arklight search <name>`'s component lookup already falls back to
`SearchEngine.search()` (retrieval -> structural importance ->
ranking) on a miss, rather than a hard error
(`arklight/cli/search.py`'s `_suggest`). This proposal's MVP (§6, stage
1) keeps doc-name matching deliberately simpler -- exact,
case-insensitive, punctuation-normalized stem matching only, per §4 --
but an unmatched `--file` value should still fail the same way
component lookup does: not a bare "not found," but a short
"did you mean" list, computed with plain string-similarity
(`difflib.get_close_matches` against that folder's filename stems) as
a starting point. Whether to eventually route this through the same
`SearchEngine` component-ranking pipeline `_suggest()` already uses
(so a typo in a doc name benefits from the same structural-importance
signal a typo in a component name does) is left as a possible later
refinement, not required for an initial landing -- see §7.

## 6. Scope

### In scope (this proposal)

- The `--retrieve-doc` mode switch on `arklight search`, mutually
  exclusive with `name` (except the literal `index`) and `--serve`.
- Root retrieval: bare `--retrieve-doc` / `--retrieve-doc index` ->
  `docs/README.md` + footer (§3).
- The seven directory flags in §2's table, one per existing lifecycle
  folder, each printing that folder's own `README.md` + a
  files-available footer when given alone (§4.1).
- `--file NAME`, scoped to a preceding directory flag, appending one
  file's full contents after the folder index (§4.2), with the
  matching rules and error behavior in §4.3-4.4.
- A basic "did you mean" fallback on an unmatched `--file` value (§5),
  scoped to `difflib`-level matching for this stage.
- Root `README.md`'s CLI section and `docs/Foundational/DEPLOYMENT-CLI.md`
  updated to document the new flags, following the existing
  `arklight search` entry's format.

### Explicitly out of scope for this proposal

- **Routing `--file` typo suggestions through `SearchEngine`'s full
  ranking pipeline** (structural importance, usage history) rather
  than plain `difflib` -- a possible follow-up once the simpler
  version has shipped and it's clear the extra machinery is worth it
  for a corpus this much smaller than the component schema (§5, §7).
- **Full-tree retrieval by file name alone, without a directory
  flag** -- i.e. `arklight search --retrieve-doc architecture`
  resolving `ARCHITECTURE.md` by searching every folder. Deferred to
  §7 pending a decision on collision handling once/if filenames ever
  do collide across folders.
- **Synthesis, summarization, or Q&A over doc contents.** This
  proposal only ever prints exact, unmodified file bytes -- anything
  resembling "answer my question by drawing from multiple docs" is
  `ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`'s territory (§1), not this
  proposal's.
- **Any change to `arklight build`'s output, the IR, or anything
  shipped to a visitor's browser.** Same as
  `ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md` §5: exclusively a
  developer-facing CLI convenience, no interaction with "the browser
  never executes Python" / "no eval" (`docs/README.md`'s Philosophy
  section), since nothing here ships to compiled output.
- **A frozen version number at filing time.** As noted in Status
  originally, this proposal did not reserve `v0.064` or any other slot
  when filed -- that was a maintainer decision made at acceptance
  time, which assigned it `v0.064`, interleaved with the JS vocabulary
  addendum stage already reserved there, per the updated Status note
  above.

## 7. Open questions for a maintainer

- **Full-tree lookup without a directory flag** (§6, out of scope for
  this stage): once filenames are unique enough in practice to make
  this safe, is a bare `arklight search --retrieve-doc <file-stem>`
  (no dir flag) worth adding as a shortcut, with the current
  dir-flag-required form staying available for the explicit/scripted
  case? This proposal leans toward "yes, as a stage-2 follow-up" but
  takes no final position.
- **Should a printed file's own cross-references become suggested
  next `--file` values** (§4.2's parenthetical) -- e.g. after printing
  `ARCHITECTURE.md`, noting "this file also links to `DESIGN-NOTES.md`,
  try `--file design-notes`"? Would need a lightweight
  markdown-link-to-sibling-file scan, not full link resolution.
- **Should `--retrieve-doc` output go through a pager** (like `less`)
  when stdout is a TTY, the way `git log`/`git diff` do, given some of
  these files (e.g. `CHANGELOG.md`-adjacent ones) are long? This
  proposal assumes plain `print()` to stdout for the first landing,
  consistent with every other `arklight search` output today, but
  flags pager support as a nice-to-have rather than deciding it here.
- **Root `README.md` and `CHANGELOG.md`/`PROGRESS.md` retrieval** --
  should a folder-flag-equivalent exist for the three files that live
  at the repo root rather than under `docs/` (e.g. `--changelog`,
  `--progress`, or treating `--retrieve-doc` with no dir flag as
  already covering `README.md` per §3, but leaving `CHANGELOG.md`/
  `PROGRESS.md` unreachable through this flag entirely)? This proposal
  takes no position and leaves it for a maintainer to decide alongside
  acceptance.
