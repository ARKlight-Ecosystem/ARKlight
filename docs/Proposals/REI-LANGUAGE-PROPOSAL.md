# Rei: A Playground Language Frontend for ARKlight (`.rei`)

## Status

**Proposed. Not accepted as written. Alpha only.** Originally filed against
`alpha` @ `8cafffe` (`v0.06501`) in the Rei-Src workspace, and imported into
this repo on 2026-09-20. Its claims about ARKlight were re-checked against
`alpha` @ `5a15ebb` (`0.06511`); see "Re-verification" below. Nothing here is
committed to. Deleting the whole feature is a supported outcome (see "Removal
and graduation").

This is a play area. It is deliberately low-ceremony: small stages, no
stability promise, and a clean exit.

> **Update 2026-09-20: Rei's standing has changed since this was filed.** The
> maintainer has decided that Rei is the **official native source language of
> ARKlight**, added *beside* Python authoring, which stays. So the
> "playground", "Fun tier" and "not accepted" framing in this file no longer
> describes Rei as a whole. What survives as useful input is the C99 mapping,
> the two file types and the stage ladder. Whether an alpha-only guard
> survives as a *maturity* gate, or the Fun tier is retired, is
> **[open]** (Open question 11). The Rei language still stops at the ARK AST:
> `.rei` -> Rei AST -> ARK AST, and nothing below that changes. The companion
> document `WHAT-REI-IS.md` (in the ARKVM repository, `docs/Foundational/`)
> records the decision, its context and the wider open questions. The body of
> this proposal is otherwise unchanged from the version filed.

## Re-verification against `alpha` @ `5a15ebb` (`0.06511`)

Checked in source on 2026-09-20. Everything this proposal says about the
current code still holds:

- `arklight/experimental.py` has `ExperimentalFeature`, `emit()`,
  `HEAVY_RELIANCE_THRESHOLD = 3` and `upstream_candidate`; the inline banner
  is `⚠️  [EXPERIMENTAL FEATURE ACTIVE]` with `-> Feature:` and `-> Note:`
  lines, and the summary block ends with a "Legacy API detected" note.
- `find_config` looks only in the entry file's own directory, and
  `_KNOWN_SECTIONS` is now `{"live_streaming", "android", "desktop",
  "experimental", "csp", "rei"}`.
- No release-channel constant exists; `_ALPHA_WARNING_MARKER` in
  `arklight/cli/main.py` still only tags warning text (Open question 1).
- `discover.py` is static analysis over Python's `ast`, `loader.py` executes
  the module, and `Site.build_ark_ast()` returns `dict[str, ARKNode]`.
- `ARKNode` still has only `type`, `props` and `children`; nothing in `ast/`
  or `ir/` stores a source position (Open question 8).
- `PreambleCollisionError` exists in `arklight/parser/preamble.py`.

What changed since filing, and is reflected below: the compiler narrator this
proposal calls "accepted" **shipped as `0.06510`**, so two names in this
proposal now collide with real code (Open question 10).

## TL;DR

- Two new file types: **`.rei`** (site source) and **`arklight.config.rei`**
  (project config, a sibling of `arklight.config.py`).
- Rei slots in ahead of the existing pipeline and changes nothing below it:

  ```
  Rei source -> Rei AST -> ARK AST -> (existing pipeline, unchanged)
  ```

- It ships as a new API tier, **Fun**, modeled on the Experimental API tier
  (`arklight/experimental.py`, `docs/Foundational/EXPERIMENTAL-APIS.md`) but
  with different meaning: *playground, no stability promise, alpha channel
  only, may vanish without notice.*
- The Rei spec **tracks ISO C99** (its structure, vocabulary, translation model
  and philosophy). It does **not** track the C language: no pointers, no manual
  memory, no `printf`.
- The surface is Dart-like: trees of constructor calls with named props and
  positional children.

## Origin and scope note

The goal behind Rei is a real language: Dart's face on C's spine. Java's
grammar and AST were studied as a reference point and are not expected to
survive as-is. **No code from javac or `java.base` is used.** Those files are
GPL-2.0-only with the Classpath Exception, which cannot be combined with this
repository's GPL-3.0-or-later. Rei's lexer, parser and spec are written from
scratch.

This proposal is intentionally narrower than "design a language". It covers:
the Fun tier, the two file types, how they enter the pipeline, what tracking
C99 means, and a short ladder of stages. Larger language decisions are listed
under "Open questions" and are **not** settled here.

## Motivation

1. **Exploration.** The author wants a place to experiment with a
   purpose-built authoring language for ARKlight's `ARKNode(type, props,
   children)` model without any pressure to make it production-grade.
2. **A small, concrete benefit.** `arklight.config.py` is loaded by
   `exec`-ing Python (`arklight/config.py`, `load_config`). A data-only
   `arklight.config.rei` parsed by Rei's own parser executes nothing, so a
   config file would carry no code-execution surface at all.
3. **Fit with ARKlight's doctrine.** "Compiler first, runtime last" and "fail
   loudly at build time" are easier to enforce for a language ARKlight owns
   than for Python, where the loader has to run the module to learn what it
   contains (`arklight/parser/loader.py`).

## 1. The Fun tier

### 1.1 How it differs from Experimental

| | Experimental | Fun |
|---|---|---|
| Meaning | steps outside the intrinsic model; a real cost to end users | playground; no stability promise |
| Registry | `arklight/experimental.py` | `arklight/fun.py` (new) |
| Availability | every channel | **alpha channel only** |
| Inline warning | multi-line `⚠️ [EXPERIMENTAL FEATURE ACTIVE]` banner | one line: `🎲 [FUN API ACTIVE]` |
| End-of-run summary | full block per distinct feature, plus a "Legacy API detected" note | short block per distinct feature |
| Heavy-reliance nudge | yes (`upstream_candidate`) | **never**. A playground is not a missing-feature signal |
| Silencing | only the nudge, via `CONFIG["experimental"]` | end-of-run block via `CONFIG["fun"]["quiet"]`; the inline line always prints |
| Reaches shipped JS | yes (`devtools_console_reminder`) | **no**. Authoring side only |
| Removal | back-compat "legacy" story | may vanish or change on any alpha, no deprecation cycle |

### 1.2 Registry

`arklight/fun.py` mirrors `experimental.py`:

```python
@dataclass(frozen=True)
class FunFeature:
    id: str                  # e.g. "rei-source", "rei-config"
    inline_note: str         # one line for the inline banner
    detail_lines: list[str]  # short paragraph for the end-of-run block
    since: str               # ARKlight version that introduced it

