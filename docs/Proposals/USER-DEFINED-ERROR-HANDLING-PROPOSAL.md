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
That is a maintainer decision (open question 8).

**How to read this file.** Three labels are used throughout:

- **Stated** -- the maintainer said it. Recorded in "The design, as
  stated" and in the clarification below.
- **Proposed** -- the author's suggestion, offered so there is
  something concrete to accept, change or kill. Nothing marked
  *Proposed* is decided.
- **Open** -- a question only the maintainer can answer. Each one is
  numbered in "Open questions". Question 1 blocks the rest.

## The design, as stated

```python
# include <stdlib.ARKlight>
# include <errhanlib.ARKlight>

# [{Catch What?}] [ARKlight Log] [{error message}]
def home():
    ...
```

Claims, reduced from the maintainer's words:

1. **Opt-in.** A user chooses to print custom error logs, "in js or
   arklight compiler."
2. **Three brackets are the syntax.** "Three [] is a syntax for user
   defined error handling."
3. **Any recognised function.** It applies to any function ARKlight
   recognises, not only site-level ones. The line goes as a special
   comment **directly above the function it wraps**. The target is
   implicit: it is the function beneath the comment, so no function
   name is written. This works because ARKlight sites are a Python
   DSL, where a comment directly above a `def` already reads as
   belonging to it. The goal is error logs that are easy to handle.
4. **No collision with Python.** It "doesn't collide with try catch
   method of python." ARKlight owns this representation because it is
   simpler, easier and aligned with ARKlight's philosophy.
5. **Library naming.** Everything ARKlight can do today is a `stdlib`.
   Backend-specific features get their own libs: `androidlib` and
   `linuxlib` now, `winlib` and `maclib` when those targets exist, so a
   site can reach cross-platform targets. `errhanlib` for error
   handling follows that spirit.

(The earlier draft of this file read the example's `Site.site(.....)`
as a site construction and treated slot 1 as a *function name*. Claim 3
corrects that: the function is not named at all.)

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
  handler each (`_DIRECTIVE_PARSERS`, `_HANDLERS`). Today only comments
  *above the first statement* are read (`_leading_comment_lines`).
  A directive that sits above a function, in the middle of a file, is
  a new place to look; it does not exist yet.
- **Loud by construction.** Anything malformed or unresolved is recorded
  during normalization and raised by validation, never skipped.
- **`# use <...>` is reserved and refused**, pointing at
  `USE-PREAMBLE-PROPOSAL.md`, precisely so nobody builds on its shape
  before it is designed. That proposal's open questions overlap with
  this one; see open questions 6 and 7.
- **Functions are registered at definition time.** `@site.page(route)`
  stores the function object in `Site.routes` the moment the decorator
  runs, and `@component(...)` registers its render function the same
  way. This matters for the compiler sink (section D).
- **Runtime errors already have one funnel** (`0.06505`):
  `arkReportError(message, err)` logs to the console, calls the
  optional `window.ARKLIGHT_ON_ERROR(message, err)`, then shows
  `arkNotify` unless the hook returned `false`. Its messages are fixed,
  compiler-chosen strings.
- **Build-time messages** go through the compiler's `[ARKlight] ...` log
  lines (`--verbose`/`--debug`); Rei's `--narrate` (shipped, `0.06510`)
  is a second presentation of the same stages.

## The syntax

A concrete use, with the target implicit:

```python
# include <stdlib.ARKlight>
# include <errhanlib.ARKlight>

# [{Catch What?}] [ARKlight Log] [The home page failed to build]
@site.page("/")
def home():
    ...

# [{Catch What?}] [JS Log] [The cart total could not be shown]
@component()
def cart_summary():
    ...
```

| Slot | Written as | Reading | Status |
| --- | --- | --- | --- |
| 1 | `[{Catch What?}]` | What to catch. **Meaning unresolved** (open question 1). | Open |
| 2 | `[ARKlight Log]` | A fixed keyword naming the *sink*: the ARKlight compiler's own log. | Stated |
| 3 | `[{error message}]` | The text to print. | Stated |

The maintainer named only the `ARKlight Log` sink, but said "in js or
arklight compiler." `JS Log` is the author's **proposed** name for the
JS side (open question 2). Whether the braces are literal is open
question 3.

## Design sketch (Proposed)

**A. The include is the switch.** `# include <errhanlib.ARKlight>`
turns on the three-bracket recogniser for that file. Without it, a
line like `# [a] [b] [c]` is an ordinary comment, so the opt-in is
structural and existing files cannot be affected. It would be the first
include that binds *no vocabulary names*; it activates a directive
family instead (relevant to `USE-PREAMBLE-PROPOSAL.md` Q1).

**B. Placement and attachment.** In an activated file, a three-bracket
comment attaches to the function definition whose **first line is the
very next line**. No blank line and no other statement may sit between
them. Consecutive directive comments above one function all attach to
it. Comments are read with `tokenize`, because `ast` discards them.
When the function has decorators, the function's first line is its
topmost decorator, so the directive goes above `@site.page(...)` or
`@component(...)`, as in the example. (Open question 5: confirm this
placement.)

**C. Attachment errors are loud.** In an activated file, each of the
following raises and names the line. A typo must not become a handler
that never fires.
- A three-bracket comment that is not directly above a function.
- A line that looks like three brackets but is malformed (two groups,
  an empty slot, an unknown sink).
- A directive above a function ARKlight does not recognise (open
  question 4 decides which functions count).

