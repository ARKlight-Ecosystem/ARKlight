# The Effect Core: an IR Redesign for Trigger-and-Dispatch Primitives

## Status

**Accepted as a direction, high priority. Deliberately NOT staged, no
version slot requested, and implementation is explicitly blocked
pending extensive review.** This is a request to go slowly, on
purpose, on a part of the compiler that touches `validate.py`,
`build.py`, `ir/binary.py`, every usage-collection pass in
`backend/js/render.py`, and every runtime fragment under
`backend/js/runtime/` -- not a small corner. The maintainer has been
through one refactor of this scope already and does not intend to
repeat the experience of doing it fast. Nothing in this document is
authorization to write code against the live tree; it is authorization
to keep discussing it until the Open Questions section is empty, at
which point this status line should be the only thing that changes.

**Explicit non-goal, stated up front because it's the thing most
likely to get re-litigated by accident:** this is not a reopening of
any already-accepted Stage 1-6 design in
[`INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md`](../Implementation/INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md),
and it does not change one character of any site author's code.
`on_click=Action.*(...)`, `Key.on(...)`, `Watch(name, then=...)`,
`Hotkey(key, then=...)` keep their exact signatures, their exact
validation errors, their exact compiled HTML and JSON hydration
blobs (or get new ones only by a separate, explicitly-called-out
decision -- see Open Question 2). This proposal is about what happens
*between* those authoring functions and the runtime they end up
calling, not about the authoring surface itself. If a reviewer finds
themselves debating whether `Hotkey(...)` should take a `combo=`
kwarg instead of folding modifiers into the key string, that's a
different, already-closed conversation -- this document isn't it.

## Origin

Stage 3 of the addendum above (`Hotkey(...)`, page-scoped key events)
was fully designed -- AST shape, validation, IR extraction, HTML
attribute, and a `runtime/hotkey.py` runtime fragment -- and, in the
course of that design work, turned out to be the fourth time this
project has hand-written the same thing: *detect some condition,
dispatch a closed set of `Action.*(...)` references through the same
`ACTION_REGISTRY`, honor the same five timing modifiers
(`prevent`/`stop`/`once`/`debounce`/`throttle`)*. `arklight/backend/js/runtime/watch.py`
(Stage 1 of `vdom-5`) and `arklight/backend/js/runtime/keys.py`
(Stage 2 of this same addendum) already contain near-duplicate
`WeakMap`/`WeakSet` debounce-throttle-once bookkeeping, a duplicate
reimplementation of "walk up from `event.target`" vs. "read a fresh
page-level JSON blob," and duplicate `arkReportError`-wrapped dispatch
loops -- the actual *content* of each file differs only in how the
listener gets attached (element-scoped `keydown`, page-scoped
`store.subscribe`, what would have been window-scoped `keydown`), not
in what happens once it fires.

`arklight/backend/js/render.py`'s `_collect_usage` is the clearest
symptom in the tree today: a function returning a 15-element
positional `tuple[set[str], set[str], set[str], bool, set[str], bool,
bool, bool, bool, bool, bool, bool, set[str], bool, bool]`, unpacked
by position at two call sites, one boolean added per addendum since
`vdom-5`. Every new trigger source means editing that tuple's
declared return type, both unpacking sites, and the return statement,
all three in lockstep, by hand, forever. That is not a one-off papercut
-- it is the IR announcing, structurally, that it has no shared concept
of "a thing that fires and dispatches," only a growing list of
unrelated things that each happen to fire and dispatch.

## The actual claim

Four things that currently look like four different kinds of IR node
(`on_click=`'s `ActionRef`/`PlatformAPIRef` props, Stage 2's flat
`KeyBinding`, `Watch(...)`'s `ARKNode(type="Watch")`, and Stage 3's
would-be `ARKNode(type="Hotkey")`) are, underneath their authoring
syntax, one shape with a closed, small set of variants on exactly one
axis -- *how the condition is detected*:

- `ClickOn(scope=element)` -- today's `on_click=`.
- `KeydownOn(scope=element)` -- today's `on_key=Key.on(...)`.
- `KeydownOn(scope=window)` -- the addendum's Stage 3, `Hotkey(...)`.
- `StateChange(name)` -- today's `Watch(...)`.
- `Intersect(scope=element)` -- `on_reveal=`, which doesn't dispatch an
  action today but could be read as a degenerate case of the same
  shape (see Open Question 5).

Everything else -- *what* fires (a tuple of `Action.*(...)`, same
`ACTION_REGISTRY` lookup, same single-or-tuple handling Stage 1 of
`vdom-5` already generalized `then=` to) and *how firing is throttled*
(the same five `MODIFIER_REGISTRY` tokens, read and applied by
identical logic in all three existing runtime files) -- is already
byte-for-byte the same code, repeated.

