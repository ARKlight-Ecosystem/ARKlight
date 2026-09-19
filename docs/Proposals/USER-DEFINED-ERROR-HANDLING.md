# User Defined Error Handling: `errhanlib.ARKlight` and the Three-Bracket Directive

## Status

**Proposal -- not yet accepted, not yet staged.** Per
`docs/Proposals/README.md`'s own definition, this describes something
that does not exist yet, may never be built as written, and could be
rejected outright.

**Requested slot: `v0.079`** (the maintainer's number). That milestone
is already reserved in `PROGRESS.md` for `arklight assistant` Miko MVP,
Stage A. This document does not schedule anything; if it is accepted
at `v0.079` it would be interleaved into that slot, the same "make
room for one more" precedent `v0.065` used for Rei and Platform API IR.
That is a maintainer decision (open question 10).

**Origin:** the maintainer's design statement, in one message. Section
"The design, as stated" records it in the maintainer's own terms and
separates it from what this document adds. Everything under "Design
sketch" is **mine**, offered so there is something concrete to accept,
change or kill -- none of it is decided.

## The design, as stated

```python
# include <stdlib.ARKlight>
# include <errhanlib.ARKlight>

# [{Catch What?}] [ARKlight Log] [{error message}]
Site.site(.....)
```

In the maintainer's words, reduced to claims:

1. **Opt-in.** A user chooses to print custom error logs, "in js or
   arklight compiler."
2. **Three brackets are the syntax.** "Three [] is a syntax for user
   defined error handling."
3. **Per function.** The logging is "per function which exists in a
   site made by ARKlight," and is meant to make error logs easy to
   handle.
4. **No collision with Python.** It "doesn't collide with try catch
   method of python." ARKlight owns this representation because it is
   simpler, easier and aligned with ARKlight's philosophy.
5. **Library naming.** Everything ARKlight can do today is a `stdlib`.
   Backend-specific features get their own libs: `androidlib` and
   `linuxlib` now, `winlib` and `maclib` when those targets exist, so a
   site can reach cross-platform targets. `errhanlib` for error
   handling follows that spirit.

(The example's `Site.site(.....)` is read as shorthand for the site
construction that follows the preamble, `site = Site(...)`.)

## What exists today (checked against the source)

- **Include labels:** `arklight/parser/preamble.py` resolves exactly
  two: `stdlib.ARKlight` and `acc.<dotted.module>`. Any other label is
  refused at load time with a `PreambleError`, so
  `# include <errhanlib.ARKlight>` fails loudly today and nobody can be
  relying on it.
- **No platform libs yet.** There is no `androidlib`, `linuxlib`,
  `winlib` or `maclib` anywhere in the source or docs. They are the
  maintainer's stated direction, not shipped.
- **Directives are a registry.** One recogniser plus one normalization
  handler each (`_DIRECTIVE_PARSERS`, `_HANDLERS`); the module says the
  door is open for more. Only comments *above the first statement* are
  ever read as directives.
- **Loud by construction.** Anything malformed or unresolved is recorded
  during normalization and raised by validation, never skipped.
- **`# use <...>` is reserved and refused**, pointing at
  `USE-PREAMBLE-PROPOSAL.md`, precisely so nobody builds on its shape
  before it is designed. That proposal's open questions (what `include`
  vs `use` mean, what `something.ARKlight` names, the label grammar)
  overlap with this one; see open questions 7 and 9.
- **Runtime errors already have one funnel** (`0.06505`):
  `arkReportError(message, err)` logs to the console, calls the
  optional `window.ARKLIGHT_ON_ERROR(message, err)`, then shows
  `arkNotify` unless the hook returned `false`. Its messages are fixed,
  compiler-chosen strings.
- **Build-time messages** go through the compiler's `[ARKlight] ...` log
  lines (`--verbose`/`--debug`); Rei's `--narrate` (accepted, planned)
  is a second presentation of the same stages.

## Reading the syntax (mine -- confirm or correct)

