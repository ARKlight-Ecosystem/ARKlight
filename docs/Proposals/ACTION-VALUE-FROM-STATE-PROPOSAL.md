# Capability fix: live-input -> action-value (`Bind(...)` as an `Action.*` argument)

## Status

Implemented, alpha (`0.06503`). Out-of-band, numbered capability fix per
`docs/Foundational/V1-DEFINITION.md`'s "Issue triage during Alpha"
section -- not a broken promise but a missing one, so it doesn't wait for
whichever milestone is already in flight. Traces to
[`ARKlight-ISSUE-REGISTER.md`](ARKlight-ISSUE-REGISTER.md) #7.

## The missing capability

The vocabulary can bind an input to state (`bind_value=Bind.model(...)`,
`vdom-6`) and can append to a list (`Action.append(name, value)`), but
`value` was a compile-time literal. Nothing said "pass whatever this state
holds *right now* as the argument," so the conventional
`[type a task] [Add]` control wasn't expressible; the Focus Board
application fell back to quick-add buttons.

`Bind`'s own docstring already promises the reading ("reference a
`State(...)` value from wherever a literal value is accepted"). An action
argument is such a place -- and it was the one that failed worst:
`Action.append("tasks", Bind("draft"))` passed Validation and then died in
the HTML backend with a raw `TypeError: Object of type ARKNode is not JSON
serializable`.

## Design

**Spelling.** `Bind("draft")` in an argument position. No new public name.

```python
State("draft", "")
State("tasks", [])
Input(bind_value=Bind.model("draft"))
Button("Add", on_click=Action.append("tasks", Bind("draft")))
Watch("tasks", then=Action.reset("draft"))     # clear the input after adding
Repeat("tasks", template=lambda: Text(RepeatItem.value()))
```

The clear-after-add step needs no new construct: `Watch(...)` (`vdom-5`)
already reuses the action dispatcher, and `renderModelBindings` already
syncs state back into the input.

**Wire shape.** `Action.*` converts the `Bind` at construction into the
plain JSON object `{"__state__": "<name>"}`. A plain dict, not a
dataclass, because a dataclass nested in `ActionRef.args` is flattened by
`dataclasses.asdict` during `.arklight` encoding and loses its type tag
(the documented `ItemIndexRef` gap in `arklight/ir/binary.py`). A dict
survives that round trip, `json.dumps` in every serialization site (HTML
`data-ark-action-args`, the `data-ark-watch` blob, `Repeat` template
specs) and needs no per-backend translation. `__state__` is a reserved key.

**Resolution.** At dispatch time, in the browser:
`arklight/backend/js/runtime/action_args.py` swaps each marker for
`store.get(name)` and passes the action fragment a plain args object -- so
`set`/`append` are unchanged and no fragment learns markers exist. Dispatch
time means a `.debounce(...)`d click reads the value when the action
*runs*. The resolver returns a new object because a `Watch(...)`'s parsed
args live for the whole page. It is inlined (one shared source string)
into both `wireClickInterceptor` and `wireWatchers` rather than shipped as
a third top-level function, so each fragment stays self-contained.
No eval, no `new Function`: the name is only ever a store key.

**Validation** (`_validate_action_args`), all build-time:

- the argument must be opted in by `ActionSpec.state_args` -- today only
  `set` and `append`, `value`. `increment`/`decrement`'s `delta` and
  `remove`'s `index` are refused: an input-bound *string* would silently
  concatenate (`0 + "5"` -> `"05"`) or, for `remove`'s strict `!==`,
  silently match nothing;
- the marker must be exactly `{"__state__": <non-empty str>}`; a literal
  dict carrying the reserved key is refused rather than misread;
- the name must be a `State(...)` or `Computed(...)` declared on the page.
  Reading a `Computed` is fine; it is still never an action *target*;
- a leftover `Bind` node in args (an `ActionRef` built by hand) gets a
  pointed error instead of the old raw `TypeError`.

**Component-owned state.** `_rewrite_component_state_refs` renames markers
in action args together with the action's target, so a component's local
`draft` and `items` move to their namespaced page keys as a pair.

## Known limits (deliberate)

- `Bind.model("draft", debounce=300)` delays the write-back into state, so
  a click inside that window reads the *previous* value. Don't debounce
  the input a submit button reads from.
- Values from an `Input` are strings. That is why numeric actions are not
  opted in.
- Only top-level argument values are read; `Bind` nested inside a list or
  dict argument is not resolved.
- No Enter-to-submit. Keyboard events are outside this fix.
- Not `Action.set_from_input` (`DESIGN-NOTES.md`): that was about binding
  state to `input`/`change` events, which `bind_value=` already covers.

## Tests

`tests/test_action_value_from_state.py`: API conversion, every validation
rule above, HTML/`Watch`/`Repeat` serialization, `.arklight` round trip,
component-state renaming, `arklight search` output, and two Node-driven
tests that run the real `WIRE_WATCHERS_JS` and `CLICK_INTERCEPTOR_JS`
(each fails if resolution is disabled). Also checked once by hand against
jsdom with a full build: add, add again, input cleared, debounced click.
