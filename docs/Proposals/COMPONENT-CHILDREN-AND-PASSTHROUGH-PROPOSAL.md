# Children/Slots and Prop Passthrough for User-Defined Components

## Status

**Proposal -- not yet accepted, not yet staged.** Per
`docs/Proposals/README.md`'s own definition, this describes something
that does not exist yet, may never be built as written, and could be
rejected outright. Nothing below is implemented.

**Origin:** the gap `docs/Foundational/WHAT-ARKLIGHT-IS.md` section 6
and `docs/Foundational/CAPABILITY-MATRIX.md`'s "Slots / children for
user-defined components" row have named for a while without a staged
plan attached. Filed as this proposal alongside the
`State(..., persist=True, scope="global")` bug fix (`CHANGELOG.md`,
"Closing a capability as a bug fix") as the next, larger piece of the
same "things web developers take for granted" list -- deliberately
scoped here rather than built outright in that same pass.

## What is already settled (context, not part of this proposal)

- **User-defined components are keyword-only, by design, today.**
  `arklight.ir.components.positional_call_message` exists specifically
  to turn Python's own `TypeError` (`Stat() takes 0 positional
  arguments but 2 were given`) into an ARKlight-shaped error: a
  component's call site is matched by *name* against its `props=`
  contract, and "user-defined components accept keyword props only"
  is the message's own wording. The same function's tail line is
  explicit about the gap this proposal addresses: *"Positional
  children are not supported on a user-defined component; pass
  content through a declared prop."* That sentence is the whole
  problem statement, already written into the error path.
- **Built-in components don't have this problem.** `Container(
  Text("hi"), class_name="box")` -- positional args are children,
  keyword args are props, per `arklight/api.py`'s `node(...)`
  wrapper. The asymmetry is specifically between built-ins (positional
  children, always) and user-defined components (no positional
  arguments at all, full stop).
- **The expansion mechanism already exists to extend.**
  `arklight.ir.components.expand_components()` walks the tree before
  Normalization and splices a registered component's rendered subtree
  in its marker's place (`ComponentSpec.render_fn`, called through
  `call_render_fn`); `_render_once` resolves a call's props against
  `ComponentSpec.props` via `_resolve_props`, applies default styling
  (`_apply_default_class`/`apply_default_style_class`,
  `ComponentSpec.default_style`), and -- for `mode="registry"`
  components with at least one backend override -- tags the rendered
  root with a `ComponentOrigin` marker consumed later by
  `arklight.ir.component_dispatch`. Children support is "one more
  thing `_render_once` does before/around `call_render_fn`," not a new
  pipeline stage; prop passthrough is "one more thing `_resolve_props`
  does with an unrecognized keyword," not a new validation subsystem.
- **`default_style`'s auto-applied `class_name` is the closest
  existing precedent for "something lands on the component's own root
  without the author writing a line for it"** (`_apply_default_class`).
  Passthrough `class_name`/`id`/`data-*`/`aria-*`/event props is the
  same shape of problem -- something arriving at the component's call
  site that belongs on its rendered root, not inside its `props=`
  contract -- solved the same way `default_style` already proved out,
  not a new idea.

## The proposal, as stated

Two related, separately stageable gaps, because they're both things a
developer runs into "once they reach for children at all," per
`WHAT-ARKLIGHT-IS.md`'s own framing, but they are different sizes of
change:

1. **Children/slots.** `Card(Text("content"))` has no way to get
   `"content"` into `Card`'s own render function, the way `children`
   (React) or `<slot>` (Vue/web components) does.
2. **Prop passthrough.** An unrecognized `class=`/`id=`/`data-*`/
   `aria-*` or event prop (`on_click=...`) passed to a user-defined
   component call has nowhere to go -- it isn't in `props=`, so
   `_resolve_props` has no slot for it, and there is no way today to
   land it on the component's own rendered root without naming it as
   a `Prop` explicitly, one at a time, for every such need.

### Children/slots: the staged shape

**Rung 1 -- single implicit slot.** A component that opts in
(`component(..., accepts_children=True)`, naming to be settled)
accepts positional arguments at its call site exactly like a built-in
does. Those positional children are collected and passed to the
render function as a new reserved argument -- `children`, matching the
word the gap description and React both already use -- a tuple of
already-built `ARKNode`s, inserted into the render function's own
returned tree wherever it places `children`. This is deliberately the
*smallest* version of the idea: one undifferentiated children
sequence, no named slots.

```python
@component(accepts_children=True)
def Card(children):
    return Container(
        *children,
        class_name="card",
    )

