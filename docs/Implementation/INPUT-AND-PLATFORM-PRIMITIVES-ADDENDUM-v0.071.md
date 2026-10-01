# Input & Platform Primitives Addendum: Staged Order, v0.071

**Shares the `v0.071` slot with `PROJECT-KNOWLEDGE-ADDENDUM.md`**
(`v0.071`-`v0.078`, Stage 1 of 8) -- two independent, unrelated pieces
of accepted work landing in the same milestone, the same precedent
`ARCHITECTURE.md`'s roadmap already documents for `v0.041` and for
`v0.065` (which carried three interleaved pieces at once). Neither
changes the other's scope, stage count, or ordering.

**Status: PLANNED, no code yet.** This file turns a set of
dogfooding-driven gap reports -- two Notepad-class apps in the
ARKlight-Ecosystem org independently hit the same ceiling -- into a
trackable, six-stage landing order, the same role
`JS-VOCABULARY-ADDENDUM-v0.070.md` played for the JS vocabulary
expansion and `PLATFORM-API-IR-ADDENDUM.md` for the Platform API
architecture. It does not re-derive first principles; it exists to
turn "here's a set of forcing use cases" into "here's the order they
ship in and why each one clears the bar."

Every rung below was checked against the same filter
[`SYSTEM-DESIGN-AGREEMENTS.md`](../Foundational/SYSTEM-DESIGN-AGREEMENTS.md)
section 17 states explicitly -- a feature existing elsewhere is not
evidence ARKlight needs it -- and each one is admitted on different
grounds: an authored primitive is closed and validated, fits an
existing extension point, is something only the runtime can know,
costs nothing on a page that never references it, has its interface
owned by ARKlight rather than copied from a browser global, fails
visibly rather than silently, and answers a concrete, already-hit use
case rather than a hypothetical one. `docs/Foundational/
CAPABILITY-MATRIX.md` tracks the full accepted/excluded/open space this
ladder is carved out of; this file is only the staged landing order for
the six rows that cleared the bar.

## Scope filter: what's in this ladder, and what isn't

- **In scope:** six primitives spanning two different extension
  points this project already has -- the event-prop family
  (`on_click=`/`on_reveal=`), the `Watch(...)` side-effect
  declaration, the `State(..., persist=/media=/query=)` source family,
  and the three-entry `PLATFORM_API_REGISTRY`. Nothing here is a new
  IR node type, a new registry *kind*, or a change to how Validation
  or the click/key dispatcher are structured -- every stage is new
  rows in a table that already exists, or one new sibling to a
  mechanism already shipped.
- **Out of scope, on purpose:** everything the Capability Matrix
  marks Excluded (filesystem paths, process spawning, a
  camera/Bluetooth/sensor bridge -- each ruled out by
  [`WHAT-ARKLIGHT-IS.md`](../Foundational/WHAT-ARKLIGHT-IS.md) section
  4, not merely unscheduled) and everything it marks No forcing case
  (`focus`/`blur`/`input`/`change` as event props, held-key state,
  online/offline status, clipboard read into bare `State`, prompt/alert
  dialogs, device info, network status, share sheet). Window control,
  lifecycle events, native menus and tray stay Deferred -- they
  belong with the Android/Desktop backends, neither of which is far
  enough along to earn them (see `PLATFORM-API-IR-ADDENDUM.md`'s own
  Stage 2). A typed hatch for hand-written widget code and user-defined-
  component slots are real gaps but are each a new subsystem the size
  of `Repeat`/`Show` when those landed, not a fragment -- they need
  their own proposal, the same line `JS-VOCABULARY-ADDENDUM-v0.070.md`
  already drew around Tier 3/4 of its own source proposal.

## Why six stages, one milestone

Unlike the ten-version JS vocabulary ladder, this one lands as six
internal stages inside a single milestone slot, `v0.071` -- closer to
how `v0.060` (user-defined components) landed as five `stage0`-`stage4`
sub-stages before rolling up, or how `PLATFORM-API-IR-ADDENDUM.md`
numbers its stages independently of the version column. The six are not
uniform in size (Stage 4 is a new `State(...)` source plus two
derivations; Stage 6 is one registry row), so they're ordered by a
mix of how cheap they are and how much they're already relied on by
the stage after them -- cheapest and most-forcing first, the weakest
forcing case last, so it's the first thing cut if `v0.071` needs to
close early.

