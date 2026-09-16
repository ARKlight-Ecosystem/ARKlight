# Provider: A Barebones, Experimental Interface for External Services

## Status

**Accepted -- staged as a six-rung ladder (`v0.065`-`v0.070`) in
[`docs/Implementation/PROVIDER-SDK-ADDENDUM.md`](../Implementation/PROVIDER-SDK-ADDENDUM.md).**
The content below is left as filed -- it's the design record this
proposal was accepted on -- and is not rewritten to reflect
in-progress implementation detail; see the addendum for the current
landing order, per-stage status, and how it resolves this document's
own open questions (§7). This remains an **experimental API** under
`docs/Foundational/EXPERIMENTAL-APIS.md`'s existing gate once it
ships -- it is not part of ARKlight's default surface.

**Origin:** a discussion of whether ARKlight should have any story at
all for sites that need to talk to an external service (Firebase was
the concrete example raised, but the same question applies to a
hand-rolled Flask API, a local-only store, or anything else), settled
by first grepping the existing docs for prior art before designing
anything new.

## TL;DR

ARKlight already overloads the word "backend" for *output* targets --
`arklight/backend/{html,css,js,android,desktop}/`, all implementing
the same `Backend.render(ir) -> {path: contents}` contract
(`arklight/backend/base.py`). This proposal is about a completely
different concept -- a site opting in to talking to an external
*service* at runtime -- and deliberately does **not** call it a
"backend," to avoid exactly that collision. It's called a **Provider**.

A Provider is, by design, barebones: ARKlight ships only a closed,
minimal *interface* a concrete integration must satisfy -- no Firebase
code, no Flask code, no networking code of any kind lives in
ARKlight's core. Enabling it is opt-in and gated as an experimental
feature, the same way `css-media-queries` or `raw-postprocess` are
today.

## 1. This is not a new idea to the project -- it was already deferred once

`docs/Foundational/DESIGN-NOTES.md`, in the Android backend section,
already raises this exact shape of problem and explicitly declines to
build it yet:

> a generalized, capability-based JS-to-native bridge (`ark.fs`,
> `ark.db`, `ark.clipboard`, `ark.notify`, ...) that would let the
> *same* ARKlight JS-facing API be backed differently per platform
> ... with a site declaring only the capabilities it actually needs

filed there as "a substantially larger design (security review, a
versioned platform ABI, an implementation per backend) with no
concrete forcing use case yet -- worth a future PLANNING section of
its own." That note is about native-platform capabilities (device
storage, clipboard), not external network services, but the shape --
one closed contract, many possible backing implementations, opt-in
per capability -- is identical. This proposal is that future planning
section, scoped to external services instead of native device APIs.

`docs/Foundational/SYSTEM-DESIGN-AGREEMENTS.md`'s "Runtime Is a
Delegation Boundary" section independently supports treating this as
a legitimate runtime concern rather than something to route around:
**network responses** are explicitly listed alongside local storage,
user input, and OS APIs as things the runtime is allowed to own,
provided the compiler still decides *that* delegation happens, *which*
capability is needed, and what config gets baked in at build time. A
Provider contract is that decision, made explicit and typed, instead
of every site author reinventing it by hand with a `raw_postprocess`
escape hatch.

## 2. What "barebones" means here, precisely

- **An interface only.** The `Provider` contract is a fixed, closed
  shape a concrete implementation must satisfy -- structurally the
  same kind of thing `Backend` already is for output targets. No
  method on it does anything by itself.
- **No shipped implementations.** ARKlight's core does not ship a
  Firebase provider, a Flask provider, or any other concrete
  integration. Firebase-or-whatever is something a site author (or a
  separate, non-core package) writes *against* the contract -- "some
  guy building a serious app," in the words this proposal started
  from -- not something this project maintains, tests against a live
  Firebase project, or takes a support burden for.
- **No logic, no opinions.** The contract does not decide what auth
  looks like, what a database schema looks like, or how errors from
  the external service should be handled. It only defines *where* a
  site's declared capabilities plug in and *what shape* data crosses
  that boundary.
- **Zero cost when unused.** Exactly like every other experimental
  feature, a site that never declares a Provider ships no Provider
  code at all -- same "only ship what's used" discipline the JS
  backend already applies to `actions`/`behaviors`/`derivations`
  (see `arklight/backend/js/render.py`).

## 3. Sketch of the contract

Not a final API -- illustrative, to make the "interface, not
implementation" claim concrete:

```python
from arklight import Site

site = Site(
    provider=Provider.declare(
        name="firebase",              # arbitrary label, not a fixed enum of vendors
        capabilities=["auth", "read"], # closed vocabulary, see open question below
    )
)
```

At compile time, ARKlight:

1. Validates that the declared `capabilities` are from the closed set
   it knows about (see §5) -- the same kind of schema check
   `arklight/ir/validate.py` already does for every other component
   and prop, not a new kind of trust.
