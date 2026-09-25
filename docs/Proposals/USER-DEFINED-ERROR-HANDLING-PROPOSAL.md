# User Defined Error Handling: `errhanlib.ARKlight`'s `Try`

## Status

**Proposal -- not yet accepted, not yet staged.** Per
`docs/Proposals/README.md`'s own definition, this describes something
that does not exist yet, may never be built as written, and could be
rejected outright.

**Full replace of an earlier draft of this file.** That draft proposed
a `# [{Catch What?}] [sink] [message]` three-bracket comment syntax
attached above a function definition. It is superseded by this one
after further design review surfaced a cleaner fit for ARKlight's
existing conventions; its own open questions are kept here wherever
they still apply, and its rationale otherwise lives in git history,
not repeated. The maintainer's original stated goals all still hold
and are carried forward unchanged: opt-in, applies to any function
ARKlight recognises, "doesn't collide with try/catch method of
python," and follows the `<x>lib.ARKlight` library-naming convention
(`errhanlib`, alongside the stated future `androidlib`/`linuxlib`/
`winlib`/`maclib`).

**Requested slot: `v0.079`** (unchanged from the prior draft). That
milestone is already reserved in `PROGRESS.md` for `arklight assistant`
Miko MVP, Stage A. This document does not schedule anything; open
question 8 is a maintainer decision.

**How to read this file.** Three labels are used throughout, the same
convention the prior draft used:

- **Stated** -- came from the maintainer, either directly or carried
  forward unchanged from the earlier draft.
- **Proposed** -- this document's own suggestion, offered so there is
  something concrete to accept, change or kill. Nothing marked
  *Proposed* is decided.
- **Open** -- a question only a maintainer can answer. Numbered in
  "Open questions"; question 1 no longer blocks the rest the way it
  did in the prior draft (see below), but is kept as an open question.

## Summary

Java's `try`/`catch`/`finally` is taken as inspiration for its
**syntax** -- a class, `catch` clauses matched by exception-type
inheritance, a guaranteed `finally` block -- not its **semantics**.
Nothing a site author writes in a `catch`/`finally` body ever executes
as code, at build time or in the browser. Instead, both bodies are
ordinary ARKlight closed-vocabulary declarations: a plain list of
`Action.*(...)` refs (already used by `on_click=`/`Watch(..., then=)`)
and two new `Log.*(...)` refs this proposal adds. The compiler reads
the class once at build time -- the same way it already reads
`Action.increment("count")` -- and never calls back into it at error
time, whether that error happens while compiling or later, live, in
the browser.

## What exists today (checked against the source)

- **Include labels:** `arklight/parser/preamble.py` resolves exactly
  two: `stdlib.ARKlight` and `acc.<dotted.module>`. Any other label,
  including `errhanlib.ARKlight`, is refused at load time with a
  `PreambleError`, so nobody can be relying on it today.
- **No platform libs yet.** Unchanged from the prior draft: there is
  no `androidlib`, `linuxlib`, `winlib` or `maclib` anywhere in the
  source or docs.
- **A real inheritance hierarchy for errors already exists -- entirely
  internal to the compiler.** `ComponentError(RuntimeError)` ->
  `DuplicateComponentError(ComponentError)`
  (`arklight/ir/components.py:148,158`); `PreambleError(SyntaxError)`
  -> `PreambleCollisionError(PreambleError)`
  (`arklight/parser/preamble.py:191,196`). Both are caught by
  `arklight/compiler/pipeline.py`'s `compile_site_file` and rewrapped
  into a single `CompileError`, never a raw traceback. This proposal's
  `catches=` is the site-author-facing version of the exact same
  pattern -- classification by real Python exception inheritance,
  resolved at build time -- not a new mechanism.
- **"Declaration says what happens, compiler resolves it later" is
  already the DSL's dominant pattern**, not something this proposal
  invents. `Action.*(...)` (`arklight/api.py:738`) returns a small,
  frozen `ActionRef` -- "deliberately a small structured object, not a
  string... never becomes a JS/Python string that gets executed"
  (`arklight/ast/nodes.py:102`) -- validated against
  `arklight.ir.schema.ACTION_REGISTRY` at compile time.
  `Watch(name, then=Action.set(...))` (`arklight/api.py:1189`) is the
  closest existing precedent for this proposal's shape specifically:
  "whenever `name` changes, run `then` -- an `Action.*(...)` reference"
  -- trigger, closed-vocab consequence, nothing else.
- **Class definitions carry no DSL meaning today.**
  `parser/preamble.py`'s `_collect_binders` only records a class's
  bound name for collision bookkeeping, the same shallow treatment
  given to any other module-level statement. This proposal is the
  first to give a class body compiler-recognised meaning.
