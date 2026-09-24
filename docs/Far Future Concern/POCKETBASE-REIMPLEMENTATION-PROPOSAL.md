# ARKbase: A PocketBase-Shaped Data Service for ARKlight, Definable in Python or Rei

## Status

**Far Future Concern. Speculative, not proposed as work, not accepted,
holds no version slot.** The maintainer's designation for it is `v1.2`.
That is an ordering label meaning "after `v1.0` ships," not a schedule:
it is deliberately not a row in `docs/Foundational/ARCHITECTURE.md`'s
Milestones table or `PROGRESS.md`'s Snapshot table, and nothing in this
file authorizes work on any of it. Until a maintainer accepts it, real
version numbers are not assigned; the stages below use `B0`-`B8`
labels, the same convention
`docs/Proposals/REI-DYNAMIC-CLASS-WASM-PROPOSAL.md` uses for its
`DC0`-`DC5` ladder.

Filed against `alpha` @ `ee106ca`. PocketBase was studied at commit
`5cec579` (2026-09-12) of https://github.com/pocketbase/pocketbase,
whose own `CHANGELOG.md` opens at `v0.40.4`. Every claim about
PocketBase below was checked against that checkout, and every claim
about ARKlight against this tree. When this file is picked up for real
it graduates to `docs/Proposals/` (per `docs/README.md`'s lifecycle
table) and must be re-verified against whatever `alpha` has become by
then, the way `docs/Proposals/REI-LANGUAGE-PROPOSAL.md` carries a
re-verification section.

**Naming note.** "Backend" is avoided on purpose:
`arklight/backend/` already means *output target* (HTML, CSS, JS,
Android, Desktop), and `docs/Proposals/PROVIDER-SDK-PROPOSAL.md`
named `Provider` specifically to dodge that collision. "ARKbase" is a
working title, not a decision (Open question 3).

## Origin

A maintainer discussion of whether ARKlight should ship a default data
service so a beginner with no backend knowledge can go from an idea to
a somewhat-working app. It began as a small prototyping server and was
settled, by the maintainer, at three decisions:

1. **The target is PocketBase's shape** -- collections, a records API,
   auth, files, realtime, an admin UI -- not a smaller JSON-file mock.
2. **From scratch, no third-party dependency.** As of `ee106ca`,
   `pyproject.toml` declares no runtime dependencies, and
   `arklight/search/` already uses stdlib `sqlite3` while
   `arklight/cli/live_streaming.py` and `arklight/cli/cctv.py` already
   use stdlib `http.server`.
3. **It must be possible in both Python and Rei.**

This file turns those three decisions into a reviewable design and
records where they collide with what the tree already says.

## TL;DR

- A self-hostable, single-directory data service in PocketBase's
  shape, implemented with Python's standard library only, and the
  first concrete implementation anyone would write against the
  `Provider` contract.
- **The Python/Rei parity contract lives at the *definition* layer.**
  A "base" (collections, fields, access rules, auth settings) is
  closed-vocabulary data, authorable in Python or in `.rei`, lowering
  to one canonical form. Acceptance criterion: the same definition
  written in both languages yields byte-identical canonical output.
  The *engine* that serves it is Python. Arbitrary-code hooks are
  Python-only until Rei has a compute story, and this file does not
  promise otherwise (Section 3.2, Open question 1).
- **It is not a small project.** PocketBase is roughly 57,000 lines of
  non-test Go (Section 2). This file proposes a ladder that ships
  usable value early and drops the expensive parts (30 OAuth2
  providers, S3, image thumbnails, a JS VM).
- **The beginner promise is blocked on something outside this
  document:** ARKlight's client side has no way to load data from a
  server (Section 6).
- Acceptance would require amending two scope lines in the Provider
  docs, which currently rule this out on purpose (Section 11).

## 1. What this is not

- Not a hosted service, and not a way to deploy one.
- Not a BaaS competitor. It is a prototyping and small-self-hosting
  tool, and inherits the `README.md` alpha notice (hobby projects
  only) until a maintainer says otherwise.
