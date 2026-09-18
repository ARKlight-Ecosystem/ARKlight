# ARKlight Platform API Interface Proposal

## Status

**Accepted, staged as a two-stage implementation ladder** --
[`docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`](../Implementation/PLATFORM-API-IR-ADDENDUM.md)
(`v0.065`). Stage 1 of 2 (the Web reference implementation -- the
architecture itself, plus `notify`/`clipboard_write` as its first two
capabilities) has shipped; Stage 2 (Android/Desktop native
implementations) stays PLANNED until each of those backends is mature
enough to earn a capability, per Section 6/22 below. The settled
design decisions this proposal argues for -- terminology, the
architecture model, the Web-default/native-earns-later split -- are
recorded permanently in
[`docs/Foundational/PLATFORM-APIS.md`](../Foundational/PLATFORM-APIS.md)
once Stage 1 landed; this document is kept in full, unedited, as the
proposal that design was accepted from.

- **Type:** Architecture / compiler proposal
- **Scope:** Compiler IR, platform API interfaces, backend
  implementation contracts
- **Initial target:** Web
- **Future targets:** Android, Linux Desktop, and other mature ARKlight
  platform backends

## Framing note

What this proposal describes is **not a conventional backend**, and
that word is avoided below wherever a more precise one is available.
The cleaner model is a **platform API interface layer in the compiler
IR**, with the Web implementation as the default and native
implementations added only when a platform backend has matured enough
to support them.