- **Runtime errors already have one funnel** (`0.06505`):
  `arkReportError(message, err)` logs to the console, calls the
  optional `window.ARKLIGHT_ON_ERROR(message, err)` hook, then shows
  `arkNotify(message)` unless the hook returns exactly `false`.
  Messages passed to it today are fixed, compiler-chosen strings --
  "no site-authored text reaches `arkNotify`"
  (`arklight/backend/js/runtime/notify.py`'s module docstring). This
  proposal is the first to put author-chosen text on that path (see
  design principle F below, carried from the prior draft).
- **"The browser never executes Python" is unchanged and still the
  wall.** (`arklight/__init__.py`; `docs/Foundational/PITCH.md:7`;
  `docs/README.md:8`; `docs/Foundational/ARCHITECTURE.md:13`.) A
  `Try` subclass is read only at build time. Nothing about it runs
  live in the browser; what reaches the browser is a fixed,
  compiler-generated lookup table, the same shape `0.06505`'s funnel
  already uses.

## The design (Proposed)

### The base class

```python
# include <stdlib.ARKlight>
# include <errhanlib.ARKlight>

class HomePageFailure(Try):
    catches = (ValueError, ComponentError)

    catch = [
        Log.compiler("The home page failed to build"),
        Log.js("Something went wrong loading this page"),
        Action.set("status", "error"),
    ]
    finally_ = [
        Action.set("loading", False),
    ]


@site.page("/")
@HomePageFailure.wraps
def home():
    ...
```

`Try` is the one name `errhanlib.ARKlight` binds -- alongside `Log`.
(The prior draft's open question 6 asked whether an `include` that
"binds no names" stretches the word `include`; this design makes the
question moot, since it now binds names the same shape
`stdlib.ARKlight` already does.)

A site author extends `Try` the way they'd extend any Python base
class -- ordinary inheritance, ordinary class-body attributes.
Nothing in the class body is arbitrary code from ARKlight's point of
view: `catch` and `finally_` are plain list literals of
`Action.*(...)`/`Log.*(...)` refs, checked against closed registries
the same way `Action` already is.

### `catches`: real exception types, matched by inheritance

`catches` is a tuple of real Python exception types -- built-ins
(`ValueError`, `KeyError`, ...) or ARKlight's own compiler-raised
types (`ComponentError`, `ValidationError`). Matching uses ordinary
`issubclass` semantics: a handler with `catches = (ComponentError,)`
also catches `DuplicateComponentError`, the same behavior Java's own
catch clauses have, because it's just Python's type system -- nothing
ARKlight invents. This directly answers the prior draft's **open
question 1** ("what does slot 1 mean") in favor of its reading (a),
exception-type filtering, without needing a bracket-comment grammar
or an escaping rule to express it.

### `finally_`, not `finally`

Python reserves `finally` as a keyword; a class attribute cannot be
named `finally`. This draft uses `finally_` (a trailing underscore,
the same convention the standard library itself uses for keyword
collisions, e.g. `type_`). Whether a trailing underscore is acceptable
ARKlight authoring style, or this should be a different word entirely
(`always`, `ensure`, `cleanup`), is **open question 2**.

### Applying it: an explicit decorator, not an implicit comment attachment

```python
@site.page("/")
@HomePageFailure.wraps
def home():
    ...
```

`Try.wraps` is a classmethod returning a decorator, applied as the
innermost decorator (directly above `def`, below `@site.page(...)`/
`@component(...)`), matching the prior draft's design sketch item D
for *why* it must sit there: `@site.page`/`@component` store the
function object the moment their own decorator runs, so wrapping must
happen before that capture or the registry would hold the unwrapped
original.

Unlike the prior draft, the target function is **explicit** --
ordinary Python decorator application, not a comment inferred to
belong to "the next line." That removes the prior draft's entire
placement-and-attachment machinery: no `tokenize`-based comment
reading, no "no blank line between them" rule, no distinct error case
for a directive sitting somewhere it can't attach to (prior draft
section B/C). It also means one `Try` subclass can be applied to
several functions (`@HomePageFailure.wraps` on more than one page),
which the comment-per-function design couldn't express without
repeating the whole class.

### Two sinks, routed by which ref appears

- **`Log.compiler(message)`** -- build-time only. When the wrapped
  function raises while the compiler is running it (a `ComponentError`
  during expansion, for instance), the compiler prints `message`
  through its own `[ARKlight] ...` log channel (or `--narrate`'s
  prose, open question 7) and **re-raises the original exception** --
  matching the prior draft's principle G, "log, don't swallow": a
  build with a caught error still fails the build.