2. Emits a small, fixed config blob (mirroring how `data-ark-state`
   carries `State(...)`'s baked initial values today) describing which
   capabilities this page uses and what DOM hooks/state keys they're
   wired to.
3. Emits **nothing else**. No network call, no vendor SDK, no
   generated glue that actually talks to anything. The concrete
   implementation -- the real Firebase JS SDK, initialized with a
   project's real config, doing the real `auth.signIn(...)` call -- is
   the site author's own code, not generated by ARKlight.

## 4. Why this doesn't violate "Compiler First"

`SYSTEM-DESIGN-AGREEMENTS.md`'s central rule is: *if the compiler can
solve it correctly and completely, the runtime shouldn't solve it
again.* A live network call to a third-party service is, definitionally,
not something the compiler can resolve ahead of time -- it depends on
data that doesn't exist until a real user, with a real session, hits a
real endpoint. That puts it squarely in the category the same document
already carves out for runtime delegation, alongside "network
responses" and "OS APIs." The compiler's job here is limited to what it
*can* still own: validating the capability declaration, deciding which
minimal config to bake in, and deciding what (if anything) ships when
the feature isn't used -- exactly the five responsibilities
`SYSTEM-DESIGN-AGREEMENTS.md` §2 already assigns the compiler for any
runtime-delegated behavior.

## 5. Experimental gating

Registers as a new entry in `arklight/experimental.py`'s `FEATURES`
dict, following the existing three-step process in
`EXPERIMENTAL-APIS.md`'s "Adding a new experimental feature" section:

- id: `provider-integration`
- inline note: along the lines of *"This site declares a Provider --
  ARKlight does not implement, audit, or guarantee the external
  service it points at."*
- detail lines: spelling out that the actual network/auth/security
  behavior is entirely the responsibility of whatever concrete
  implementation the site author supplies, same disclaiming tone
  `raw-postprocess`'s entry already uses for its own "widest escape
  hatch" warning.
- legacy note: n/a at first (nothing to be backward-compatible with
  yet) -- follows the same field shape as the other entries regardless,
  for consistency.

Printed both inline (at the point a page's IR shows a declared
Provider) and in the end-of-build summary, same two-surface contract
every other experimental feature already gets. Not gated behind
`--verbose`, for the same reason none of the others are: this is the
entire point of gating, not incidental extra output.

## 6. Explicitly out of scope

- No bundled Firebase, Supabase, or any other vendor SDK, now or as a
  planned follow-up.
- No server ARKlight stands up, packages, or deploys on the site
  author's behalf -- ARKlight remains a compiler producing static
  files.
- No opinion on auth flows, token storage, or security rules -- that
  risk belongs entirely to whichever concrete Provider implementation
  a site chooses, same way `raw_postprocess`'s own "million different
  ways to shoot yourself in the foot" warning already puts the burden
  on the author, not the compiler.
- No client-side data-fetch orchestration (loading states, caching,
  retries). `docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md`
  already lists "client-side data fetch" as a separate, larger
  IR-node-sized gap in its own catalog -- Provider is meant to be the
  vendor-neutral boundary that feature would eventually plug into, not
  a rebuild of it here.

## 7. Open questions

1. **Where does the concrete implementation's own JS actually ship
   from?** A real Firebase integration needs the Firebase JS SDK
   loaded somehow. ARKlight doesn't currently offer an authored way to
   add an arbitrary external `<script src>` (`css-import`'s `@import`
   is the closest existing precedent, and it's flagged experimental
   for the same "fetched at request time, can't be validated by
   ARKlight" reason). This may need its own small experimental prop
   (e.g. a gated `Page(scripts=[...])`) before Provider is usable for
   anything beyond a same-origin, already-loaded global.
2. **How closed should `capabilities` be?** Recommend a fixed,
   versioned enum (`auth`, `read`, `write`, `subscribe`, ...) rather
   than a free-form string, matching the closed-registry discipline
   `Action.*`/`Behavior.*` already use everywhere else in the runtime
   -- and for the same reason: it keeps the generated output
   inspectable and keeps ARKlight's "no eval, no `new Function`, no
   string ever executed as code" promise (stated in
   `arklight/backend/js/render.py`'s htmx-5 section) intact even as
   this surface grows.
3. **Naming.** "Provider" is used here to sidestep the "backend"
   collision; "connector" and "service adapter" were also considered.
   Whichever is picked should be used consistently across this
   proposal, the eventual `arklight/experimental.py` entry, and any
   public API (`Provider.declare(...)` above is illustrative, not
   final).

## 8. Relationship to other proposals

`JS-VOCABULARY-EXPANSION-PROPOSAL.md`'s "client-side data fetch" gap is
the most likely first real consumer of this contract once both exist.
This proposal is deliberately narrower and lower-level than that one --
it defines *where the boundary is*, not what gets built on top of it.