The proposal is to stop teaching the compiler's core (`validate.py`,
`build.py`, `_collect_usage`, and the runtime) a new case per
addendum, and instead give it exactly one case -- an `EffectBinding`
-- with `detect` as its one closed, small enum, and have every
authoring-surface function (present and future) **desugar** into it at
a single, fixed point, rather than reach the core as its own IR node
kind at all.

## Precedent, named directly rather than gestured at

This isn't a novel idea being proposed on no authority -- it's the
same move two very different, very battle-tested systems both make,
for the same reason:

**LLVM** keeps its true instruction set deliberately small and
orthogonal, and pushes almost everything else out to *intrinsics* --
functions with a known contract that the optimizer and code generator
don't need new cases for. Chris Lattner, on the original design
rationale (`llvm-dev`, Oct 2004): "I tend to prefer to make only very
simple and orthogonal operations be the instructions, relegating the
rest to be intrinsics... Adding stuff to the IR makes it more powerful
but also more complex to deal with and process." LLVM IR has had
roughly the same handful of true opcodes (`load`, `store`, `call`,
`br`, `getelementptr`, arithmetic) for two decades; everything that
*feels* like a feature is an intrinsic layered on top, never a new
case the verifier or every optimization pass has to learn.

**Racket/Scheme** make the complementary move from the language-design
side: the entire surface language (`cond`, `let`, `letrec`, `for`,
`class`) is macros that *desugar* into a small, fixed core form set
before the real expander ever sees them. The standard framing (see
*Desugaring as a Language Feature*, the standard PL-education
treatment of this): desugaring is used both to shrink a language down
to its core, and to grow a language by adding new surface forms that
expand to that same, unchanged core. A new surface form costs a new
macro; it never costs a new core case.

Applied here: `on_click=`, `Key.on(...)`, `Watch(...)`, `Hotkey(...)`
are the macros. `EffectBinding` is the core form. `validate.py`,
`build.py`'s extraction, `_collect_usage`, and one runtime dispatcher
only ever need to understand `EffectBinding` -- once, permanently --
no matter how many more addenda this project writes.

## Shape of the core (sketch, not final -- see Open Questions)

```python
@dataclass(frozen=True)
class EffectBinding:
    detect: DetectSpec            # the one closed, small enum below
    run: tuple[ActionRef | PlatformAPIRef, ...]
    modifiers: tuple[str, ...]    # prevent/stop/once/debounce/throttle,
                                   # MODIFIER_REGISTRY unchanged

@dataclass(frozen=True)
class DetectSpec:
    kind: str       # "click" | "keydown" | "state-change" | "intersect"
    scope: str      # "element" | "page" | "window" -- not every kind
                     # supports every scope; validated per-kind
    params: dict    # e.g. {"key": "S", "key_modifiers": ("Ctrl",)} for
                     # keydown; {"name": "celsius"} for state-change
```

`on_click=Action.increment("count")` desugars to one `EffectBinding`
with `detect=DetectSpec("click", "element", {})`. `Hotkey("Ctrl+S",
then=Action.set(...))` desugars to one with `detect=DetectSpec("keydown",
"window", {"key": "S", "key_modifiers": ("Ctrl",)})`. `Watch("celsius",
then=...)` desugars to `detect=DetectSpec("state-change", "page",
{"name": "celsius"})`. The desugaring happens once, early, in a single
`_lower_effects(page) -> list[EffectBinding]` pass -- the only place in
the whole compiler that still needs to know `on_click=`/`Key.on`/
`Watch`/`Hotkey` are different things. Validation, extraction into the
IR, and the runtime never see those four names again; they see
`EffectBinding` and branch, at most, on `detect.kind` -- a fixed,
closed set that changes only when a genuinely new *detection
mechanism* (not a new feature) is added -- which per LLVM's own
twenty-year experience with this split, should be rare.

The runtime side collapses the same way: one dispatcher, parameterized
by `detect.kind`, replacing `watch.py` + `keys.py` + the un-written
`hotkey.py` with one file holding the debounce/throttle/once/prevent/
stop bookkeeping exactly once, and four small "how do I attach this
listener" cases (delegated `click`, delegated `keydown` with ancestor
walk, `store.subscribe`, window `keydown` reading a fresh page-level
blob) instead of three-going-on-four full copies of the whole thing.

## What this would touch

Named explicitly because "IR redesign" undersells the blast radius,
and the reviewer should see the real list before signing off on
anything:

- `arklight/ast/nodes.py` -- `KeyBinding` likely retired in favor of
  `EffectBinding`/`DetectSpec`, or kept as a thin authoring-time
  wrapper that lowers to it (Open Question 1).
- `arklight/api.py` -- `on_click=`'s handling inside each component
  constructor, `Key.on`, `Watch`, and the not-yet-written `Hotkey` all
  gain a lowering step; their public signatures do not change (see
  the non-goal above).
- `arklight/ir/validate.py` -- `_validate_behavior_props`,
  `_validate_key_props`, `_validate_watch_declaration`, and the
  would-be `_validate_hotkey_declaration` collapse toward one
  `_validate_effect_binding`.
- `arklight/ir/build.py` -- `_extract_page_state`'s `Watch` branch, and
  the click/key handling currently living as plain `IRNode` props, both
  move through `_lower_effects`.
- `arklight/ir/binary.py` -- `.arklight` round-trip encoding for
  whatever replaces `KeyBinding`/the `Watch` node's `then=` tuple;
  this format is also what the accepted-but-unstaged `.rei` frontend
  (`REI-LANGUAGE-ADDENDUM.md`) will eventually need to target, which
  is argument *for* doing this now rather than after a second frontend
  exists to migrate too (see Open Question 6).
- `arklight/backend/html/attrs.py` and `page_render.py` -- the
  `data-ark-on-key`/`-key-action`/`-key-action-state`/
  `-key-action-args`/`-key-modifiers` and `data-ark-watch` attribute
  families either unify into one `data-ark-effects` shape or stay
  split per `detect.kind` for generated-HTML readability (Open
  Question 2 -- this is a compiled-output format change either way and
  deserves its own sign-off independent of the Python-side IR shape).
- `arklight/backend/js/render.py` -- `_collect_usage`'s 15-element
  tuple shrinks to something keyed by `detect.kind`, not one new
  boolean per addendum.
- `arklight/backend/js/runtime/` -- `watch.py` + `keys.py` (+ the
  unwritten `hotkey.py`) collapse into one dispatcher file with four
  small "attach" cases.
- `arklight/ir/components.py` -- `_rewrite_component_state_refs`'s
  duck-typed `on_click=`/`on_key=` branches need the equivalent case
  for however component-local state namespacing works against the new
  shape.
- Every existing test keyed to the current wire format:
  `tests/test_on_key.py`, `tests/test_vdom_5.py`,
  `tests/test_action_value_from_state.py`, and whatever Stage 3 tests
  would have been.

## Migration posture: strangler fig, not a cutover

Given the maintainer's own stated history with this kind of change,
this is explicitly scoped as incremental, under the existing test
suite, not a single big-bang rewrite:

1. Land `EffectBinding`/`DetectSpec` and the one runtime dispatcher
   *alongside* the existing code, unused by anything yet.
2. Migrate the smallest, newest, least-depended-on surface first:
   `Hotkey(...)` (Stage 3) was never shipped, so it becomes the first
   real caller of the new core instead of the fourth copy of the old
   pattern -- no regression risk, because there is no existing behavior
   to regress.
3. Migrate `on_key=` (Stage 2) next -- shipped, but recent, with one
   dedicated test file (`tests/test_on_key.py`) whose assertions can be
   run unchanged against the new dispatcher to confirm byte-for-byte
   (or deliberately, visibly different -- Open Question 2 again)
   output.
4. Migrate `Watch(...)` (`vdom-5`, Stage 1) last -- the oldest, most
   depended-on of the three, after the other two migrations have
   already shaken out whatever the lowering pass gets wrong.
5. Only once all three are migrated does `_collect_usage`'s old
   per-feature booleans actually get deleted. Nothing is deleted until
   its replacement has run against the full existing test suite with
   no behavior change (or an explicitly reviewed and accepted behavior
   change -- never a silent one).
6. `on_click=`/`on_reveal=`'s still-unbuilt Stage 1 half (the
   `then=`-style tuple-of-actions extension `on_click=`/`on_reveal=`
   never got -- see the addendum's own Stage 1 progress note) is
   deliberately sequenced *after* this, not before: building it against
   the old per-feature plumbing would just be a sixth thing to migrate
   later. It should be the first new feature built directly on
   `EffectBinding` once this lands, which also makes it a second,
   independent proof that the core shape is right before anything
   older gets touched.

## Open questions (this proposal stays unstaged until these have answers)