FEATURES: dict[str, FunFeature] = {...}

def emit(feature_id: str, on_warning=...) -> None: ...
```

Callers own *when* to `emit()`, exactly as with `experimental.emit()`. The
module owns the wording.

### 1.3 What the user sees

Inline, at detection:

```
🎲 [FUN API ACTIVE]: 'site.rei' is compiled by the Rei playground frontend.
   -> Feature: rei-source
   -> Note: alpha only. Syntax and behavior may change or vanish without notice.
```

End of run, once per distinct feature:

```
🎲 Fun API in use
    Feature : rei-source
    Alpha only. Nothing here is covered by any stability promise.
```

### 1.4 Invariants (each one is a test)

- **I1. No residue for non-Rei sites.** A build that never touches a `.rei`
  file is byte-identical with the Fun code present. Golden-output test over
  `examples/`.
- **I2. Authoring side only.** A Rei site lowers to ARK AST, so its output is
  ordinary ARKlight output. Nothing "Fun" is emitted into HTML, CSS or JS.
- **I3. Refuse, never ignore.** On a non-alpha channel a `.rei` file or an
  `arklight.config.rei` is a loud build error. It is never silently skipped.
- **I4. Not a nudge input.** Fun uses never count toward
  `HEAVY_RELIANCE_THRESHOLD`.
- **I5. Clean removal.** See "Removal and graduation".

### 1.5 The alpha guard

No existing channel marker was found in the code: `_ALPHA_WARNING_MARKER`
(`arklight/cli/main.py`) tags warning text and is not a channel flag. The guard
needs a minimal marker, for example `RELEASE_CHANNEL = "alpha"` in
`arklight/__init__.py`, checked by `fun.emit()`. See Open question 1.

## 2. The two file types

### 2.1 `.rei`

- Entry point: `arklight build site.rei`. `build` already takes a path
  (`GETTING-STARTED.md`: `arklight build site.py`).
- Dispatch by suffix happens **before** `arklight.parser.discover`, because
  `discover` performs static analysis over Python's `ast` and cannot read Rei.
- Output of the frontend: the same `dict[str, ARKNode]` (one tree per route)
  that `Site.build_ark_ast()` returns today. Component expansion and
  everything after it are untouched.

### 2.2 `arklight.config.rei`

- Lives next to the entry file, with **no parent-directory search**, the same
  rule as `arklight.config.py` (`find_config`).
- If both `arklight.config.py` and `arklight.config.rei` exist, that is a
  `ConfigError` naming both files. This is the same fail-loudly doctrine as
  `PreambleCollisionError`; no silent winner.
- **Data-only** in its first stage: one top-level initializer, no functions, no
  calls. That is what lets it load without an evaluator (see Open question 3).
- New known section `"fun"` in `_KNOWN_SECTIONS`. The Rei
  *narrator* (shipped as `0.06510`) already owns a top-level `"rei"` section
  (`default_mode`), so language settings must not use that name (Open
  question 6).

### 2.3 Illustrative sketch (non-normative)

Shown only to make the shape reviewable. Spelling is **not** decided.

```
// arklight.config.rei
config = {
    experimental: { heavy_reliance_nudge: false },
    fun:          { quiet: true },
};
```

```
// a tree expression: constructor calls, named props, positional children
Container(
    Link("Home",  href: "/"),
    Link("About", href: "/about"),
    class_name: "nav",
)
// lowers to:
// ARKNode("Container",
//         {"class_name": "nav"},
//         [ARKNode("Link", {"href": "/"},      ["Home"]),
//          ARKNode("Link", {"href": "/about"}, ["About"])])
```

## 3. The spec tracks C99, not C

**Tracks:** the *shape* of ISO/IEC 9899:1999 as a specification, plus its
philosophy. **Does not track:** the C language's feature set.

### 3.1 What "tracks" means

1. **Spec structure.** Rei's spec is organized the way C99 is: conformance,
   terms, environment, language (lexical elements, expressions, declarations,
   statements, preprocessing), library. Rei's "library" is the ARKlight
   vocabulary (`stdlib.ARKlight`).
2. **A translation-phase model.** C99 5.1.1.2 defines eight ordered phases.
   Rei defines its own, mapped onto the pipeline (mapping to be refined):

   | C99 phase | Rei |
   |---|---|
   | 1-2: source mapping, line splicing | decode UTF-8 (no trigraphs) |
   | 3: tokenize | tokenize |
   | 4: run preprocessing directives | `#include`, `#define` (promoting today's `# include` / `# define` comment directives to real syntax) |
   | 5-6: charset mapping, adjacent string concatenation | keep adjacent-string concatenation |
   | 7: translate (syntax + semantic analysis) | parse, check, evaluate `const`, lower to ARK AST |
   | 8: link | hand-off to ARKlight's pipeline |