## Stage 1 -- `Watch(...)` with more than one effect (PLANNED)

**The gap.** `Watch(name, then=ActionRef)` takes exactly one
`Action.*(...)` reference (`arklight/api.py`'s `Watch(...)`, see
"`vdom-5`"). Chaining two watchers to fake multiple effects from one
state change was floated as a workaround and has not been confirmed
to actually compose -- and even if it does, it is not the same
authored intent as "this one change does two things," and it does
nothing for the symmetric gap on `on_click=`/`on_reveal=`, which take
exactly one `ActionRef`/`BehaviorRef` today.

**The fix.** `then=` (and, by the same extension, `on_click=`/
`on_reveal=`) accepts either a single `ActionRef` (unchanged, zero
cost for every existing call site) or a tuple of them, run in the
order given. No new dispatch mechanism -- the click/watch/reveal
runtime already resolves one `ActionRef` into one dispatch call; this
is that same call made N times instead of once, still inside the
existing try/catch guard per entry point.

**Forcing case.** Both reporting projects hit this independently: a
click that must both mutate state and close a menu, or a state change
that must both derive a value and reset an unrelated flag -- exactly
the shape `Computed(...)`'s own docstring says it will never do itself
("a `Computed(...)` only ever *derives* a value -- it can't dispatch
an `Action.*(...)` of its own").

## Stage 2 -- `on_key=`, element-scoped key events (PLANNED)

**The gap.** The closed vocabulary has no key-event surface at all --
a project-wide search for `keydown`/`keyup` on this branch finds
nothing outside the browser's own `IntersectionObserver`/`matchMedia`
plumbing. `on_click=` is the only interaction prop; any app whose
input model is keyboard-first (a text editor, a game, a kiosk/feature-
phone target) has no authored path in.

**The fix.** `on_key=Key.on("Escape", Action.set(...))` on any element
-- a closed enum of key names (starting with the keys the forcing
cases below actually need: `Escape`, `Enter`, arrow keys, `Tab`),
compiling to one delegated `keydown` listener per page that checks
`event.key` against the declared table, the same "one listener, data-
driven dispatch" shape `wireClickInterceptor` already established for
clicks. The existing `MODIFIER_REGISTRY` tokens (`prevent`, `stop`,
`once`, `debounce`, `throttle`) attach the same way they already do to
an `ActionRef` -- no new modifier vocabulary.

**Forcing case.** A text-editor-class app needs `Escape` to close a
dialog from anywhere focus happens to be, and a keypad/remote-input
target (a feature-phone-class build) has no pointer device at all --
its entire input model is `keydown` on a small fixed key set
(`SoftLeft`/`SoftRight`/`Enter`/arrows), which the existing click-only
wiring structurally cannot reach.

## Stage 3 -- `Hotkey(...)`, page-scoped key events (PLANNED)

**The gap.** Stage 2's `on_key=` is element-scoped -- it fires only
when the carrying element has focus. `Escape`-to-close-dialog and
menu-bar shortcut hints (`Ctrl+S`, decorative today because nothing
backs them) both need to fire regardless of where focus currently is.

**The fix.** `Hotkey("Escape", then=Action.set(...))`, a page-scoped
declaration with the same shape as `Watch(...)` and `State(...)` --
a direct child of `Page(...)`, compiled into the Website IR rather
than reaching any backend as a renderable element -- backed by exactly
one delegated `window`-level `keydown` listener per page, regardless
of how many `Hotkey(...)` declarations it carries (the same "one
listener, many declared entries" discipline Stage 2 and the click
interceptor both already follow).

**Forcing case.** `Escape`-closes-dialog and modifier-combo shortcuts
(`Ctrl+S`) are the two cases Stage 2's element scoping cannot reach by
construction -- confirmed independently by both reporting projects.

## Stage 4 -- Selection as a `State(...)` source (PLANNED)

**The gap.** `State(..., persist=)`, `State(..., media=)` and
`State(..., query=)` are the established family of keys where the
runtime, not `Action.*(...)`, is the writer. Caret position and text
selection are the same shape of fact -- something only the browser
knows, changing independently of any click -- and have no member in
that family yet.

**The fix.** A fourth, independent member of the same `State(...)`
keyword family: `State("sel_start", 0, selection="editor")` (and a
paired `sel_end`-style key, naming shape to be finalized at
implementation), where `selection=` names the `id` of the element
whose `selectionStart`/`selectionEnd` the runtime mirrors into
`State(...)` on `select`/`keyup`/`click`, with the same fail-open
posture `persist=`/`media=`/`query=` already hold (an element that
doesn't exist or isn't selectable degrades to "this key just doesn't
update," never a thrown error). Two new pure derivations,
`Derive.line_number`/`Derive.column_number`, compose a caret offset
and the source text into a 1-based line/column pair -- `Derive.
slice_string` alone cannot do this because it takes literal bounds,
not a scanned position, so it can't be composed into this shape
without a new derivation. Writing the selection back (editor-sets-
caret) stays an open question, out of scope here: its target is a DOM
property, not a `State(...)` value, which is a different shape of
problem than every read-only `State(...)` source family member
shipped so far.

**Forcing case.** A text-editor-class app showing "Ln 4, Col 12" in a
status bar -- the canonical editor affordance -- has no authored way
to read either value today.

## Stage 5 -- Open/save a file, user-mediated (PLANNED, Web)

**The gap.** `PLATFORM_API_REGISTRY` holds `notify`, `clipboard_write`
and `db` -- no capability touches the filesystem at all, so an
editor-class app with "Open" and "Save" menu items has nothing to
call.

**The fix.** Two new one-shot Platform API entries following the
registry's own extension comment ("Extending this table is how a
future capability ... gets added -- one entry here, plus a per-backend
implementation, never a change to the validation/dispatch machinery
that reads this table"): an open that reads a user-picked file's text
into a declared `State(...)` (the same `into=` shape `db.get` and
`Action.geolocate` already use for one-shot reads), and a save that
writes a known string back out through the browser's native
save-file UI. Text only, no paths, no silent background access --
`WHAT-ARKLIGHT-IS.md` section 4's "no general native escape hatch"
line holds exactly because this is scoped to a user-initiated file
picker, the same trust boundary `clipboard_write` and `notify`
already sit behind, not a path/handle the page could read without the
user choosing a file each time.

**Forcing case.** A Notepad-class app's Open/Save menu items are the
textbook case a one-shot, user-mediated file dialog exists to serve,
and replace a hand-rolled server-side file endpoint one of the
reporting projects had stood up as a workaround.

## Stage 6 -- Confirm dialog (PLANNED, Web -- weakest case, first to cut)

**The gap.** No dialog primitive of any kind is in the registry; a
destructive action ("Delete this file?") has no sanctioned way to ask
first.

**The fix.** One more one-shot Platform API entry, `confirm`, wrapping
the browser's native confirm prompt and writing the boolean result
into a declared `State(...)` via `into=` -- the same one-shot-read
shape as Stage 5's file open and `Action.geolocate`. Deliberately not
a general prompt/alert family: `Prompt`/`alert` already has a no-
forcing-case verdict in the Capability Matrix (`Input` +
`bind_value=` and the in-page notice already cover those cases), and
`confirm` is kept separate rather than bundled with them so that
dropping this stage doesn't require re-deriving which half of a
combined entry was actually wanted.

**Forcing case.** The weakest of the six -- "guard a destructive
action" is real but has more workarounds (a two-step UI, an undo) than
the other five rows. Ordered last on purpose: if `v0.071` needs to
close before every stage lands, this is the first one deferred to a
later milestone without reopening anything Stages 1-5 already shipped.

## Status tracking

| Stage | Covers | Status |
| --- | --- | --- |
| 1 of 6 | `Watch(...)`/`on_click=`/`on_reveal=` accept more than one `Action.*(...)` | PLANNED |
| 2 of 6 | `on_key=`, element-scoped key events, closed key enum, existing modifier tokens | PLANNED |
| 3 of 6 | `Hotkey(...)`, page-scoped key events, one delegated `window` listener | PLANNED |
| 4 of 6 | `State(..., selection=...)` + `Derive.line_number`/`Derive.column_number` | PLANNED |
| 5 of 6 | Platform API: open/save a file, text only, user-mediated (Web) | PLANNED |
| 6 of 6 | Platform API: `confirm` dialog (Web) | PLANNED |

See `docs/Foundational/CAPABILITY-MATRIX.md` for the full space this
ladder was filtered out of, including the rows that did not clear the
bar and why.
