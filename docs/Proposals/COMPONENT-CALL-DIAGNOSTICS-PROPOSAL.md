# Capability fix: compiler-native diagnostics for user-defined component calls

## Status

Implemented, alpha (`0.06506`). Out-of-band, numbered capability fix per
`docs/Foundational/V1-DEFINITION.md`'s "Issue triage during Alpha"
section, the same slot-sharing precedent as `0.0650`-`0.06505`; the
roadmap's `v0.065` is untouched. Traces to
[`ARKlight-ISSUE-REGISTER.md`](ARKlight-ISSUE-REGISTER.md) #5 (positional
component errors leak a raw `TypeError`) and #32 (component API
diagnostics aren't consistently compiler-native). Not a broken promise
but a missing one: `@component`'s own docstring already says a misused
component "fails the build with a clear message instead of a raw Python
`TypeError`", and two boundaries didn't keep it.

## The gap

`@component` checks props against the `props=` contract at *expansion*
time (`_resolve_props`), and that check is compiler-quality:
`ComponentError` naming the component, the unexpected or missing prop and
the declared ones. But Python gets to a call first, in two places:

1. **The call site.** A component's call-site marker was declared
   `marker(**call_props)`, so `Stat("a", "b")` never reached ARKlight's
   own checks. Python refused it with `Stat() takes 0 positional
   arguments but 2 were given`: true about Python, silent about the
   actual rule (props are keyword-only) and about what `Stat` accepts.
2. **The render function.** Expansion calls `render_fn(**resolved_props)`,
   where `resolved_props` holds exactly the keys `props=` declares. If
   `props=` names a prop the function has no parameter for, or the
   function has a required parameter `props=` doesn't declare, the call
   raised a raw `TypeError` from inside the expansion pass, with no
   mention of `props=`.

Reproduced first, on `alpha` at `0.06505`:

```python
@component(props={"label": Prop(), "value": Prop(default=0)})
def Stat(label, value=0): ...

Stat("a", "b")   # TypeError: Stat() takes 0 positional arguments but 2 were given
```

Through `compile_site_file` that surfaced as `Error while building
page(s): Stat() takes 0 positional arguments but 2 were given`, with no
file or line.

## Design

**Positional calls.** The marker now accepts `*args` only so a positional
call reaches ARKlight's own check, then raises `ComponentError` (already
the type every other component misuse raises, and already wrapped into
`CompileError` by the pipeline). The message names the component, the
argument count, the rule (keyword props only), the declared props, a
by-name example built from them, and a note that positional *children*
have no equivalent on a user-defined component. It also carries the
offending call's `file:line`, read from the caller's frame, so it points
into the user's own site file. A component that declares no props says
so ("takes no arguments at all"); one called with more arguments than it
has props says how many it declares.

```text
Component 'Stat' was called with 2 positional arguments, but user-defined
components accept keyword props only. Declared props: ['label', 'value'].
Pass each value by name instead, e.g. Stat(label=..., value=...).
Positional children are not supported on a user-defined component; pass
content through a declared prop. (called at site.py:12)
```

**Props vs. signature.** Expansion, and a `mode="registry"` backend
override's dispatch, now go through `call_render_fn`, which runs
`inspect.Signature.bind(**resolved_props)` first. A binding failure
becomes a `ComponentError` naming the component, Python's own binding
reason, the declared props and the function's parameters, and stating the
rule (every declared prop is passed by keyword, so each must be a
parameter or the function must take `**kwargs`, and every required
parameter must be declared).

Why bind-checking is safe: `bind` never runs the function, and because
`resolved_props` holds exactly the declared props, every call it rejects
was already certain to raise `TypeError`. It cannot reject a working
component. Errors raised *inside* the render function are never
rewritten. A callable `inspect.signature` can't introspect is called
unchecked, as before.

**Why at call time and not registration.** Checking `props=` against the
signature in `@component(...)` would fail a broken component at import
even if nothing ever uses it, which changes behavior for existing
projects. Checking at use fails exactly the builds that were already
going to fail, only with a better message.

## Behavior changes

- A positional component call now raises `ComponentError` (a
  `RuntimeError`), not `TypeError`. Nothing in the tree caught the old
  `TypeError`; anything outside it that did should catch `ComponentError`.
- A `props=`/signature mismatch now raises `ComponentError` from the
  expansion pass rather than `TypeError`.
- Valid components, valid calls and every build that succeeded before are
  unchanged.

## Not done, on purpose

- **Positional children for components.** Deliberately not made to work.
  It would need a declared "children" prop and a spelling for it, which
  is a design question, not a diagnostic. The message says they're
  unsupported.
- **Auto-mapping positional arguments onto props.** The error suggests the
  keyword form instead. Order-based matching would make `props=`'s
  declaration order part of the public contract.
- **Type-checking the values of ARKlight's built-in components' misuse.**
  Only user-defined components are in scope.
- **A registration-time signature audit** (see above).

## Verification

`tests/test_component_call_diagnostics.py` (19 tests): message contents,
singular/plural, no-props and too-many-args cases, unchanged keyword
calls, the call-site location through `compile_site_file`, mismatch in
both directions, `**kwargs` and defaulted extras still accepted, a
`TypeError` raised in the function body left alone, `mode="registry"`
components, and a backend override whose signature disagrees with its
component's `props=`.
