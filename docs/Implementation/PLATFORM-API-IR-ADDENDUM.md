# Platform API IR Addendum: Staged Order, v0.065

**Status:** Stage 1 of 2 SHIPPED (`v0.065`); Stage 2 PLANNED, with no
version slot reserved yet -- it waits on Android/Desktop backend
maturity, not on a fixed schedule. This file turns the accepted part
of
[`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`](../Proposals/PLATFORM-API-IR-PROPOSAL.md)
into a trackable landing order, the same role
`JS-VOCABULARY-ADDENDUM-v0.070.md` plays for the JS vocabulary
expansion proposal. It does not restate that proposal's reasoning; it
exists to turn "here's an accepted architecture" into "here's the
order it ships in and why the order has only two rungs, not ten."

Only two stages, not a longer ladder, because the proposal's own
Section 23 ("Initial scope") already drew the line tight: this
accepts the *architecture* -- IR representation, backend contract,
capability discovery, diagnostics, versioning, the Web implementation
model -- plus exactly two starter capabilities to prove the
architecture against (`notify`, `clipboard_write`), not a large
catalog. Growing the capability catalog later is new registry entries
against an already-accepted architecture, not a new proposal; growing
the *backend* list (Android, Desktop) is Stage 2, gated on backend
maturity per Section 6/22 of the proposal, not on anything in this
file.

## Stage 1 of 2 -- Web reference implementation (SHIPPED, `v0.065`)

Everything needed for an author to call a Platform API on a site that
compiles to Web (HTML/CSS/JS) output, end to end:

- **Compiler-owned interface registry**
  (`arklight/ir/platform_api.py`): `PlatformAPISpec`,
  `PLATFORM_API_REGISTRY` (`notify`, `clipboard_write`),
  `BACKEND_PLATFORM_API_SUPPORT` (`web`: both; `android`/`desktop`:
  neither -- Stage 2's job), `PlatformAPIError`,
  `check_backend_support()`.
- **Authoring surface** (`arklight/api.py`): `PlatformAPI.notify(title,
  body=None)`, `PlatformAPI.clipboard_write(text)`, each building a
  `PlatformAPIRef` (`arklight/ast/nodes.py`) for `on_click=` -- the
  same shape `Action.*(...)`/`ActionRef` already established.
- **Validation** (`arklight/ir/validate.py`):
  `_validate_platform_api` -- capability existence and keyword-
  argument-name checks, wired into both `on_click` validation sites
  (top-level and inside a `Repeat(...)` template).
- **HTML compilation** (`arklight/backend/html/attrs.py`): a
  `PlatformAPIRef` on `on_click=` compiles to
  `data-ark-on-click="platform:<capability>"` +
  `data-ark-platform-api-args`, reusing the same attribute slot
  `ActionRef`'s `"action:"` prefix already established.
- **Web (JS) implementation** (`arklight/backend/js/platform_apis/`):
  one module per capability (`notify.py`, `clipboard_write.py`),
  mirroring the `actions`/`behaviors` per-file fragment pattern
  exactly -- `NAME` + `JS_FRAGMENT`, only shipped when a site's IR
  actually references that capability. `clipboard_write` is
  deliberately not a duplicate of the pre-existing `copy` **behavior**
  (`arklight/backend/js/behaviors/copy.py`, `v0.063`'s JS vocabulary
  addendum) -- see
  [`docs/Foundational/PLATFORM-APIS.md`](../Foundational/PLATFORM-APIS.md)'s
  "Relationship to the `copy` behavior" section for the boundary
  between the two.
- **Dispatch wiring** (`arklight/backend/js/runtime/dispatch.py`):
  `wireClickInterceptor` grows a third `"platform:"` branch alongside
  its existing `"action:"`/`"behavior:"` ones, reading
  `data-ark-platform-api-args` and dispatching into a `platformApis`
  object, its own try/catch guard mirroring the other two branches'.
- **Runtime assembly** (`arklight/backend/js/render.py`):
  `_collect_usage` tracks `used_platform_apis` from every
  `on_click=PlatformAPIRef` in a site's IR; `_platform_apis_object_js`
  builds the "only ship what's used" `platformApis` dispatch object,
  same discipline as `_actions_object_js`/`_behaviors_object_js`;
  `needs_click_interceptor` now also triggers on platform API usage
  (a Platform API call never touches `State(...)`, so it never
  triggers `needs_actions_object` the way a `Watch(...)` does);
  `check_backend_support(used_platform_apis, backend_name="web")` runs
  unconditionally during `_build_runtime_js`, failing the build with a
  named-capability diagnostic (Section 11 of the proposal) rather than
  silently dropping an unsupported request or deferring the failure to
  runtime.
- **Tests:** `tests/test_platform_api.py` (18 tests) -- API factory
  return values, validation errors (unknown capability, unexpected
  keyword argument), HTML attribute compilation, JS "only ship what's
  used" discipline for both capabilities individually and together,
  click-interceptor dispatch wiring, the no-`eval`/`new Function`
  invariant, and `check_backend_support` actually firing (both as a
  standalone check and from inside `JSBackend.render()`).

## Stage 2 of 2 -- Android/Desktop native implementations (PLANNED)

Not started, and deliberately not slotted into a specific version yet
-- Section 6/22 of the proposal is explicit that a backend earns a
platform API capability by actually implementing its contract, not by
existing. `BACKEND_PLATFORM_API_SUPPORT["android"]` and
`["desktop"]` stay empty frozensets until each backend's own
implementation work happens (Kotlin for Android per
`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`'s own staging
ladder; C/GTK for Desktop per
`docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`'s), most naturally
as a stage inside each of those ladders rather than a new entry here,
once either backend reaches the maturity bar Section 22 sets.
`check_backend_support` already fails loudly for either backend today
-- Stage 2 is closing that gap, not opening a new one.

## Status tracking

| Stage | Covers | Status |
| --- | --- | --- |
| 1 of 2 | Web reference implementation (architecture + `notify`/`clipboard_write`) | SHIPPED (`v0.065`) |
| 2 of 2 | Android/Desktop native implementations | PLANNED, unscheduled |

See `docs/version history/v0.065.md` for this stage's forward-looking,
user-facing summary (updated to reflect actual shipped behavior), and
`PROGRESS.md`/`CHANGELOG.md` for the internal record.