**D. Compiler sink.** Because the target is the function directly
beneath the comment, ARKlight can wrap it *where it is defined*. The
sketch: the compiler inserts an internal wrapper as the innermost
decorator of that `def` (directly below any user decorators), which
calls the original and, if it raises, prints the author's message
through the compiler's log channel and **re-raises the original
exception**. Doing it at definition time is not optional. `@site.page`
and `@component` store the function they are handed at the moment they
run, so swapping a name in the module after the file has executed would
leave the registry holding the unwrapped original and the handler would
never fire. A wrapper rather than a source rewrite means line numbers
stay true and the author writes no `try`/`except`. Nested functions and
methods are covered whenever they are recognised (open question 4).

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
provenance and is the real cost of this feature (open question 9).

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

**H. Nested calls.** If a wrapped function calls another wrapped
function and the inner one raises, each wrapper that sees the exception
prints its own message, innermost first, then the original exception
propagates unchanged. (Open question 10: confirm, or print only the
innermost.)

## Philosophy fit

Checked against `docs/README.md`'s philosophy list and
`SYSTEM-DESIGN-AGREEMENTS.md` (sections 1, 8, 16):

- **Fail loudly at build time.** Misplaced or malformed directives
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

1. **What is slot 1, `[{Catch What?}]`, now that the function is
   implicit?** The function is no longer named, so this slot must mean
   something else. Two readings: (a) **which error to catch**, e.g. an
   exception type such as `ValueError`, with some keyword for "any";
   (b) **dropped**, leaving `[sink] [message]`, which contradicts "three
   brackets." This document currently lists exception-type filtering as
   out of scope, which only holds under a reading that is not (a). This
   blocks everything below; nothing should be built before it is
   answered.
2. **Which sinks, and what are they called?** `ARKlight Log` is given;
   `JS Log` is the author's guess, and "ARKlight Log" is ambiguous when
   ARKlight also emits the JS (`Compiler Log`/`Build Log` would pair
   more clearly with `JS Log`). Are there levels (warn vs error), or
   more sinks later?
3. **Are the braces literal, and can the message interpolate?**
   `{Catch What?}` reads like a placeholder, but if a message can also
   carry the error text or function name (`{error}`, `{function}`), the
   same braces would mean two things. Also unspecified: how a message
   contains a literal `]`, for example `[Failed on items[0]]`. Pick one
   notation and an escape rule before anything is built.
4. **What counts as "a function ARKlight recognises"?** Page functions
   (`@site.page`) and `@component`s clearly. Plain helpers like `nav()`?
   Nested functions and methods? A component that is defined but never
   used never runs; is a handler on it an error? A directive above an
   unrecognised function raises (section C); the set needs a definition.
5. **Placement with decorators.** Section B puts the directive above the
   topmost decorator. Confirm, or specify between-decorator-and-`def`.
   Either way, the other placement should be an error, not a silent
   second meaning.
6. **Is this an `include` or a `use`?** An include that binds no names
   stretches the word. Related: `errhanlib.ARKlight` follows
   `stdlib.ARKlight`'s `<x>.ARKlight` shape, but nothing resolves such a
   label besides the built-in stdlib today. Built into the `arklight`
   package, or resolved some other way? (And it is spelled `errhanlib`
   throughout the maintainer's message; kept as written, but if
   `errhandlib` was meant, the label changes by a letter.)
7. **Do `androidlib`/`linuxlib`/`winlib`/`maclib` belong here?** This
   proposal only borrows their naming. A documented `<x>lib.ARKlight`
   label family, and how backend-specific libs relate to
   `PlatformAPI` and `check_backend_support`
   (`docs/Foundational/PLATFORM-APIS.md`), is bigger than error handling
   and probably wants its own proposal.
8. **The version slot, and one release or two.** `v0.079` is held by
   Miko Stage A. Interleave (as Rei was into `v0.065`), or take another
   slot? The compiler sink is small; the JS sink needs new IR
   provenance. Should they ship separately, compiler sink first?
9. **JS attribution granularity.** Elements only, or also State,
   Computed and Watch? The second is more useful and a much larger IR
   change.
10. **Nested and duplicate handlers.** Section H proposes that every
    wrapper in the call chain prints. Confirm or change. Separately:
    two directives for the same function and sink: refuse, allow both,
    or must they agree, as duplicate `# define`s must?
11. **Does Rei narrate it?** Should `--narrate` mention a handler's
    message when it fires, and does Project Knowledge's diagnostics
    integration (`v0.076`) record it?

## Explicitly out of scope

- Recovering from, retrying or swallowing an error.
- New exception classes, or any `try`/`except`-like syntax.
- Remote reporting or analytics; `window.ARKLIGHT_ON_ERROR` (`0.06505`)
  remains the seam for that.
- Designing the platform libs themselves.

(Filtering by exception type was listed here in an earlier draft. It is
removed from this list because open question 1 may make it the meaning
of slot 1.)

## Relationship to other work

- **`0.06505` / `RUNTIME-ERROR-HANDLING-PROPOSAL.md`:** the JS sink is
  a customization of that funnel, not a new mechanism.
- **`USE-PREAMBLE-PROPOSAL.md`:** shares the label-grammar and
  include-vs-use questions; whichever settles first constrains the
  other.
- **`REI-COMPILER-NARRATOR-PROPOSAL.md`, `PROJECT-KNOWELEDGE-PROPOSAL.md`:**
  possible consumers of a handler's messages (question 11).
- **`PLATFORM-API-IR-PROPOSAL.md`:** the backend-specific-libs direction
  overlaps it (question 7).
