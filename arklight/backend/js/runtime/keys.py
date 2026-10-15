"""
`wireKeyInterceptor`: the single, delegated `keydown` listener for
Stage 2 of `docs/Implementation/INPUT-AND-PLATFORM-PRIMITIVES-
ADDENDUM-v0.071.md` -- `on_key=Key.on(<key>, Action.*(...))`,
element-scoped key events. Same "one listener, data-driven dispatch"
shape `wireClickInterceptor` (`runtime/dispatch.py`) already
established for clicks, not a per-element `addEventListener` pass.

Compiled attribute shape (see `arklight/backend/html/attrs.py`'s own
note on this): `data-ark-on-key` carries the bare `event.key` string
this binding matches; `data-ark-key-action`/`-key-action-state`/
`-key-action-args` mirror `on_click`'s `data-ark-on-click`/
`-action-state`/`-action-args` attributes exactly, dispatched through
the same closed `actions` object `wireClickInterceptor` reads (see
`arklight/backend/js/render.py`'s `_actions_object_js`,
`used_key_actions` folded into the broader `used_actions` set by
`_collect_usage`). `data-ark-key-modifiers` is the one real
difference from `on_click=`'s compiled shape -- a plain
comma-separated token list (`prevent,stop,once`, or
`debounce:300`/`throttle:300`), parsed directly below rather than
compiled to `hx-trigger`: HTMX's trigger syntax has no notion of "this
key, on this element, bubbled from keydown" (`keydown` itself firing
for every key would defeat the closed key enum), so Stage 2 doesn't
route through it at all -- see `attrs.py`'s module comment on
`on_key=` for the full reasoning.

Element matching -- "walks up through ancestors to find the first
matching binding": unlike `wireClickInterceptor`'s `event.target
.closest("[data-ark-on-click]")` (any one attribute, no value to
match), a `keydown`'s `event.target` may sit inside several nested
elements that each carry a *different* `on_key=` binding (an inner
input's `Escape` handler nested inside an outer dialog's own
`Escape` handler, say) -- the nearest element whose compiled key
*matches the key that was actually pressed* is the one that should
fire, not simply the nearest element carrying `data-ark-on-key` at
all. So this walks `event.target` and its ancestors by hand
(`parentNode`, not `.closest()`, which only takes a selector -- not a
dynamic attribute *value* to compare against `event.key`), stopping at
the first element whose own `data-ark-on-key` equals the pressed key.
"Only fires while the carrying element itself has focus (or the event
bubbles up to it from a focused descendant)" (`arklight.api.Key`'s
docstring) falls out of this for free: a `keydown` only ever reaches
this listener via the normal DOM bubble path from whichever element
actually has focus, so an unfocused element's `on_key=` binding is
never reachable from this event at all -- no explicit focus check
needed.

Guards, both unconditional (not modifier-gated -- these decide whether
*any* binding can match at all, before `data-ark-key-modifiers` is
even read):
- `event.isComposing` / the legacy `event.keyCode === 229` fallback
  (older WebKit/Android IME builds that predate `isComposing`): an IME
  composition keystroke's `event.key` is frequently `"Process"` or the
  in-progress candidate text, never a real key name, and firing an
  action mid-composition would be surprising regardless.
- `event.ctrlKey || event.altKey || event.metaKey`: Stage 2's
  `on_key=` only ever fires for the bare key (+ `Shift`, which changes
  no `event.key` value this registry cares about -- `Shift+Tab` still
  reports `event.key === "Tab"`, so it matches a plain `Tab` binding
  with no special-casing needed here). A `Ctrl`/`Alt`/`Meta` combo is
  always left alone, reserved for Stage 3's page-scoped `Hotkey(...)`
  (see `arklight.ir.schema.KNOWN_KEYS`'s module comment).

`prevent` is modifier-gated here -- unlike `wireClickInterceptor`,
where `event.preventDefault()` is unconditional on every matched
click. A keydown is frequently the browser's *own* handling of that
key too (`Tab` moving focus, the arrow keys scrolling or moving a
caret, `Enter` submitting a form) -- calling `preventDefault()`
unconditionally would silently break native behavior like Tab-based
focus movement on every element that merely happens to carry an
`on_key=`. Only `Key.on(...).with_modifiers("prevent")` suppresses it,
same opt-in `MODIFIER_REGISTRY` token `on_click=` already uses, just
honored conditionally instead of unconditionally.

`stop`/`once`/`debounce`/`throttle` are otherwise identical in
behavior to their `on_click=` counterparts in `dispatch.py` -- same
`WeakSet`/`WeakMap` bookkeeping, keyed by the *matched* element (not
`event.target`), so two different elements each bound to the same key
track their own independent `once`/timing state.
"""

