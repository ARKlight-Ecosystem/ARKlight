# Rei: A Compiler Narration Flag for `arklight build`

## Status

**Accepted -- interleaved into `v0.065`'s milestone slot as a third
piece of work, alongside JS vocabulary addendum stage 5 and
`Provider` stage 1 of 6. Staged in
[`docs/Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md`](../Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md).**

**A version-number note, kept for history:** at filing time, `v0.065`
was already the shared slot for two accepted, staged pieces of work
(JS vocabulary addendum stage 5 and `Provider` stage 1 of 6 -- see
`docs/Proposals/PROVIDER-SDK-PROPOSAL.md`). A maintainer chose to
interleave this proposal into `v0.065` as a third piece rather than
push every later reserved slot down by one. This is the same
precedent `v0.041` set (CLI/pipeline hardening + two JS vocabulary
addenda sharing one slot) and `v0.064` repeated (`--retrieve-doc` +
JS vocabulary addendum stage 4) -- see
`docs/Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md`'s own version-number
note for that instance. `v0.065`'s other two pieces of work are
unaffected; all three are independent and simply share a milestone
number.

**Origin and scope note:** an earlier draft of this idea (not filed
in this repo) sketched a much larger system -- a structured compiler
event bus, a formal diagnostic redesign, multiple output modes
(`--explain`, `--explain=verbose`, `--trace`, `--log=shadow`), an
`arklight explain <event-id>` subcommand, IDE integration, and a
seven-stage rollout. At acceptance, a maintainer deliberately
narrowed that down to what's described below: **one CLI flag and one
config line, nothing else.** Anything from the earlier draft not
mentioned in this document (the event schema, a diagnostic-object
redesign, `--trace`, `arklight explain <id>`, IDE integration) is
**not** part of this proposal. Revisiting any of that later needs its
own proposal filed on its own merits, not an assumed extension of
this one.

## TL;DR

A new `--narrate` flag on `arklight build`, sibling to the existing
`--verbose`/`--debug` (`docs/Foundational/CLI-REFERENCE.md`). Instead
of `--verbose`'s `[ARKlight] ...` stage lines, `--narrate` prints the
same pipeline progress as short natural-language sentences, in the
voice of **Rei**, ARKlight's compiler narrator. A new `rei` section in
`arklight.config.py` lets a project pin its own default log mode
(`plain` / `verbose` / `narrate`) so a team doesn't have to type the
flag on every invocation. That's the entire feature.

```bash
arklight build site.py --narrate
```

```python
# arklight.config.py
CONFIG = {
    "rei": {
        "default_mode": "narrate",   # "plain" (default) | "verbose" | "narrate"
    },
}
```

## 1. CLI surface

- `--narrate` -- opt-in, off by default, exactly like `--verbose`.
  Mutually exclusive with `--verbose`/`--debug`: at most one log mode
  wins per invocation, following the same "last flag on the command
  line wins, no silent stacking" rule `docs/Foundational/CLI-REFERENCE.md`
  already documents for `--open`/`--no-open`.
- Narrates the same stage boundaries `--verbose` already prints
  (discovery, component expansion, normalization, validation, IR
  build, each backend's render/postprocess, `raw_postprocess`
  functions, writing files, copying assets) -- no new stages, no new
  compiler hooks. `--narrate` is a second renderer over the exact
  same stage-completion calls `--verbose` already makes in
  `arklight/cli/main.py`'s build path, not a parallel instrumentation
  pass.
- Experimental-feature warnings and alpha-limitation warnings
  (`CLI-REFERENCE.md`'s "Two more things print unconditionally"
  section) are unaffected -- they print exactly as they do today,
  regardless of log mode.

## 2. Config surface

