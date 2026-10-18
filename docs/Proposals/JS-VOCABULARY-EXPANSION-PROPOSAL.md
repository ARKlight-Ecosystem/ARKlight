# Proposal: Expanding the Client-Side JS Vocabulary

**Status:** Partially accepted. Tier 1, Tier 2, and §6 (the
exhaustive scalar catalog, including §6.5) have been accepted and
staged as a ten-rung implementation ladder --
[`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`](../Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md)
(`v0.061`-`v0.070`), of which stages 1-7 (`v0.061`-`v0.067`) have
shipped and stages 8-10 remain PLANNED. The new Tier 3 (§7, added
below) and the renumbered Tier 4/Tier 5 (§8/§9) remain unsettled
proposals -- nothing in this file's acceptance covers any of them.
The rest of this document is kept in full, unedited, as the source
catalog that ladder was staged from, with Tier 3 inserted in place
as a follow-up finding rather than folded into §6's catalog, for the
reason given in §7's own rationale.

**Origin:** an audit of `alpha` branch (`arklight/backend/js/*`,
`arklight/ir/schema.py`, `PROGRESS.md`, `docs/Foundational/DESIGN-NOTES.md`)
against what real-world sites lean on client-side JS for.

## TL;DR

ARKlight's client-side "computation" is a **closed, named vocabulary**
compiled into vanilla JS -- not a real expression language. That's a
deliberate, documented, *permanent* design decision (no `eval`/`new
Function`, ever, per `docs/Foundational/DESIGN-NOTES.md`), not an
oversight. Within that constraint, the vocabulary already covers most
of what Vue-3-style reactivity needs (state, computed values,
watchers, two-way binding, list rendering, conditional rendering,
persistence).

This proposal covers five things, in ascending order of effort:

1. **Tier 1 -- trivial gaps** already designed but never shipped
   (basic arithmetic, basic string casing, the comparison predicates)
   -- one-hour, one-file, one-registry-line additions each.
2. **Tier 2 -- small new runtime primitives** (`IntersectionObserver`-
   based `reveal`/lazy-load, debounced two-way binding, clipboard
   paste, geolocation, `matchMedia`-driven state) -- a day or two
   each, same registry pattern, no new IR node.
3. A **much larger, exhaustive catalog of scalar derivations and
   predicates** -- pulled from JS's own `Math`, `String`, `Number`,
   and `Array` built-ins (§6.1-6.4) plus common cross-language
   "batteries included" idioms JS itself has no built-in for at all,
   like C++'s `lerp`, Rust's saturating arithmetic and `Option`
   combinators, and Python/Rust "humanize"/inflection libraries
   (§6.5) -- as candidate `DERIVATION_REGISTRY`/`PREDICATE_REGISTRY`
   entries. The point here is to establish the *full* boundary of
   what a closed-vocabulary scalar-derivation system can cover before
   reaching for a real evaluator, so the registry grows once, in a
   principled way, instead of by one-off requests forever.
4. **Tier 3 -- closed-vocabulary conditional/value-selection and
   indexing primitives** (§7, new) -- `Derive.if_`/`Derive.select`,
   arbitrary list indexing, and date/time arithmetic. These are
   placed in their own tier, after §6's scalar catalog and before
   the old Tier 3's IR-node-sized bucket (renumbered Tier 4 below),
   because they're closed-arity and side-effect-free like §6's
   entries, but every one of them needs a new `DerivationRef`/
   `PredicateRef` shape rather than a same-shape registry line, so
   they don't belong folded into §6's flat catalog either.
5. The **IR-node-sized gaps** (client-side data fetching chief among
   them, now Tier 4, §8) and the **out-of-scope bucket** (now Tier 5,
   §9) that conflicts with ARKlight's stated non-goals -- kept here
   because they're the part of the original audit that actually
   needs a maintainer decision, not just typing.

---

## 1. What ARKlight ships today

