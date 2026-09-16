# `arklight assistant`: An In-CLI Docs & FAQ Companion (Raeliana)

## Status

**Proposal — not yet accepted, not yet staged.** Follows the format
and conventions of
[`docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md`](JS-VOCABULARY-EXPANSION-PROPOSAL.md).
Per `docs/Proposals/README.md`'s own definition, this describes
something that does not exist yet, may never be built as written, and
could be rejected outright.

**Origin:** the doc tree (`docs/`) has grown large enough — five
lifecycle folders, each with its own `README.md` index, per
`docs/README.md`'s Folder Guide — that "which file answers my
question" is itself becoming a support burden. This proposes a `arklight
assistant` subcommand that answers that question from inside the CLI
someone is already running, instead of sending them out to grep the
repo or open eight tabs.

## TL;DR

A new `arklight assistant` subcommand, off by default and entirely
inert until explicitly invoked, that launches a small conversational
companion — named **Raeliana** — scoped to one job: helping the person
running `arklight` find and understand the right doc, FAQ answer, or
CLI flag. Two flags gate its two independently-shippable pieces:

- `--wake-up-raeliana` — starts the assistant and prints its
  introduction. This is the whole feature in its smallest useful
  form: a scoped, doc-grounded Q&A session, nothing persisted anywhere
  once the process exits.
- `--activate-memory` — a **separate, opt-in** flag that lets a
  session remember things about *this* project across runs (past
  questions, which doc areas a person keeps landing on, notes they
  asked Raeliana to remember). Off by default; `--wake-up-raeliana`
  alone never writes anything to disk. Proposed as its own follow-up
  stage, not bundled into the first landing (see §6).

Nothing here touches the compiler, the IR, or generated output —
this is a dev-time CLI convenience, same category as `arklight search`
and `arklight live-streaming`, not a runtime feature.

## 1. Why this is a CLI concern, not a docs-restructuring concern

`docs/README.md` already solved "where does a fact live" for
*writing* docs — the five-folder lifecycle table, the "does this fact
already have a home" rule. What it hasn't solved is *retrieval* for
someone who doesn't already know the folder structure: a person
running `arklight build` and hitting a validation error doesn't know
whether the answer is in `Foundational/DESIGN-NOTES.md`,
`Foundational/EXPERIMENTAL-APIS.md`, or a `Proposals/` doc that hasn't
shipped yet. Today that's a `grep -r` or a folder-by-folder skim.

This proposal doesn't change where docs live or how they're indexed —
it adds a CLI-native way to query the index that already exists,
surfaced at the moment someone is already at a terminal running
`arklight`.

## 2. Command surface

```bash
arklight assistant --wake-up-raeliana
arklight assistant --wake-up-raeliana --activate-memory
```

Consistent with every other subcommand in the root `README.md`'s CLI
section: a subcommand name, flags that are off unless named, no
behavior change to any existing command. `arklight assistant` with
neither flag prints short usage and exits — same "inert until asked"
default as `arklight live-streaming`'s dev-only posture.

## 3. `--wake-up-raeliana` — the assistant itself

On `arklight assistant --wake-up-raeliana`, the CLI prints a short
introduction before handing control to an interactive prompt:

```
$ arklight assistant --wake-up-raeliana

Hi, I'm Raeliana. I'm here to help you find your way around
ARKlight's docs -- architecture, the CLI, proposals, FAQ, whatever
you're stuck on. I don't write or change any of your project files.
Ask me anything, or type `exit` to leave.