- **`Log.js(message)`** -- runtime only. `@site.page`/`@component`
  functions run at build time to produce IR; what can fail *live* in
  the browser is the compiled JS behind that function's own
  `State`/`Computed`/`Watch`/`bind_value` declarations, through the
  existing `0.06505` guards. The compiler sketch, carried over from
  the prior draft's section E: nodes produced under a `wraps`-covered
  function get a compact id attribute, and a fixed id-to-message table
  ships in the output; on failure the existing guards find the nearest
  stamped ancestor and pass `message` to `arkReportError` instead of
  its generic string. With no `Log.js(...)` present, no attribute,
  table or lookup code is emitted -- unchanged "only ship what's used"
  discipline.
- **`Action.*(...)` inside `catch`/`finally_`** -- runtime only, for
  the same reason `Log.js` is: `Action.set(...)` mutates a live
  browser `State` store that doesn't exist while the compiler is
  running. An `Action.*(...)` entry compiles into the same JS
  `catch`/`finally` block `Log.js` stamps in; a `Log.compiler(...)`
  entry contributes nothing to that block.

Whether a `Log.compiler(...)`-only handler is even allowed to omit
`Log.js`/`Action.*` entirely (a purely build-time handler, no runtime
footprint at all) is **Proposed: yes**, and is the expected common
case for build-only functions.

## Design sketch (Proposed) -- compiler mechanics

Carried forward from the prior draft's section D/E, adapted for the
new syntax:

- **Build-time wrapping.** `Try.wraps` inserts the same kind of
  internal wrapper the prior draft sketched -- calls the original
  function, and on a caught exception type runs the `catch` list's
  `Log.compiler(...)` entries (if any) through the compiler's log
  channel before re-raising. Doing it via an explicit decorator (not a
  source rewrite or a comment-triggered insertion) means line numbers
  stay true and there's no separate "where does this attach" logic to
  validate.
- **JS-sink stamping.** Unchanged in substance from the prior draft's
  section E: id-stamped nodes, a fixed id-to-message table, the
  existing `0.06505` guards doing the lookup. The harder case flagged
  there is unchanged too: a `Computed(...)`/`Watch(...)` failure is
  per state name, not per element, so attributing it to a `wraps`-ed
  function means stamping `State`/`Computed`/`Watch` declarations with
  their owning function -- new IR provenance, and the real cost of
  this feature (open question 9, carried over).
- **`finally_` in the generated JS.** Compiles to an actual JS
  `finally` block wrapping the stamped operation, running each
  `Action.*(...)` entry unconditionally -- the literal Java-shaped
  guarantee, expressed as closed-vocab dispatch calls, never arbitrary
  code.
