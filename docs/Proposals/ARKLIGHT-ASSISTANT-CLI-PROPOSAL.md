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

# Addendum: Miko as a Second Assistant

## Status

**Proposal addition — not yet accepted, not yet staged.**

This addendum extends the existing `arklight assistant` proposal with
a second, deliberately different assistant named **Miko**. It does
not replace Raeliana.

Raeliana and Miko serve different purposes:

- **Raeliana** is the reliable secretary: document-grounded, explicit
  about sources, conservative about unsupported claims, and concerned
  primarily with helping a person navigate canonical ARKlight
  documentation.
- **Miko** is the exploratory companion: an LLM-backed assistant that
  can invoke controlled ARKlight knowledge tools to retrieve compiler
  knowledge and then explain the returned result conversationally.

The distinction is intentional. The project should not pretend that
one conversational interface can simultaneously behave like a
deterministic documentation index and a free-form reasoning companion
without making the boundary between those behaviors muddy.

## 8. `--wake-up-miko` — the exploratory assistant

A second wake-up flag is proposed alongside `--wake-up-raeliana`:

```bash
arklight assistant --wake-up-miko
```

The command remains inert unless explicitly requested. It does not
change `arklight build`, generated output, the Website IR, or any
browser/runtime behavior.

On startup, Miko prints her own introduction before accepting
questions:

```text
$ arklight assistant --wake-up-miko

Hi! I'm Miko.
I'm ARKlight's little shrine maiden, and I can use my telekinesis
to reach into ARKlight's compiler knowledge when you ask me
something about the project.

I can look things up, connect the results, and help you think
through what they mean. I can also be wrong, so don't mistake
confidence for a compiler diagnostic.

Ask me something, or type `exit` to leave.

> what does ARKlight currently know about this component?
```

The introduction is intentionally different from Raeliana's. Miko
is not presented as the authoritative project secretary. She is an
interactive reasoning surface that can reach authoritative project
data through controlled tools.

## 9. Miko's telekinesis

Miko's defining mechanism is **tool-mediated access to ARKlight
compiler knowledge**.

"Telekinesis" is the persona name for the capability, not a second
runtime or a magical abstraction inside the compiler. Underneath the
persona, the implementation is an explicit tool-call interface.

Conceptually:

```text
User question
     |
     v
   Miko
     |
     | tool call: retrieve compiler knowledge
     v
ARKlight knowledge providers
     |
     +--> project configuration
     +--> filesystem facts
     +--> Git facts
     +--> build state
     +--> .arklight/ Project Knowledge
     |
     v
structured result
     |
     v
   Miko
     |
     v
human-readable answer
```

Miko should not receive unrestricted access to the project as a
generic filesystem agent. The tool surface should expose specific
read operations whose contracts are defined by ARKlight itself.

Examples of possible sanctioned tools include:

- retrieve the current compiler/project context;
- retrieve a known Project Knowledge fact;
- retrieve an observation from `.arklight/`;
- resolve a component name against compiler knowledge;
- inspect the current build state;
- retrieve relevant project documentation;
- retrieve the compiler's known relationship between a source
  construct and a generated/backend representation.

The exact tool set belongs in implementation staging. The proposal
freezes the architectural property instead:

> **Miko reaches ARKlight knowledge through explicit tool calls, not
> arbitrary shell access or unrestricted code execution.**

## 10. Miko's knowledge boundary

Miko is allowed to reason over information returned by her tools, but
the tool boundary remains authoritative about what project knowledge
she can actually access.

This gives the assistant two distinct layers:

1. **Knowledge layer:** ARKlight-owned providers and Project Knowledge
   return structured, inspectable facts or observations.
2. **Reasoning layer:** Miko's language model interprets those results,
   connects them, explains them, and may form hypotheses.

Miko must distinguish between those layers in her answers.

For example:

> **Known:** the compiler's Project Knowledge says component `Card`
> was previously resolved at a particular revision.
>
> **Interpretation:** that may explain why the current diagnostic
> appears after a source change.
>
> **Uncertain:** Miko cannot claim that the source change caused the
> failure unless the available evidence actually establishes that
> relationship.

The important property is not that Miko never makes mistakes. An
LLM assistant is an LLM assistant; pretending otherwise would be a
particularly elaborate form of documentation debt. The important
property is that project facts have a recoverable source and that Miko
cannot silently turn an unsupported inference into compiler knowledge.

