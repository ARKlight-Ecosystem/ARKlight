# URL State as a Primitive: Query Parameters for `State`

## Status

**Proposal — not yet accepted, not yet staged.** Follows the format
and conventions of
[`docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md`](JS-VOCABULARY-EXPANSION-PROPOSAL.md).
Per `docs/Proposals/README.md`'s own definition, this describes
something that does not exist yet, may never be built as written, and
could be rejected outright.

**Origin:** an exhaustive grep of `arklight/` for `location.search`,
`URLSearchParams`, and any query-string handling, done while auditing
the client-side vocabulary for gaps the static-compilation model
doesn't already dissolve (see §1 below).

## TL;DR

ARKlight has no authored primitive for reading, writing, or reacting
to URL query parameters (`?page=2`, `?sort=price&category=cpu`).
Confirmed by exhaustive grep of `arklight/` for `location.search`,
`URLSearchParams`, and any query-string handling: the only hits are
inside the vendored `htmx.py` (used internally for htmx's own request
plumbing, never exposed as an authored feature) and the dev-only
`cctv.py`. This is a genuine, unaddressed gap — not a case where the
static-compilation model dissolves the problem the way it does for
routing, layouts, or metadata.

This proposal defines a minimal `State(..., query=...)` primitive that
extends the existing `persist=True` mechanism rather than inventing a
parallel one, and settles the one open design question (which of three
possible navigation architectures a query-param change should trigger)
in favor of the option that already matches how every other reactive
primitive in ARKlight behaves.

## 1. Why the static model doesn't dissolve this one

Every other routing-adjacent gap in ARKlight's feature surface
(dynamic routes, nested layouts, metadata) turns out not to be a gap
at all once you look at the actual compiler: `_output_path_for_route`
maps a **finite, fully known** set of declared routes to files at
build time, and Python's own control flow (a `for` loop calling
`site.page(...)` per item) already covers what other frameworks need
a dedicated "dynamic routes" feature for.

Query parameters break this. `/products?page=2` and `/products?page=3`
resolve, at the static-file-server level, to the exact same file —
`products.html`. The compiler never sees the query string, because
static file resolution ignores it entirely before ARKlight's output
is even in the picture. The space of possible query values is
unbounded (a search box alone rules out "generate one file per
value"), so this is the first item on the wider feature-parity audit
where build-time compilation structurally cannot absorb the problem.
It has to be a client-runtime concern, in a runtime that currently has
no concept of the URL beyond the route it was loaded from.

## 2. The existing primitive this should extend, not duplicate

ARKlight already ships `State(name, initial=None, persist=False)`
(`vdom-8`, DONE), which:

- bakes `initial` into `data-ark-state` at build time (the only value
  the compiler can know),
- reads a client-side override (from `localStorage`) at page-init,
  before the page is meaningfully interactive,
- fails open to the baked default on any read/parse error, with a
  `console.warn` rather than a thrown exception, isolated per key.

This is structurally identical to what URL-state needs: a value the
compiler can't know at build time, corrected from an external source
at runtime, with the same fail-open safety property. The proposed API
reuses this shape directly:

```python
State("page", initial=1, query="page")
```

## 3. Design, broken into eight sub-questions

Each of these was raised as a separate concern worth resolving on its
own rather than bundling into one vague "query param support" ask.
Most fall out directly from the `persist=True` precedent; one is
genuinely new surface.

### 3.1 Reading (falls out of the existing pattern)

At page-init, alongside the existing `data-ark-persist` check, also
check a new `data-ark-query` attribute. If present, read
`new URLSearchParams(location.search)` and override the baked-in
default for any key found — same code shape as the `localStorage`
check, different source.

### 3.2 Serialization / type coercion (falls out of the existing pattern)

`initial`'s Python type is already inspected by the compiler today —
it's what lets `Computed` values be evaluated at build time and what
lets `persist` be validated as a bool. The same type-carrying
mechanism supplies the coercion function for free: `initial=1` (int)
→ `parseInt`; `initial=False` (bool) → a `"true"`/`"false"` string
mapping; `initial=""` (str) → passthrough. No new concept required,
just a second consumer of information the IR already carries.

### 3.3 Fail-open behavior (falls out of the existing pattern — now a
confirmed, repeated convention, not a one-off)

A missing or malformed query value should silently fall back to the
baked default, exactly as a corrupt/unavailable `localStorage` value
already does in the shipped `persist` runtime. This proposal treats
"every external-input read in this runtime fails open to its safe
default" as an established design invariant worth stating explicitly,
since it now applies identically across two independent features.

### 3.4 Writing (mostly falls out — one real decision embedded here)

