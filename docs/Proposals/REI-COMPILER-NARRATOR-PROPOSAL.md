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
flag on every invocation. On a schema violation specifically (an
unknown component type or a prop-shape mismatch), Rei's narration of
the failure appends one fixed line pointing at the real tool that
already resolves it -- `arklight search <name>` -- the same
"terse diagnostic plus a pointer to a real tool" pattern `rustc`
already uses (`try `rustc --explain E0308``), not a hint she invents
on the spot (§5). That's the entire feature.

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

## 5. On a schema violation, point to `arklight search <name>`

When a build narrated with `--narrate` fails on a `ValidationError`
that names a specific component type against
`arklight.ir.schema.SCHEMA` -- either an unrecognized type
(`"Unknown component type 'Pciture' at ..."`,
`arklight/ir/validate.py`'s two `SCHEMA.get(node.type) is None`
sites) or a known type with a prop-shape violation (e.g. a missing
required prop) -- Rei's narration of that failure appends one fixed
line naming the exact, already-existing tool that resolves it:

```
[Rei] Compilation halted.

[Rei] Unknown component type 'Pciture' at pages/home.py:12.

Try: arklight search Pciture
```

`arklight search <name>` (`arklight/cli/search.py`) already does
the real work here -- exact lookup against `SCHEMA` on a hit, and
the existing typo-tolerant ranking pipeline
(`arklight.search.engine`) on a miss, which is precisely the "does
`Picture` take `sources=` or `srcs=`" job that module's own
docstring describes. Rei does not re-implement, call into, or wrap
that pipeline herself -- she has no typo-correction logic of her own
and never guesses a corrected name. The line she prints is a fixed
template with the *literal* offending name substituted in, taken
directly from the same `node.type` (or component name) the
`ValidationError` already carries -- the same "explain compiler
facts, never invent them" boundary the rest of this proposal holds
her to (§4's determinism requirement, and the original concept
sketch's "Rei may not invent" rule this proposal inherits). Compare
`rustc`'s own pattern: a terse diagnostic plus a fixed
`For more information about this error, try `rustc --explain E0308`.`
line -- a pointer to a real tool, not an explanation generated on
the spot.

**This is not Rei becoming a conversational assistant.** She prints
exactly one line, once, using the error's own data; she does not run
`arklight search` for the user, does not show its output inline, does
not answer "why is this wrong," and takes no follow-up input. That
boundary is deliberate and matches this document's own §6 scope
limits below.

**Scope of this pointer, deliberately narrow:** only the SCHEMA-backed
errors above. Validation failures against a *different* registry --
unknown `on_click`/`Action.*` name, an undeclared `Bind`/`State`
target, an unknown modifier -- are not schema-lookup problems, and
`arklight search` doesn't cover them (it reflects `SCHEMA` only, not
`ACTION_REGISTRY`/`BEHAVIOR_REGISTRY`/`PREDICATE_REGISTRY`/
`DERIVATION_REGISTRY`). Rei narrates those failures the same way §3-
§4 already describe, with no tool pointer appended, rather than
printing a command that wouldn't actually help. Extending
`arklight search` itself (or adding an equivalent lookup) to cover
those other registries, so a future version of this pointer could
cover them too, is explicitly out of scope for this proposal -- see
§7.

## 6. Relationship to Raeliana and Miko

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

## 7. Explicitly out of scope

Everything the earlier, unfiled draft described beyond §1-§5 above:
a structured compiler event bus or event-ID scheme, a diagnostic
object redesign, `--trace` / machine-readable event output, a
`--plain` sub-mode of `--narrate` (there is exactly one narrate
style; a plainer alternative is just `--verbose` or no flag), an
`arklight explain <event-id>` subcommand, IDE integration, and any
notion of multiple narrator personalities. Also out of scope: any
tool pointer beyond §5's single, fixed
`Try: arklight search <name>` line -- no pointers for
action/behavior/predicate/derivation-registry errors (§5's own scope
note), no other suggested commands for any other failure category,
and no extension of `arklight search` itself to cover those other
registries (that would be its own proposal, on its own merits). None
of this is committed. If any of it is wanted later, it needs its own
proposal, filed and accepted on its own terms -- not treated as an
implicit stage 2 of this one.

## 8. Open questions for a maintainer

- Exact wording/tone for each stage's narrated sentence(s) -- left to
  implementation (`docs/Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md`),
  not fixed by this proposal.
- Whether `--narrate` should also cover `arklight pack`/`unpack`/
  `pwa`/`android`/`desktop`'s own build-adjacent output, or stay
  scoped to `arklight build` only for this first landing. This
  proposal assumes `arklight build`-only and leaves the rest for a
  future follow-up.