| Category | Registry | Items | File pattern |
|---|---|---|---|
| **Actions** (state mutation) | `ACTION_REGISTRY` | `set`, `increment`, `decrement`, `toggle_bool`, `reset`, `append`, `remove` | `arklight/backend/js/actions/<name>.py` |
| **Behaviors** (DOM-only, no state) | `BEHAVIOR_REGISTRY` | `toggle` (class), `scroll-to`, `copy` (clipboard), `dismiss` | `arklight/backend/js/behaviors/<name>.py` |
| **Derivations** (`Computed`) | `DERIVATION_REGISTRY` | `sum`, `multiply`, `join`, `count`, `format`, `compare` (`eq/ne/gt/lt/gte/lte`) | `arklight/backend/js/derivations/<name>.py` |
| **Predicates** (`Show`) | `PREDICATE_REGISTRY` | `truthy`, `falsy` only -- `equals`/`gt`/`lt` were designed but never shipped | `arklight/ir/schema.py` |
| **Event modifiers** | `MODIFIER_REGISTRY` | `prevent`, `stop`, `once`, `debounce:<ms>`, `throttle:<ms>` | `arklight/ir/schema.py` |
| **Runtime primitives** | n/a (fixed core) | reactive store (`get/set/reset/subscribe`), text/class bindings, two-way `Input` binding (`Bind.model`), `Watch`, `Repeat`, `Show`, nav-link highlighting, on-page toast (`arkNotify`), `localStorage` persistence (`State(persist=True)`) | `arklight/backend/js/runtime/*.py` |
| **Navigation/AJAX** | vendored htmx 2.0.10 | `hx-boost`, form submission, history cache, `revealed`/`intersect` triggers | `arklight/backend/js/htmx.py` |
| **Offline** | `arklight pwa` | generated Service Worker, cache-first precache, Web App Manifest | `arklight/pwa.py` |

Everything here is generated by concatenating small, named JS
fragments -- **only the fragments a given site actually uses ship in
the output**. Adding a new action/behavior/derivation is explicitly
documented as: one new module (`NAME` + `JS_FRAGMENT`), one registry
line, done -- "never a change to the backend's generation logic
itself."

## 2. Why the computation ceiling is deliberate

