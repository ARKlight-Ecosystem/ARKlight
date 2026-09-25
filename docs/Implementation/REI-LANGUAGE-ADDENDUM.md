# Rei Language Addendum: Staged Order, v0.081 -> v0.084

**Status:** PLANNED -- stages 1-4 (`v0.081`-`v0.084`) not yet started.
This file turns the accepted
[`docs/Proposals/REI-LANGUAGE-PROPOSAL.md`](../Proposals/REI-LANGUAGE-PROPOSAL.md)
into a trackable, four-rung landing order, the same role
`JS-VOCABULARY-ADDENDUM-v0.070.md` plays for the JS vocabulary
addendum and `PROVIDER-SDK-ADDENDUM.md` plays for `Provider`. It does
not restate that proposal's reasoning or its 2026-09-21 acceptance
update's five resolved open questions and four language-surface
decisions; it exists to turn "here's what was decided" into "here's
the version each rung ships under."

This is a **capability fix** in `V1-DEFINITION.md`'s Alpha issue-triage
sense (see that file's "Issue triage during Alpha" section): before
this ladder, ARKlight shipped no authored answer at all for a native,
compiler-owned source language -- Python authoring was the *only* way
to write a site, with no closed-vocabulary alternative that skips
`exec`-ing an arbitrary module to learn what it contains. The
proposal's own §3 ("Fit with ARKlight's doctrine") already frames this
as easier fail-loudly enforcement for a language ARKlight owns than
for Python's `loader.py`; the maintainer's 2026-09-21 acceptance turns
that from a playground exploration into a real missing capability
being closed, the same shape the `Bind`-as-action-argument fix
(issue-register #7, `docs/Foundational/DESIGN-NOTES.md`) and `PROVIDER-SDK-ADDENDUM.md` already are.

## Scope filter: what's in this ladder, and what isn't

Every rung below is scoped by the proposal's own §6 ("Non-goals"),
unchanged by acceptance:

- **In scope:** the `.rei` source frontend and `arklight.config.rei`,
  both lowering to the exact same `dict[str, ARKNode]`/`CONFIG` shapes
  Python authoring already produces; the alpha-channel maturity gate;
  RNI, Rei's own gated escape-hatch tier (replacing the retired Fun
  tier); the four language-surface decisions the maintainer specified
  directly at acceptance (shared preamble syntax, the entry-point
  class + fixed `site` method, Java-adjacent markup / Kotlin-adjacent
  style, Java-shaped exceptions, and Platform APIs as an `interface`).
- **Out of scope, on purpose:** replacing Python authoring (it stays
  the default and the supported path); any new IR node type, backend
  change, or runtime -- Rei is never shipped to the browser; Java
  compatibility of any kind (no JVM, no `java.*`, no bytecode); a
  package ecosystem, LSP, or formatter; and a stability promise for
  the Rei syntax itself. Nothing in this ladder authorizes work on any
  of it.

The proposal's Stage 3 ("Compute": `const`, functions, a minimal
evaluator) is **not** one of this ladder's four rungs -- it stays
**Blocked** on Open question 3 (build-time evaluator design) exactly
as the proposal states, and holds no version slot, the same
"unscheduled, pending a real decision" treatment
`PLATFORM-API-IR-ADDENDUM.md` gives its own Stage 2. Adding it later
is a version-slot decision for whoever resolves Open question 3, not
implied by this ladder reaching `v0.084`.

## Why four versions, not one

Same precedent every other multi-piece capability in this repository
already follows: `v0.054`'s 8 `vdom-N` stages, `v0.060`'s 5
`stage0`-`stage4` stages, the JS vocabulary addendum's ten-rung
`v0.061`-`v0.070` ladder, and `PROVIDER-SDK-ADDENDUM.md`'s six-rung
`v0.065`-`v0.070` ladder. This ladder follows the same shape, in
landing order (gate and registry first, the language surface itself
next, config third, the two acceptance-specified feature decisions
last):

1. The maturity gate, the package skeleton, and RNI -- nothing
   parses `.rei` source yet (`v0.081`).
2. The lexer, parser, Rei AST, and lowering for the tree subset, plus
   the fixed entry-point shape -- the first version that actually
   compiles a `.rei` file (`v0.082`).
3. `arklight.config.rei`, data-only, as a sibling of
   `arklight.config.py` (`v0.083`).
