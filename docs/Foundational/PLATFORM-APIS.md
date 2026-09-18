# Platform APIs

Settled design record for ARKlight's platform API interface layer,
accepted from
[`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`](../Proposals/PLATFORM-API-IR-PROPOSAL.md)
and staged in
[`docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`](../Implementation/PLATFORM-API-IR-ADDENDUM.md).
This file records the decisions that don't change as more capabilities
or backends are added; the addendum tracks the staged rollout itself.

## Terminology

**Platform backend** -- a compilation target capable of implementing
ARKlight's platform interfaces (Web, Android, Linux Desktop).

**Platform API interface** -- a backend-independent semantic interface
represented in ARKlight IR (notifications, clipboard, filesystem
access, device information, platform storage, future capabilities).

**Platform implementation** -- the target-specific implementation of a
platform API interface (a Web implementation in JavaScript, an Android
implementation in Kotlin, a Desktop implementation in C).

> **The interface belongs to ARKlight. The implementation belongs to
> the platform backend.** Source describes intent; the backend
> implements the target. The compiler is not a collection of
> platform-specific API calls.

## Architectural model

```text
                 ARKlight Source
                       |
                       v
                  Python AST
                       |
                       v
                    ARK AST
                       |
                       v
                  Normalization
                       |
                       v
                   Website IR
                       |
                       +-- Web application semantics
                       |
                       +-- Platform API requirements
                                  |
                                  v
                         Backend capability check
                                  |
                    +-------------+-------------+
                    v             v             v
                  Web          Android       Desktop
                    |             |             |
                    v             v             v
                JavaScript      Kotlin          C
                Web APIs      Android APIs   OS APIs
```

The platform interface is an IR-level concept, not a collection of
ad-hoc source transformations. In code: an author writes
`PlatformAPI.notify(...)`/`PlatformAPI.clipboard_write(...)`
(`arklight.api.PlatformAPI`) on `on_click=`, which compiles to a
`PlatformAPIRef` (`arklight.ast.nodes`) -- validated against
`arklight.ir.platform_api.PLATFORM_API_REGISTRY` at Validation, then
checked against the selected backend's own
`BACKEND_PLATFORM_API_SUPPORT` entry once per build
(`check_backend_support`).

## Web is the default

If no native platform backend is selected, platform interfaces resolve
against their Web implementations. This isn't a fallback added later
-- Web is the **first-class default implementation**, so an ordinary
ARKlight site continues to compile to HTML/CSS/JavaScript without
requiring Android or Desktop support at all.

## Native implementations are earned by backends

A platform backend does not automatically receive access to every
platform API interface merely because the backend exists. Each backend
explicitly implements the interfaces it can support:

```text
Interface              Web       Android       Desktop
--------------------------------------------------------
notify                 done      later         later
clipboard_write        done      later         later
```

> **An interface becomes available on a platform only when that
> platform backend implements its contract.** This lets the compiler
> architecture mature before every native target is forced to expose a
> large native API surface -- see
> `docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`'s Stage 2 for
> where that work lands once it starts.

## Relationship to the `copy` behavior

`PlatformAPI.clipboard_write(text)` is not a duplicate of the
pre-existing `copy` **named behavior**
(`on_click="copy"`/`behavior_target=`, `arklight/backend/js/behaviors/
copy.py`, shipped in `v0.063`'s JS vocabulary addendum) -- both end up
calling `navigator.clipboard.writeText` on the Web backend, but they
answer different authoring questions:

- **`on_click="copy"`** -- "copy whatever is currently in this other
  element." The text is read from the DOM, at click time, from
  whatever element `behavior_target` (compiled to `data-ark-target`)
  points at (a `<textarea>`'s `.value`, or another element's
  `.textContent`). It also gives the clicked element itself a
  transient "Copied!" label swap -- UI feedback tied to that specific
  interaction pattern (a visible "copy this snippet" button).
- **`PlatformAPI.clipboard_write("some text")`** -- "copy this exact,
  already-known string." The text is a literal value the author
  supplied at build time (or, once `Bind`/derived values are wired
  into `PlatformAPIRef` args in a future stage, at most a value the
  compiler already knows about) -- there's no DOM element to read
  from, and no click-target UI feedback, since a `PlatformAPIRef`
  carries only a capability name and its own JSON args, not a
  `data-ark-target`.

The distinction generalizes: named behaviors describe *DOM-local
interaction patterns* (toggle a class, scroll to a target, dismiss an
element, copy from a target); Platform APIs describe *capabilities of
the underlying execution platform itself*, addressed with values the
author already has in hand rather than values read off the page at
click time. An interface that reads better as "do something to/with an
element already on this page" stays a behavior; an interface that
reads as "ask the platform to do something, given these inputs" is a
Platform API. This is also why `clipboard_write` takes a `text`
argument at all while a hypothetical `clipboard_read` (not yet
proposed) would look more like `Action.geolocate` -- a state-mutating
write-back -- than like either `copy` or `clipboard_write`: reading
the clipboard produces a value with nowhere to put it *except*
`State(...)`, the same shape `Action.geolocate` already established
for one-shot platform reads.

Two authoring paths to the same browser API is an accepted, understood
overlap, not an oversight -- an author reaching for "copy whatever's
in this input" and an author reaching for "copy this known string"
have different requests, and forcing either one through the other's
shape would mean either threading a fake DOM target through
`clipboard_write` or threading a literal string through `copy`'s
target-selector-only argument.

## Zero-cost requirement

A site that never references a Platform API capability ships none of
this layer's runtime code -- no `platformApis` object, no extra
dispatch branch cost beyond the fixed, always-present (but empty when
unused) `"platform:"` check in the click interceptor. Only the
capability fragments a site's IR actually references are concatenated
into the shipped `platformApis` dispatch object
(`arklight.backend.js.render._platform_apis_object_js`), the same
"only ship what's used" discipline every other closed-vocabulary
dispatch object (`actions`, `behaviors`, `derivations`) already
follows.