`docs/Foundational/DESIGN-NOTES.md` ("Why 'Vue 3 parity' needs a
different mechanism than Vue 3 uses") states outright that Vue 3's
breadth comes from a real expression evaluator, and that ARKlight
rules that mechanism out *categorically, not as a matter of degree* --
no arbitrary JS/Python string is ever handed to the browser to
execute, no `eval`, no `new Function`. The documented trade instead
is breadth of closed, compiler-recognized primitives: where Vue writes
`v-if="count > 5"`, ARKlight writes `Show(Predicate.gt("count", 5))`.

That means there's a real, intentional ceiling: you cannot write
`price * qty * 1.08` inline. You declare a `Computed(...)` against a
fixed catalog of derivation kinds. This proposal takes that boundary
as fixed and asks: **how far can the catalog itself be pushed before
a genuinely open expression is required?** The answer, worked out
below, is "considerably further than seven derivations" -- most of
what a `v-if`/`v-bind`/computed-property author reaches for in
practice reduces to a scalar function of a small, fixed arity, which
is exactly the shape a registry entry can express.

## 3. Real-world client-JS patterns still uncovered

Grounded in current usage data (State of JS 2025, MDN/web-analytics
API-popularity trackers) plus common front-end patterns. This table
is carried over from the original audit for context; most rows are
addressed by the small-primitive or IR-node tiers, not by this
proposal's derivation catalog:

| Pattern | Why it's common | ARKlight today |
|---|---|---|
| `fetch`/AJAX to a JSON API | Most common client-side JS use case outside form/nav handling | Not available; htmx only swaps HTML fragments |
| Drag-and-drop (reorder lists, Kanban) | Common in dashboards/admin UIs | Not available; `Repeat` has no reorder action |
| Client-side form validation beyond native HTML5 | Cross-field checks, async validation | Only native browser validation |
| `IntersectionObserver` (lazy-load, reveal-on-scroll) | Common performance/animation pattern | Used internally by htmx, not exposed as an authoring primitive |
| Web Share API, print-this-page, geolocation | Common small utilities | Not available |
| WebSocket / Server-Sent Events (live data) | Common for dashboards, chat, live status | Only in dev-tooling (`live_streaming.py`, `cctv.py`), not authored sites |
| Sort/filter a rendered list client-side | Very common (tables, product grids) | `Repeat` has no sort/filter derivation |
| ResizeObserver / `matchMedia`-driven state | JS-side responsive behavior beyond CSS | Not available |
| File upload preview | Common on any upload form | Not available |
| Keyboard shortcuts | Common in app-like sites | Not available (click-only dispatch) |

## 4. Tier 1 -- Trivial gaps (hours each)

Already designed in the docs, just never implemented -- mirrors an
existing module's `op` logic almost exactly, so each is a same-day,
one-file, one-registry-line addition:

- **Math**: `subtract`, `divide`, `min`, `max` -- the missing
  siblings of `sum`/`multiply`.
- **Strings**: `uppercase`, `trim` -- the missing siblings of
  `join`/`format`.
- **`Show` predicates**: `equals`, `gt`, `lt` -- already speced
  alongside `compare`'s `eq/ne/gt/lt/gte/lte` op set, just never
  wired into `PREDICATE_REGISTRY` (which today only has
  `truthy`/`falsy`).

## 5. Tier 2 -- Small new runtime primitives (a day or two each)

Same registry pattern as Tier 1, but each needs a small new runtime
module (extends `arklight/backend/js/runtime/*.py`) rather than just
a fragment file -- no new IR node type required:

- **`reveal`/`lazy` behavior via `IntersectionObserver`** -- same
  shape as `scroll-to`, wraps an observer instead of
  `scrollIntoView`.
- **Debounced two-way binding** -- extends `Bind.model` to accept
  the existing `MODIFIER_REGISTRY` debounce/throttle tokens (the
  modifier plumbing already exists for actions; this wires it into
  `wireModelBinding` too).
- **Clipboard *paste*** behavior (`navigator.clipboard.readText()`)
  -- mirrors `copy.py` almost exactly.
- **Geolocation one-shot action** (`Action.geolocate(name)` writes
  `{lat, lng}` into state) -- self-contained, no new dependency-graph
  edges.
- **`matchMedia`-driven boolean state**
  (`State(..., media="(min-width: 768px)")`) -- one
  `MediaQueryList` listener per declared media state.

## 6. The exhaustive scalar-derivation and predicate catalog

This is the core of the proposal. Every function below returns a
single scalar (number/string/boolean) from a small, fixed set of
named inputs plus a JSON-serializable `args` dict -- the exact shape
`DERIVATION_REGISTRY`/`PREDICATE_REGISTRY` already require, and the
exact shape `sum`/`multiply`/`compare` already use. None of these
need a parser, an evaluator, or a change to `_evaluate_derivation`'s
dispatch pattern in `arklight/ir/build.py` -- each is "one new file +
one registry line," just a *lot* of them, cataloged here once so they
can be triaged as a set instead of trickling in one GitHub issue at a
time. Tier 1's `subtract`/`divide`/`min`/`max`/`uppercase`/`trim`/
`equals`/`gt`/`lt` (§4) are not repeated below; everything here is
additional to those.

### 6.1 Math derivations (beyond the basic arithmetic in §4)

Pulled from JS's own `Math` object, which is the de facto exhaustive
list any language's numeric vocabulary converges on:

| Derivation | JS equivalent | Notes |
|---|---|---|
| `absolute` | `Math.abs(x)` | |
| `ceiling` | `Math.ceil(x)` | |
| `floor` | `Math.floor(x)` | |
| `truncate_number` | `Math.trunc(x)` | distinct from string `truncate` |
| `sign` | `Math.sign(x)` | -1/0/1 |
| `sqrt` | `Math.sqrt(x)` | |
| `cbrt` | `Math.cbrt(x)` | |
| `power` | `Math.pow(base, exp)` | |
| `exp` | `Math.exp(x)` | |
| `log` | `Math.log(x)` | natural log |
| `log2` | `Math.log2(x)` | |
| `log10` | `Math.log10(x)` | |
| `hypot` | `Math.hypot(...values)` | Euclidean distance/norm over `names` |
| `clamp` | -- (no direct JS builtin, but ubiquitous utility) | `min(max(x, lo), hi)` |
| `average` / `mean` | -- | mean over `names`, complements existing `sum`/`count` |
| `median` | -- | middle value over `names` |
| `gcd` | -- | greatest common divisor, common in layout/grid math |
| `lcm` | -- | least common multiple |
| `percentage_of` | -- | `(a / b) * 100`, extremely common in progress bars/stats UIs |
| `to_fixed` | `Number.prototype.toFixed(n)` | fixed-decimal string formatting, common for prices |
| `to_precision` | `Number.prototype.toPrecision(n)` | |
| `random_int` | `Math.random()` composed with rounding | seeded carefully -- see caveat below |

**Caveat on `random_int`:** unlike every other entry, this
derivation is not a pure function of its inputs, which cuts against
the "server-rendered `Bind` text should agree with the client
recompute" invariant `sum.py`'s own docstring calls out. If adopted,
it needs an explicit design note (e.g. it's excluded from
build-time pre-rendering and always resolves client-side only) rather
than silently reusing the existing derivation dispatch contract.

### 6.2 String derivations (beyond `uppercase`/`trim` in §4)

Pulled from JS's `String.prototype` methods:

| Derivation | JS equivalent | Notes |
|---|---|---|
| `capitalize` | -- (composed from `charAt`/`toUpperCase`) | first letter only |
| `title_case` | -- | capitalize each word |
| `trim_start` | `String.prototype.trimStart()` | |
| `trim_end` | `String.prototype.trimEnd()` | |
| `pad_start` | `String.prototype.padStart(len, fill)` | |
| `pad_end` | `String.prototype.padEnd(len, fill)` | |
| `repeat` | `String.prototype.repeat(n)` | |
| `slice_string` | `String.prototype.slice(start, end)` | |
| `char_at` | `String.prototype.charAt(i)` | |
| `replace_first` | `String.prototype.replace(a, b)` | literal substring only, never a regex -- see caveat |
| `replace_all` | `String.prototype.replaceAll(a, b)` | literal substring only |
| `split_count` | `String.prototype.split(sep).length` | scalar output over a delimiter |
| `reverse_string` | -- (composed) | |
| `string_length` | `String.prototype.length` | complements existing `count` (which counts `names`, not chars) |
| `includes_substring` | `String.prototype.includes(s)` | as a **predicate**, not derivation |
| `starts_with` | `String.prototype.startsWith(s)` | predicate |
| `ends_with` | `String.prototype.endsWith(s)` | predicate |
| `is_empty` | `str.length === 0` | predicate, very common in `Show` guards for empty-state UI |

**Caveat on `replace_first`/`replace_all`:** these must take a
literal substring argument, never a regex pattern string. A regex
string passed through `new RegExp(pattern)` and executed is a much
softer version of the same `eval`-shaped risk the project has already
ruled out categorically for template expressions -- worth stating
explicitly in the registry entry's docstring so a future contributor
doesn't "helpfully" add regex support later.

### 6.3 Predicates (beyond `equals`/`gt`/`lt` in §4)

`Show`'s `PREDICATE_REGISTRY` currently only has `truthy`/`falsy`,
plus the Tier 1 comparison predicates in §4 once those are wired up.
Beyond those, common `v-if`-equivalent guards include:

| Predicate | Meaning | Notes |
|---|---|---|
| `and` | logical AND over 2+ named booleans | mirrors `sum`'s `names`-list shape |
| `or` | logical OR over 2+ named booleans | |
| `not` | logical negation of one named boolean | |
| `in_range` | `lo <= x <= hi` | complements `clamp` |
| `one_of` | value is a member of a fixed `args` list | common for tag/category filters |
| `is_empty` / `is_not_empty` | string/array/`null` emptiness | see 4.2 |
| `is_null` | value is `null`/`undefined` | common guard before rendering optional data |

### 6.4 List-scalar derivations (input is a list-valued state name, output is still scalar)

`Repeat` renders lists, but nothing today reduces a list-typed
`State` value to a scalar the way `sum`/`count` reduce multiple
*named* states. These read `Array.prototype` methods but stay
scalar-out, so they don't need the new "list-in, list-out" registry
(`SORT_REGISTRY`/`FILTER_REGISTRY`) that sorting/filtering would --
that stays in Tier 4 (§8) below.

| Derivation | JS equivalent | Notes |
|---|---|---|
| `list_length` | `Array.prototype.length` | |
| `list_min` | `Math.min(...arr)` | |
| `list_max` | `Math.max(...arr)` | |
| `list_average` | -- | |
| `list_first` | `arr.at(0)` | |
| `list_last` | `arr.at(-1)` | |
| `list_includes` | `Array.prototype.includes(v)` | predicate |
| `list_any` | `Array.prototype.some(...)` over a fixed comparison | predicate, bounded to the existing `compare` op set, not an arbitrary callback |
| `list_all` | `Array.prototype.every(...)` over a fixed comparison | predicate, same bound |

### 6.5 Cross-language "batteries included" primitives (beyond JS's own built-ins)

§6.1-6.4 above are all things JS itself already ships as `Math`/
`String`/`Array` methods -- ARKlight is just missing a registry
fragment around them. This subsection instead looks at what Python,
Rust, and C++ standard libraries offer that JS has *no* built-in for
at all, filtered down to the ones that still reduce to a scalar
function of fixed inputs and so still fit the closed-registry shape
without a new IR node:

| Derivation/Predicate | Inspired by | Notes |
|---|---|---|
| `lerp` | C++20 `std::lerp(a, b, t)` (`<cmath>`) | linear interpolation, `a + t*(b-a)` with the correctly-rounded edge cases C++20 specifically added a stdlib function for (`t=0` returns exactly `a`, `t=1` returns exactly `b`). Very common in progress-bar/slider/drag-to-scale UI, which is exactly ARKlight's territory -- JS has no built-in equivalent, everyone hand-rolls it. |
| `midpoint` | C++20 `std::midpoint(a, b)` (`<numeric>`) | `(a + b) / 2` computed without the intermediate-overflow risk of the naive version -- niche in JS's float world, but cheap to add for parity/precision. |
| `saturating_add` / `saturating_subtract` | Rust `i32::saturating_add`/`saturating_sub` | clamps to a fixed min/max instead of overflowing or going negative -- e.g. a quantity stepper that should stop at 0 rather than go negative. Complements `clamp` (§6.1) but reads more naturally for increment/decrement-style UI. |
| `value_or` | Rust `Option::unwrap_or` | returns a named state value, or a fallback from `args` if it's `null`/`undefined`/empty-string -- the scalar, non-panicking cousin of Rust's `Option` combinators; useful for "show this, or a placeholder" text bindings without a full `Show`/`Watch` pair. |
| `first_present` | Rust `Option::or` chains / SQL `COALESCE` | first non-null/non-empty value across 2+ named states, in order -- generalizes `value_or` to more than one fallback. |
| `to_ordinal` | Python/Rust "humanize"-style libraries (`inflection`, `humanize`, `humfmt`) | `1` -> `"1st"`, `2` -> `"2nd"`, etc. -- common in date/ranking UI. |
| `humanize_bytes` | Rust `humanize-bytes`, Python `humanize.naturalsize` | `1536` -> `"1.5 KB"` -- extremely common for upload/download/storage UI; JS has no built-in (`Intl` covers currency/number/date, not byte counts). |
| `humanize_duration` | Rust `humantime`/`humanize-duration`, Python `humanize.naturaldelta` | seconds -> `"2h 15m"`-style string -- common for "time remaining"/"elapsed" UI. |
| `pluralize` | Python `inflection`, Rust `inflector-plus`, Ruby on Rails inflector (the common ancestor most of these port) | `"item"` + count -> `"item"`/`"items"` -- ubiquitous in list-count UI copy ("3 items in cart"). English pluralization has enough irregular forms (`person` -> `people`, `octopus` -> `octopi`) that this is closer to Tier 2 effort than Tier 1: it needs a small irregular-word table, not just a suffix rule, and should ship with a documented "regular-plural-only" fallback rather than pretending to be exhaustive. |
| `to_snake_case` / `to_camel_case` / `to_kebab_case` / `to_title_case` | Python `inflection`/`camelcase-to-snakecase`, Rust `inflector-plus`, Dart `Inflector` (all cross-porting the same idea) | pure string-rewrite case converters, ubiquitous across *every* language's utility-belt library -- no irregular-word problem like `pluralize`, so these stay genuinely Tier 1/one-hour-shaped despite living in this cross-language section. |

None of these need a parser or a callback -- `lerp`/`midpoint`/
`saturating_add`/`value_or`/`first_present` are pure arithmetic or
null-coalescing over named states; the humanize/case/pluralize
entries are pure string rewrites over one input plus a locale/rules
table baked into the fragment (same shape `format.py` already uses
for its format-string argument). `pluralize` is the one entry worth
flagging as more than an hour's work; everything else here is exactly
as cheap as §6.1-6.4.

**Not included here:** Python's `itertools`/Rust's `Iterator`
combinators (`pairwise`, `batched`/`chunk`, `accumulate`/running-sum,
`dedupe`/`unique`) are common across every language's "batteries
included" story too, but they're list-*in*, list-*out* -- the same
shape as sort/filter in Tier 4 (§8), not a scalar reduction like
§6.4's `list_min`/`list_average`. They're flagged there instead of
here so this section stays honest about what's actually
registry-shaped today versus what needs the new list-transform
registry Tier 4 already calls for.

## 7. Tier 3 -- Closed-vocabulary conditional/value-selection and indexing primitives

Found in a follow-up pass over `DERIVATION_REGISTRY`/
`PREDICATE_REGISTRY` against this file's own original audit, after
Tier 1/Tier 2/§6 were accepted: a small set of entries that are
closed-arity and side-effect-free -- the same test §2 and §6 already
apply -- but that didn't surface in either the original audit or §6's
pass, because none of them are a `Math`/`String`/`Array` built-in or a
cross-language batteries-included idiom. They're placed in their own
tier, between Tier 2 and the old Tier 3 (renumbered Tier 4, §8 below),
rather than folded into §6, because every entry here costs a new
`DerivationRef`/`PredicateRef` *shape*, not just a same-shape registry
line -- which is exactly the "registry-filling exercise" vs. "genuine
design decision" split §8 below already draws, just at a smaller
scale than a full new IR node.

### 7.1 `Derive.if_` -- two-branch conditional value selection

The single most basic thing missing: "pick value A or value B based
on a condition" -- Jinja's `{{ a if cond else b }}`, Liquid's
`{% if %}`, Vue's ternary-in-text-binding. Today `Show(Predicate.*)`
gates whether a whole *element* renders; nothing gates which *value* a
binding resolves to. `compare` (§1) returns a bool, not a selection;
`value_or`/`first_present` (§6.5) are null-coalescing only, not
predicate-gated.

```python
Computed("price_label", deps=["qty"],
    derive=Derive.if_(
        Predicate.gt("qty", 10),     # condition -- reuses the existing,
                                       # already-validated predicate vocabulary
        "bulk price",                 # when_true
        "regular price",              # when_false
    ))
```

- **External precedent for the scope line:** JSONLogic ships
  `{"if": [cond, then, else]}` as its one conditional primitive, with
  the same "no setters, no loops, no functions, never `eval`"
  discipline this file already cites for ARKlight's own ceiling (§2)
  -- a widely-adopted precedent that closed-vocabulary conditional
  value-selection is a different, safer mechanism than an open
  expression, not a softened version of one.
- **The actual design cost:** every existing `DerivationRef` keeps
  `names` (state/computed references) and `args` (literal data)
  strictly separate -- no kind mixes the two within one slot.
  `when_true`/`when_false` each need to be *either* a literal or a
  name, which is a new `DerivationRef` shape, not just a new `kind`
  string in the existing one. That's the one real design decision
  here; the conditional logic itself costs nothing new, since the
  condition is just a `PredicateRef`, already fully specified by
  `PREDICATE_REGISTRY`.
- **Validation** follows the exact pattern `compare`'s `op` arg
  already uses in `arklight/ir/validate.py`, extended to check each
  branch value is either a literal or a declared `deps` name.
- **Not pursued alongside this:** making `and`/`or` (§6.3)
  value-returning the way JSONLogic's are, rather than boolean-only --
  once `Derive.if_`/`Derive.select` exist, that's the more direct way
  to express the cases JSONLogic covers through short-circuiting
  `and`/`or`, so widening `and`/`or` on top would just be two ways to
  write the same thing; left out to avoid that overlap.

### 7.2 `Derive.select` -- multi-branch conditional (natural follow-on)

Chained `(predicate, value)` pairs plus a default, same lineage as
JSONLogic's `if` accepting more than three arguments as chained
else-ifs. Ships *after* `Derive.if_` lands and sees real use --
building the N-branch version first would mean guessing at the common
branch count instead of observing it.

### 7.3 `list_at` -- arbitrary list indexing

`char_at` (§6.2) already reads one character out of a string at a
literal index (`DerivationSpec(min_names=1, max_names=1,
extra_args=("index",))`); nothing equivalent exists for a list-typed
`State`/`Computed` value -- only `list_first`/`list_last` (§6.4), both
fixed-position. `list_at(list, index)` is the direct list-side
counterpart, same shape and same `LITERAL_ARG_RULES`-checked
range-bound index as `char_at` already gets.

### 7.4 Date/time arithmetic and formatting

A `Time` component already exists in the IR, but `DERIVATION_REGISTRY`
has no date-related kind at all -- not even a §6.5-style "batteries
included" entry, despite that subsection explicitly sweeping JS's
`Math`/`String`/`Number`/`Array` built-ins and their cross-language
equivalents. Candidates: `date_add`/`date_diff` (closed unit argument:
`"days"`/`"hours"`/... -- same closed-choice-not-raw-string shape
`compare`'s `op` already establishes), and `format_date` (closed
format-token argument, not a user-supplied strftime/ICU pattern
string, for the same reason `replace_first`/`replace_all` (§6.2) take
a literal substring and never a regex). **Flagged for explicit
maintainer sign-off before implementation**, same as `pluralize`/
`random_int` were in §6.5/§10 -- locale-aware date formatting in
particular has enough surface area (timezones, calendar systems,
locale-specific token sets) that it risks becoming its own
`Intl.DateTimeFormat`-shaped subsystem rather than a one-file registry
addition, and that scoping question should be settled before any code
is written, not discovered partway through.

## 8. Tier 4 -- New IR-node-sized features (kept from the original audit)

These need a new IR node + schema + validation, the size of
`Repeat`/`Show` when those landed. Listed here because they're the
part of the original audit that's a genuine design decision, not a
registry-filling exercise:

- **Client-side data fetch -> `State`** (e.g.
  `DataSource("items", url="/api/items.json")`) -- the actual "not
  enough computation" gap. Needs a new node type, new IR fields,
  HTML-side markup for loading/error states, and a runtime `fetch` +
  JSON-parse + `store.set` pipeline. Comparable scope to `vdom-7`
  (`Repeat`+`Show` combined).
- **Reorderable lists** (drag-and-drop over `Repeat` items, plus a
  `move`/`reorder` action operating on list index) -- needs an
  index-to-index action shape and a drag-event runtime module.
- **Sort/filter over `Repeat`** -- a genuinely list-in/list-out
  concept, needing its own registry since `DERIVATION_REGISTRY`
  assumes scalar output (unlike the list-*reducing* derivations in
  §6.4, which stay scalar). The same registry is the natural home for
  Python `itertools`/Rust `Iterator`-style list-in/list-out
  transforms flagged in §6.5 -- `pairwise` (consecutive-pair diffs),
  `batched`/`chunk` (fixed-size groups, e.g. for a grid layout),
  `accumulate` (running totals for a sparkline), and `dedupe`/
  `unique` -- once that registry exists, since none of them fit
  today's scalar-only `DERIVATION_REGISTRY`.
- **File upload + preview** -- `<input type=file>` handling, a
  `FileReader`-based preview runtime module, and IR support for
  binding the preview into `Bind`.

## 9. Tier 5 -- Out of scope (maintainer/design decision required)

- **General arithmetic/string expressions** (`price * qty - discount`)
  -- exactly what the permanent non-goal in §2 rules out. However
  exhaustive §6's catalog gets, an open expression syntax is a
  different mechanism entirely and stays off the table by design.
- **WebSocket/SSE as an authored primitive** -- technically
  approachable (dev CLI already uses `EventSource` internally), but
  productizing a "live state channel" as a first-class site feature
  is a new subsystem, not a fragment.
- **IndexedDB / offline data mutation & sync** -- much bigger than
  `localStorage` persistence; conflicts with "static, dependency-free
  output" positioning unless scoped very narrowly.
- **Third-party API calls needing auth/secrets client-side** -- a
  static-site generator has no safe place to keep a secret; an
  anti-pattern for the project's whole premise, not just a missing
  feature.

## 10. Suggested order

1. Ship **Tier 1** (§4) first -- same day, closes the most-noticed
   gaps (basic math ops, the already-designed `Show` predicates).
2. **Tier 2** (§5) next, prioritizing `reveal`/`IntersectionObserver`
   and debounced input binding -- the two most commonly reached-for
   browser APIs missing today.
3. Triage §6 as a batch: it's long on purpose, so a maintainer should
   pick a subset (math-heavy sites want §6.1, text-heavy sites want
   §6.2, list-heavy dashboards want §6.4, animation/UI-heavy sites
   want §6.5's `lerp`) rather than shipping all of it reflexively.
   Flag `random_int` (§6.1), `replace_first`/`replace_all` (§6.2),
   and `pluralize` (§6.5) for explicit sign-off given their caveats.
4. Ship **Tier 3** (§7) next, in the order it's written: `Derive.if_`
   (§7.1) first since it's the one other proposals/sites are already
   asking for and the one new `DerivationRef` shape everything else in
   this tier either reuses or doesn't need; `list_at` (§7.3) same day,
   same shape as the already-shipped `char_at`; `Derive.select` (§7.2)
   only once `Derive.if_` has real usage to generalize from; date/time
   (§7.4) only after the explicit sign-off its own entry calls for.
5. Treat §8's `DataSource`/client-side fetch as its own milestone
   (like `v0.054` was for reactivity) -- it's the actual answer to
   "the computation isn't enough," since today ARKlight genuinely
   cannot express "load this JSON and render it" without a full
   server round-trip via htmx.
6. Leave §9 out of scope unless the "no eval, ever" and "static
   output only" invariants themselves are up for reconsideration --
   that's a philosophy call, not an engineering one.
