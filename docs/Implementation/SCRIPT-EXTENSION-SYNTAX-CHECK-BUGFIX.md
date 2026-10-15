# Bug fix: `ScriptExtension` JS is never syntax-checked

**Component:** `arklight/backend/script_extension.py`
(`site.register_script_extension(...)`, experimental feature
`script-extension`)
**Class:** build-time validation gap -- a broken script ships silently
**Fix status:** implemented; tests in `tests/test_script_extension.py`

## 1. The bug

`ScriptExtension.lower()` strips the `<script>` wrapper and `register()`
appends the resulting text to `arklight.js`. Nothing parses it. A typo --
an unclosed brace, a stray `}` -- compiles cleanly and ships.

The failure is not local. `arklight.js` is the single runtime every page
loads (`<script src="arklight.js" defer>`), so one syntax error in an
extension makes the browser reject the *whole file*: nav highlighting,
actions, state, every behavior -- not just the extension -- stops
working, with the only symptom a console error in production. The
experimental banner said as much ("no guarantee it's even syntactically
valid"), but a documented hazard that a one-line check can catch is a
bug, not a feature.

Reproduction (before the fix):

```python
class Analytics(ScriptExtension):
    script = "<script>document.addEventListener('click', (e) => {</script>"

site.register_script_extension(Analytics)   # no error
build("site.py", "out/")                    # no error; out/arklight.js is dead
```

## 2. Why the obvious fix (`node --check`) is itself wrong

The first instinct -- shell out to `node --check` on the lowered JS --
passes the bug's own reproduction but is the wrong gate. The reason is in
how Node implements it. All references below are to `nodejs/node` at
`1c90519c` (shallow clone, `main`).

### 2.1 What `node --check` actually does

- `--check` / `-c` sets `syntax_check_only` (`src/node_options.cc`);
  `src/node.cc:387-388` then dispatches to
  `internal/main/check_syntax` instead of running the file.
- `lib/internal/main/check_syntax.js` does **not** parse the file as a
  classic script. `checkSyntax()` (line 59) first decides a *format*:
  - For a file, `defaultGetFormat()` (lines 64-67) looks at the extension
    and the **nearest `package.json` `"type"`**.
  - If that yields no format -- a `.js` file with no `"type"` -- it falls
    back to `containsModuleSyntax(source, filename)` (lines 75-80), a
    sniff for `import`/`export`/top-level `await`; if found, the file is
    parsed as an **ES module** (`new ModuleWrap(...)`, line 84).
  - Otherwise it calls `wrapSafe(...)` (line 88), which reaches
    `compileFunctionForCJSLoader` (`lib/internal/modules/cjs/loader.js`
    line 1900; C++ at `src/node_contextify.cc:1649`). That compiles the
    source as the **body of a function** -- the CommonJS module wrapper.

So `node --check file.js` parses as *CommonJS-function-body or ESM*,
chosen by environment. A browser loading `<script src=... defer>` (no
`type="module"`) parses as a **classic script**. Those are three
different grammars.

### 2.2 The mismatch, measured

Same Node (v22), same V8, run against the cases that differ. `OK` = parse
accepted. The last column is the grammar a browser actually applies.

| Source                         | `node --check` | `--check` + nearby `package.json` `"type":"module"` | classic script (browser) |
|--------------------------------|:--------------:|:---------------------------------------------------:|:------------------------:|
| valid classic JS               | OK  | OK  | OK  |
| unbalanced brace               | ERR | ERR | ERR |
| `export const a = 1;`          | **OK** | **OK** | ERR |
| `import x from 'y';`           | **OK** | **OK** | ERR |
| top-level `await fetch(...)`   | **OK** | **OK** | ERR |
| top-level `return;`            | **OK** | ERR | ERR |
| `new.target` at top level      | **OK** | ERR | ERR |
| `with (Math) { ... }`          | OK  | **ERR** | OK  |
| `var await = 1;`               | OK  | **ERR** | OK  |

Two distinct failure modes:

1. **False negatives (the dangerous one).** `export`, `import`,
   top-level `await`, top-level `return` and `new.target` all pass
   `node --check` and are all fatal in the browser. A developer pasting
   a snippet from a module or a Node script -- the most likely source of
   a hand-written extension -- gets a green build and a dead site, which
   is exactly the bug we set out to fix.
2. **False positives, environment-dependent.** Whether a valid sloppy
   classic script is rejected depends on a `package.json` near the
   checked file. `with` and `var await` are valid in a classic script
   and invalid in a module, so the gate can fail a correct extension
   based on directory layout the user never chose.

A gate that disagrees with the real consumer in both directions is
worse than no gate on the false-negative side, because it manufactures
confidence.

## 3. The fix

### 3.1 Parse with the right goal

Use the same V8 parser Node exposes, but request the classic-script
goal directly via `vm.Script`, which compiles without executing and
never consults `package.json`:

```js
const vm = require('vm'), fs = require('fs');
new vm.Script(fs.readFileSync(process.argv[1], 'utf8'),
              { filename: process.argv[1] });
```

invoked as `node -e <program> -- <tempfile>`. (`--eval` and `--check`
are mutually exclusive in Node -- `src/node_options.cc:315` -- which is a
second, minor reason the literal flag could not simply be combined with
anything else.) The table's last column is this check's behavior: it
agrees with the browser on every row.

### 3.2 Check at two points

`check_js_syntax(js, *, label)` is called:

1. **At `register()`**, on the lowered fragment alone. Fails fast, and
   the error names the extension and uses the line numbers of the JS the
   author actually wrote. Nothing is half-registered: a failure leaves
   `site.raw_postprocessors` and `site.experimental_usages` untouched.
2. **At compile time**, inside the registered postprocessor, on the
   fully combined `arklight.js`. This catches a fragment that parses
   fine alone but breaks the file once appended -- e.g. a top-level
   `const` that collides with one already in the runtime is a
   redeclaration `SyntaxError` only in the combined text. It surfaces
   through the existing `raw postprocess function #N raised an error`
   `CompileError` path in `arklight/compiler/pipeline.py`, before any
   file is written.

### 3.3 Never block on tooling, always block on real errors

`check_js_syntax` returns `True` (parsed), `False` (could not check) or
raises `ScriptExtensionError` (genuine `SyntaxError`).

- **No `node` on PATH, process fails to start, timeout (15 s), or a
  non-`SyntaxError` failure** -> returns `False`; `register()` emits one
  warning ("JS syntax was NOT checked") and the build continues. This
  mirrors the module's existing posture for the `#include` marker: a
  missing prerequisite is a louder warning, never a hard stop, so ARKlight
  does not gain a Node dependency.
- **A real `SyntaxError`** -> `ScriptExtensionError` with Node's
  diagnostic (file:line, source line, caret, message). The temp-file path
  is replaced with `<ExtensionName>.script`, and Node's internal stack
  frames (`at wrapSafe (node:internal/...)`) and version footer are
  stripped -- noise to someone fixing a typo.
- **Opt-out:** `check_syntax = False` on the subclass skips both checks.

Resulting message (broken extension):

```
CompileError: Error while running site.py: Analytics.script failed Node's
classic-script syntax check -- the JS is not valid in a browser, so it was
not appended to arklight.js:
Analytics.script:4
...
SyntaxError: Unexpected end of input
```

## 4. Scope and non-goals

- **Syntax only.** This proves the JS parses. It says nothing about what
  it does. The `script-extension` experimental banner still applies and
  still warns on every build; its wording is updated to say syntax is
  checked when Node is available and behavior is not.
- **Not a security boundary.** Parsing is not sandboxing; the CSP-related
  limits on `arklight.js` are unchanged.
- **No new hard dependency.** Node stays optional.
- **Known residual gap.** Parsing a fragment as a classic script cannot
  tell that it was *meant* to run later than `DOMContentLoaded`, or
  against a different global. Out of scope.

## 5. Files changed

| File | Change |
|------|--------|
| `arklight/backend/script_extension.py` | `check_js_syntax()`, `NODE_EXECUTABLE`, `check_syntax` opt-out; checks wired into `register()` and the postprocessor |
| `arklight/experimental.py` | `script-extension` banner/detail no longer claims the JS is wholly unchecked |
| `docs/Foundational/EXPERIMENTAL-APIS.md` | same, in prose |
| `tests/test_script_extension.py` | 15 new tests (below); two marker-warning tests scoped to their own warning so they pass with or without Node |
| `docs/Implementation/SCRIPT-EXTENSION-SYNTAX-CHECK-BUGFIX.md` | this file |

## 6. Tests

New, in `tests/test_script_extension.py` (Node-dependent ones are
`skipif` when `node` is absent):

- valid JS accepted; invalid JS rejected, error names the label, no
  temp-path or Node-internals leakage
- `register()` fails fast and leaves the site untouched
- compile step catches a fragment that breaks the *combined* file, and
  reports (not swallows) an already-broken runtime
- **grammar-goal regression, one case each:** `export`, `import`,
  top-level `await`, top-level `return`, `new.target` are rejected --
  every one passes plain `node --check`
- **inverse regression:** `with` and `var await` are accepted -- both
  rejected under a module goal
- the script is parsed and **never executed** (a `throw`/`process.exit`
  body passes)
- missing `node` -> warns, still registers, still builds
- `check_syntax = False` never invokes Node

## 7. Verification performed

- `tests/test_script_extension.py`: 29 passed.
- Full suite: all passing except tests that require `arklight` to be
  pip-installed (`test_scaffold`, `test_version` -- pre-existing and
  environmental in a sandbox without an editable install; confirmed
  failing identically on an unmodified checkout).
- End-to-end through `arklight.compiler.pipeline.build()`: a valid
  extension is appended to `out/arklight.js`; an unbalanced-brace
  extension fails the compile with the message above and writes no
  `arklight.js`.
- The behavior table in section 2.2 was produced by running each case
  through `node --check` (with and without a `"type":"module"`
  `package.json`) and through the `vm.Script` program on Node v22.