4. Exceptions and Platform APIs as native Rei syntax, plus RNI's own
   grammar wired in (`v0.084`).

## The ladder

### v0.081 -- Foundation: maturity gate, package skeleton, RNI

Proposal §1.5 (the alpha guard) and the 2026-09-21 acceptance update's
resolutions to Open questions 10 and 11. Nothing here parses a `.rei`
file yet -- this stage is the scaffolding every later stage builds on.

- **Package skeleton.** `arklight/rei_lang/` (not `arklight/rei/`,
  per Open question 10's resolution) -- empty modules for now, plus
  `tests/test_rei_lang_*.py` as the test-file glob. The compiler
  narrator keeps `arklight/compiler/rei/` and `tests/test_rei_narrator.py`
  unchanged; the two packages no longer share a name.
- **The maturity gate, not the Fun tier.** Per Open question 11's
  resolution, the Fun tier (`arklight/fun.py`, the `🎲` banner,
  invariants I3/I4) is retired in full and never built -- checking
  `arklight.CHANNEL == "alpha"` at the `.rei` dispatch point is an
  ordinary "not yet stable" maturity gate, the same mechanism
  `EXPERIMENTAL-APIS.md`'s gate already uses, not a "may vanish
  without notice" playground marker. A `.rei` file or
  `arklight.config.rei` on a non-alpha channel is a loud build error,
  never a silent skip -- the one invariant (I3) that survives the Fun
  tier's retirement, now stated as an ordinary channel guard rather
  than a playground rule.
- **RNI (Rei Native Interface).** `arklight/rei_lang/rni.py`,
  registered the same shape `arklight/experimental.py`'s
  `ExperimentalFeature`/`emit()`/`HEAVY_RELIANCE_THRESHOLD` already
  use -- RNI is Experimental's sibling for Rei authoring, not a
  renamed Fun tier. Inert at this stage (no grammar reaches it yet);
  Stage 4 below wires an actual `.rei` construct into it.
- **`CONFIG["rei_lang"]` known section.** Added to
  `_KNOWN_SECTIONS` alongside the existing `"rei"` (the narrator's,
  unchanged) per Open question 6's resolution -- inert until Stage 3
  gives it real config keys to hold.
- **Suffix dispatch hook.** `arklight build site.rei` recognizes the
  extension ahead of `arklight.parser.discover` (which cannot read
  Rei source), and currently raises "not yet implemented" rather than
  attempting to compile anything -- the hook exists so Stage 2 has
  somewhere to plug in, not so this stage does any parsing.

**Acceptance:** a build that never touches a `.rei` file is
byte-identical with this stage's code present (the same no-residue
invariant the retired Fun tier's own I1 stated, now checked against
the real package instead of a playground one). The maturity gate
fires a loud, named error for a `.rei` file or `arklight.config.rei`
on a non-alpha channel.

### v0.082 -- Tree subset and the entry point

Proposal §2.1, §5, and the acceptance update's language-surface
decisions 1-3 (shared preamble, entry-point class + `site` method,
Java-adjacent markup / Kotlin-adjacent style). The first version that
actually compiles a `.rei` file.

- **Lexer, parser, Rei AST, and lowering** for the Dart-like tree
  subset: constructor calls with named props and positional children
  (no `new`), trailing commas, collection-level `if`/`for`/spread
  inside child lists, string interpolation. Lowers to the same
  `dict[str, ARKNode]` shape `Site.build_ark_ast()` already returns
  for Python-authored sites -- component expansion and everything
  after it is untouched.
- **Shared preamble, promoted to real syntax.** `#include
  <stdlib.ARKlight>` and `#define <name> -> <text>` -- the exact two
  directives `AUTHORING-GUIDE.md` documents for `.py`, resolved by
  the same `PreambleCollisionError` model, same recognized labels, no
  silent winner. The only difference from Python authoring is
  spelling: real C-style preprocessor syntax instead of comment-shaped
  directives, per the proposal's §3.1 phase-4 mapping. A `.rei` file
  that never writes `#include <stdlib.ARKlight>` has no `Page`,
  `Container`, `Button`, etc. in scope, identical to a `.py` site file
  today.
