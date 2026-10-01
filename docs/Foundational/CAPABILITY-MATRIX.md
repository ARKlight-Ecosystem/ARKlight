# Capability Matrix

_Current as of `alpha` (`48feb6d`), with the planned `v0.071` column
showing only what is accepted but not built. Status values are read
from the registries and source directly; cross-check `PROGRESS.md`'s
Snapshot table if something might have moved since this was last
updated._

## What this is, and what it is not

A single place that answers, for each thing an interactive page might
want to do: does ARKlight do it today, is it planned, or was it
deliberately left out -- and *why*. It exists so that every exclusion
is a **decision with a reason** rather than a gap nobody noticed.

It is **not** a feature-parity chart. [`SYSTEM-DESIGN-AGREEMENTS.md`](SYSTEM-DESIGN-AGREEMENTS.md)
section 17 is explicit that a feature existing in another framework "is
not evidence that ARKlight needs the feature," so no row here is
justified by what some other tool ships. A row earns a place in the
roadmap only by passing the filter in
[`INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md`](../Implementation/INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md)
(closed and validated, fits an existing extension point, only the
runtime can know it, zero cost when unused, interface owned by ARKlight,
fails visibly, and a concrete forcing use case).

**Status values.** *Shipped* -- on this branch. *Planned* -- accepted
and staged, no code yet. *No forcing case* -- not admitted because the
project's own bar is unmet; a future use case reopens it. *Deferred* --
belongs with a backend that isn't far enough along to earn it.
*Excluded* -- ruled out by design, not by schedule. *Gap* -- a
documented hole with no decision yet.

## Events and input

| Capability | Today | `v0.071` | Reason |
| --- | --- | --- | --- |
| Click (`on_click=`), named behaviors, `Action.*`, `PlatformAPI.*` | Shipped | -- | The original interaction model. |
| Typed-text binding (`bind_value=Bind.model(...)`, debounce/throttle) | Shipped | -- | |
| Scroll visibility (`on_reveal=`) | Shipped | -- | |
| More than one effect from one event | Gap | **Planned** (Stage 1 of 6) | A `Watch(...)`'s `then=` takes exactly one `ActionRef`; chaining `Watch`es as a workaround is unconfirmed, and doesn't fix the same single-`ActionRef` limit on `on_click=`/`on_reveal=`. |
| Key events, element-scoped (`on_key=`) | Gap | **Planned** (Stage 2 of 6) | Forcing cases: a keyboard-first editor, a keypad-only target whose input model is `keydown` and has no click surface at all. |
| Key events, page-scoped (`Hotkey(...)`) | Gap | **Planned** (Stage 3 of 6) | `Escape` and modifier-combo shortcuts must fire regardless of where focus currently sits -- element scoping structurally can't reach that. |
| `focus`, `blur`, `input`, `change` as event props | Gap | No forcing case | `bind_value=` + `Watch(...)` already react to typed text. |
| Hold/release (`keyup`, held-key state) | Gap | No forcing case | |

## State sources the runtime must supply

| Capability | Today | `v0.071` | Reason |
| --- | --- | --- | --- |
| Persisted state (`persist=True`, `localStorage`) | Shipped | -- | |
| Viewport state (`media=`) | Shipped | -- | |
| URL query state (`query=`, `history=`) | Shipped | -- | |
| Text selection / caret (`selection=`) | Gap | **Planned** (Stage 4 of 6) | Only the browser knows it; a fourth, independent member of the existing `persist=`/`media=`/`query=` `State(...)` source family. |
| Line / column from a caret | Gap | **Planned** (Stage 4 of 6) | `Derive.slice_string` takes literal bounds, not a scanned position, so it can't compose this on its own; two new pure derivations instead. |
| Online/offline status | Gap | No forcing case | Would be a `State` source like `media=`, not a platform call. |
| Writing the selection back | Gap | No forcing case | Target is a DOM property, not `State(...)` -- a different shape of problem than every read-only `State` source shipped so far; open design question. |

## Platform capabilities