This is structurally closer to the Web-first/native-extension model
used by [Capacitor](https://capacitorjs.com/docs), but ARKlight keeps
the interface itself compiler-owned rather than making a runtime/plugin
system the primary abstraction -- see Section 17 for where the
borrowing stops.

---

## 1. Summary

ARKlight should introduce a **platform API interface layer** into its
compiler IR.

The compiler defines platform-facing APIs as **backend-independent
interfaces**. These interfaces become part of the ARKlight semantic/
Website IR rather than being implemented directly by any single
platform.

The **Web platform is the default implementation**.

When compiling for another mature platform backend, the backend
examines the platform interfaces requested by the IR and supplies the
corresponding platform implementation. For example:

- Web → JavaScript/Web APIs
- Android → Kotlin/Android APIs
- Linux Desktop → C/GTK/WebKit2GTK/system APIs

The compiler therefore owns the **semantic interface**, while each
platform backend owns the **actual implementation**.

The resulting architecture is:

**ARKlight source → ARK AST → normalized IR → platform interface
requirements → selected backend implementation → platform output**

This is deliberately different from making ARKlight itself a general
native application framework -- see `docs/Foundational/
WHAT-ARKLIGHT-IS.md` Section 4 for that boundary, which this proposal
is designed to respect rather than push against.

ARKlight remains Web-first. Native platform APIs are an extension of
the Web application model, not a replacement for it.

---

## 2. Motivation

ARKlight already has a compiler architecture in which semantic
concepts are represented before a backend emits platform-specific
output. Platform APIs fit naturally into this model.

A source program should be able to express a semantic requirement such
as "this application requires notifications" without knowing whether
the final target uses the Web Notifications API, Android notification
channels, Linux desktop notification facilities, or another future
implementation.

The source therefore describes **what capability is required**, while
the backend determines **how that capability is implemented**. This
preserves the central ARKlight architectural rule:

> **Source describes intent. The backend implements the target.**

The compiler should not become a collection of platform-specific API
calls.

---

## 3. Terminology

This proposal intentionally avoids describing these as ordinary
"backends."

**Platform backend** -- a compilation target capable of implementing
ARKlight's platform interfaces (Web, Android, Linux Desktop).

**Platform API interface** -- a backend-independent semantic interface
represented in ARKlight IR (notifications, clipboard, filesystem
access, device information, platform storage, future capabilities).

**Platform implementation** -- the target-specific implementation of a
platform API interface (a Web implementation in JavaScript, an Android
implementation in Kotlin, a Desktop implementation in C).

The distinction is important:

> **The interface belongs to ARKlight. The implementation belongs to
> the platform backend.**

---

## 4. Architectural model

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

The platform interface is an IR-level concept. It should not be
implemented as a collection of ad-hoc source transformations.

---

## 5. Web is the default

If no native platform backend is selected, platform interfaces are
resolved against their Web implementations where possible:

```text
Platform Interface -> Web Backend -> Browser API
```

This means the ordinary ARKlight application continues to compile to
HTML/CSS/JavaScript without requiring Android or Desktop support. The
Web implementation is not a fallback added later -- it is the
**first-class default implementation**.

---

## 6. Native implementations are earned by backends

A platform backend does not automatically receive access to every
platform API interface merely because the backend exists. Each backend
explicitly implements the interfaces it can support:

```text
Interface              Web       Android       Desktop
--------------------------------------------------------
notify                 done      later         later
clipboard              done      later         later
storage                done      later         later
filesystem             done      later         later
```

The exact matrix is implementation-specific and should not be
hard-coded into this proposal. The rule that matters:

> **An interface becomes available on a platform only when that
> platform backend implements its contract.**

This lets the compiler architecture mature before every native target
is forced to expose a large native API surface.

---

## 7. Compiler responsibility

The compiler owns the platform interface definition. For every
platform API interface, the compiler should know: its identity, its
semantic contract, its accepted arguments/options, its result
semantics, its IR representation, its required permissions/
capabilities (where applicable), which backends currently implement
it, and its diagnostic behavior when an implementation is unavailable.

The compiler does **not** own the platform-specific implementation --
it may understand `PlatformCapability: name = notify, arguments = ...,
result = ...` without containing any Android notification code.

---

## 8. IR representation

Platform API requests become explicit IR nodes or equivalent IR
requirements:

```text
PlatformAPIRequest
    capability
    arguments
    source_location
    semantic_options
```

e.g. `PlatformAPIRequest(capability="notify", arguments=...)`. Exact
class/field names are an implementation decision for later IR work.
The important property: the request survives compilation as structured
information, never as an opaque string.

---

## 9. Backend contract

Each platform backend implements the platform interfaces it supports:

```text
PlatformBackend
    - supported_interfaces()
    - emit_interface(...)
```

The implementation model differs by platform -- Web maps an interface
to browser APIs and generated JavaScript; Android maps the same
interface to Kotlin and Android APIs; Linux Desktop maps it to its
native C/GTK/WebKit implementation. The interface remains identical at
the ARKlight semantic level; only the implementation changes.

---

## 10. Backend capability discovery

Every platform backend exposes a machine-readable list of platform
interfaces it implements. The compiler then checks, at compile time,
whether the requested interface is supported by the selected backend:
if yes, emit; if no, compiler error. This check must not wait until
application execution.

---

## 11. Unsupported platform interfaces

If source code requests a platform interface the selected backend does
not implement, compilation must fail with a clear diagnostic, e.g.:

```text
ARK1234: platform interface 'notify' is not implemented
         by backend 'android'

requested at:
    src/site.py:42
```

The compiler must not silently remove the request, silently substitute
another API, generate a partial implementation, pretend the feature
exists, or defer a known incompatibility to runtime. The interface
layer exists partly to make these platform differences explicit.

---

## 12. Web-first does not mean Web-only architecture

The initial implementation is deliberately Web-first, but that does
not mean the compiler architecture should hard-code Web assumptions
into the interface model. The compiler should be capable of
representing `interface requested -> backend implementation selected`
even while only the Web backend currently implements most or all
interfaces -- giving ARKlight the architectural foundation for future
native implementations without requiring them prematurely.

---

## 13. Native platform code

Platform implementations belong to their respective backend projects,
not to the compiler's general semantic implementation.

**Android** implementations use Kotlin and Android platform APIs; the
Android backend owns Kotlin implementation, Android permission
requirements, lifecycle constraints, API-level differences, packaging
requirements, and WebView/native integration.

**Desktop** implementations use the existing Linux/GTK/WebKit2GTK
architecture; the Desktop backend owns its native implementation.

---

## 14. Security and permissions

Platform APIs create a real trust boundary. The interface layer must
explicitly model that some interfaces require platform permissions or
privileged access -- eventually describing `interface { capability,
permission requirements, backend requirements }`, with the backend
mapping those requirements onto the target platform's own permission/
policy model. The compiler should not assume identical semantics imply
identical permission behavior across platforms.

---

## 15. No generic native escape hatch

This proposal does **not** introduce `execute_native(...)`,
`call_android(...)`, `call_c(...)`, `run_platform_code(...)`, or an
equivalent arbitrary native execution mechanism. Platform APIs remain
closed-vocabulary compiler interfaces. This preserves ARKlight's
existing architecture:

> **The author requests a known capability. ARKlight chooses a known
> implementation.**

It must not become a mechanism for smuggling arbitrary platform code
through the compiler -- this is the specific boundary
`docs/Foundational/WHAT-ARKLIGHT-IS.md` Section 4 names when it says
ARKlight is "not a general-purpose native-app framework."

---

## 16. Relationship to JavaScript

The interface layer does not require the generated Web runtime to
expose every native concept. For Web builds, the interface may compile
directly to existing browser APIs or generated JavaScript runtime
helpers. For native builds, the same semantic request may cross the
WebView/native boundary and invoke the native implementation. The
exact bridge mechanism is deliberately outside this proposal -- an
implementation detail of each mature platform backend.

---

## 17. Capacitor as architectural reference

Capacitor is a useful precedent for the general direction: it is
explicitly Web-first while exposing native functionality through a
consistent API model, with documented Web implementations and native
implementations per supported platform.

ARKlight should borrow the **architectural idea**, not reproduce
Capacitor's implementation. The key difference is that ARKlight's
platform API request is intended to exist as a compiler/IR concept:

```text
Capacitor: Web application -> native runtime/plugin API
ARKlight:  Python source -> ARKlight IR platform interface -> backend implementation
```

ARKlight's compiler remains the authority over which interfaces exist
and how they are represented.

---

## 18. Zero-cost requirement

Unused platform APIs should have no meaningful cost: no interface
request means no interface implementation emitted, no unnecessary
JavaScript, no unnecessary native bridge, no unnecessary native
packaging. This is an architectural requirement, not just a goal of
avoiding unused-API execution -- unused platform interfaces should
ideally avoid being shipped at all.

---

## 19. Platform API registration

The compiler maintains a registry of platform interfaces (`notify`,
`clipboard`, `storage`, `filesystem`, ...), each with its own semantic
contract. Each backend provides its own implementation registry
against that shared interface registry. This fits naturally with
ARKlight's existing registry-oriented backend concepts (the same shape
as `ACTION_REGISTRY`/`DERIVATION_REGISTRY`) without requiring platform
APIs to become arbitrary plugins.