- **The entry-point class and fixed `site` method.** One class per
  valid `.rei` site file; every route is a `public static void
  site(Page <name>)` method on it -- `public static void` and `Page`
  fixed by the acceptance decision, the parameter name file-local.
  One `.rei` file, one route, derived from the filename (Open
  question 2's resolution).
- **Java-adjacent markup, Kotlin-adjacent style, on purpose.** The
  tree surface above stays Java/Dart-adjacent for HTML/JS-equivalent
  authoring; the style-block (CSS-equivalent) grammar reads
  Kotlin-adjacent instead, per the acceptance decision -- exact
  grammar is this stage's own work, fixing only the influence.

**Acceptance:** `hello_site`'s page trees compile from `.rei` to the
same ARK AST as the Python-authored version (tree-equality test).
Malformed `.rei` reports `file:line:col` from Rei's own tokens.

### v0.083 -- Config

Proposal §2.2, §2.3. `arklight.config.rei`, a sibling of
`arklight.config.py`, next to the entry file with no parent-directory
search -- the same rule `find_config` already applies. **Data-only**:
one top-level initializer, no functions, no calls, so it loads without
an evaluator (consistent with Stage "Compute" staying blocked on Open
question 3). Language settings live under `CONFIG["rei_lang"]` (the
section `v0.081` reserved), never the narrator's own `CONFIG["rei"]`.
If both `arklight.config.py` and `arklight.config.rei` exist, that is
a `ConfigError` naming both files -- the same fail-loudly doctrine as
`PreambleCollisionError`, no silent winner.

**Acceptance:** the same `CONFIG` dict a `.py`-authored equivalent
config would produce; the both-files-present `ConfigError` test
passes.

### v0.084 -- Exceptions and Platform APIs

The acceptance update's language-surface decisions 4 and 5.

- **RNI's grammar, decided and wired.** Open question 12 (block,
  annotation, or another shape) is resolved as part of this stage's
  own parser work, and an actual `.rei` construct reaches
  `arklight/rei_lang/rni.py` (from `v0.081`) for the first time --
  gated, inline-warned, counted toward `HEAVY_RELIANCE_THRESHOLD`,
  authoring-side only, never silently unused-but-shipped, the same
  contract `EXPERIMENTAL-APIS.md` already describes for Python's own
  escape hatch.
- **Java-shaped exceptions.** Real `try`/`catch`/`finally` keyword
  syntax, matched by inheritance against typed exception classes --
  the same shape `USER-DEFINED-ERROR-HANDLING-PROPOSAL.md` proposed
  for Python (`catches=` matched by inheritance, `catch`/`finally_`
  restricted to closed-vocab `Action.*`/`Log.*` references, never
  arbitrary executed code), reused here as native keyword syntax
  since Rei owns its own grammar. That Python-side proposal's own
  acceptance is unaffected -- it remains **not accepted** on its own
  terms; only its *shape* is reused here.
- **Platform APIs as an interface.** An `interface`/`abstract class`
  declares the capability surface (`notify`, `clipboard_write`, ...),
  matching `arklight.ir.platform_api.PLATFORM_API_REGISTRY`
  one-for-one rather than introducing a second registry -- authoring-
  surface sugar over the existing `PlatformAPIRef` lowering, type-
  checked at Rei's own parse/lower stage instead of at Python call
  time. No new IR node, no new backend contract.

**Acceptance:** an RNI construct round-trips through the gate the same
way an Experimental-API use does today (inline warning + end-of-build
summary entry); a `.rei` `try`/`catch` compiles to the same lowering
`USER-DEFINED-ERROR-HANDLING-PROPOSAL.md`'s Python shape would if it
were accepted; a `.rei` Platform API interface call compiles to the
identical `PlatformAPIRef` a Python `PlatformAPI.notify(...)` call
already produces.

## Status tracking

| Stage | Covers | Status |
| --- | --- | --- |
| 1 of 4 | Maturity gate, package skeleton (`arklight/rei_lang/`), RNI registry | PLANNED |
| 2 of 4 | Lexer/parser/AST/lowering for the tree subset, shared preamble, entry-point class + `site` method | PLANNED |
| 3 of 4 | `arklight.config.rei`, data-only | PLANNED |
| 4 of 4 | RNI grammar, Java-shaped exceptions, Platform APIs as an interface | PLANNED |
| -- | Compute (`const`, functions, minimal evaluator) | **Blocked** on Open question 3, no version slot |

See `docs/Proposals/REI-LANGUAGE-PROPOSAL.md` for the full design
record and open questions, and `docs/version history/` for each
stage's forward-looking, user-facing summary once filed.
