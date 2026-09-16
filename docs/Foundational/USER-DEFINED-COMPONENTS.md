# User-Defined, Reusable Components (v0.060)

_Current as of **v0.063** (latest shipped milestone) — see
[`PROGRESS.md`](../../PROGRESS.md)'s Snapshot table if this file's own
status line below might have moved since it was last updated._

Status: **shipped in full** (Stages 0-4). This is the one practical
reference for using `component(...)` -- what it does, its full prop
surface, and its scope boundaries. For *why* it's shaped this way (the
Option A/macro-expansion vs. Option B/registry decision, and how this
fits ARKlight's positioning against `htpy`/FastHTML), see
[`DESIGN-NOTES.md`](./DESIGN-NOTES.md) ("Does v0.060 change the
comparison?"). For where it sits in the compiler pipeline, see
[`ARCHITECTURE.md`](./ARCHITECTURE.md).

## What it is

`component(...)` promotes a plain Python render function into a real,
named node type the compiler itself understands -- not just a Python
function ARKlight is oblivious to. A registered component gets a
checked props contract, participates in `arklight search`'s typo
suggestions, can ship default styling, and (in `mode="registry"`) can
render differently per backend.

```python
from arklight import component, Prop, Container, Link

@component(props={"active": Prop(default=None)})
def NavBar(active=None):
    return Container(
        Link("Home", href="/", class_name="active" if active == "home" else None),
        Link("About", href="/about", class_name="active" if active == "about" else None),
        class_name="nav",
    )

NavBar(active="home")
```

The decorated name becomes callable exactly like a built-in
(`NavBar(active="home")`). Under the hood, the call produces a marker
node that gets expanded -- spliced into its real, rendered subtree --
before Validation ever runs, so every existing compiler stage and
backend keeps working against the same closed built-in vocabulary it
always has. Zero required changes downstream for a plain component.

## Props

```python
component(props={"active": Prop(default=None), "count": Prop(type=int)})
```

- A `Prop` with no `default` is **required** -- a missing prop fails
  the build.
- An **unknown** prop at a call site fails the build too (closed
  contract, not silently passed through).
- Errors surface as a clear `ComponentError` at build time, not a raw
  Python `TypeError` two frames deep inside your render function.
- There is no dedicated children slot yet -- pass child content as an
  ordinary prop value (`Card(body=Container(...))`), the same way
  built-ins that need a non-text child already work.

## Default styling

```python
@component(default_style={"display": "flex", "gap": "1rem"})
def NavBar(...): ...
```

- Validated with the same rules `Site.style(...)` uses, at
  registration time.
- When a build actually uses the component, the rules are folded into
  the site's stylesheet under a `.NavBar` class, and that class is
  folded onto the rendered subtree's own root automatically -- callers
  don't need to pass `class_name=` themselves.
- Only emitted for components a given build actually calls; an unused
  registration contributes nothing.
- An explicit `site.style("NavBar", {...})` always wins over a
  component's own default on a name collision.

## Two modes: macro (default) vs. registry (experimental)

```python
@component(mode="macro")     # default -- one shared render_fn, always
@component(mode="registry")  # experimental -- can add per-backend overrides
```

- **`mode="macro"`** -- the component's marker is always, fully
  spliced away by its one shared `render_fn`. This is what you want
  unless you specifically need per-backend rendering.
- **`mode="registry"`** -- additionally lets you register a
  backend-specific override:

  ```python
  @component(mode="registry")
  def NavBar(active=None):
      return Container(...)  # shared default

  @NavBar.register_backend("html")
  def _(active=None):
      return Container(..., class_name="html-only-navbar")
  ```

  A backend with no override registered for a given component falls
  back to the shared `render_fn` -- identical output to `mode="macro"`.
  Only the HTML backend can consume an override today (Android/Desktop
  aren't separate IR renderers yet).

## Component-owned state

```python
@component(state={"open": False})
def Accordion(open=False, ...):
    return Container(
        Button("Toggle", on_click=Action.toggle_bool("open")),
        Show(Predicate.truthy("open"), Text("...")),
    )
```

- Declares **local, instance-scoped** reactive state: every call site
  (`Accordion()` used twice on one page) gets its own independent
  copy -- they never share one `"open"` value.
- Reference a declared name exactly like a page-level `State(...)`:
  `Bind(...)`, `on_click=Action.*(...)`, `bind_class=Bind.when(...)`,
  `bind_value=Bind.model(...)` all work unchanged.
- Use `{name: ComponentState(initial=..., persist=True)}` instead of a
  bare initial value when an instance needs `localStorage`
  persistence.
- A component can still *consume* `Bind(...)`/`ActionRef` values
  passed in as ordinary props from a page's own `State(...)` --
  independent of, and combinable with, its own local `state=`.

## Scope boundaries (know these before reaching for a workaround)

- No children slot -- use a prop instead (see "Props" above).
- `state=` is not supported inside a `mode="registry"` component's
  own per-backend override subtree -- raises `ComponentError`.
- A component can't declare its own `Computed(...)`/`Watch(...)` --
  only `State(...)`-equivalent local state. It can still read a
  page-level `Computed`/react to a page-level `Watch` passed in as a
  prop.
- `responsive_style={...}` inside a `mode="registry"` backend
  override's own subtree doesn't collect into the site-wide `@media`
  rules -- use `site.media_query(...)` instead for that case.
- `arklight search NavBar` (an exact-name lookup) doesn't yet print a
  schema summary for a user component the way it does for a built-in
  -- only the *typo-suggestion* path knows about registered
  components.
- A component with `state=` used inside a `Repeat(...)` template, or a
  `mode="registry"` backend override that itself calls another
  state-owning component, are both untested edge cases -- likely fine
  (no special-casing excludes them), but not a covered guarantee.