3. **The behavior taxonomy.** C99 sorts non-fully-specified behavior into
   undefined, unspecified, implementation-defined and locale-specific. Rei
   adopts the vocabulary so every corner of the spec is *classified*, not left
   silent. Whether Rei permits any *undefined* behavior is Open question 4.
4. **The as-if rule (5.1.2.3).** The compiler may transform freely as long as
   the observable result is unchanged. For Rei the observable result is the ARK
   AST and its emitted output. This is ARKlight's "the compiler may specialize
   for the target" agreement, stated in C99's terms.
5. **C99 precedents that fit trees.**
   - *Designated initializers* (`.name = value`) are C's native answer to
     named props. The Dart-style `name: value` spelling is the leading
     candidate; the C99 spelling is the alternative (Open question 5).
   - `//` comments, declarations mixed with statements, `_Bool`, and
     `<stdint.h>`-style fixed-width integer names (a ready answer to "how wide
     is an int").
   - The preprocessor as a compiler-owned name-binding layer.

### 3.2 What it does not track

Pointers, address-of, pointer arithmetic, `void *`, `malloc`/`free`, `union`,
`goto`/`setjmp`, `volatile`/`restrict`, variable-length arrays, `stdio`,
`signal`, K&R and function-pointer declarator syntax, trigraphs, textual macro
hygiene problems, and implicit narrowing conversions.

### 3.3 Sourcing

Cite C99 by section number and consult the public working draft (N1256,
C99 with technical corrigenda). Write Rei's spec as **original prose**. The
standard's text is not reproduced.

## 4. Philosophy

Read from the "Spirit of C" tenets in the C99 Rationale (this proposal's
reading, to be confirmed by the author). Tenets are paraphrased.

| Tenet | Rei reading | Tension |
|---|---|---|
| Trust the programmer | No ceremony: no forced classes, no boilerplate, no nannying syntax | Validation at the ARK AST boundary still happens. That is the closed-vocabulary contract, not distrust |
| Don't prevent what needs doing | An escape hatch exists, but it is **visible** | Exactly what the Experimental and Fun gates enforce |
| Keep the language small | Adding a construct requires removing or justifying one; the spec stays readable in one sitting | "Small" is a budget rule here, not a number |
| One way to do an operation | No duplicate spellings for loops, conditionals or construction | Dart offers several; Rei picks one |
| Fast, even if not portable | Inverts. ARKlight's portability comes from *standard output* (design agreement 15), so Rei reads this as **predictable output over clever output** | The one tenet translated instead of adopted |
| No hidden costs | **No hidden output.** Every emitted node traces to a Rei construct; no implicit wrapper elements | Needs the source-span work in Open question 8 |

## 5. Surface

Dart-like, non-normative, listed only to scope Stage 1:

- constructor calls with named props and positional children; no `new`
- trailing commas
- collection-level `if` / `for` / spread inside child lists
- string interpolation
- a `const` form for subtrees resolvable at compile time
- reusable pieces as plain functions

## 6. Non-goals

- **Not a Python replacement.** Python authoring remains the default and the
  supported path.
- **No new IR node types, no backend changes, no runtime.** Consistent with
  ARKlight's non-goals (`ARCHITECTURE.md`): no browser-side Python, no virtual
  DOM, no runtime execution of source in the browser. Rei is never shipped to
  the browser.
- **No Java compatibility.** No JVM, no `java.*`, no bytecode.
- **No stability, package ecosystem, LSP or formatter in alpha.**
- **No stability promise for the Rei syntax itself.**

## 7. Stages

| Stage | Adds | Acceptance |
|---|---|---|
| **0: The tier** | `arklight/fun.py`, the alpha guard, `"fun"` config section, docs | Registry with one inert entry; I1 and I3 tests pass; warnings render as in 1.3 |
| **1: Tree subset** | lexer, parser, Rei AST and lowering for constructor-call trees, literals, named props, comments, `#include` | `hello_site`'s page trees compile from `.rei` to the same ARK AST as the Python version (tree-equality test) |
| **2: Config** | `arklight.config.rei`, data-only | same `CONFIG` dict as the `.py` equivalent; both-files error works |
| **3: Compute** | `const`, functions, minimal evaluator | **Blocked** on Open question 3. Do not start until decided |

Each stage is independently shippable and independently deletable.

## 8. Tests

New `tests/test_fun.py` and `tests/test_rei_*.py`, following the existing
`tests/` layout.

- I1 to I4 above.
- Round-trip: `.rei` tree to `ARKNode` equals the Python-authored `ARKNode`.
- Malformed `.rei` reports `file:line:col` from Rei's own tokens.
- `.py` and `.rei` config coexisting raises `ConfigError` naming both.

## 9. Removal and graduation

**Removal (supported, zero residue).** Delete `arklight/fun.py` and
`arklight/rei/`, and revert the two hook points (suffix dispatch in the build
entry, config-file lookup). I1 guarantees nothing else changed.

**Graduation.** A Fun feature that proves itself moves up only through a normal
new proposal, to Experimental first and stable after that. There is no
automatic promotion.

## 10. Open questions

1. **Alpha-channel marker.** No channel constant exists today. Add one, or gate
   purely on the code living only on the `alpha` line? (Recommend both.)
2. **Route naming.** `Site.page("/")` is Python-side registration. What names a
   route in `.rei`? Strawman: one file, one route, derived from the filename.
3. **Build-time evaluator.** Python gave loops, conditionals and helpers for
   free by `exec`-ing the module. Rei needs its own interpreter, a static-only
   subset, or a Python escape hatch. This decides Stage 3.
4. **Undefined behavior.** C99 permits it. ARKlight's doctrine is "fail loudly
   at build time". Options: diagnose every would-be UB site, or keep the
   taxonomy fully and let *unspecified* (e.g. argument evaluation order) exist
   where it costs nothing.
5. **Named-argument spelling.** Dart's `name: value` or C99's `.name = value`.
6. **Config key collision.** The narrator (shipped as `0.06510`) owns
   `CONFIG["rei"]` (`default_mode`, in `_KNOWN_SECTIONS`). Language settings go
   under `"fun"`, or wherever Open question 11 lands.
7. **Two Reis.** Rei is the compiler narrator persona and now also the
   language. Always say "the Rei language" where the two could be confused.
8. **Source spans.** `ARKNode` holds only `type`, `props`, `children` (checked
   in `arklight/ast/nodes.py`); nothing in `ast/` or `ir/` carries source
   positions. Validation errors raised after lowering cannot point at a Rei
   line unless a side table (node identity to span) is added. Decide in
   Stage 1. Precedent: `0.06506` already captures `file:line` at a component
   call site with `sys._getframe(1)` (`arklight/api.py`), but only to build an
   error message; it is not stored on the node.
9. **Integer semantics.** Fixed-width names (`int32`-style) with defined
   overflow, or checked arithmetic. Java's wraparound, division rounding and
   UTF-16 string length differ from CPython and JS, so any inherited default
   needs an explicit decision.
10. **Names that now collide with shipped code.** This proposal puts the
    language in `arklight/rei/` and its tests in `tests/test_rei_*.py`. The
    narrator already lives in `arklight/compiler/rei/` and its tests in
    `tests/test_rei_narrator.py`, and prints `[Rei]` lines. The paths do not
    clash, but two packages named `rei` and a `test_rei_*` glob that already
    matches narrator tests will confuse readers. Pick distinct names before
    Stage 1 (for example `arklight/rei_lang/` and `tests/test_rei_lang_*.py`).
    This is Open question 7 applied to the file tree.
11. **Gating, now that Rei is the official language.** Retire the Fun tier
    (Stage 0 and invariants I3 and I4 go with it), or keep an alpha guard as a
    *maturity* gate until Stage 1 ships? Every "Fun", "playground" and "alpha
    only" statement above depends on the answer.

## Correction carried over from `WHAT-REI-IS.md`

Section 4's "No hidden costs" row is **not** one of the C99 Rationale's "Spirit
of C" tenets, as best recalled (the five are: trust the programmer; do not
prevent the programmer from doing what needs to be done; keep the language
small and simple; provide only one way to do an operation; make it fast, even
if not guaranteed portable). Label it as Rei's own addition, and verify against
the Rationale before citing it as C99's.