- Not part of the `v1.0` stability promise.
  `docs/Foundational/V1-DEFINITION.md` scopes that promise to the Web
  Developing parts of the compiler and excludes experimental
  features; a `Provider` implementation stays
  behind the `provider-integration` gate in
  `docs/Foundational/EXPERIMENTAL-APIS.md` unless a maintainer
  decides differently.

## 2. What PocketBase is, as studied

At `5cec579`, PocketBase's non-test Go is about 57,000 lines (raw
`wc -l`, comments and blanks included):

| Area (PocketBase repo path) | Lines | What it holds |
| --- | --- | --- |
| `core/` | ~22,400 | Collection and record models, 14 field types (`autodate`, `bool`, `date`, `editor`, `email`, `file`, `geo_point`, `json`, `number`, `password`, `relation`, `select`, `text`, `url`), validation, the rule/filter resolver, hooks |
| `tools/` | ~17,400 | `filesystem` (~5,000, local + S3), `auth` (~3,700, 30 OAuth2 provider files), `router` (~1,900), `search` (~1,700, filter/sort parsing), mailer, cron, security |
| `apis/` | ~8,700 | Route handlers and middleware (body limit, rate limit, CORS, gzip) |
| `plugins/` | ~5,100 | Optional extras, including the JS VM that runs user hooks |
| `migrations/`, `forms/`, `mails/`, `cmd/` | ~3,000 | System migrations, validation forms, mail templates, the `serve` command |
| `ui/` | separate | A JavaScript admin dashboard, embedded into the binary (`ui/embed.go`) |

The behavior that matters for this design:

- **Three collection types:** `base`, `auth`, `view`
  (`core/collection_model.go`). Auth collections add password auth,
  OAuth2, OTP, MFA, an `authRule`, a `manageRule` and auth alerts.
- **Records API:** list, view, create, update, delete under one route
  group (`apis/record_crud.go`), plus collections CRUD, batch,
  files, backups, logs, cron, settings and a health check.
- **Realtime is Server-Sent Events**, a `GET` that opens a
  `text/event-stream` and a `POST` that sets subscriptions
  (`apis/realtime.go`).
- **Access is five rules per collection** (list, view, create, update,
  delete), each a nullable string. `nil` means superusers only; an
  empty string means everyone; anything else is a filter expression
  compiled into the SQL `WHERE` clause (`core/record_query.go`,
  `CanAccessRecord`). A one-character difference separates "locked"
  from "public." Rules are validated when a collection is saved
  (`checkRule` in `core/collection_validate.go`), i.e. at admin time,
  not at a build step.
- **`pocketbase serve` binds `127.0.0.1:8090`** when no domain is
  given (`cmd/serve.go`), and, with no built UI, tells the operator to
  create the first superuser from the command line
  (`apis/installer.go`).
- **PocketBase is pre-1.0.** Its README warns that backward
  compatibility is not guaranteed before `v1.0.0`. Any promise of
  wire compatibility (Open question 2) chases a moving target.
- **Licence:** MIT (`LICENSE.md`).

## 3. What the three decisions mean

### 3.1 From scratch, no dependency

| PocketBase piece | Standard-library route | Cost or risk |
| --- | --- | --- |
| Embedded SQLite (pure-Go driver) | `sqlite3` | SQLite version and extensions depend on the Python build; feature-detect, do not assume. One writer at a time. |
| `net/http` server | `http.server.ThreadingHTTPServer` | Python's own docs say `http.server` is not recommended for production and implements only basic security checks. See Section 7. |
| JWT auth tokens | `hmac`, `hashlib`, `secrets` | ARKlight already seals `.ark` bundles with these three modules alone (`arklight.packer.seal`, `docs/Foundational/AUTHORING-GUIDE.md`). Token signing is a different job from sealing, but the primitives are the same. |
| Password hashing | `hashlib.scrypt` where the Python build has it, else `hashlib.pbkdf2_hmac` | Record the algorithm and parameters per hash so they can be upgraded. |
| Mail | `smtplib` | Default to a dev mail sink (console or a folder) so a beginner never needs SMTP. |
| OAuth2 | `urllib.request` | Generic OIDC at most; 30 provider files is not a target. |
| File storage | Local directory | No S3 (request signing is doable but large), no thumbnails (no stdlib image library). |
| Backups | `zipfile` plus the `sqlite3` backup API | Small. |
| Realtime | SSE over the threaded server | One thread per open connection; a hard ceiling (Section 7, B7). |
| JS hooks (goja VM) | Not replicated | See 3.2 and B8. |