A new `rei` section, added to `arklight/config.py`'s `_KNOWN_SECTIONS`
the same way `live_streaming`/`android`/`desktop` already work (one
line in the schema set, plus whatever module reads it -- see that
module's own docstring on why the schema stays this small and flat):

```python
CONFIG = {
    "rei": {
        "default_mode": "narrate",
    },
}
```

- `default_mode` -- one of `"plain"` (the current, unnamed default
  behavior), `"verbose"`, or `"narrate"`. Sets what a bare
  `arklight build` does for this project without a flag.
- A CLI flag (`--verbose` or `--narrate`) always overrides the config
  default for that one invocation -- the config only changes what
  happens when *no* log-mode flag is passed, the same override
  relationship `--max-width`/`--bg`/etc. already have with
  `Site(...)` kwargs.
- No key means `"plain"` -- a project with no `arklight.config.py`,
  or one with no `rei` section, is completely unaffected. This is an
  opt-in feature end to end: absent from the CLI, absent from config,
  nothing changes.

## 3. First-compile introduction

When `--narrate` is active (via flag or config default) **and** the
build's output directory either doesn't exist yet or exists but is
empty, Rei prints a short introduction and a summary of the active
`rei` config (source: flag or config-file default, and the resolved
`default_mode`) before the first narrated stage line. This is a
one-time-per-fresh-output-directory banner, not a one-time-ever
banner -- deleting or clearing the output directory and rebuilding
shows it again, the same "detect a fresh build from the output
directory's state" signal the rest of the pipeline already has
available (it already knows whether it's writing into an existing
tree). On every build after that first one for a given output
directory, Rei skips the introduction and narrates stages directly.

## 4. Implementation approach

Rei is a **pure-Python, deterministic pattern renderer** -- no JSON,
no config files of her own, no network access, and no LLM. Given the
same stage-completion call, she produces the same sentence, every
time; this is a design requirement, not an incidental property, since
`--narrate` output should be as reproducible as `--verbose` output
already is.

**ELIZA as a studied reference, not a dependency.** The classic ELIZA
pattern-matching technique (keyword/pattern -> templated response,
no understanding, no model) is the right shape for this problem: Rei
never needs to understand a build, only to describe a small, closed
set of known stage-completion events in varied natural-language
phrasing. A reference ELIZA implementation is vendored into the repo
*for study purposes only* -- read as a design reference for how a
minimal pattern/template engine is structured, then set aside. Rei's
actual renderer is an original, custom implementation purpose-built
for compiler stage events (which are structured data, not free text),
not a reuse or adaptation of ELIZA's script-transformation code
itself. Unlike Raeliana (which reads/serializes structured doc-index
data), Rei has no need for JSON or any other serialized data format
at all -- her stage-to-sentence mapping is plain Python data
(dicts/lists of template strings) living in the module that renders
her, which is sufficient for a closed, small vocabulary of build
stages and keeps her free of any runtime dependency beyond the
standard library.

## 5. Relationship to Raeliana and Miko

Unchanged from the original concept sketch's separation, restated
briefly since both those assistants are discussed in
`docs/Proposals/ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`:

- **Raeliana** -- read-only, doc-grounded question answering. Not
  authorized for implementation yet (see that proposal's own status).
- **Miko** -- exploratory, tool-mediated conversation. Staged as
  `v0.079`, not yet built.
- **Rei** -- doesn't converse, isn't asked anything, and isn't
  invoked by name at all from the CLI (`--narrate`/`--verbose` are
  the actual flags; "Rei" is the voice behind `--narrate`'s output,
  the same relationship `docs/README.md`'s Philosophy section has to
  the project as a whole). No shared code, no shared trust model, no
  dependency between any of the three.

## 6. Explicitly out of scope

Everything the earlier, unfiled draft described beyond §1-§4 above:
a structured compiler event bus or event-ID scheme, a diagnostic
object redesign, `--trace` / machine-readable event output, a
`--plain` sub-mode of `--narrate` (there is exactly one narrate
style; a plainer alternative is just `--verbose` or no flag), an
`arklight explain <event-id>` subcommand, IDE integration, and any
notion of multiple narrator personalities. None of this is committed.
If any of it is wanted later, it needs its own proposal, filed and
accepted on its own terms -- not treated as an implicit stage 2 of
this one.

## 7. Open questions for a maintainer

- Exact wording/tone for each stage's narrated sentence(s) -- left to
  implementation (`docs/Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md`),
  not fixed by this proposal.
- Whether `--narrate` should also cover `arklight pack`/`unpack`/
  `pwa`/`android`/`desktop`'s own build-adjacent output, or stay
  scoped to `arklight build` only for this first landing. This
  proposal assumes `arklight build`-only and leaves the rest for a
  future follow-up.