> why does arklight query params live in Proposals and not Foundational?
```

Design constraints on this surface, matched to the CLI's existing
tone (`arklight search`'s typo-tolerant "did you mean" behavior,
`arklight new --explain-architecture`'s guidance-printing, rather than
a generic chatbot skin):

- **Scoped, not general-purpose.** Raeliana answers questions about
  *this* project — its docs, its CLI, its FAQ — not general
  programming questions. A question outside that scope gets a short,
  honest "that's outside what I can help with here" rather than a
  best-effort guess dressed up as project knowledge.
- **Grounded in the doc tree, not invented.** Answers are drawn from
  `docs/` (and `README.md`, `CHANGELOG.md`, `PROGRESS.md`) as they
  exist in the checked-out branch, with the source file named so the
  answer is checkable — the same "point to the canonical file, don't
  restate it" norm `docs/README.md`'s "Adding a new doc" section
  already asks of every doc author, applied to Raeliana's answers
  too.
- **Never edits project files.** No file writes, no `arklight build`
  invocation, no side effects on the project — a read-only companion
  over the docs, matching `arklight search`'s read-only posture over
  the component registry.
- **Leaves cleanly.** `exit`, `quit`, or `Ctrl-C` ends the session
  with no state left behind unless `--activate-memory` was also
  passed (§5).

### 3.1 The persona

Raeliana is a **female-presenting voice and name**, consistently
applied — the same "pick one persona and hold it" principle general
system-prompt design guidance converges on: an assistant that
sometimes drops the persona reads as less predictable and less
trustworthy, not more flexible. Concretely, that means the same name,
the same voice, and the same self-introduction every time
`--wake-up-raeliana` is passed, rather than a persona that only shows
up in the banner and vanishes in the actual answers.

A first working system prompt for Raeliana:

> You are Raeliana, ARKlight's in-CLI assistant. Your job is to help
> the person running `arklight` understand ARKlight's documentation,
> answer their FAQ, and be a clear, friendly, honest presence while
> they work — nothing more. Answer only from ARKlight's own docs,
> README, CHANGELOG, and PROGRESS files as they exist in the current
> checkout; name the file you're drawing from so the person can go
> check it themselves. If something isn't documented yet, say so
> plainly instead of guessing. You don't write or edit project files,
> you don't run builds, and you don't have opinions about undecided
> proposals beyond what the proposal doc itself says. Keep answers
> short and direct first, and offer to go deeper only if asked.

This is a starting sketch, not a final spec — the exact wording is
implementation detail a maintainer should be free to iterate on
without that requiring a new proposal, same as `DEPLOYMENT-CLI.md`
treats CLI copy as implementation detail under the frozen command
shape.

### 3.2 What "helpful presence" rules out

Worth stating explicitly, since it's an easy scope-creep target once
the assistant exists at all:

- No opinions on unsettled `Proposals/` content beyond summarizing
  what the doc itself argues — Raeliana explains a proposal, it
  doesn't advocate for or against one on a maintainer's behalf.
- No silent fallback to general knowledge when the doc tree doesn't
  cover something. A confident wrong answer is worse than "that's not
  documented yet."
- No file writes, ever, from `--wake-up-raeliana` alone.

## 4. `--activate-memory` — opt-in, separate, off by default

Session memory — Raeliana recalling past questions, or notes a person
explicitly asks it to remember, across separate `arklight assistant`
invocations — is real, useful, and *not* the same feature as §3. It's
proposed here as its own gated flag so the two can land, be reviewed,
and be trusted independently:

- **Off by default.** `arklight assistant --wake-up-raeliana` alone
  never touches disk. Memory only activates when `--activate-memory`
  is passed explicitly, every time — not a one-time setup step that
  silently stays on.
- **Local-first, project-scoped.** If built, memory would live
  somewhere like `.arklight/assistant/` next to the project (mirroring
  how per-workspace CLI state is conventionally kept beside the
  project rather than in a global user directory), never uploaded
  anywhere, and easy to point to and delete — a person should be able
  to `rm -rf .arklight/assistant/` and be back to zero state.
- **Legible, not a black box.** Whatever gets remembered should be
  inspectable as plain text/JSON a person can open and read, not an
  opaque store — consistent with `docs/Foundational/DESIGN-NOTES.md`'s
  broader "fail loudly, stay inspectable" posture for the project as
  a whole (`docs/README.md`'s Philosophy section).
- **No project source or secrets.** Memory is scoped to the assistant
  session itself (questions asked, doc areas visited, explicit
  "remember this" notes) — never a copy of project source files,
  environment variables, or anything from `arklight.config.py`.

### 4.1 Why this is deliberately a separate flag, not a default-on feature

Two independent reasons, not just one:

1. **Trust is earned per-capability.** A read-only Q&A companion and
   a companion that persists data about a person's usage across runs
   carry different risk profiles even when both are "just local
   files." Gating them separately means accepting §3 doesn't
   implicitly accept §4.
2. **It's genuinely a separate implementation stage.** §3 requires no
   new persistence layer at all. §4 requires one — a storage format,
   a read/write path, a clear-and-reset command. Bundling them would
   force the smaller, lower-risk feature to wait on the larger one's
   design review, the same reason
   [`docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md`](URL-STATE-AS-PRIMITIVE-PROPOSAL.md)
   §3.5 flags its one genuinely-new-surface stage separately from the
   stages that fall out of existing patterns.

## 5. Scope

### In scope (this proposal)

- `arklight assistant` subcommand, inert with no flags (prints usage).
- `--wake-up-raeliana` — read-only, doc-grounded Q&A session as
  described in §3, no persistence.
- `--activate-memory` — opt-in flag description and the persistence
  properties it must have (§4), as a design contract for a *later*
  implementation stage — not full storage-format spec work, which
  belongs in a follow-up staging doc once this is accepted.
- The system-prompt sketch in §3.1, explicitly marked as iterable
  implementation detail rather than a frozen spec.

### Explicitly out of scope for this proposal

- **The actual model/backend Raeliana runs on** (local model, hosted
  API, which provider) — an implementation decision for the staging
  doc, not a design question this proposal needs to settle.
- **Building `--activate-memory`'s storage layer.** This proposal
  defines the contract (§4); the storage format, migration story, and
  exact on-disk layout are follow-up work, mirroring how
  `docs/Implementation/` docs turn an accepted proposal into a staged
  ladder.
- **Any change to `arklight build`'s output, the IR, or anything
  shipped to a visitor's browser.** This is exclusively a
  developer-facing CLI convenience — it has no interaction with the
  "browser never executes Python" / "no eval" guarantees
  `docs/README.md`'s Philosophy section states, since nothing here
  ships to compiled output.

## 6. Suggested order

1. `arklight assistant --wake-up-raeliana` as the smallest useful
   slice — no persistence, no new storage format, pure read-only Q&A
   over the existing doc tree.
2. `--activate-memory`, staged separately per §4.1, once the storage
   contract in §4 has its own design pass.

## 7. Open questions for a maintainer

- Should Raeliana's answers be strictly retrieval-grounded (only ever
  quoting/pointing at doc files) or allowed limited synthesis across
  multiple docs (e.g. answering a question `docs/README.md`'s index
  doesn't directly answer, but whose pieces exist across two files)?
  This proposal leans toward starting strictly retrieval-grounded and
  loosening later, but takes no final position.
- Where `.arklight/assistant/` (or wherever `--activate-memory` writes
  to) should sit relative to the existing `.gitignore` conventions —
  should it be gitignored by default so a person's question history
  doesn't end up committed to the repo by accident? This proposal
  assumes yes but flags it for an explicit decision rather than
  assuming silently.