1. **Does `KeyBinding` disappear, or become a thin authoring wrapper?**
   `KeyBinding` is deliberately flat today specifically so it survives
   `.arklight` binary round-trip without losing its `__ark_type__` tag
   (nested dataclasses inside another dataclass's field lose that tag
   -- see `ir/binary.py`'s own documented "known gap"). Does
   `EffectBinding`/`DetectSpec` hit the exact same flattening problem,
   and if so, does it need the same "deliberately flat, not nested"
   treatment, or does the binary encoder's "known gap" get fixed as
   part of this instead of worked around again?
2. **Does the compiled HTML attribute vocabulary unify or stay split?**
   One `data-ark-effects="[...]"` blob is less code and one less thing
   to keep in sync, but the project has an explicit, stated value on
   generated output staying human-inspectable per `detect.kind`
   (`data-ark-on-key` reads, to a human looking at compiled HTML,
   obviously differently from `data-ark-watch` -- a unified blob loses
   that at a glance). This is a compiled-output format decision, not
   an internal refactor, and should get its own explicit sign-off.
3. **Is `scope` truly orthogonal to `kind`, or does the matrix have
   dead cells?** The sketch above implies `click`×`page`,
   `state-change`×`element`, `intersect`×`window`, etc. all
   type-check even though none of them mean anything. Should `scope`
   be folded into `kind` instead (five flat kinds: `click-element`,
   `keydown-element`, `keydown-window`, `state-change-page`,
   `intersect-element`), trading a smaller cross-product for a less
   "elegant" enum? This is exactly the kind of premature-generality
   trap the LLVM precedent above warns against -- true orthogonality
   should fall out of what the cases actually need, not be imposed
   because it looks tidier on paper.
4. **Does `run` accepting `PlatformAPIRef` belong in the core, or is a
   Platform API dispatch a structurally different thing wearing the
   same clothes?** `on_click=PlatformAPI.confirm(...)` already works
   today through the click interceptor's own `"platform:"` branch,
   never touches `State(...)`, and `used_platform_apis` is already
   tracked separately from `used_actions` in `_collect_usage` for
   exactly that reason. Folding it into `EffectBinding.run` is
   convenient but may be conflating "what detects" with "what kind of
   thing responds," which is the same mistake this whole proposal is
   trying to get the codebase out of on the other axis.
5. **Does `on_reveal=` belong in this core at all?** It has no
   `Action.*(...)` path today (`KNOWN_REVEAL_BEHAVIORS` only, no state
   mutation), it never reads or writes `State(...)`, and folding it in
   only works if `run` is allowed to be empty or behavior-only, which
   none of the other four variants need. This may be a case the
   "small orthogonal core" principle says should stay *outside* the
   core, not a case the core was missing.
6. **Sequencing against `REI-LANGUAGE-ADDENDUM.md`.** The accepted
   (if unscheduled past its first rungs) `.rei` frontend ultimately
   targets "the ARK AST, changing nothing below it" -- which means
   whatever `EffectBinding` ends up being is also what `.rei`'s own
   `Hotkey`/`Watch`/key-event syntax will need to lower into. Doing
   this IR work before `.rei` exists means designing for a second
   frontend that isn't built yet; doing it after means migrating two
   frontends' lowering code instead of one later. No strong recommendation
   here -- flagged because it changes how conservative Open Question 3's
   answer should be.
7. **How much of this does `arklight/ir/schema.py`'s existing
   `MODIFIER_REGISTRY`/`ACTION_REGISTRY` closed-vocabulary pattern
   already solve, versus how much is genuinely new ground?** Worth an
   explicit audit before writing `DetectSpec` from scratch -- it's
   possible `detect.kind` should itself be `SCHEMA`-registered the
   same way component types already are, rather than a bespoke enum,
   for the same "closed, but a human can grep the registry to see the
   whole set" reason `ACTION_REGISTRY` already works that way.

## Acceptance criteria (for moving this out of "unstaged")

This proposal is ready to be staged as an addendum (its own
`EFFECT-CORE-ADDENDUM.md`, the same pattern every accepted proposal
above has followed) once, and only once:

- Every Open Question above has a written answer, not just a leaning.
- A reviewer (not the same session that wrote this document) has
  independently re-derived the `EffectBinding`/`DetectSpec` shape, or
  an explicitly different one, from the four existing cases and agrees
  it covers them without a special case.
- The migration order in "Migration posture" above has been walked
  through against the *actual* `Hotkey(...)` design work already done
  (this proposal's own Origin section) as a concrete first rung, not
  left abstract.
- There is explicit, written agreement on Open Question 2 (the
  compiled-output format question), since that is the one decision
  here that is visible outside the compiler's own source and hardest
  to walk back once sites exist that depend on it.

Until then: no `EffectBinding` code lands on `alpha`, Stage 3's
`Hotkey(...)` implementation (fully designed, not yet written) stays
paused rather than shipped against the old per-feature pattern, and
this document's Status line is the single source of truth for whether
any of the above has changed.