- **Nested calls.** Because application is now an explicit decorator
  rather than implicit attachment, this is no longer a special rule
  ARKlight must define (the prior draft's open question 10): if a
  `wraps`-ed function calls another `wraps`-ed function, ordinary
  Python call-stack behavior already decides who sees what, the same
  as any two decorated functions calling each other. Confirmation that
  this reasoning is sufficient is open question 5.

## Philosophy fit

Checked against `docs/README.md`'s philosophy list and
`SYSTEM-DESIGN-AGREEMENTS.md`:

- **Fail loudly at build time.** A malformed `catches` (not exception
  types), an unrecognised entry in `catch`/`finally_` (not an
  `Action.*`/`Log.*` ref), or `wraps` applied to a function ARKlight
  doesn't recognise all raise at build time, named to the line.
- **Compiler first, runtime last.** The compiler decides which nodes,
  which messages, and whether anything ships at all; the browser only
  ever looks a fixed id up in a fixed table.
- **No eval, no `new Function`.** `catch`/`finally_` are literal list
  attributes read once at build time -- never a method the compiler
  calls back into, never code executed at error time, at build time
  or in the browser.
- **Only ship what's used / zero drift when opted out.** No
  `errhanlib` include means no `Try` name and no change to output. A
  handler with no `Log.js`/`Action.*` entries emits no JS attribute,
  table or lookup code at all.
- **Not a second untrusted layer.** There is nothing to run inside a
  handler, only a closed list of refs to read -- the same trust
  boundary `Action`/`Watch` already have, extended to a class body
  instead of a function call's keyword arguments.
- **Not a reimplementation of `try`/`except`.** `Try` does not
  subclass `Exception`; it is never raised or caught by Python's own
  exception machinery. It is introspected once at build time, the
  same relationship `Action` already has to `on_click=`. Real Python
  `try`/`except` written elsewhere in the site file (the loader
  genuinely executes ARKlight source as Python) is untouched and
  orthogonal -- this is what "doesn't collide" means here, unchanged
  from the prior draft's claim 4.

## Open questions

1. ~~What is slot 1?~~ Resolved by this redesign: `catches` is a
   tuple of real exception types, matched by `issubclass`. Kept here,
   renumbered, only to record that it is no longer blocking.
2. **`finally_`'s naming collision with the `finally` keyword.**
   Trailing underscore, or a different word (`always`/`ensure`/
   `cleanup`)?
3. **Can a site define its own exception types purely for `catches=`
   grouping?** A marker subclass with no body/behavior (since nothing
   about it ever executes) would let a site group several build-time
   failure kinds under one handler without reaching for unrelated
   built-ins. If yes, does ARKlight need to recognise "an empty
   exception subclass" as its own small closed shape, or is any
   subclass of `Exception` accepted as-is since nothing in it ever
   runs?
4. **Can more than one `Try` subclass wrap the same function?**
   Stacked `@wraps` decorators, first match wins, or refused as
   ambiguous the same way duplicate `# define`s are refused?
5. **Nested calls.** Confirm that ordinary Python call-stack behavior
   (see design sketch above) is sufficient, or does a `wraps`-ed
   function calling another need an explicit rule after all?
6. **Where can a `Try` subclass live?** Must it be declared in the
   same file as the function(s) it wraps, or can one be defined once
   and imported/reused across files as a shared "standard failure
   handler"?
7. **Does Rei narrate a `catch`/`finally_` firing?** Does Project
   Knowledge's diagnostics integration (`v0.076`) record it? (Carried
   from the prior draft's open question 11.)
8. **The version slot, and one release or two.** Unchanged from the
   prior draft: `v0.079` is held by Miko Stage A. Interleave, or take
   another slot? Compiler-sink-only support is small; the JS sink
   needs new IR provenance (question 9) and could ship separately.
9. **JS attribution granularity.** Elements only, or also `State`,
   `Computed` and `Watch`? The second is more useful and a much larger
   IR change. (Carried from the prior draft's open question 9.)
10. **Do `androidlib`/`linuxlib`/`winlib`/`maclib` belong in this
    document at all?** This proposal only borrows their naming
    convention for `errhanlib`. (Carried from the prior draft's open
    question 7.)

## Explicitly out of scope

- Recovering the *build* from a build-time exception; a caught
  build-time exception still fails the build.
- Arbitrary code inside `catch`/`finally_` bodies, or a handler that
  receives the actual exception object to inspect or format at error
  time. If that's wanted later, it is a new proposal, not folded in
  here -- it would reopen "the browser never executes Python" for the
  JS sink and "no eval" for the compiler sink.
- A `catch`/`finally_` entry that isn't a recognised `Action.*(...)`/
  `Log.*(...)` ref -- no expressions, no string formatting beyond what
  `Log.*(...)`'s own argument accepts as a literal.
- Remote reporting or analytics; `window.ARKLIGHT_ON_ERROR` (`0.06505`)
  remains the seam for that, unchanged.
- Designing the platform libs themselves (open question 10).

## Relationship to other work

- **`0.06505` / `RUNTIME-ERROR-HANDLING-PROPOSAL.md`:** the JS sink is
  a customization of that funnel, not a new mechanism -- unchanged
  from the prior draft.
- **`ir/components.py`'s `ComponentError`/`DuplicateComponentError`,
  `parser/preamble.py`'s `PreambleError`/`PreambleCollisionError`:**
  the existing, compiler-internal precedent for `catches=`'s
  inheritance-based matching. New to this redesign.
- **`arklight/api.py`'s `Action`/`Watch`:** the existing precedent for
  "closed-vocab declaration, resolved once at build time, never
  executed as code" that `catch`/`finally_` extend into a class body.
  New to this redesign.
- **`USE-PREAMBLE-PROPOSAL.md`:** shared label-grammar and
  include-vs-use questions from the prior draft no longer apply in the
  same way, since `errhanlib.ARKlight` now binds names (`Try`, `Log`)
  the ordinary way `stdlib.ARKlight` does.
- **The Rei compiler narrator record in `docs/Foundational/DESIGN-NOTES.md`,
  `PROJECT-KNOWELEDGE-PROPOSAL.md`:**
  possible consumers of a handler's messages (open question 7).
- **`PLATFORM-API-IR-PROPOSAL.md`:** the backend-specific-libs
  direction overlaps `errhanlib`'s naming convention (open question
  10).