### 3.2 Both Python and Rei

What the tree says about Rei as of `ee106ca`
(`docs/Implementation/REI-LANGUAGE-ADDENDUM.md`):

- Rei is a *source frontend*: `.rei` files lower to the same
  `dict[str, ARKNode]` and `CONFIG` shapes Python authoring produces.
  Nothing below that lowering changes.
- Rei is never shipped to the browser and has no runtime of its own.
- `arklight.config.rei` is **data-only**: one top-level initializer, no
  functions, no calls.
- The Compute stage (constants, functions, a minimal evaluator) is
  **blocked** on the Rei proposal's Open question 3 and holds no
  version slot.
- Dynamic classes compiled to WebAssembly
  (`docs/Proposals/REI-DYNAMIC-CLASS-WASM-PROPOSAL.md`) are proposed,
  not accepted.

So a data service **written in Rei** is not reachable under any spec
in this tree. A data service **defined in Rei** is: schema, rules and
settings are exactly the kind of closed, data-shaped content the Rei
ladder already lowers. This file therefore reads decision 3 as:

> Every part of a base that is *data* must be authorable in Python or
> in Rei with identical meaning. Every part that is *code* is Python
> until Rei can express it.

That reading is a working interpretation, not a settled one. It is
Open question 1, and it should be confirmed or corrected first.

## 4. The definition layer

### 4.1 One canonical form, two authoring surfaces

Both languages lower to a single, deterministic, JSON-serializable
description. The engine reads only that form; it never imports the
author's Python, so the two languages cannot diverge in behavior. This
mirrors the invariant the Rei proposal already states for sites.

### 4.2 Fields

First cut: `text`, `number`, `bool`, `date`, `autodate`, `email`,
`url`, `select`, `relation`, `json`. Deferred: `file` (B5), `editor`,
`geo_point`. `password` exists only inside auth collections.

### 4.3 Rules are a closed tree, not a string language

PocketBase's rules are strings interpreted by a server-side
expression engine. ARKlight's doctrine is the opposite: closed
vocabulary, no string ever executed, and "fail loudly at build time."
So rules are a small typed tree:

- Predicates: `Rule.public()`, `Rule.authenticated()`,
  `Rule.owner(field)`, `Rule.field(name)` with `eq`, `ne`, `gt`, `lt`,
  `in_`, and `Rule.superuser()`.
- Combinators: `Rule.all(...)`, `Rule.any(...)`, `Rule.not_(...)`.
- **A missing rule means locked.** Public access must be spelled
  `Rule.public()`. This removes PocketBase's `nil` versus `""`
  footgun by construction.
- A malformed or unknown rule raises at build time, before any
  server starts.
- Cross-collection relation traversal is out of the first cut. Where
  the vocabulary stops before it becomes a general expression
  language is Open question 10.

Optionally, a PocketBase rule *string* can be **imported** by a
parser that accepts a documented subset and refuses everything else.
The string is never executed.

### 4.4 Illustrative sketches (non-normative)

Spelling is **not** decided in either language. Shown only so the
shape is reviewable.

```python
Collection(
    "posts",
    fields=[
        Field.text("title", required=True),
        Field.select("status", values=["draft", "public"]),
        Field.relation("author", to="users"),
    ],
    list_rule=Rule.any(Rule.field("status").eq("public"),
                       Rule.owner("author")),
    create_rule=Rule.authenticated(),
    update_rule=Rule.owner("author"),
    # delete_rule omitted -> locked to superusers
)
```

