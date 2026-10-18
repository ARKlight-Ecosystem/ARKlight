# Fetch / HTTP as a Primitive: `Action.fetch_json` and `State(..., fetch=...)`

## Status

**Stage 1 (infra) and stage 2 (`Action.fetch_json`) accepted and
shipped on `alpha`**, gated as
`arklight.experimental.FEATURES["fetch-json"]`. Stage 3
(`State(..., fetch=...)`, load-triggered) is still unbuilt and
unstaged -- this document now describes a partially-implemented
feature, not a purely hypothetical one; only the "## Stage 3" section
below still fits `docs/Proposals/README.md`'s "does not exist yet, may
never be built as written" definition. Followed the format and
conventions of
[`docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md`](URL-STATE-AS-PRIMITIVE-PROPOSAL.md)
and
[`docs/Proposals/APP-SHELL-CAPABILITY-PROPOSAL.md`](APP-SHELL-CAPABILITY-PROPOSAL.md),
both of which also graduated from proposal to shipped feature in
place rather than being retired to `docs/Implementation/`.

**Where this sits relative to `Provider`:** `fetch_json` is authored
as `Action.fetch_json(...)`, not `Provider.declare(...)` -- it needs
no external-service declaration at all, since a same-origin or
explicitly trusted JSON endpoint is not "an external service" in the
sense `Provider` means (a hosted database, an auth vendor). But it is
the concrete, closed-vocabulary answer to the gap
`docs/Foundational/PROVIDER-SDK.md`'s "Explicitly out of scope"
section and `docs/Foundational/WHAT-ARKLIGHT-IS.md`'s gap list both
name as "client-side data-fetch orchestration" -- treat it as sitting
on the `Provider` boundary conceptually (the same "declare vs. act"
line this document's TL;DR draws below), even though its authoring
surface is `Action.*`. A `Provider`-declared external service that
also happens to be same-origin or trusted-origin JSON can use
`fetch_json` directly for the read/write half of that integration;
anything else (auth headers, a vendor SDK's own request shape) still
goes through the site author's own code, same as before this
shipped.

**Direction being worked on: an optional real backend behind
`fetch_json`, for devs who want one.** Nothing here forces a site to
talk to a server -- `fetch_json` is as usable against a static,
pre-built JSON file as against a live endpoint -- but for a dev who
*does* stand up a real backend, testing the frontend means having some
way to interface with it while iterating, not just at final deploy.
ARKlight already has prior art for exactly that shape of problem:
`arklight live-streaming --channel [PORT]` (`arklight/cli/channel.py`)
is a dev-only, opt-in second server that serves one page's
`State(...)` live over SSE/HTTP to any external client -- a Flask app,
curl, a second browser tab -- for the length of a `--subscribe`
session. It's not a production feature and it isn't `fetch_json`'s
backend, but it's the same underlying need this proposal is reaching
for: a sanctioned, closed-vocabulary way for the frontend half of a
build to interface with something standing in for -- or actually
being -- a real backend, instead of every dev reinventing that bridge
by hand via `ScriptExtension`. Treat `--channel` as the dev-tool
precedent, not the mechanism itself: the open question this direction
still needs to answer is what a *production* `fetch_json` request
against a dev's own backend should look like once `trusted_fetch_origins`
already covers "is this origin allowed," which is a question about
request shape (headers, auth, non-GET bodies) more than about the
trust boundary itself.

**Origin:** `docs/Foundational/CAPABILITY-MATRIX.md` lists Fetch / HTTP
as a `Gap`, with the note "By design for now; `PROVIDER-SDK.md` is the
accepted route for external services." This proposal is not a
challenge to that note's premise -- `Provider` should stay the
declaration layer -- it argues that the gap sits one layer lower than
where `Provider` operates, and that the gap is now load-bearing rather
than theoretical.

## TL;DR

`Provider.declare(name=..., capabilities=["read"])` lets a site say it
talks to an external service. It compiles to exactly one artifact:
`window.ARKLIGHT_PROVIDER = {name, capabilities}`, a frozen config
object for the site author's own hand-written script to read
(`arklight/provider.py`'s module docstring is explicit that this is
the entirety of what it emits -- "no vendor code, no networking code").
There is currently no ARKlight-native way to *act* on that
declaration. A site that wants to actually issue the read it just
declared has one option: drop into `ScriptExtension`, which the
project's own docs flag as the one place "the JS itself is
unchecked" -- i.e., exactly the kind of unvalidated, closed-vocabulary-
violating code the rest of the runtime exists to avoid.

This proposal defines two narrow additions, both shaped after
precedents already shipped in this codebase rather than a generic
`fetch()` escape hatch:

- **`Action.fetch_json(target, url=..., method="GET")`** -- a new
  `ACTION_REGISTRY` entry, same async "fire and forget" shape as
  `geolocate` (`arklight/backend/js/actions/geolocate.py`): issues a
  `fetch`, parses the response as JSON, and writes the result into a
  declared `State(...)` key. Click-triggered, same as every other
  action.
- **`State(..., fetch="/api/...")`** -- an extension of the same
  pattern `persist=True`/`query=` already established: a value the
  compiler can't know at build time, populated from an external source
  at runtime, on page load instead of on click.

Both are scoped to **same-origin or `Site(trusted_fetch_origins=...)`-
listed, JSON-only, GET-by-default** requests -- no arbitrary method,
no arbitrary body serialization, no response type beyond JSON. Neither
adds a general networking primitive; both add one more closed, typed
action to a vocabulary that already has one async, fire-and-forget
precedent (`geolocate`) and one "sourced from outside the compiler at
runtime" precedent (`persist`/`query`).

## 1. Why this doesn't collapse into "just use `Provider`"

Re-reading `Provider`'s own module docstring
(`arklight/provider.py`) against what it actually emits settles this:
`Provider` makes zero network calls, ships zero networking code, and
is explicit that "data-fetch orchestration" -- loading states, caching,
retries, the thing a real "talk to a server" primitive needs -- is a
**separate, still-open gap** that `Provider` is meant to eventually
plug into, not something it already covers. `Provider` answers "does
this site talk to something external and what kind of thing does it
do" (a declaration, checked at compile time, zero runtime cost
unused). It was never designed to answer "how does a click actually
issue that read" -- there's no `State(...)` key or DOM hook for a
capability to attach to, by the docstring's own admission ("It carries
no DOM hooks or `State(...)` keys yet -- there is no authoring surface
to wire a capability to one.").

So a site with `Provider(capabilities=["read"])` declared today still
has to hand-write the actual fetch call. That hand-written call is
exactly the failure mode `SYSTEM-DESIGN-AGREEMENTS.md`'s closed-
vocabulary stance exists to prevent elsewhere in the project: unchecked
JS, not validated by the compiler, not covered by the IR, not subject
to the same-origin/CSP discipline every other generated primitive
gets for free.

## 2. Why "static sites don't need this" doesn't hold up

Static output was never the same claim as "no runtime network calls."
Every major static-first tool (Next, Nuxt, Gatsby, Astro) treats
build-time fetch and client-side fetch as two different jobs, and
ships an answer for both -- data stable enough to bake in at build time
goes through the generator; content that changes after the page has
already loaded (a vote count, a cart, an inbox, anything behind auth)
has to be a runtime call, because the compiler cannot have known it.
ARKlight already accepts this distinction in one area: `State(...,
query=...)` exists precisely because the compiler "never sees the
query string" and some values are structurally unknowable at build
time. Fetched data is the same shape of problem -- unknowable at
compile time, needed at runtime -- just sourced from a server instead
of the URL bar.

The concrete forcing case already named in this repo's own docs: the
`APP-SHELL-CAPABILITY-PROPOSAL.md` checklist explicitly carves out "a
general client-side route table" and "component state that survives
across pages" as permanently out of scope for `app_shell` -- but an
`app_shell` site with no fetch primitive still can't do the most
basic dynamic thing a boosted-navigation site would want (refresh a
cart count, re-check an auth session after a boosted swap) without
the same hand-written-JS escape hatch this proposal is trying to
close.

## 3. Design

### 3.1 `Action.fetch_json` -- the click-triggered case

```python
State("weather", initial=None)
Button("Check weather", on_click=Action.fetch_json(
    "weather", url="/api/weather", method="GET",
))
Show(Predicate.truthy("weather"), Text(Derive.format("weather", "{temp}°")))
```

`ACTION_REGISTRY` entry, same shape `geolocate` already established
for an async action:

```python
"fetch_json": ActionSpec(args=("url", "method"), state_args=("url",)),
```

`state_args=("url",)` lets a dynamic path come from `Bind(...)` (e.g.
`Action.fetch_json("result", url=Bind("search_query"))`) the same way
`Action.set`'s `value` already allows a state-sourced argument --
`url` is a plain string either way, never an expression, so this
doesn't reopen the "general expression evaluation" door
`SYSTEM-DESIGN-AGREEMENTS.md` keeps shut elsewhere.

`JS_FRAGMENT`, same "fire and forget" shape as `geolocate.py`:

```js
fetch_json: function (store, key, args) {
  var url = args.url;
  if (!arkIsTrustedFetchURL(url)) {
    arkNotify("This fetch target isn't on the site's trusted-origin list.");
    return;
  }
  fetch(url, { method: args.method || "GET", headers: { "Accept": "application/json" } })
    .then(function (res) {
      if (!res.ok) { throw new Error("HTTP " + res.status); }
      return res.json();
    })
    .then(function (data) {
      store.set(key, arkStripDangerousKeys(data));
    })
    .catch(function () {
      arkNotify("Couldn't load that -- check your connection and try again.");
    });
}
```

Two helpers factored out, not inlined, because both are shared with
§3.2 below:

- **`arkIsTrustedFetchURL`** -- same-origin by default; additionally
  checks a page-level allow-list emitted from
  `Site(trusted_fetch_origins=[...])`, the same mechanism
  `trusted_script_origins` already threads through
  (`arklight/api.py`). This mirrors standard CSP `connect-src`
  practice (list specific trusted origins rather than leaving the
  door open) and gives ARKlight's compiler something concrete to
  validate at build time: `trusted_fetch_origins` entries are checked
  for well-formedness the same way `trusted_script_origins` already
  is, and a `fetch_json`/`fetch=` target that isn't same-origin and
  isn't on the list is a **build-time** validation error, not a
  runtime surprise -- the compiler can already see the literal `url=`
  string in every case except the `Bind(...)`-sourced one, which gets
  the runtime check above as a second line of defense.
- **`arkStripDangerousKeys`** -- strips `__proto__`, `constructor`, and
  `prototype` keys from the parsed response (recursively, one shallow
  pass per nesting level actually reachable from `JSON.parse` output)
  before the value ever reaches `store.set`. `JSON.parse` can produce
  an object with an own property literally named `__proto__` from
  `{"__proto__": {...}}` input; that's inert by itself, but if this
  runtime's own `Derive`/`Bind` machinery -- or a later version's
  nested-merge handling -- ever assigns fields from a fetched object
  into existing state without this check, that's the textbook
  prototype-pollution path dedicated sanitizer libraries exist for.
  Stripping at the fetch boundary, once, means every consumer
  downstream (today's `Derive.format`, any future per-field access)
  inherits the safety property for free instead of needing to
  remember it.

### 3.2 `State(..., fetch=...)` -- the load-triggered case

```python
State("weather", initial=None, fetch="/api/weather")
```

Same trusted-origin and sanitization machinery as §3.1, triggered once
at page-init (`initState()`,
`arklight/backend/js/runtime/state.py`) instead of on click -- the
load-time equivalent of `persist=True`'s localStorage read and
`query=`'s `URLSearchParams` read, which already run in that same
init pass. Unlike those two, this one is asynchronous: `initial` is
what a JS-disabled or slow-network visitor sees until the fetch
resolves, same "server-rendered guess, then runtime correction"
contract `media=` already documents for its own case
(`arklight/api.py`'s `State` docstring).

Mutually exclusive with `query=` and `media=` on the same key -- three
different runtime sources writing the same key on init is a build-time
validation error, the same way `ir/validate.py` already rejects other
combinations that don't compose cleanly, rather than a silent
last-writer-wins.

### 3.3 What's deliberately left out

- **No `POST`/`PUT`/`DELETE` body in v1.** `method=` is accepted for
  forward compatibility (`GET`/`POST` only, validated at compile
  time), but no request-body serialization is proposed here -- that's
  a materially different trust surface (user-authored data leaving
  the site) and deserves its own forcing case and its own proposal,
  not a rider on this one.
- **No response caching/dedup logic.** `Provider`'s own docstring
  already names "loading states, caching, retries" as the open
  follow-on gap; this proposal deliberately ships the narrowest thing
  that clears the philosophy-fit checklist below and leaves that
  layer for whoever picks it up next, the same staged-rungs approach
  `PROVIDER-SDK.md`'s six stages and `URL-STATE-AS-PRIMITIVE-
  PROPOSAL.md` both used.
- **No generic `fetch()` escape hatch.** Both additions are closed,
  typed, registry entries -- not a string of JS handed to the browser,
  and not an arbitrary-URL/arbitrary-method primitive.

## 4. Philosophy-fit checklist

Same checklist `APP-SHELL-CAPABILITY-PROPOSAL.md` used, applied here:

1. **Delegates, doesn't reimplement.** Yes -- the browser's own
   `fetch`/`JSON.parse`; ARKlight contributes validation and
   sanitization, not a new networking stack.
2. **Stays closed-vocabulary.** Yes -- `url`/`method` are data, never
   evaluated as code; no `eval`, no `new Function`.
3. **Compiler resolves what it can, ahead of time.** Yes -- a literal
   `url=` is validated against `trusted_fetch_origins` at compile
   time; only the `Bind(...)`-sourced case needs the runtime check,
   and that's the same `state_args` pattern `Action.set` already uses.
4. **No second untrusted layer.** Yes -- this is explicitly the
   alternative to the untrusted `ScriptExtension` escape hatch sites
   currently need for this, not an addition alongside it.
5. **Byte-for-byte unaffected when opted out.** Yes -- no `fetch=`/
   `Action.fetch_json` usage, no `trusted_fetch_origins`, no runtime
   diff, following the same precedent every `Site(...)`/`State(...)`
   flag in this codebase already holds.

## 5. Relationship to `Provider`

This does not fold into `Provider` or require a `Provider` declaration
to use -- a site fetching from its own `/api/...` same-origin endpoint
has nothing external to declare. Where a site *does* have a
`Provider` declared, nothing here changes `Provider`'s contract: it
stays the "this site talks to something external, here's roughly what
kind of thing" declaration, and `Action.fetch_json`/`State(...,
fetch=...)` become the first concrete authoring surface a `Provider`-
adjacent capability can actually wire up to, closing the gap the
`provider.py` docstring names explicitly as still open.

## 6. What "accepted" would look like

Staged the same way `PROVIDER-SDK.md` and `URL-STATE-AS-PRIMITIVE-
PROPOSAL.md` were: `trusted_fetch_origins` + `arkIsTrustedFetchURL` +
`arkStripDangerousKeys` land first as pure infrastructure (zero new
authoring surface, fully testable in isolation, same spirit as
landing the `localStorage` read/write machinery before `persist=True`
was documented as a feature); `Action.fetch_json` lands second since
it's the smaller, click-scoped surface; `State(..., fetch=...)` lands
third once the first two are proven, since it's async at page-init
rather than at a user-triggered moment and has the three-way
mutual-exclusion check with `query=`/`media=` to get right.

## 7. What this proposal is not

Not a pitch to make ARKlight a general HTTP client, and not a
reversal of the `Provider`/`PROVIDER-SDK.md` stance that ARKlight
itself should stay out of the vendor-SDK business. It's the one rung
of "a site needs to actually talk to a server" that was missing
underneath that stance: a closed, validated, same-origin-by-default
way to issue a read and land the result in `State(...)`, scoped
narrowly enough that saying yes to it doesn't require saying yes to a
generic `fetch()` anywhere in the vocabulary.