Whenever an `Action` mutates a `query=`-tagged `State`, after the
normal in-memory update and re-render, also call
`history.replaceState(...)` with the updated search string. See §3.6
for why `replaceState` (not `pushState`) is the correct **default**.

### 3.5 Back/forward — the one genuinely new runtime surface

Nothing in ARKlight's shipped runtime listens for `popstate` today —
there is no SPA router, so there has never been a reason to. This
proposal is honest that this is not a free extension of an existing
mechanism: it requires one new listener, registered once per page that
declares a `query=` state, which re-runs the same read-and-override
logic from §3.1 and feeds the result through the same `setState` path
every `Action` already uses. Small in scope, but new, and should be
scoped and reviewed as such rather than folded silently into the
`persist`-adjacent work above.

### 3.6 Which of three navigation architectures — resolved, not left open

Three architectures could plausibly answer "what happens when
`?page=1` becomes `?page=2`":

1. A full browser navigation to the new URL.
2. An `hx-boost`-style XHR fetch-and-swap.
3. A local, in-place `State` update with `history.replaceState` and no
   network request at all.

(1) and (2) both re-fetch a document that is, by construction,
byte-identical to the one already on screen — the compiler-rendered
page is invariant to the query string, since it never sees it. Both
options only look tempting if this feature is framed as routing. It
isn't: `State`, `Computed`, `Derive`, and every `Action` in ARKlight's
vocabulary are synchronous, in-memory, closed-vocabulary primitives
with no navigation or network step anywhere in them. Option (3) is the
only one consistent with that grain, and this proposal treats it as
**settled by the existing model**, not as an open fork requiring a
separate maintainer decision.

### 3.7 History granularity (extends an existing registry, doesn't invent one)

Not every `query=`-tagged state should create a back-button-worthy
history entry on every change — a live-updating search box firing
`replaceState` on every keystroke is correct; a paginated list
advancing a page number is arguably worth a real history entry per
page. `MODIFIER_REGISTRY` already carries debounce/throttle tokens for
two-way input binding (`v0.063`). This proposal suggests a `history`
mode reusing that same registry —
`State("page", initial=1, query="page", history="push")` for the
opt-in case, `replaceState` remaining the unmarked default — rather
than inventing a second, parallel modifier system.

### 3.8 Reactivity (falls out directly)

Yes — `query=`-tagged state is ordinary `State` once initialized. It
participates in `Bind`, `Show`, `Computed`, and every derivation the
same as any other named state. No special-casing needed once §3.1–3.5
are in place; this is the payoff for building the feature as an
extension of `State` rather than as a separate concept.

## 4. Scope

### In scope (this proposal)

- `State(..., query=<param name>)`.
- Build-time: bake `initial` as today; validate `query` is a string
  naming a legal query-parameter key.
- Runtime: init-time read/override (§3.1), coercion by `initial`'s
  type (§3.2), fail-open on bad/missing values (§3.3), write-back via
  `history.replaceState` on `Action`-driven change (§3.4), a new
  `popstate` listener (§3.5), an opt-in `history="push"` modifier
  reusing `MODIFIER_REGISTRY` (§3.7).

### Explicitly out of scope for this proposal

- **Query-driven full navigation or `hx-boost` swapping** — ruled out
  in §3.6 as inconsistent with the existing reactive-core model, not
  merely deferred.
- **Arbitrary/unstructured query-string parsing** (e.g., nested
  objects, nonstandard array encodings) — `query=` names exactly one
  flat key; anything more structured is a separate, larger proposal.
- **Generating static output per query combination** — ruled out in
  §1 on the same "unbounded value space" grounds that make this a
  client-runtime feature in the first place.

## 5. Suggested order

1. §3.1–3.3 (read + coerce + fail-open) as the smallest useful slice —
   comparable in size to the original `persist=True` stage, since it's
   almost entirely a second consumer of that stage's existing code
   paths.
2. §3.4 (write-back via `replaceState`) — the point at which this
   becomes bidirectional rather than read-only.
3. §3.5 (`popstate` listener) — flagged separately because, unlike
   every other stage here, it is genuinely new runtime surface with no
   existing analog to extend, and should get its own review attention
   for that reason.
4. §3.7 (`history="push"` modifier) — smallest, most deferrable slice;
   pure sugar over what §3.4 already provides.

## 6. Open question for a maintainer

Whether `query=` should be restricted to top-level pages only, or
whether it composes with the user-defined component system (`v0.060`
Stages 0–4) — e.g., a component that declares its own `query=`-bound
prop. This proposal takes no position on that interaction and flags it
as unresolved rather than guessing at an answer the component system's
own design docs don't already imply.