from __future__ import annotations

from arklight.backend.js.runtime.action_args import RESOLVE_ACTION_ARGS_JS

KEY_INTERCEPTOR_JS = """  function wireKeyInterceptor(getStore) {
""" + RESOLVE_ACTION_ARGS_JS + """
    var debounceTimers = new WeakMap();
    var throttleLast = new WeakMap();
    var onceFired = new WeakSet();

    function parseKeyModifiers(el) {
      var mods = { prevent: false, stop: false, once: false, debounce: null, throttle: null };
      var raw = el.getAttribute("data-ark-key-modifiers");
      if (!raw) return mods;
      var tokens = raw.split(",");
      for (var i = 0; i < tokens.length; i++) {
        var token = tokens[i];
        if (token === "prevent") {
          mods.prevent = true;
        } else if (token === "stop") {
          mods.stop = true;
        } else if (token === "once") {
          mods.once = true;
        } else if (token.indexOf("debounce:") === 0) {
          mods.debounce = parseInt(token.slice("debounce:".length), 10);
        } else if (token.indexOf("throttle:") === 0) {
          mods.throttle = parseInt(token.slice("throttle:".length), 10);
        }
      }
      return mods;
    }

    function findMatchingAncestor(start, key) {
      var node = start;
      while (node && typeof node.getAttribute === "function") {
        if (node.getAttribute("data-ark-on-key") === key) return node;
        node = node.parentNode;
      }
      return null;
    }

    document.addEventListener("keydown", function (event) {
      if (event.isComposing || event.keyCode === 229) return;
      if (event.ctrlKey || event.altKey || event.metaKey) return;
      var el = findMatchingAncestor(event.target, event.key);
      if (!el) return;
      var store = getStore();
      if (!store) return;
      var mods = parseKeyModifiers(el);
      if (mods.prevent) event.preventDefault();
      if (mods.stop) event.stopPropagation();
      if (mods.once) {
        if (onceFired.has(el)) return;
        onceFired.add(el);
      }
      if (mods.throttle !== null) {
        var now = Date.now();
        var lastRun = throttleLast.get(el) || 0;
        if (now - lastRun < mods.throttle) return;
        throttleLast.set(el, now);
      }
      var runAction = function () {
        try {
          var actionName = el.getAttribute("data-ark-key-action");
          var stateKey = el.getAttribute("data-ark-key-action-state");
          var argsRaw = el.getAttribute("data-ark-key-action-args");
          var args = argsRaw ? JSON.parse(argsRaw) : {};
          var action = actions[actionName];
          if (!action) return;
          action(store, stateKey, resolveActionArgs(store, args));
        } catch (err) {
          arkReportError("Something went wrong updating this page -- an unsupported or unexpected case was hit.", err);
        }
      };
      if (mods.debounce !== null) {
        var existingTimer = debounceTimers.get(el);
        if (existingTimer) clearTimeout(existingTimer);
        debounceTimers.set(el, setTimeout(function () {
          debounceTimers.delete(el);
          runAction();
        }, mods.debounce));
      } else {
        runAction();
      }
    });
  }"""