The interface layer is [`PLATFORM-APIS.md`](PLATFORM-APIS.md); the
registry on this branch holds `notify`, `clipboard_write` and `db`,
all three implemented on Web, with `db` also earned by Android
(SQLite behind a narrow, origin-restricted bridge). Desktop implements
none of the three yet.

| Capability | Today | `v0.071` | Reason |
| --- | --- | --- | --- |
| Notifications (`PlatformAPI.notify`) | Shipped (Web) | -- | |
| Clipboard write (`PlatformAPI.clipboard_write`) | Shipped (Web) | -- | |
| Clipboard read into a DOM element (`paste` behavior) | Shipped | -- | |
| Clipboard read into `State` (DOM-less) | Gap | No forcing case | The `paste` behavior already covers the editor case. |
| Local key/value storage (`PlatformAPI.db`) | Shipped (Web, Android) | -- | |
| Geolocation (`Action.geolocate`) | Shipped | -- | |
| Open / save a file (user-mediated) | Gap | **Planned** (Stage 5 of 6, Web) | Text only, no paths -- the same user-mediated trust boundary `clipboard_write`/`notify` already sit behind. Replaces a hand-rolled file endpoint one dogfooding project had stood up as a workaround. |
| Confirm dialog | Gap | **Planned** (Stage 6 of 6, Web) | Guards a destructive action; the weakest forcing case of the six, ordered last so it's the first thing cut if the milestone needs to close early. |
| Prompt / alert dialogs | Gap | No forcing case | `Input` + `bind_value=` and the in-page notice already exist. |
| Device info, network status, share sheet | Gap | No forcing case | |
| Window control, lifecycle events, native menus, tray | Gap | Deferred | Tied to the Android/Desktop backends; neither is far enough along to earn these capabilities yet ([`SYSTEM-DESIGN-AGREEMENTS.md`](SYSTEM-DESIGN-AGREEMENTS.md) section 12). |
| Page title driven by state, leave-page guard | Gap | Open | Meaningful on Web; needs a confirmed forcing case. |
| Filesystem paths, directories, watchers | Excluded | -- | A generic native escape hatch. File access stays user-mediated, one picked file at a time (Stage 5), never a path or handle. |
| Spawning processes / shell execution | Excluded | -- | Conflicts with the closed vocabulary. |
| Camera, Bluetooth, sensors, contacts, calendar | Excluded | -- | "No camera/Bluetooth/sensor bridge, by explicit design choice" ([`WHAT-ARKLIGHT-IS.md`](WHAT-ARKLIGHT-IS.md) section 4). |
| Native backends implementing any of the above | Deferred | -- | A backend earns a capability by implementing its contract; Android has earned exactly one (`db`), Desktop none. |

## Authoring structure and tooling

| Capability | Today | `v0.071` | Reason |
| --- | --- | --- | --- |
| Components with props (`@component`) | Shipped | -- | |
| Slots / children for user-defined components | Gap | -- | Documented gap ([`WHAT-ARKLIGHT-IS.md`](WHAT-ARKLIGHT-IS.md) section 6); a separate compiler change, the size of `Repeat`/`Show`, not a fragment this ladder's filter admits. |
| Fetch / HTTP | Gap | -- | By design for now; [`PROVIDER-SDK.md`](PROVIDER-SDK.md) is the accepted route for external services. |
| Hand-written widget code | Shipped, gated | -- | `ScriptExtension`, experimental ([`EXPERIMENTAL-APIS.md`](EXPERIMENTAL-APIS.md)); the JS itself is unchecked. |
| A typed boundary for that hatch | Gap | Not admitted | A new subsystem (IR node, schema, Validation); needs its own proposal, same reasoning as the slots row above. |
| Python-side page simulator | Gap | Not admitted | Derivations and predicates have Python mirrors; actions do not. Tooling, unscheduled. |

## Keeping this honest

A future close-out should add a test that every `PLATFORM_API_REGISTRY`
entry has a row in the Platform capabilities table above, so adding a
capability without recording the decision fails the suite -- the same
discipline `PLATFORM-APIS.md`'s own "zero-cost requirement" section
already holds code to. Until that lands, this file is maintained by
hand: when a stage ships, change its row's *Today* cell and trim the
*Planned* marker in the same change.
