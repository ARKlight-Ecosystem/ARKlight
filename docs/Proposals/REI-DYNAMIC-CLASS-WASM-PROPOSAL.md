# Rei Dynamic Classes: A WASM-Compiled Tier for Business Logic

## Status

**Proposed. Not accepted, not staged, not scheduled against a version.**
Requests no version slot -- `v0.081`-`v0.084` already belongs to the
accepted Rei language ladder
([`docs/Implementation/REI-LANGUAGE-ADDENDUM.md`](../Implementation/REI-LANGUAGE-ADDENDUM.md)),
and this proposal's own placeholder stages below use `DC0`-`DC5`
labels, the same convention
[`AVM-WASM-SANDBOX-PROPOSAL..md`](<../Far Future Concern/AVM-WASM-SANDBOX-PROPOSAL..md>)
uses for its own unaccepted `A0`-`A6` ladder. Real version numbers are
assigned only if a maintainer accepts this.

**Origin:** every class shape Rei has today -- accepted in
[`docs/Proposals/REI-LANGUAGE-PROPOSAL.md`](REI-LANGUAGE-PROPOSAL.md),
landing across the four-rung ladder above -- is a **tree-authoring**
class: one entry-point class per `.rei` file, one fixed
`public static void site(Page X)` method per route, lowering to the
exact `ARKNode(type, props, children)` shape Python authoring already
produces. That shape is closed vocabulary on purpose (Section 3.1's
translation-phase model ends at "lower to ARK AST," not "run
arbitrary computation"), and it should stay closed vocabulary -- this
proposal does not touch it. What it does not cover is **application
business logic that needs to be fast and needs a real type system**:
validation rules, pricing/ledger math, parsing, anything a site author
would reach for generics, real inheritance, or checked arithmetic to
express cleanly. Today that logic either lives in hand-rolled
`Derive.*`/`Predicate.*` registry entries (closed, but scalar-only and
maintainer-curated) or falls through to `raw_postprocess` (open, but
forfeits every guarantee the closed vocabulary provides). This
proposal is a third option: a second, distinct Rei class kind --
**dynamic classes** -- compiled ahead-of-time to WebAssembly instead
of lowered to ARK AST, carrying the parts of Java-adjacent syntax the
accepted ladder deliberately left out (generics chief among them)
because the tree-authoring surface never needed them.

## TL;DR

- A new top-level declaration in `.rei` source, sitting **beside** the
  entry-point class the accepted ladder already defines, not replacing
  or extending it: `dynamic class Name<T> { ... }`.
- Compiles to a **new backend target**, WebAssembly -- not to ARK AST,
  not to the JS backend's registries. A dynamic class never produces
  an `ARKNode`; it produces a `.wasm` module plus a small, fixed,
  generated JS glue stub, the same "compiler generates the smallest
  bridge necessary" shape `SYSTEM-DESIGN-AGREEMENTS.md` §16 already
  asks for.
- Carries the Java-adjacent features the tree-authoring surface never
  needed and the accepted ladder never added: **generics** (type
  parameters, monomorphized at compile time -- see §4), real fields
  and constructors, method overloading, interfaces with default
  methods, and enums with fields. Exceptions and Platform APIs are
  **not** duplicated here -- they already landed on the tree-authoring
  side in the accepted ladder's Stage 4, and a dynamic class reuses
  that same syntax and lowering rather than inventing a second one.
- A tree-authoring page calls into a dynamic class through a new,
  closed reference kind -- `DynamicClassRef`, structurally the
  `ActionRef`/`PlatformAPIRef` sibling this project already has two
  precedents for -- never through `eval`, `new Function`, or any
  string-as-code path.
- Gated as a **new, separate experimental tier**, not folded into RNI
  or `provider-integration` -- see §6 for why.

## 1. What problem this solves that nothing else does

`ARKlight-ISSUE-REGISTER.md` #8 ("No general-purpose arbitrary
expression layer") and #40 ("Closed vocabulary inherently limits
access to the existing web ecosystem") both name variations of this
gap, and both explicitly decline to solve it by opening the tree
surface itself -- correctly, since a general expression evaluator
inside `Show`/`Computed`/`Bind` would reintroduce exactly the
"string ever executed as code" risk `arklight/backend/js/render.py`'s
htmx-5 section exists to rule out. Three existing escape hatches each
cover a different, narrower slice, and none covers this one:

| Existing mechanism | What it's for | Why it doesn't cover business logic |
| --- | --- | --- |
| `Derive.*`/`Predicate.*` registries | Small, pure, scalar derivations (`Derive.clamp`, `Predicate.in_range`, ...) | Maintainer-curated, one Python file per kind (`v0.061`-`v0.070`'s ten-rung ladder) -- a site author cannot add a new kind without a new ARKlight release |
| `raw_postprocess` | The widest escape hatch that already exists | Forfeits every guarantee: no validation, no type system, no "only ship what's used," `ARKlight-ISSUE-REGISTER.md` #9/#52 already name it as the place escape hatches sit outside compiler guarantees |
| `Provider` (`PROVIDER-SDK-ADDENDUM.md`) | A site talking to an **external service** at runtime | Explicitly not a compute story -- §6 of that proposal rules out "client-side data-fetch orchestration," and there's no external service here, just local computation |
| RNI (`REI-LANGUAGE-ADDENDUM.md` Stage 4) | An escape hatch to arbitrary **JS** output the closed vocabulary doesn't cover | Authoring-side sugar over hand-written JS, still gated as "steps outside the intrinsic model" -- not a typed, generic, compiled-for-performance tier, and every RNI use is meant to be occasional, not the shape a whole pricing engine would take |

Dynamic classes are none of these: not a curated registry entry, not
an unguarded escape hatch, not a network boundary, not a sprinkle of
raw JS. They're a second, smaller compiler -- Rei source to WASM --
sitting next to the first one (Rei source to ARK AST) the accepted
ladder already built, each honest about producing a different kind of
output for a different kind of problem.

## 2. Explicitly not AVM

[`AVM-WASM-SANDBOX-PROPOSAL..md`](<../Far Future Concern/AVM-WASM-SANDBOX-PROPOSAL..md>)
also proposes WebAssembly and is easy to confuse with this one --
worth stating the boundary as plainly as Open question 7 already does
for "the two Reis":

- **AVM** runs **existing, maintainer-curated, pre-built** JavaScript
  libraries inside isolated, discardable WASM sandboxes -- the payload
  is somebody else's npm package, orchestrated by ARKlight's own AVM
  runtime, and nothing about it is authored in Rei or Python.
- **Dynamic classes** compile **the site author's own Rei source** --
  code they wrote in this file, in this proposal's syntax -- ahead of
  time, the same way a C or Rust toolchain compiles source to WASM.
  There is no sandboxing story here because there is no untrusted
  third-party payload to sandbox: the compiler already validated and
  compiled everything that ends up in the module.

If both are ever accepted, they could plausibly share low-level WASM
tooling (a `.wasm`-module packaging convention, a shared loader
stub), but that is a Stage 0 implementation detail for whoever accepts
either one first, not a reason to treat them as the same proposal.

## 3. Sketch of the surface

Not a final grammar -- illustrative, to make "generics, real fields,
compiled for speed" concrete against the tree-authoring surface's
Section 5 sketch in `REI-LANGUAGE-PROPOSAL.md`:

```java
// A dynamic class: computation, not markup. Never returns an ARKNode.
dynamic class Ledger<T extends Numeric> {
    private T balance;

    public Ledger(T initial) {
        balance = initial;
    }

    // Real generics: T is monomorphized at compile time (see Section 4),
    // not erased the way the JVM erases them.
    public T apply(List<T> transactions) {
        for (T t : transactions) {
            balance = balance.add(t);
        }
        return balance;
    }

    public T currentBalance() {
        return balance;
    }
}
```

Called from the tree-authoring side through a new, closed reference
kind, the same shape `Action.*`/`PlatformAPI.*` already establish:

```java
// Inside an entry-point class's site(...) method:
Button(
    "Apply transactions",
    on_click: DynamicClass.call(Ledger.apply, Bind("pendingTransactions")),
)
```

`DynamicClass.call(...)` builds a `DynamicClassRef` (a new
`arklight/ast/nodes.py` node, structurally identical in spirit to
`ActionRef`/`PlatformAPIRef`) validated at build time against the
dynamic class's own compiled signature -- an unknown method name or an
argument-count/type mismatch is a build-time `ComponentError`-shaped
diagnostic, not a runtime `TypeError` surfacing from inside a `.wasm`
call, the same "fail loudly at build time" doctrine every other
closed-vocabulary boundary in this project already enforces.

## 4. Generics: monomorphize, don't erase

The single largest new type-system feature this proposal adds. Two
real options exist, and this proposal recommends the first:

- **Monomorphization (Rust/C++ template style).** Each concrete
  instantiation (`Ledger<Int>`, `Ledger<Decimal>`) compiles to its own
  specialized WASM code, generated at build time once every
  instantiation used anywhere in the site's source is known -- no
  runtime type tag, no boxing, and it fits "only ship what's used"
  exactly: an instantiation nothing calls never gets compiled.
- **Erasure (JVM style).** A single generic implementation plus
  runtime casts. Rejected as the default: it reintroduces a runtime
  type-check surface WASM's own type system doesn't otherwise need,
  and it's a worse fit for "the compiler owns everything it can know"
  (`SYSTEM-DESIGN-AGREEMENTS.md` §1) when every instantiation actually
  used is statically known at `arklight build` time, the same way
  every `Derive.*`/`Action.*` usage already is today.

This is Open question 1 below, not settled here, but monomorphization
is the leading candidate specifically because it needs nothing at
runtime that isn't already true of every other Rei-compiled artifact:
zero dynamic dispatch the compiler couldn't resolve ahead of time.

## 5. What else this tier carries that the tree surface doesn't

Everything below is scoped to dynamic classes only -- **none of it
extends the entry-point/tree-authoring class shape** the accepted
ladder already fixed:

- **Real fields, constructors, and instance state.** A tree-authoring
  class has exactly one method shape and no fields; a dynamic class
  looks like an ordinary Java-adjacent class because it's solving an
  ordinary compute problem, not a tree-construction one.
- **Method overloading.** Explicitly left as "deliberately not
  resolved" for the tree-authoring `site` method in
  `REI-LANGUAGE-ADDENDUM.md`'s v0.082 stage; dynamic classes need it
  for the same reason any typed business-logic language does
  (`apply(T)` vs. `apply(List<T>)`), and resolving it here doesn't
  reopen that other, narrower question.
- **Interfaces with default methods**, distinct from the tree-
  authoring side's Platform-APIs-as-`interface` sugar
  (`REI-LANGUAGE-ADDENDUM.md` v0.084) -- that `interface` type-checks
  calls into `PLATFORM_API_REGISTRY` and carries no implementation of
  its own; a dynamic-class `interface` is an ordinary interface with
  real default-method bodies, compiled like everything else in this
  tier.
- **Enums with fields**, C99's plain enumerator list
  (`REI-LANGUAGE-PROPOSAL.md` §3.1's `stdint.h`-style precedent)
  being too thin for a business-logic tier that wants
  `enum Currency { USD(100), JPY(1) }`-shaped data alongside a tag.
- **Exceptions and Platform APIs are explicitly reused, not
  reinvented.** A dynamic class's `try`/`catch`/`finally` is the exact
  syntax `REI-LANGUAGE-ADDENDUM.md`'s v0.084 stage already lands on
  the tree-authoring side, and a dynamic class that needs a Platform
  API capability calls through the same `interface` that stage
  defines -- this proposal only extends the *class* shape, never
  duplicates syntax the accepted ladder already settled.

## 6. Why this needs its own gate, not RNI's or `provider-integration`'s

Three gated tiers now exist or are proposed once this lands, and each
should stay narrow rather than becoming a catch-all:

| Tier | Registers in | Covers |
| --- | --- | --- |
| Experimental (`arklight/experimental.py`) | Every channel | Steps outside the intrinsic model, real cost to end users (`@media`, `raw-postprocess`, `css-import`, `provider-integration`) |
| RNI (`REI-LANGUAGE-ADDENDUM.md` Stage 4, `arklight/rei_lang/rni.py`) | Alpha-gated | Rei's own escape hatch to arbitrary JS output the closed vocabulary doesn't cover |
| **Dynamic classes (this proposal)** | Alpha-gated, own registry | A distinct, compiled, typed tier -- **not** an escape hatch to unvalidated output; every dynamic class is fully type-checked and compiled before it ships |

Folding this into RNI specifically would be a category error: RNI is
for the moment a `.rei` author needs to reach past the vocabulary into
raw JS, an occasional, visible, ideally-rare event exactly like
`raw_postprocess`. A dynamic class is the opposite shape -- a whole
typed module, meant to be substantial, fully checked at build time,
never "stepping outside the model" the way RNI's own gate assumes.
Proposed as its own registry, `arklight/rei_lang/dynamic_class.py`,
mirroring `ExperimentalFeature`'s shape one more time but with its own
inline note (`🧬 [DYNAMIC CLASS COMPILED]`, illustrative) and its own
end-of-build summary line, alpha-channel-gated the same maturity-gate
way `REI-LANGUAGE-ADDENDUM.md`'s v0.081 stage already gates the
language as a whole.

## 7. Relationship to the blocked "Compute" stage

`REI-LANGUAGE-ADDENDUM.md` leaves one stage explicitly unscheduled:
Compute (`const`, functions, a minimal build-time evaluator), blocked
on the proposal's own Open question 3 -- what interprets a `.rei`
file's own computed expressions, since Python authoring got this for
free from `exec`. This proposal is **not** that stage, and does not
resolve Open question 3 -- Compute is about the tree-authoring side
needing *some* way to fold a `const` expression or run a tiny helper
function at build time, scoped to values that end up in an ARK AST.
Dynamic classes are a full compiled-to-WASM tier for business logic
that runs in the browser at request time, a different problem an
order of magnitude larger. The two could share a parser/type-checker
core once both exist (the proposal's own lexer/parser work from
`v0.082` is a natural foundation for either), but resolving Open
question 3 is not a prerequisite for this proposal, and accepting this
proposal does not resolve it either.

## 8. Explicitly out of scope

- **No change to the tree-authoring entry-point class.** `site(Page
  X)`'s fixed shape, one route per file, is untouched.
- **No garbage collector shared with the JS heap.** A dynamic class's
  own memory management is this proposal's own compiled runtime's
  concern (a bump allocator or an arena, most likely -- Stage `DC2`'s
  problem, not decided here); it does not reach into or share state
  with the JS backend's `State`/vdom machinery.
- **No general FFI to arbitrary WASM modules.** Only Rei-compiled
  dynamic classes are callable this way -- no "load an arbitrary
  `.wasm` file" primitive, which would be exactly the kind of
  unvalidated escape hatch §6 above argues against.
- **No multithreading.** A dynamic class call is synchronous from the
  calling `DynamicClassRef`'s point of view, same as every
  `Action.*`/`PlatformAPI.*` call today.
- **No package ecosystem, no way to import someone else's dynamic
  class across sites.** Same "no stability, package ecosystem, LSP or
  formatter in alpha" non-goal `REI-LANGUAGE-PROPOSAL.md` §6 already
  states for the language as a whole.

## 9. Open questions

1. **Generics: monomorphize or erase.** §4 recommends
   monomorphization; not settled here.
2. **WASM toolchain.** Rei's own lexer/parser/type-checker (from
   `v0.082`) needs a code-generation backend targeting WASM bytecode
   -- hand-rolled, or emit a text-format (`.wat`) and shell out to an
   existing assembler (`wat2wasm`)? The second is a real external
   toolchain dependency this project has avoided everywhere else
   (`DESIGN-NOTES.md`'s own "graceful failure when no JDK is present"
   pattern for the Android backend is the nearest precedent for how
   badly an unavailable toolchain needs to fail if this route is
   chosen).
3. **Memory model.** Fixed-size arena per instantiated call, or a
   longer-lived heap per page load? Affects whether a dynamic class
   can hold state across multiple `DynamicClassRef` calls or is
   re-initialized every time, a real semantic decision, not just a
   performance one.
4. **Async boundary.** A WASM call is currently sketched as
   synchronous (§8). If a dynamic class's logic is expensive enough to
   want off the main thread, does that mean a Web Worker, and if so,
   does `DynamicClassRef` need an async variant alongside the
   synchronous one?
5. **Numeric semantics**, the same question Open question 9 already
   raises for the tree-authoring language: fixed-width integers with
   defined overflow, or checked arithmetic -- doubly relevant here
   since business logic (the `Ledger` example above) is exactly where
   silent overflow is most dangerous.
6. **Debuggability.** A build-time `ComponentError`-shaped diagnostic
   covers a bad `DynamicClassRef` call site, but what does a runtime
   panic *inside* a compiled dynamic class surface as, given the
   browser's WASM stack traces are notoriously unfriendly compared to
   a JS one?
7. **Where the registry's inline banner and summary live** relative
   to RNI's and Experimental's -- same shape, but should the
   end-of-build report merge all three into one combined "gated
   features" block, or stay three separate sections the way
   Experimental and the (retired) Fun tier used to print separately?