| Slot | Written as | Reading |
| --- | --- | --- |
| 1 | `[{Catch What?}]` | The function to watch: a function defined in the site. |
| 2 | `[ARKlight Log]` | A fixed keyword naming the *sink*: the ARKlight compiler's own log. |
| 3 | `[{error message}]` | The text to print. |

Under this reading the braces are placeholder notation ("put your thing
here"), and a concrete line has none:

```python
# include <stdlib.ARKlight>
# include <errhanlib.ARKlight>

# [home] [ARKlight Log] [The home page failed to build]
# [nav] [ARKlight Log] [The shared nav bar raised while building]
# [cart_summary] [JS Log] [The cart total could not be shown]

site = Site()
```

The maintainer named only the `ARKlight Log` sink, but said "in js or
arklight compiler." `JS Log` is my working name for the JS side. Whether
the braces are literal is open question 1.

## Design sketch (mine)

**A. The include is the switch.** `# include <errhanlib.ARKlight>`
turns on the three-bracket recogniser for that file. Without it, a
line like `# [a] [b] [c]` is an ordinary comment, so the opt-in is
structural and existing files cannot be affected. It would be the first
include that binds *no vocabulary names*; it activates a directive
family instead (relevant to `USE-PREAMBLE-PROPOSAL.md` Q1).

**B. Recognition.** Same rules as every directive: preamble only, per
file. A line in an activated preamble that looks like three brackets but
is malformed (two groups, an empty slot, an unknown sink) is a
diagnostic, not a silent comment.

**C. The target must exist.** After the file executes, slot 1 must name
a module-level function (or registered page/component) the file
defines. An unknown name raises, naming the line -- a typo must not turn
into a handler that never fires. This is the same post-`exec` step
`check_namespace_shadowing` already uses.

**D. Compiler sink.** After `exec`, ARKlight replaces each named
function in the module namespace with a wrapper that calls the original,
and if it raises, prints the author's message through the compiler's log
channel and **re-raises the original exception**. A wrapper rather than a
source rewrite, so line numbers stay true and the author writes no
`try`/`except`. Calls between module-level functions go through module
globals, so they hit the wrapper. Not covered: nested functions,
methods, references captured before the swap.

**E. JS sink.** This is the hard half. The generated JS is closed
vocabulary and has no idea which site function produced a node. The
sketch: when at least one `[JS Log]` line exists, the compiler stamps
the nodes produced under that function with a compact id attribute and
bakes a fixed id-to-message table into the output. The `0.06505` guards
already hold the failing `el`/`container` in hand, so on failure they
find the nearest stamped ancestor and pass *the author's message* to
`arkReportError` instead of the generic one. `ARKLIGHT_ON_ERROR` still
receives it and `false` still suppresses the notice. With no `[JS Log]`
line, no attribute, table or lookup code is emitted.

The catch: some runtime failures are not tied to an element. A
`Computed(...)` recompute or a `Watch(...)` effect is per state name, so
attributing it means the compiler must also stamp State/Computed/Watch
declarations with the function that produced them. That is new IR
provenance and is the real cost of this feature (open question 6).

**F. Author text reaches the runtime.** `RUNTIME-ERROR-HANDLING-PROPOSAL.md`
section 4 deliberately kept site-authored strings out of `arkNotify`.
This proposal reverses that on purpose, so it should be decided openly.
The text comes from the site author's own source, not from visitors, and
`arkNotify` uses `textContent`; the table would be JSON-encoded, with no
inline script. It still stays a literal: no expressions and no code.

**G. Log, don't swallow.** A handler adds a message; it never turns a
failure into success. A build with a caught error still fails; the JS
guards still keep the rest of the page running exactly as they do now.
Anything that recovers or retries is a different feature (out of scope).

## Philosophy fit

Checked against `docs/README.md`'s philosophy list and
`SYSTEM-DESIGN-AGREEMENTS.md` (sections 1, 8, 16):

- **Fail loudly at build time.** Unknown targets and malformed lines
  raise; handlers do not suppress errors.
- **Compiler first, runtime last.** The compiler sink is pure compiler.
  For JS the compiler decides which nodes, which messages and whether
  anything ships at all; the runtime only looks a string up.
- **No eval, no `new Function`.** The message is a literal, never
  evaluated.
- **Only ship what's used / zero drift when opted out.** No `errhanlib`
  include means no change to output. No `[JS Log]` line means no
  attribute, table or lookup code.
- **Not a second untrusted layer.** No arbitrary developer JS or Python
  runs in a handler; there is nothing to run, only text to print.
- **Not a reimplementation of `try`/`except`.** The directive is a
  comment; Python's exception semantics are untouched, which is what
  "doesn't collide" means here.

## Open questions

1. **Are the braces literal, and can the message interpolate?**
   `{Catch What?}` reads like a placeholder, but if a message can also
   carry the error text or function name (`{error}`, `{function}`), the
   same braces would mean two things. Pick one notation before anything
   is built.
2. **Which sinks, and what are they called?** `ARKlight Log` is given;
   `JS Log` is my guess. Are there levels (warn vs error), or more sinks
   later?
3. **Where does a directive live?** In the preamble naming a function
   (as in the example) it can only see the file it is in; a function in
   another module needs that module's own preamble. Or should it sit
   directly above the function it names? Per-file scope, like
   `# define`, is my default.
4. **What counts as "a function in a site"?** Page functions and
   `@component`s clearly. Plain helpers like `nav()`? Nested functions?
   A component that is defined but never used never runs; is a handler
   on it an error?
5. **Log-only, confirmed?** Sketch G says a handler never swallows. If
   the maintainer wants "handle" to mean more than "log", that needs its
   own design.
6. **JS attribution granularity.** Elements only, or also State,
   Computed and Watch? The second is more useful and a much larger IR
   change.
7. **Is this an `include` or a `use`?** An include that binds no names
   stretches the word. Related: `errhanlib.ARKlight` follows
   `stdlib.ARKlight`'s `<x>.ARKlight` shape, but nothing resolves such a
   label besides the built-in stdlib today. Built into the `arklight`
   package, or resolved some other way? (And it is spelled `errhanlib`
   throughout the maintainer's message; kept as written, but if
   `errhandlib` was meant, the label changes by a letter.)
8. **Several lines for one function.** Two handlers for the same target
   and sink: refuse, allow both, or must they agree, as duplicate
   `# define`s must?
9. **Do `androidlib`/`linuxlib`/`winlib`/`maclib` belong here?** This
   proposal only borrows their naming. A documented `<x>lib.ARKlight`
   label family, and how backend-specific libs relate to
   `PlatformAPI` and `check_backend_support`
   (`docs/Foundational/PLATFORM-APIS.md`), is bigger than error handling
   and probably wants its own proposal.
10. **The version slot.** `v0.079` is held by Miko Stage A. Interleave
    (as Rei was into `v0.065`), or take another slot?
11. **Does Rei narrate it?** Should `--narrate` mention a handler's
    message when it fires, and does Project Knowledge's diagnostics
    integration (`v0.076`) record it?

## Explicitly out of scope

- Recovering from, retrying or swallowing an error.
- New exception classes, or any `try`/`except`-like syntax.
- Filtering by exception type (`[ValidationError] ...`); the slot is
  "what function", per the stated design.
- Remote reporting or analytics; `window.ARKLIGHT_ON_ERROR` (`0.06505`)
  remains the seam for that.
- Designing the platform libs themselves.

## Relationship to other work

- **`0.06505` / `RUNTIME-ERROR-HANDLING-PROPOSAL.md`:** the JS sink is
  a customization of that funnel, not a new mechanism.
- **`USE-PREAMBLE-PROPOSAL.md`:** shares the label-grammar and
  include-vs-use questions; whichever settles first constrains the
  other.
- **`REI-COMPILER-NARRATOR-PROPOSAL.md`, `PROJECT-KNOWELEDGE-PROPOSAL.md`:**
  possible consumers of a handler's messages (question 11).
- **`PLATFORM-API-IR-PROPOSAL.md`:** the backend-specific-libs direction
  overlaps it (question 9).
