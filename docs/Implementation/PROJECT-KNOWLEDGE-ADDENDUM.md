# Project Knowledge Addendum: Staged Order, v0.071 -> v0.078

**Status:** PLANNED -- stages 1-8 (`v0.071`-`v0.078`) not yet started.
This file turns the accepted
[`PROJECT-KNOWLEDGE-PROPOSAL.md`](PROJECT-KNOWLEDGE-PROPOSAL.md) into a
trackable, eight-rung landing order, the same role
`JS-VOCABULARY-ADDENDUM-v0.070.md` plays for the JS vocabulary
addendum and `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md` plays
for the Android backend's staging list. It does not restate that
proposal's reasoning; it exists to turn "here's a suggested order"
(the proposal's own §19) into "here's the version each rung ships
under."

## Scope filter: what's in this ladder, and what isn't

Every rung below comes directly from the proposal's own §19
"Suggested order," unchanged in sequence -- this ladder only attaches
a version number to each of the eight steps already listed there. The
proposal's §18 "Scope" section is the acceptance boundary this ladder
inherits wholesale:

- **In scope:** `.arklight/` as a compiler-owned, plain-text,
  inspectable project-local directory; the Project Knowledge
  providers/facts/observations model; Git as the first (and, for this
  ladder, only) external knowledge provider; persistence of derived
  compiler knowledge across builds; compiler-owned build history;
  safe behavior when `.git/` is absent; safe deletion/regeneration of
  `.arklight/`.
- **Out of scope, on purpose:** implementing Git or a Git-compatible
  VCS, any write access to `.git/`, GitHub API integration, remote
  repository access, a required database, AI-generated diagnostics,
  full incremental compilation, and everything else the proposal's
  §18 lists under "Explicitly out of scope." Nothing in this document
  authorizes work on any of it; it stays exactly where the proposal
  left it.

Stage 8 (`v0.078`, "Future knowledge providers") is deliberately the
odd rung out: the proposal's own §19 frames it as "add only when a
concrete compiler feature needs them; do not create providers merely
to populate `.arklight/`" -- so unlike stages 1-7, `v0.078` is not a
fixed deliverable with a predetermined feature list. It reserves the
version slot and exists to close the ladder out, not to promise a
specific new provider.

## Why eight versions, not one

ARKlight already has direct precedent for landing one capability as
many small, independently shippable stages rather than one release:
`v0.054` (JS backend reactive core) landed as 8 `vdom-N` stages,
`v0.060` (user-defined components) landed as 5 `stage0`-`stage4`
stages, and the JS vocabulary addendum is landing as the ten-rung
`v0.061`-`v0.070` ladder -- each rolled up into a single milestone
summary only after every stage in it had actually shipped. This
ladder follows the same shape, in the exact order the proposal's own
§19 lays out (foundation first, speculative extension point last):

1. The directory and format marker, with nothing depending on it yet
   (`v0.071`).
2. The internal Project Knowledge abstraction -- providers, facts,
   observations -- as a concept the compiler can hold, still with no
   external provider wired in (`v0.072`).
3. Git as the first concrete provider, read-only (`v0.073`).
4. Writing what Git provided into `.arklight/` so it survives after
   `.git/` is gone (`v0.074`).
5. The first concrete consumer: build history (`v0.075`).
6. Surfacing that knowledge where a developer actually sees it:
   diagnostics (`v0.076`).
7. Deriving observations (plural-build comparisons) from the facts
   and history the earlier stages already persist (`v0.077`).
8. Leaving the door open for later providers, without committing to
   one now (`v0.078`).

## The ladder

### v0.071 -- `.arklight/` foundation

Proposal §19, stage 1. Detect-or-create the directory, establish a
minimal knowledge-format marker (`knowledge_format=1`, per §17), and
provide safe read/write helpers. The format stays human-readable
(§4/§17) and nothing in the compiler depends on the directory's
presence yet -- deleting it must be a no-op for buildability, per the
proposal's core invariant (§2, §21.3).

### v0.072 -- Project Knowledge context

Proposal §19, stage 2. Introduce the internal Project Knowledge
abstraction inside the compiler: the providers/facts/observations
separation from §3, made available through compiler context. No
provider is wired in yet -- this stage is the shape, not the data.

### v0.073 -- Git provider

Proposal §19, stage 3. Detect `.git/`, read repository identity and
working-tree state (head, branch/ref, clean/dirty, shallow-clone
state -- §3.1/TL;DR), and gracefully report unavailable Git state
when `.git/` doesn't exist. Read-only: this stage never writes to
`.git/` (§2's ownership boundary) and nothing is persisted to
`.arklight/` yet -- that's the next stage.

### v0.074 -- Persistent project context

Proposal §19, stage 4. Write the derived Git facts `v0.073` can now
read into `.arklight/`, and preserve them once `.git/` becomes
unavailable (§1's `git clone` / `rm -rf .git` walkthrough is the
worked example this stage exists to satisfy). Stores derived facts
like `last_successful_revision`, not repository objects -- per §14/
§16, no repository object copies and no remote URLs by default.

### v0.075 -- Compiler build history

Proposal §19, stage 5. Record build results, associate them with
whatever source/repository identity is available, and store compiler
version and timestamp (§3.2's `build.result`/`build.compiler_version`
facts). The first concrete consumer of the `.arklight/` write path
`v0.071`/`v0.074` built.

### v0.076 -- Diagnostics integration

Proposal §19, stage 6. Surface compact project knowledge in compiler
error output, add last-known-good information where available, and
keep verbose knowledge behind explicit debug output rather than
ordinary logs (§16's privacy boundary applies here too). This is the
first stage where Project Knowledge becomes something a developer
running `arklight build` actually sees.

### v0.077 -- Historical observations

Proposal §19, stage 7. Compare known build states, identify the last
successful and first recorded failing states, and correlate
repository changes with build transitions -- the §3.3 "observations"
layer (`last_successful_revision`, `changed_since_last_success`,
`current_state_reproducible`), now with real facts and history from
`v0.073`-`v0.075` to derive them from.

### v0.078 -- Future knowledge providers

Proposal §19, stage 8. Not a fixed feature list -- reserves the slot
for whatever provider a later, concrete compiler feature actually
needs, per the proposal's own instruction not to add providers
speculatively. Closes the ladder; anything landing here gets its own
scoped description once a real feature motivates it, rather than
being predetermined now.

## Status tracking

| Stage | Covers | Status |
| --- | --- | --- |
| v0.071 | `.arklight/` foundation | PLANNED |
| v0.072 | Project Knowledge context | PLANNED |
| v0.073 | Git provider | PLANNED |
| v0.074 | Persistent project context | PLANNED |
| v0.075 | Compiler build history | PLANNED |
| v0.076 | Diagnostics integration | PLANNED |
| v0.077 | Historical observations | PLANNED |
| v0.078 | Future knowledge providers (open slot) | PLANNED |

See `docs/version history/v0.071.md` through `v0.078.md` for each
stage's forward-looking, user-facing summary (updated to reflect
actual shipped behavior once a stage lands), and `PROGRESS.md`/
`CHANGELOG.md` for the internal record once work on a stage begins.
