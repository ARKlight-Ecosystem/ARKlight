# Runtime Error Handling: Closing the Coverage Gap, With a Default Boundary and a User Override

## Status

**Implemented, alpha (`0.06505`) -- sections 3a, 3b and 3c. Not
implemented: the `Site(on_error=...)` spelling (open question 1) and
a message registry (open question 3). See "Implementation notes
(`0.06505`)" at the end for what was decided.** Out-of-band, numbered
capability fix per `docs/Foundational/V1-DEFINITION.md`'s "Issue
triage during Alpha" section. The rest of this document is the
original proposal text, kept as the design record. Unlike
`PROVIDER-SDK-PROPOSAL.md`, this is **not** proposed as an
experimental feature: nothing here steps outside the intrinsic layout
model `docs/Foundational/EXPERIMENTAL-APIS.md` gates against (see
`EXPERIMENTAL-APIS.md`'s "What counts as experimental" -- this
touches reliability of the generated JS runtime, not viewport-keyed
CSS or an unchecked escape hatch), so it's argued below to belong in
`arklight.js` by default, on every stateful page, the same way
`arkNotify` already does.

**Origin:** built `examples/hello_site/site.py` with `arklight build`
and inspected the emitted `arklight.js` directly, as asked. That
example ships no `State(...)` at all, so its own runtime is nearly
inert here -- `wireClickInterceptor` is registered but `getStore`
always returns `null`, and none of `renderBindings`/`renderRepeat`/
`renderShow`/`wireModelBinding` ship at all (confirmed against
`arklight/backend/js/render.py`'s "only ship what's used" gating).
The gap this proposal is about doesn't show up in that example for
exactly that reason -- it only exists once a site reaches for
`Computed(...)`, `Repeat(...)`, `Show(...)`, or `bind_value=`. So the
example was the starting point, not the finding itself: it led
directly to reading `arklight/backend/js/runtime/*.py` and
`CHANGELOG.md`'s `[0.041] -- JS runtime error-handling hardening`
entry to see what was already decided here and why.

## TL;DR

`[0.041] -- JS runtime error-handling hardening` (`CHANGELOG.md`) did
real, deliberate work: it wrapped `initState()`'s JSON parsing,
wrapped each element's setup and click dispatch in `wireActions()`/
`wireBehaviors()` independently, added a rejection handler to the
`copy` behavior's clipboard promise, and shipped `arkNotify` as the
one user-visible surface for all of it. It also explicitly, by name,
declined to guard `renderBindings()` and `highlightActiveNavLink()`,
reasoning at the time that neither "has a plausible runtime failure
mode given their inputs."

That reasoning was correct **for the vocabulary that existed at
v0.041**. Five stateful primitives have shipped since, under `vdom-4`
through `vdom-8` (`REFACTOR-INDEX.md`, retired -- see `CHANGELOG.md`): `Computed(...)`/
`recomputeAll` (vdom-4), `wireWatchers` (vdom-5), `renderModelBindings`
/ `wireModelBinding` (vdom-6), `renderRepeat` (vdom-7), `renderShow`
(vdom-7), plus the `v0.063` debounce/throttle modifiers on model
bindings. None of them received the equivalent of the v0.041 audit.
Reading them directly (`arklight/backend/js/runtime/`) turns up a real
gap, not a hypothetical one -- see \u00a71.

This proposal is two things: closing that gap with the same
per-element, "one bad case doesn't take down the others" discipline
v0.041 already established, and adding one genuine last-resort layer
(a page-level `error`/`unhandledrejection` listener) underneath all of
it -- with a documented, closed hook for a site author to override
what happens next, in the same "interface, not opinion" spirit
`PROVIDER-SDK-PROPOSAL.md` argues for a completely different surface.

## 1. What's covered today, and what isn't

Read directly out of `arklight/backend/js/runtime/`:

| Path | Guarded? | Where |
| --- | --- | --- |
| `initState()`'s JSON parsing | Yes | `state.py`, whole-function `try`/`catch`, notifies via `arkNotify` |
| `wireClickInterceptor`'s `action:` dispatch | Yes | `dispatch.py`, per-click `try`/`catch` around `action(...)` |
| `wireClickInterceptor`'s `behavior:` dispatch | Yes | `dispatch.py`, separate per-click `try`/`catch` |
| `copy` behavior's clipboard promise | Yes | `behaviors/copy.py`, `.catch()` |
| `wireWatchers`' per-effect callback | Yes | `watch.py`, per-`spec` `try`/`catch` inside the `forEach` |
| `recomputeAll()` (backs every `Computed(...)`) | **No** | `state.py` -- called unguarded, both at `createState()` construction and inside every `set`/`reset`, before subscribers even run |
| `renderBindings()` | **No** | `bindings.py` |
| `renderClassBindings()` | **No** | `bindings.py` |
| `renderModelBindings()` | **No** | `model.py` |
| `renderRepeat()`, incl. `JSON.parse(container.getAttribute("data-ark-repeat-template"))` | **No** | `repeat.py` |
| `renderShow()` | **No** | `show.py` |
| `wireModelBinding`'s `input` listener (`store.set(key, value)`) | **No** | `model.py` |

Two things stand out:

- Every function in the shared `store.subscribe(...)` callback
  registered inside `initState()` (`renderBindings`,
  `renderClassBindings`, `renderModelBindings`, `renderRepeat`,
  `renderShow`) runs back-to-back with no guard between them. If any
  one throws, every function after it in that same callback silently
  never runs for that state change -- not just the one at fault. This
  is precisely the "one bad case takes down every other element on the
  page" failure mode v0.041's own changelog entry names as the reason
  `wireActions()`/`wireBehaviors()` needed per-element guards, just
  recurring one layer up, in code that didn't exist yet when that
  audit was written.
- `wireModelBinding`'s `input` listener and `wireClickInterceptor`'s
  `action:` dispatch are structurally the same shape -- both read a
  `data-ark-*` attribute, then call `store.set(...)` (directly, or via
  an `actions[name]` lookup that itself calls `store.set(...)`,
  see `arklight/backend/js/actions/set.py`). Only one of the two is
  wrapped. Typing into a `bind_value=Bind.model("query")` input is, by
  design (`model.py`'s own docstring), one of the most common ways
  `store.set(...)` gets called on any real site that uses two-way
  binding -- and it's the one path with zero exception handling
  anywhere between the keystroke and whatever `recomputeAll()` /
  the five render passes above do with it.

None of this is about `renderBindings()`/`highlightActiveNavLink()`
specifically -- v0.041's call on those two was reasonable and is left
alone here. It's about the four render passes and the `Computed(...)`
recompute step that arrived after that audit and inherited none of
its guards.

## 2. Why this matters for "any user who builds anything with it"

`Repeat(...)`, `Show(...)`, `Computed(...)`, and `bind_value=` are not
edge-case vocabulary -- they're the primitives `docs/Foundational/
DESIGN-NOTES.md` and the JS-vocabulary addenda describe as the actual
answer to "how do I build something interactive" beyond a static
toggle button. A site author reaching for any of them is, by
construction, past the point `examples/hello_site` exercises. Today,
the first time one of those four code paths hits an unanticipated
shape -- a `Repeat(...)` item whose structure doesn't match what
`spec.text.item_value`/`spec.children` expects, a `Computed(...)`
recompute racing a rapid sequence of model-bound keystrokes, anything
neither this project's own tests nor the author anticipated -- the
failure is a bare, uncaught exception. No `arkNotify`. No console
message beyond the browser's own default "Uncaught TypeError" log,
which most end users never open. Depending on which render pass failed
first, the rest of that state change's UI updates silently don't
happen either, and the page is left showing stale data with no
indication anything went wrong.

## 3. Proposal

Two layers, deliberately kept separate:

### 3a. Close the coverage gap (same discipline as v0.041, extended)

Wrap `recomputeAll()`'s per-`Computed(...)` entry (not the whole
function -- one bad `Computed(...)` shouldn't stop every other
computed value from recomputing, same reasoning `wireWatchers`
already applies per-`spec`). Wrap each of `renderBindings`,
`renderClassBindings`, `renderModelBindings`, `renderRepeat`,
`renderShow` **per matched element inside their own `forEach`**, not
as one `try`/`catch` around the whole function -- so one malformed
`data-ark-repeat-template` on one container doesn't stop `Show(...)`
elsewhere on the page from updating, mirroring exactly what v0.041
already did for `wireActions()`/`wireBehaviors()`. Wrap
`wireModelBinding`'s `store.set(key, value)` call the same way
`wireClickInterceptor`'s `runAction` already wraps its own
`action(...)` call -- closing the asymmetry in \u00a71 directly.

Each of these, on failure, calls `arkNotify(...)` with the same kind
of specific, this-is-what-broke message v0.041 established (not a
generic "something went wrong" for every case) and otherwise leaves
the rest of that update pass to keep running.

### 3b. A default, page-level last-resort boundary

Even with 3a done, a truly unanticipated failure -- something outside
all of the above call sites, e.g. a future primitive that hasn't had
its own audit yet -- currently has no floor at all. A single
`window.addEventListener("error", ...)` and
`window.addEventListener("unhandledrejection", ...)` pair, registered
once at the same point `wireClickInterceptor`/`wireModelBinding` are
today, calls `arkNotify` with a fixed, generic fallback message. This
doesn't replace 3a's per-path guards -- those still produce a more
specific, more localized message and keep the rest of the page
working -- it's strictly the floor underneath them, and underneath
anything not yet covered.

Shipped only on a page that ships any of this runtime JS at all (same
`needs_htmx`/`has_computed`/etc. gating `_build_runtime_js` already
does for everything else here) -- a page with no `State(...)` and no
behaviors, like `hello_site`'s current pages, ships no `arklight.js`
error-handling code at all, unchanged from today.

### 3c. A user override, kept as a closed hook -- not an opinion

`arkNotify`'s fixed on-page toast is a reasonable default, but it's
still ARKlight's own opinion about what "something broke" should look
like. Some sites will want to log to their own analytics, show
something styled differently, or do nothing visible and only report
silently. Rather than growing `arkNotify` itself into a
configuration surface, the compiler emits one more optional,
`typeof`-guarded call before `arkNotify` runs -- the same "call it if
the identifier exists, no-op otherwise" pattern `initState()` already
uses for `wireWatchers`/`renderModelBindings`/`renderRepeat`/
`renderShow`:

```js
if (typeof window.ARKLIGHT_ON_ERROR === "function") {
  window.ARKLIGHT_ON_ERROR(message, err);
}
```

A site author supplies `window.ARKLIGHT_ON_ERROR` however they already
add their own script -- there is nothing here for ARKlight's core to
implement, test against a live logging backend, or take a support
burden for, deliberately the same "closed interface, zero shipped
implementation" posture `PROVIDER-SDK-PROPOSAL.md` \u00a72 argues for a
completely different surface. `Site(on_error=...)` is the sketched
Python-side spelling -- illustrative, not final (see Open Questions).
Returning `false` from the override could suppress `arkNotify`'s
default toast for sites that want to fully replace it rather than
supplement it; returning anything else (or not being declared at all)
leaves `arkNotify` running exactly as it does today. Every one of
these calls stays inside its own `try`/`catch`, same as `arkNotify`
itself already is -- a broken override must never become a second,
worse failure.

## 4. Why this doesn't violate "Compiler First"

`SYSTEM-DESIGN-AGREEMENTS.md` \u00a72 assigns the compiler five
responsibilities for any runtime-delegated behavior: deciding *that*
it's needed, *which* behavior, what data it needs, what's baked in,
and what's omitted. All five still hold here. The compiler decides
*whether* any error-handling code ships at all (gated on whether the
page ships runtime JS, same as every other fragment in
`_build_runtime_js`); it decides the fixed, closed message text for
each guarded path (no site-authored strings interpolated into
`arkNotify`, avoiding the "user-controlled string rendered as
content" question entirely); and it decides whether the
`ARKLIGHT_ON_ERROR` `typeof` check is even worth emitting. What it
cannot decide ahead of time is *whether a given page load will
actually hit one of these failure modes* -- that's runtime by
definition, the same category `SYSTEM-DESIGN-AGREEMENTS.md` \u00a72
already places "user input" and "network responses" in.

## 5. Explicitly out of scope

- No new derivation-level validation (e.g. rejecting a malformed
  `Repeat(...)` spec at build time) -- that's a `arklight/ir/
  validate.py` concern, a different layer, and doesn't remove the
  need for a runtime floor regardless (a spec that's valid at build
  time can still meet unexpected *data* at request time, which is
  the actual failure mode most of \u00a71's table is about).
- No remote error reporting, analytics, or third-party logging SDK
  bundled into ARKlight's core -- `ARKLIGHT_ON_ERROR` is exactly the
  seam a site author wires their own reporting through, same
  division of responsibility `PROVIDER-SDK-PROPOSAL.md` draws for
  external services generally.
- No change to `arkNotify`'s own visual design or to the CLI/pipeline
  error handling `[0.041] -- CLI & pipeline error-handling hardening`
  already covers -- this proposal is scoped entirely to the generated
  client-side runtime, the same boundary that changelog entry drew
  for itself.

## 6. Open questions

1. **Is `Site(on_error=...)` the right spelling?** It reads as a
   build-time site-wide setting, which is what's intended, but it
   sits next to `Site(app_shell=...)`/`Site.raw_postprocess(...)` in
   `arklight/api.py` and should be named to avoid implying it's
   itself an experimental escape hatch -- it isn't one, by the same
   "not stepping outside the layout model" argument as the rest of
   this proposal, and register accordingly.
2. **Should 3a's per-path `arkNotify` calls also funnel through
   `ARKLIGHT_ON_ERROR`, or only 3b's page-level catch-all?** Funneling
   all of them gives one consistent override point at the cost of a
   few more `typeof`-guarded calls in already-dense per-element
   `forEach` loops; funneling only 3b keeps the granular paths simple
   but means an author who wants to override *everything* has to
   handle two different mechanisms.
3. **Does the message vocabulary need its own small registry**, the
   way `arklight/experimental.py`'s `FEATURES` dict owns every
   experimental-feature warning's text in one place, rather than each
   guarded call site hand-writing its own string inline as today?
   Worth doing once the per-path count in \u00a71's table grows much
   past what it is now, not obviously worth it yet.

## 7. Relationship to other work

Directly closes the gap `CHANGELOG.md`'s `[0.041] -- JS runtime
error-handling hardening` entry left open by construction (its own
reasoning was correct for the vocabulary it audited; this proposal is
the follow-up audit for everything `vdom-4` through `vdom-8` added
afterward). `PROVIDER-SDK-PROPOSAL.md` is the closest sibling in
spirit, not mechanism: both argue for a closed, ARKlight-owned
interface with zero shipped opinion about what a site author does on
the other side of it -- there, an external service; here, what
"something broke" should look like to an end user.

## Implementation notes (`0.06505`)

What shipped, and how the three open questions were answered.

**3a -- per-element guards.** `recomputeAll` (per `Computed(...)`
entry), `renderBindings`, `renderClassBindings`, `renderModelBindings`,
`renderRepeat` (per container), `renderShow`, and `wireModelBinding`'s
`store.set(...)` write-back (including the debounced and throttled
paths) each catch inside their own loop iteration, so one bad case
reports and the rest of the pass -- and the rest of the
`store.subscribe` callback -- keeps running. Each path has its own
fixed message; no site-authored text reaches the notice.

**3b -- page-level boundary.** `wireErrorBoundary()` registers `window`
`error` and `unhandledrejection` listeners once, at `DOMContentLoaded`
next to `wireClickInterceptor` (never from `arkInitPage()`, so an
`app_shell` boosted swap can't double-register it). It ships wherever
`arkNotify` ships, so a page with no `State(...)` and no click
interceptor is byte-for-byte unchanged. Browser-generated
`ResizeObserver loop` notices are ignored -- benign, and not a page
fault. Note the boundary sees *every* uncaught error on the page,
including ones from a site author's own scripts; that is the intended
floor, and `ARKLIGHT_ON_ERROR` returning `false` is how a site opts out
of the toast.

**3c -- the override hook.** `arkReportError(message, err)` is the one
funnel: console first (a guarded failure is no longer an uncaught
exception, so the console line is the developer's only trace), then
`window.ARKLIGHT_ON_ERROR(message, err)` if it is a function, then
`arkNotify(message)` unless the hook returned exactly `false`. Every
step is independently guarded, so a broken hook, console or notice
never blocks the next step or becomes a second failure. ARKlight ships
no implementation of the hook.

**Open question 1 (`Site(on_error=...)`).** Not implemented. The hook
is a plain `window` function a site supplies through its own script
file (a strict-CSP page can't take it inline), which needs nothing
from the compiler. A Python-side spelling can be added later without
changing the runtime contract.

**Open question 2 (funnel everything?).** Yes. The existing v0.041
guards (`initState`, both `wireClickInterceptor` dispatch branches,
`wireWatchers`) and the platform-API branch now call `arkReportError`
too, so an author has exactly one override point. Feature-availability
notices (clipboard/geolocation/paste unavailable, `PlatformAPI.notify`'s
fallback) are not errors and still call `arkNotify` directly. `arkNotify`
itself is unchanged.

**Open question 3 (message registry).** Not done; the per-path count is
still small. Revisit if it grows.

A failing element reports on every pass that hits it (each state
change), not once. `arkNotify` reuses one on-page element and restarts
its timer, so the notice doesn't stack; a hook receives every call.

Tests: `tests/test_runtime_error_handling.py`.