## 11. Persona

Miko is a **female-presenting shrine-maiden persona** with a playful,
clever, energetic, and sometimes overconfident voice.

Her personality is deliberately less formal than Raeliana's. She can
be curious, mischievous, imaginative, and occasionally wrong. That
personality is part of the companion experience, but it must never
change the underlying tool contracts or the distinction between
retrieved facts and generated interpretation.

A first working system-prompt sketch:

> You are Miko, ARKlight's exploratory CLI companion. You are a
> cheerful shrine maiden who can use telekinesis to reach ARKlight's
> compiler knowledge through the tools provided to you. Help the
> person understand the project, investigate compiler knowledge, and
> think through questions using the information those tools return.
>
> Treat tool results as project evidence. Do not invent compiler
> facts, Project Knowledge entries, build state, source locations, or
> implementation details that the tools did not provide. Clearly
> distinguish retrieved facts from your own interpretation or
> hypothesis.
>
> You are not the authoritative documentation secretary. Raeliana
> handles conservative documentation lookup. You are allowed to
> synthesize information from multiple tool results and explain
> possibilities, but you must not present speculation as established
> project knowledge.
>
> You do not edit project files, modify compiler state, execute
> arbitrary shell commands, or invent capabilities that are not
> exposed through your tools. If the available tools cannot answer a
> question, say so.
>
> Be playful and personable, but keep technical answers useful. Your
> personality must never override a tool result or conceal uncertainty.

This is implementation guidance, not a frozen personality script.

## 12. What Miko is allowed to do

Miko's tool access should be deliberately additive to the existing
Project Knowledge architecture rather than creating a parallel
knowledge system.

### In scope

- Read compiler-owned Project Knowledge.
- Read compiler/build observations exposed through sanctioned tools.
- Read relevant project documentation when the tool permits it.
- Combine results from multiple tool calls.
- Explain compiler state and project context.
- Identify uncertainty and distinguish facts from hypotheses.
- Help investigate questions that span documentation and compiler
  knowledge.
- Return concise answers with enough source/context information for
  the user to verify important claims.

### Explicitly out of scope

- Arbitrary shell execution.
- Arbitrary Python execution.
- Arbitrary filesystem traversal outside sanctioned tool contracts.
- Editing source files.
- Editing `.arklight/` knowledge directly.
- Running `arklight build` as an implicit side effect.
- Modifying compiler state.
- Treating an LLM-generated answer as a compiler fact.
- Sending project knowledge to an external service unless a future
  implementation explicitly introduces such a backend and the user
  explicitly enables it.

## 13. Miko and Project Knowledge

Miko is the first proposed consumer that makes the `.arklight/`
Project Knowledge layer conversationally useful.

The intended flow is:

```text
compile
   |
   v
observe
   |
   v
retain
   |
   v
retrieve
   |
   v
Miko
   |
   v
explain
```

This does not make Miko part of the compiler pipeline. Project
Knowledge remains compiler-owned derived knowledge, while Miko is a
consumer of that knowledge.

This separation matters because the compiler must remain able to
build without Miko, and Miko must remain unable to rewrite the
knowledge she is reading.

The `.arklight/` directory therefore remains the source of compiler
knowledge. Miko is an interface to that knowledge, not its owner.

## 14. Miko versus Raeliana

The two assistants should be treated as complementary interfaces,
not competing implementations of the same feature.

| Concern | Raeliana | Miko |
|---|---|---|
| Primary role | Project secretary | Exploratory companion |
| Knowledge source | Docs, README, CHANGELOG, PROGRESS | Controlled compiler-knowledge tools plus docs |
| Reasoning style | Conservative, source-first | Generative, multi-result synthesis |
| Unsupported claims | Refuses / says undocumented | May hypothesize, but must label hypotheses |
| Project Knowledge | Future/limited consumer | Primary proposed conversational consumer |
| Persona | Composed, reliable | Playful, curious, energetic |
| Writes files | No | No |
| Runs builds | No | No |
| Changes compiler state | No | No |
| Arbitrary code execution | No | No |
| Memory | Separate opt-in proposal | Separate future capability |
| Intended question | "What does ARKlight document?" | "What does ARKlight know, and what might it mean?" |

