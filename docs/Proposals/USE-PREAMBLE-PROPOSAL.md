# `# use`: a Preamble Directive for Components, ACC, and a UI/UX Split

## Status

**Proposal — not yet accepted, not yet staged.** Per
`docs/Proposals/README.md`'s own definition, this describes something
that does not exist yet, may never be built as written, and could be
rejected outright.

**Origin:** the maintainer's design discussion while fixing `# define`
(`CHANGELOG.md` `[0.06502]`). This is a *discussion* document: it
records the maintainer's current thinking as stated, separates what is
already settled from what is only proposed, and lists the questions
that are still open. It decides none of them.

**Until this is accepted**, a `# use <...>` line in a file's preamble is
refused with an error that points here. It is deliberately not ignored:
a directive that silently does nothing invites people to write it
believing it works.

## What is already settled (context, not part of this proposal)

- **`# include <label>`** exists: binds a vocabulary source into the
  file's namespace. Labels today: `stdlib.ARKlight`, and
  `acc.<dotted.module>`.
- **`# define <name> -> <text>`** exists (`0.06502`): C's `#define`.
  The left name is replaced by the right text at compile time. It is
  the exception on purpose — it is neither an `include` nor a `use`,
  because it binds nothing; it rewrites the file's own source. The
  earlier worry ("is a macro preamble even needed?") is closed: it
  stays, as `define`.
- **The preamble stays open to more directives.** A directive is one
  recogniser plus one handler in `arklight/parser/preamble.py`.
- **Every Python file ARKlight takes in gets its preamble** — the site
  file, project modules, `arklight.config.py` (`0.06502`).
- **`from arklight import *` is retired** (notice only, today). The
  maintainer's stated direction is to drop it in favor of the preamble.

## The proposal, as stated

Three ideas, in the maintainer's terms:

1. **`# use <something.ARKlight>`** — for User Defined Components
   (UDC).
2. **`# use <something.ACC>`** — for ACC *components*. An ACC package
   that is **not** components must be `# include <something.ACC>`
   instead, "else? Error basically."
3. **`# use <UI.ARKlight>`** for the HTML and CSS side, and
   **`# use <UX.ARKlight>`** for the JS side — "to make it even more
   obvious."

```python
# include <stdlib.ARKlight>      # today
# define ROWS -> 3               # today

# use <UI.ARKlight>              # proposed: HTML + CSS vocabulary
# use <UX.ARKlight>              # proposed: JS vocabulary (State, Action, ...)
# use <cards.ARKlight>           # proposed: my own components
# use <charts.ACC>               # proposed: an ACC package of components
# include <analytics.ACC>        # proposed: an ACC package that is not components
```

## A working hypothesis (mine — confirm or kill it)

> `include` puts *names* into the file. `use` brings in *components*.

It fits the ACC rule above (components → `use`, everything else →
`include`, wrong verb → error). But it immediately runs into Q1: a
component is called by name in ordinary Python (`Card(...)`), so a
`use`d component has to end up bound in the namespace too. If so, what
does `use` do that `include` doesn't?

## Open questions

**Q1. Where exactly is the line between `include` and `use`?**
If both end with names in the namespace, the difference must be
something else: registration in the component registry, the
`allow_redefine` / duplicate rules, what gets validated, or what the
error says when it goes wrong. Which one is it?

**Q2. What does `something.ARKlight` name?**
A Python module path, a file (would `something.ARKlight` be a file
extension?), or a package label? And where does `something` resolve:
the project directory, an installed package, an entry point?
Relatedly, the label grammar would now have two shapes: today's
`acc.<dotted.module>` is a *prefix* form, while `stdlib.ARKlight` and
the proposed `<x>.ACC` are *suffix* forms. Does `# include <acc.x>`
migrate to `# include <x.ACC>`?

**Q3. How does ARKlight know an ACC package is components?**
ACC packages are installed distributions found through entry points
(`docs/Foundational/ACC-CAPABILITIES.md`). "Components or not" would
need to come from somewhere — declared metadata on the capability, a
new field, inspecting exports? And what should the error say when the
wrong verb is used?

**Q4. Is `UI` + `UX` a split of the stdlib, or an addition to it?**
If `stdlib.ARKlight` = `UI.ARKlight` + `UX.ARKlight`, someone has to
decide which names live where, and many names straddle:
`Button(..., on_click=Action.increment(...))` is HTML *and* JS;
`Page(State(...), ...)` mixes them. Options worth weighing:
what does a file that only `use`s `UI` get when it calls `State`
(a `NameError`, or a targeted "`State` is in `UX.ARKlight`")?
Is it worth two lines in every file? And does naming compile targets
(HTML/CSS/JS) in the author's own source fit "author in ordinary
Python, the compiler picks the targets"?

**Q5. Collisions.**
Since `# define` stopped being a collision resolver (`0.06502`), two
includes that bind one name to different objects have no directive that
resolves it: drop one, or rename an export. With more sources arriving
via `use`, does the answer become namespacing (a label-qualified
access), an `as`-style clause, or nothing?

**Q6. When does `from arklight import *` actually go?**
With `use` (one migration, one story), or independently and sooner
(it is already retired, and every scaffold now uses the preamble)? A
hard error needs a version to land in.

**Q7. Should the "reserved" behavior stay until acceptance?**
Today `# use <...>` errors rather than being ignored. It keeps anyone
from building on a shape that may change. If that is more friction than
it's worth while this is being designed, it is one entry to delete in
`_RESERVED_DIRECTIVES`.

## If accepted — a sketch, not a commitment

- A `use` recogniser in `_DIRECTIVE_PARSERS` and a handler in
  `_HANDLERS`; its entry removed from `_RESERVED_DIRECTIVES`.
- Whatever cross-checks Q1–Q5 end up needing, in `validate_preamble`
  (the only place the preamble raises).
- `AUTHORING-GUIDE.md` and tests, following the existing preamble
  ones. Nothing staged; this would graduate to `docs/Implementation/`
  only once accepted.

## Not in scope

- `# define` (settled; see above).
- Changes to the ACC repository or its entry-point contract, beyond
  whatever Q3 turns out to need.
- New file types or a new module system.