```
// a data-only .rei definition, in the tree-expression style
// REI-LANGUAGE-PROPOSAL.md section 2.3 already sketches
Collection("posts",
    Field.text("title", required: true),
    Field.select("status", values: ["draft", "public"]),
    Field.relation("author", to: "users"),
    list_rule:   Rule.any(Rule.field("status").eq("public"),
                          Rule.owner("author")),
    create_rule: Rule.authenticated(),
    update_rule: Rule.owner("author"),
)
```

Both must produce the same canonical bytes. That equality is the
parity test.

### 4.5 Invariants (each one a test)

- **I1. Parity.** Same definition, either language, identical
  canonical output.
- **I2. Locked by default.** Every collection route without an
  explicit rule refuses non-superusers.
- **I3. Refuse, never ignore.** An unknown field type, rule kind or
  setting raises; it is never dropped silently.
- **I4. No string is executed or spliced.** Rules and client query
  parameters are parsed by a closed grammar and reach SQLite only as
  bound parameters.
- **I5. Zero third-party imports.** The engine imports only the
  standard library; a test scans for anything else.
- **I6. Deterministic canonical form.** Stable ordering and
  formatting, so diffs are meaningful.

## 5. Storage and migrations

The canonical definition generates SQLite tables. A *diff* between two
canonical definitions produces a migration plan. Additive changes
apply; anything destructive (dropping a field, narrowing a type) is
refused unless the author passes an explicit flag. PocketBase
auto-writes JS migration files; this design keeps the definition as
the single source of truth and derives the plan from it.

## 6. The client side is the real blocker

What ARKlight can and cannot do as of `ee106ca`:

- `Provider` is a declaration only. It adds no networking; the only
  runtime trace is the read-only `window.ARKLIGHT_PROVIDER`
  (`{name, capabilities}`) (`arklight/provider.py`).
- `docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md` Section 7
  names client-side data fetch (a `DataSource`-style node) as the
  actual missing capability, recommends treating it as its own
  milestone, and notes that a site cannot express "load this JSON and
  render it" without a server round-trip through htmx. As of `ee106ca`
  that gap is still open.
- The same proposal's Section 8 puts SSE/WebSocket as an authored
  primitive **out of scope**, and calls client-side third-party
  secrets an anti-pattern. The second point constrains this design:
  no compiled page may need a static secret. Login yields a per-user
  token, never a key baked into the site.

Consequences for the ladder: a beginner cannot build a working app
against the service until a client data primitive exists, and an
admin UI written in ARKlight (B6) and realtime (B7) both depend on it
or on a decision to reopen Section 8. The definition layer (B1) and
the server (B2-B5) do not.

The `Provider` capability vocabulary (`auth`, `read`, `write`,
`subscribe`) is provisional as of `ee106ca`; the Provider ladder
finalizes it at its last stage, `v0.070`. It has no name for files,
batch or admin operations. Whether that matters is Open question 9.

## 7. Security posture

Commitments this design would have to keep, each to be reviewed:

- **Locked by default, loopback by default.** Bind `127.0.0.1`;
  print a loud banner if bound elsewhere.
- **Parameterized SQL only,** closed query grammar, no `eval`
  (invariant I4).
- **Request limits.** PocketBase ships body-size, rate-limit, CORS and
  gzip middleware. The stdlib server ships none of them; a minimal
  set is part of B3 and B5, not optional.
- **Honest label.** `http.server` is documented as unsuitable for
  production. Unless a hardened HTTP layer is separately designed
  (Open question 5), the service is prototype and small-self-hosting
  grade and says so at startup.
- **Threaded SSE** holds one thread per open connection, which caps
  realtime scale well below a Go server. State the ceiling.
- **Passwords and tokens** use stdlib primitives with per-hash
  parameters and constant-time comparison (`hmac.compare_digest`).

## 8. Staged ladder (non-normative order)