---

## 20. Versioning

Platform interfaces require explicit versioning -- an interface
contract must not silently change underneath an existing backend
implementation. Conceptually `notify@1`, `notify@2`; a backend declares
which contract version it implements, so a Web backend can sit on
`notify@1` while a future backend adopts `notify@2` without forcing
every backend to change simultaneously. The exact versioning scheme
should be designed before the first native interface is considered
stable.

---

## 21. Compatibility matrix

The proposal should introduce a formal, living compatibility matrix
(interface x platform, each cell "implemented" / "pending" / "not yet
implemented"). This is not merely documentation -- it should eventually
become compiler metadata used for backend validation.

---

## 22. Backend maturity requirement

A platform backend earns native platform APIs progressively: backend
exists -> backend stabilizes -> native integration point is proven ->
first platform API selected -> interface implemented -> security/
permission behavior verified -> compiler/backend integration verified
-> interface becomes supported. This keeps native API development
proportional to actual backend maturity rather than granting the full
catalogue the moment a WebView shell works.

---

## 23. Initial scope

The initial proposal establishes only the architecture, not a large
collection of platform APIs:

1. Define platform API interfaces as IR concepts.
2. Define the compiler/backend contract.
3. Define backend capability discovery.
4. Define compile-time unsupported-interface diagnostics.
5. Define interface versioning requirements.
6. Define the Web implementation model.
7. Define how future native backends register implementations.
8. Define security and permission metadata requirements.
9. Define zero-cost behavior for unused interfaces.
10. Define the compatibility matrix.

The first actual platform API can be selected separately once the
interface architecture itself is accepted.

---

## 24. Explicit non-goals

This proposal does not introduce: a general native application
framework; arbitrary native code execution; arbitrary Java/Kotlin/C
injection; a general plugin marketplace; a replacement for ARKlight's
Web runtime; a mandatory Android native API layer; a mandatory Desktop
native API layer; a universal IPC protocol; a Capacitor clone; a
requirement that every backend implement every interface; or native
APIs shipped before their backend is mature enough to support them.

---

## 25. Relationship to `Provider`

Platform API interfaces and ARKlight `Provider`s
(`docs/Proposals/PROVIDER-SDK-PROPOSAL.md`, accepted, staged
`v0.065`-`v0.070`) remain separate concepts:

**`Provider`** represents an external service or external application
dependency -- Firebase, Flask, a remote service, other network-backed
functionality.

**Platform API** represents a capability supplied by the *execution
platform* itself -- clipboard, notifications, device storage,
filesystem, other platform-specific OS facilities.

The architectural shape may look similar (both require an interface
and an implementation), but the semantic domains are different:

> **`Provider` is external-service abstraction. Platform API is
> execution-platform abstraction.**

Neither should absorb the other.

---

## 26. Compiler pipeline

```text
Python Source -> Python AST -> ARK AST -> Normalization -> Validation
-> Website IR
     +-- HTML/CSS/JS semantics
     +-- Platform API requirements
              -> Backend capability validation
                     +-- supported     -> implementation -> emission
                     +-- unsupported   -> diagnostic
```

This keeps platform support inside the compiler's existing IR-first
architecture.

---

## 27. Architectural principle

> **ARKlight defines the platform API. Each platform backend
> implements it.**

The compiler knows what the application requires; the backend knows
how the platform provides it. This keeps platform differences out of
application source code while avoiding the much larger commitment of
turning ARKlight into a general native framework.

---

## 28. Proposed development order

Treated as architectural planning, not an implementation checklist:

1. **Interface model** -- identity, semantic contract, IR
   representation, source locations, versioning.
2. **Backend contract** -- registry, capability discovery, support
   validation, unsupported-interface diagnostics.
3. **Web implementation** -- reference implementation, establishing
   the actual contract against a functioning platform.
4. **Native backend qualification** -- evaluate the interface against
   Android/Desktop once mature enough; do not assume Web semantics map
   cleanly onto the native platform.
5. **First native implementation** -- select one small, well-defined
   platform API and implement it in the mature backend (Kotlin for
   Android, native C/platform APIs for Desktop).
6. **Expand deliberately** -- only after the first native
   implementation establishes the bridge contract should additional
   interfaces be added.

---

## 29. Acceptance criteria

The architecture is not complete merely because a `PlatformAPI` type
exists. It should establish that: platform API requests are
represented in IR; platform implementations are backend-owned; Web is
the default implementation target; backend support is discoverable;
unsupported interfaces fail during compilation; interface versions are
explicit; platform permissions can be represented; unused interfaces
cause no unnecessary emitted functionality; arbitrary native code is
not exposed; Android can eventually implement interfaces independently
in Kotlin; Desktop can eventually implement interfaces independently in
C; and a future backend can implement the same interfaces without
modifying the semantic source contract.

---

## 30. Final architectural position

ARKlight remains **Web-first**. Platform APIs do not redefine ARKlight
as a native framework -- the compiler provides a stable semantic
interface for platform capabilities:

```text
                    ARKlight
                       |
                       v
               Platform API IR
                       |
             +---------+---------+
             v         v         v
            Web     Android    Desktop
             |         |         |
       JavaScript    Kotlin       C
             |         |         |
       Web APIs    Android APIs   OS APIs
```

The Web implementation exists first because Web is ARKlight's native
execution environment. Android and Desktop implementations are added
only when those backends have matured enough to justify exposing
platform functionality.

The important architectural decision is therefore not "ARKlight gets
native APIs." It is:

> **ARKlight's compiler defines platform API interfaces, and mature
> platform backends earn the right to implement them.**

That gives the compiler a stable architectural contract now without
forcing immature backends to pretend they can provide native
functionality they cannot yet support. The interesting property is
that the compiler can become platform-API-ready before Android/Desktop
are platform-API-ready -- exactly the asymmetry this proposal is
designed to allow.