# call site, positional children now accepted:
Card(Text("content"))
```

The call-site change is exactly the inverse of
`positional_call_message`'s existing rule: a component that declares
`accepts_children=True` is explicitly opting out of the "keyword props
only" error for positional arguments specifically -- keyword `props=`
matching is unaffected and still works exactly as it does today.

**Rung 2 -- named slots, if Rung 1's single-slot shape turns out not
to be enough in practice.** Something closer to Vue's named
`<slot name="...">` -- e.g. a reserved prop convention
(`Card(header=Heading("Title"), children=[Text("body")])`) rather than
one flat `children` tuple. Deliberately left unshaped here: Rung 1
should ship and get used before deciding whether real ARKlight
components actually need more than one slot, rather than designing
Rung 2's exact syntax against a hypothetical need.

### Prop passthrough: the staged shape

**Rung 1 -- a fixed, closed set.** `class_name`, `id`, and an explicit
allow-list of `data-*`/`aria-*` prop names (matched by prefix, not
individually enumerated) are accepted at any user-defined component's
call site without being declared in `props=`, and are merged onto the
rendered root the same way `_apply_default_class` already merges
`default_style`'s class today -- call-site `class_name` appended to
rather than replacing a component's own default class, consistent
with how `_apply_default_class` already treats an author-supplied
`class_name`.

**Rung 2 -- event props.** `on_click=`/`on_*=` forwarded onto a
component's own rendered root when the component itself doesn't
already bind that event somewhere in its render tree. This rung is
explicitly listed second and separately because it touches
`Action.*` resolution (`arklight.ir.schema.ACTION_REGISTRY`) rather
than being a pure prop-copying operation like Rung 1 -- it needs its
own look at whether an action bound at the call site and one bound
inside the component's own render function can ever collide on the
same root node, and what happens if they do.

### Why staged, not built outright

Per `docs/Proposals/README.md`, filing this as a proposal rather than
a patch is the point: this is "a separate compiler change, the size of
`Repeat`/`Show`" (`CAPABILITY-MATRIX.md`'s own description of this
row), not a fragment any existing capability-ladder filter admits.
Rung 1 of children and Rung 1 of passthrough are the pieces worth
building first if this is accepted at all -- both are additive,
backward-compatible (no existing component call site changes
behavior unless it opts in with `accepts_children=True`, or happens to
pass a `class_name`/`id`/`data-*`/`aria-*` prop today, which currently
either errors or silently does nothing depending on whether it's
declared -- worth auditing before shipping Rung 1, see Q4).

## Acceptance criteria

1. A component declared with `accepts_children=True` accepts
   positional arguments at its call site without
   `positional_call_message` firing, and its render function receives
   them as `children`.
2. A component that does *not* opt in keeps today's behavior exactly:
   positional arguments still raise `positional_call_message`'s error.
3. `class_name`/`id`/`data-*`/`aria-*` props reach a user-defined
   component's rendered root without being declared in `props=`, and
   compose with (rather than silently discard) that component's own
   `default_style`-applied class.
4. Existing components -- every one registered today, with no
   `accepts_children=True` and no passthrough props at any real call
   site -- produce byte-identical output to before this change, the
   same invariant `default_style`/Stage 3's backend-override work
   already held itself to.
5. Nothing here requires a new compiler stage: children/slot expansion
   and passthrough both resolve inside the existing
   `expand_components()`/`_render_once`/`_resolve_props` path.
6. An unrecognized prop that is *not* on the passthrough allow-list,
   and is not a declared `Prop`, still raises today's error -- Rung 1
   is a fixed allow-list addition, not a general "anything
   unrecognized passes through silently" rule.

## Open questions

**Q1. Where does `children` live relative to `props=`?** A reserved
keyword name that can't also be a declared `Prop` (an explicit
collision check, erroring at `component(...)` registration time if a
component tries to declare both `accepts_children=True` and a `Prop`
named `children`), or a distinct function argument Python itself keeps
separate from `**resolved_props`? The call-render signature
(`call_render_fn`) would need to decide this either way.

**Q2. `mode="registry"` interaction.** `ComponentOrigin.resolved_props`
is what a backend override gets called with (Stage 3,
`arklight.ir.component_dispatch`). Does `children` ride along in
`resolved_props` the same way, so a per-backend override can also
place children -- or is children-placement something only the shared
`render_fn` ever controls, with overrides limited to prop-driven
differences? This wasn't settled by Stage 3 because Stage 3 predates
children entirely.

**Q3. Nested components as children.** `Card(OtherComponent(...))` --
does the inner `OtherComponent` expand before or after it's handed to
`Card`'s render function as part of `children`? `expand_components()`
walking the tree top-down vs. bottom-up decides this, and it changes
what `Card`'s render function actually sees (an already-expanded
built-in subtree, vs. a still-opaque component marker it can't
introspect).

**Q4. Audit before shipping Rung 1 of passthrough.** What does an
unrecognized `class_name=`/`data-*` prop at a user-defined component
call site do *today* -- a hard error (most likely, since it isn't in
`props=`), or something that already silently passes through some
other path? If any real project depends on today's error behavior for
one of these specific names, Rung 1 is a breaking change for that
project, not a pure addition. This needs checking against
`_resolve_props`'s actual behavior before the acceptance criteria
above can be called complete.

**Q5. Naming.** `accepts_children` is a placeholder, not a decision --
`children=True`, `slot=True`, or folding it into `mode=` are all live
options and should be weighed against `arklight.api.component`'s
existing keyword surface (`default_style=`, `state=`) for consistency.

## If accepted -- a sketch, not a commitment

- `ComponentSpec` gains an `accepts_children: bool = False` field
  (or equivalent, per Q5), defaulting to today's behavior.
- `positional_call_message`'s call site (wherever it's invoked for a
  user-defined component's marker) gains the opt-in check from
  acceptance criterion 2.
- `_render_once`/`call_render_fn` pass `children` through to
  `render_fn`, per however Q1 settles.
- `_resolve_props` (or a sibling function next to it) gains the fixed
  passthrough allow-list from Rung 1, landing passthrough props onto
  the rendered root the same way `_apply_default_class` already lands
  `default_style`'s class.
- Event-prop forwarding (Rung 2) stays unscheduled pending its own
  look at `ACTION_REGISTRY` interaction (see "Why staged, not built
  outright").
- `AUTHORING-GUIDE.md`, `docs/Foundational/USER-DEFINED-COMPONENTS.md`,
  and tests following `tests/test_persist_global_scope.py`'s pattern
  (unit coverage per layer, plus an end-to-end case). Nothing staged;
  this would graduate to `docs/Implementation/` only once accepted,
  per `docs/Proposals/README.md`'s own graduation path.

## Not in scope

- Named slots (Rung 2 of children) -- deliberately deferred until
  Rung 1 ships and gets used; see "Children/slots: the staged shape."
- Event-prop forwarding (Rung 2 of passthrough) -- deferred pending
  its own `ACTION_REGISTRY` interaction question; see Q above.
- A general "any unrecognized prop passes through" rule -- Rung 1 is a
  fixed, closed allow-list (`class_name`, `id`, `data-*`, `aria-*`),
  not an escape from `props=` validation entirely.
- Changes to `mode="macro"` vs. `mode="registry"` selection itself, or
  to `default_style`'s existing behavior, beyond whatever Q2 turns out
  to need.