The distinction can be summarized as:

> **Raeliana tells you what the project says. Miko looks at what
> the project knows and helps you think about it.**

Neither assistant should silently inherit the other's authority model.

## 15. Command surface with both assistants

With Miko added, the proposed command surface becomes:

```bash
arklight assistant --wake-up-raeliana
arklight assistant --wake-up-miko
arklight assistant --wake-up-raeliana --activate-memory
arklight assistant --wake-up-miko --activate-memory
```

The exact interaction between `--activate-memory` and Miko should remain
a staging decision. In particular, accepting the memory design for
Raeliana must not automatically imply that Miko receives persistent
memory.

The safer conceptual model is that **wake-up flags select an
assistant, while capability flags explicitly grant additional
capabilities**.

If both wake-up flags are supplied simultaneously, the CLI should
not invent an ambiguous mode. The implementation should reject the
combination with a clear diagnostic unless a future proposal defines
a deliberate multi-assistant mode.

For example:

```text
error: choose one assistant to wake:
  --wake-up-raeliana
  --wake-up-miko
```

## 16. Miko's trust model

Miko's playful personality must not be confused with permission to
fabricate project state.

The project should therefore maintain three explicit categories in
Miko's responses:

- **Retrieved fact** — directly returned by a sanctioned ARKlight
  knowledge tool or canonical project document.
- **Derived explanation** — a conclusion supported by one or more
  retrieved facts.
- **Hypothesis** — a plausible interpretation that is not established
  by the available evidence.

This is especially important for Project Knowledge observations.
For example, an observation such as `changed_since_last_successful`
does not by itself establish why a build failed. Miko may explain the
relationship as a possibility, but she must not silently upgrade an
observation into causality.

The compiler's knowledge model therefore remains stricter than the
language model's conversational model.

## 17. Suggested implementation order

Miko should not block the first Raeliana implementation.

A reasonable staged order is:

1. Ship the smallest read-only Raeliana surface.
2. Establish the compiler-owned Project Knowledge providers and
   retrieval contracts.
3. Expose a minimal read-only tool interface over those providers.
4. Add `arklight assistant --wake-up-miko`.
5. Give Miko only the smallest useful set of sanctioned tools.
6. Verify that tool results remain inspectable and sourceable.
7. Expand the tool vocabulary only when a real project question
   requires it.
8. Treat persistent Miko memory, if ever added, as a separate
   capability with its own design review.

This keeps the assistant from becoming an excuse to prematurely build
a general-purpose agent framework. The compiler owns knowledge; the
assistant consumes it.

## 18. Open questions for Miko

- What exact Project Knowledge providers should be exposed to the
  first Miko tool surface?
- Should documentation retrieval use the same retrieval
  implementation as Raeliana, or should Miko receive a single unified
  `project_knowledge` tool?
- Should tool results carry explicit provenance metadata so Miko can
  cite the provider, fact name, revision, and source path directly?
- Should Miko be permitted to request multiple tool calls
  automatically, or should the first implementation impose a strict
  tool-call budget?
- Should Miko's LLM backend be local-only initially, or should the CLI
  permit an explicitly configured remote provider?
- If a remote model is supported, what project-data disclosure warning
  must be shown before the first tool result is sent?
- Should Miko be able to consume `.arklight/` observations that are
  not intended for human-facing diagnostics, or should the provider
  expose a curated public subset?
- Should Miko have a dedicated `--no-telekinesis` or offline mode, or
  should unavailable tools simply produce an explicit capability
  error?
- Should `arklight assistant` eventually support a shared assistant
  protocol so additional project companions can be added without
  changing the core command structure?

## 19. Proposal boundary

This Miko addition intentionally does **not** define:

- a particular LLM vendor;
- a particular model;
- a network protocol;
- a persistent memory format;
- a general agent framework;
- arbitrary tool execution;
- compiler modifications required solely to satisfy Miko;
- any change to ARKlight's browser runtime;
- any change to the Website IR;
- any native backend behavior.

The architectural proposal is narrower:

> **Miko is an optional, explicitly invoked, LLM-backed CLI companion
> whose "telekinesis" is a controlled tool interface into ARKlight's
> compiler-owned Project Knowledge.**

That keeps the joke at the persona layer and the safety boundary at the
architecture layer.