| Stage | Scope | Depends on |
| --- | --- | --- |
| **B0** | Prerequisites, not work in this ladder: `v1.0` shipped; the `Provider` ladder (`v0.065`-`v0.070`) finished; a decision on a client data primitive (`JS-VOCABULARY-EXPANSION-PROPOSAL.md` Section 7) | -- |
| **B1** | Definition layer: `Collection`, `Field.*`, `Rule.*`, canonical form, build-time validation, Python/Rei parity tests. No server, no SQLite. Useful alone: typo'd rules fail the build | B0 (Rei ladder for the `.rei` half) |
| **B2** | Storage: definition to SQLite DDL, migration plan from definition diffs, refuse-destructive default | B1 |
| **B3** | Records API, query grammar, rule enforcement, loopback default, body limit, superuser created from the CLI (no UI) | B2 |
| **B4** | Auth collections: password, signed tokens, verification and reset via the dev mail sink | B3 |
| **B5** | Local files, batch, request logs, rate limiting | B3 |
| **B6** | Admin dashboard authored in ARKlight itself | B3 plus a client data primitive |
| **B7** | Realtime over SSE | B3 plus reopening `JS-VOCABULARY-EXPANSION-PROPOSAL.md` Section 8 |
| **B8** | Hooks: declarative closed-vocabulary hooks (both languages); Python hook functions (Python only); Rei hooks unscheduled | B3; Rei Compute or dynamic classes |

Unscheduled, no stage: generic OIDC, backups, S3, `view` collections,
PocketBase schema import/export.

## 9. Non-goals

- Wire compatibility with PocketBase or its SDKs as a promise.
- The 30 OAuth2 providers, S3, image thumbnails, a JS VM.
- Multi-node, high availability, multi-tenant hosting.
- Reading PocketBase's `pb_data` directory.
- Replacing Python authoring, or shipping Rei to any runtime.
- A stability promise for any of it before a maintainer gives one.

## 10. Provenance and licence

PocketBase is MIT; ARKlight is `GPL-3.0-or-later` (`pyproject.toml`).
MIT permits reuse with the notice retained, but this design ports no
Go source: it reimplements behavior and API shapes in a different
language. Anything that is copied verbatim (documentation text, test
fixtures) keeps PocketBase's copyright notice. Whether to formalize
that rule (a third-party notice file, a clean-room rule for
implementers) is Open question 8.

## 11. What acceptance would have to amend

- `docs/Proposals/PROVIDER-SDK-PROPOSAL.md` Section 2 ("No shipped
  implementations").
- `docs/Implementation/PROVIDER-SDK-ADDENDUM.md`'s scope filter, which
  lists "any server ARKlight stands up or deploys" as out of scope on
  purpose and says nothing in that ladder authorizes it.
- `docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md` Section 7
  (client data primitive) would gain a forcing use case; Section 8
  would be reopened for B7.
- `docs/Implementation/REI-LANGUAGE-ADDENDUM.md`: a new data-only
  `.rei` file kind for definitions, beyond `arklight.config.rei`.

## 12. Open questions

1. **What does "possible in both Python or Rei" mean?** This file
   reads it as definition-layer parity (Section 3.2). If it means the
   *engine* must be writable in Rei, that needs the dynamic-class
   proposal accepted and a host runtime that does not exist in this
   tree. Confirm the reading first.
2. **Wire compatibility.** Mirror PocketBase's record URL shapes so
   its docs transfer, promise nothing about SDKs, or diverge fully?
   PocketBase is pre-1.0, so the target moves.
3. **Name.** "ARKbase" is a placeholder.
4. **Where the code lives.** Inside `arklight/`, or a separate
   package in the way `Provider` implementations were meant to be?
5. **Production stance.** Prototype-grade only, or design a hardened
   HTTP layer?
6. **PocketBase interop.** Import PocketBase collection JSON? Read
   `pb_data`? Neither?
7. **Client token storage** and the XSS/CSRF model. This needs the
   client primitive designed first (Section 6).
8. **Provenance mechanics** (Section 10).
9. **Capability vocabulary.** Do files, batch and admin need names
   before or after `v0.070` finalizes it?
10. **How far the rule vocabulary may grow** before it becomes the
    general expression language `JS-VOCABULARY-EXPANSION-PROPOSAL.md`
    Section 2 rules out for the browser runtime, and whether that
    non-goal is meant to bind a server-side rule tree too.
