"""
Script Extension -- successor to the now fully-deprecated
`Site.raw_postprocess(fn)` (see `arklight/experimental.py`'s
`raw-postprocess` entry: calling it no longer registers or runs
anything, it only logs a pointer here) for the one job most
`raw_postprocess` uses were actually for: injecting extra hand-written
JS alongside the `arklight.js` runtime every page already loads (see
`arklight/backend/js/render.py`'s `SCRIPT_PATH`).

Where `raw_postprocess` hands you the *entire* output-file dict --
free-form, unchecked, one function in, one dict out -- `ScriptExtension`
narrows the surface on purpose, and does it differently in kind, not
just in degree:

  * You extend a class. Plain Python inheritance -- the "oops way", as
    opposed to ARKlight's normal declarative/functional call style
    (`Site(...)`, `site.page(...)`, `site.raw_postprocess(fn)`). The
    difference is deliberately jarring: a `ScriptExtension` subclass
    should read, at a glance, as something categorically different
    from a normal ARKlight component or page.
  * `script` is restricted to the <script> portion of Svelte's
    single-file-component syntax -- no <template>, no <style>.
    `ScriptExtension.lower()` parses (lowers) only that block down to
    plain JS text; markup and styling stay completely outside this
    hatch's reach, unlike `raw_postprocess`, which can rewrite any
    file at all.
  * The lowered text is appended to `arklight.js` specifically, not
    spliced into arbitrary output files.
  * Pure Python stdlib (`re`, `inspect`) -- no parser dependency.

None of that makes the *content* any safer than `raw_postprocess`'s --
it's still hand-written JS ARKlight cannot validate the way it
validates its own generated runtime (no `eval`, no `new Function`, see
`arklight/backend/js/render.py`'s module docstring) -- so it is still
gated as its own experimental feature (`"script-extension"`, see
`arklight/experimental.py`), flagged exactly like every other entry in
that registry: not blocked, always warned.

What ARKlight *can* do cheaply is refuse JS that doesn't even parse.
Whenever Node is on PATH, the lowered JS is parsed by Node's V8 as a
classic script (see `check_js_syntax` -- the same check `node --check`
does, minus its CommonJS/ESM grammar, which is the wrong one for a
browser `<script>`) twice: once at `register()`
time, on the fragment alone, so the error names the extension and its
own line numbers; and once at compile time, on the fully combined
`arklight.js`, so a fragment that is fine alone but breaks the file
once appended (e.g. a top-level redeclaration) still fails the build
instead of shipping a dead runtime. Syntax only -- it proves the JS
parses, nothing about what it does. No Node on PATH never blocks the
build: it prints one warning that the check was skipped. Set
`check_syntax = False` on a subclass to opt out.

Usage is expected to carry the literal marker comment
`#include <expapilib.ARKlight>` (see `REQUIRED_MARKER`) somewhere in
the subclass's own source file. Its absence never blocks the build --
`register()` still runs the extension -- it just prints one extra,
louder warning on top of the normal experimental banner. The marker's
only job is the same one `#include` lines do in C: a reader scanning a
diff can tell, at a glance and without running anything, "this file
opts into the experimental script API."
"""

from __future__ import annotations

import inspect
import re
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path

from arklight import experimental

# Marker a ScriptExtension subclass's *source file* is expected to
# contain. Python has no preprocessor and never enforces this at
# import time -- ARKlight only checks for the literal text, via
# `inspect.getsource`, at registration time, and only to decide
# whether to print the extra "missing marker" warning below.
REQUIRED_MARKER = "#include <expapilib.ARKlight>"

# Only the <script>...</script> body of a Svelte single-file component
# is accepted; bare JS with no wrapper at all is accepted too (it's
# still "just the script part"). <template>/<style> are refused
# outright -- a ScriptExtension isn't a component and this escape
# hatch has no business touching layout or styling.
_SCRIPT_BLOCK_RE = re.compile(r"<script[^>]*>(?P<body>.*?)</script>", re.DOTALL)
_FORBIDDEN_BLOCK_RE = re.compile(r"<template[^>]*>|<style[^>]*>", re.IGNORECASE)

# Executable looked up on PATH for the syntax gate, and a ceiling on how
# long it may run -- `node --check` on even a large arklight.js is well
# under a second, so a hang means something is wrong with the install,
# and that is treated like "Node unavailable" rather than a build stall.
NODE_EXECUTABLE = "node"
_NODE_CHECK_TIMEOUT_SECONDS = 15

# Why this is not literally `node --check <file>`. Node's own
# implementation (lib/internal/main/check_syntax.js) does not parse a
# `.js` file as a classic script. It picks a goal from the extension, the
# nearest package.json "type", and a module-syntax sniff
# (`containsModuleSyntax`), then for CommonJS calls
# `wrapSafe` -> `compileFunctionForCJSLoader`, i.e. it compiles the file
# as a *function body*. arklight.js is served as a plain classic
# `<script src="arklight.js" defer>`, so that is the wrong grammar in both
# directions: `export`/`import`/top-level `await`/top-level `return`/
# `new.target` all pass `node --check` and are fatal in the browser,
# while a package.json "type":"module" near the file makes valid sloppy
# classic code (`with`, `var await`) fail. `vm.Script` is the same V8
# parser with the classic-script goal, compiles without running
# anything, and does not consult package.json at all. See
# docs/Foundational/DESIGN-NOTES.md, "Design record: ScriptExtension syntax check".
_PARSE_AS_CLASSIC_SCRIPT_JS = (
    "const vm = require('vm'), fs = require('fs');"
    "new vm.Script(fs.readFileSync(process.argv[1], 'utf8'),"
    " { filename: process.argv[1] });"
)


class ScriptExtensionError(ValueError):
    """Raised when a ScriptExtension's `script` can't be lowered --
    e.g. it smuggles in a <template>/<style> block, or is empty -- or
    when the lowered JS fails the classic-script syntax check."""


def check_js_syntax(js: str, *, label: str) -> bool:
    """
    Parse `js` with Node's V8 as a *classic script* -- the grammar a
    browser applies to `<script src="arklight.js" defer>`. Parse only:
    nothing is executed.

    Returns `True` when it parsed cleanly, `False` when the check could
    not be performed at all (no `node` on PATH, the process couldn't
    start, it timed out, or it failed for a reason that isn't a syntax
    error) -- the caller decides how loudly to say so. Raises
    `ScriptExtensionError` only for a genuine `SyntaxError`, with Node's
    diagnostic (offending line, caret, message) and the temp-file path
    replaced by `label` so the message names the extension, not a
    directory that is deleted a moment later.

    Deliberately not `node --check`: that parses `.js` as CommonJS/ESM
    (see `_PARSE_AS_CLASSIC_SCRIPT_JS`) and so accepts `export`,
    `import`, top-level `await` and `return`, all of which break in a
    browser.
    """
    node = shutil.which(NODE_EXECUTABLE)
    if node is None:
        return False
    with tempfile.TemporaryDirectory(prefix="arklight-node-check-") as tmp:
        path = Path(tmp) / "script.js"
        path.write_text(js, encoding="utf-8")
        try:
            proc = subprocess.run(
                [node, "-e", _PARSE_AS_CLASSIC_SCRIPT_JS, "--", str(path)],
                capture_output=True,
                text=True,
                timeout=_NODE_CHECK_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
    if proc.returncode == 0:
        return True
    diagnostic = proc.stderr.replace(str(path), label)
    if "SyntaxError" not in diagnostic:
        return False
    # Keep the file:line, offending source line, caret and message; drop
    # Node's own internals (`at wrapSafe (node:internal/...)`) and its
    # version footer -- noise to someone fixing a typo in their script.
    diagnostic = "\n".join(
        line
        for line in diagnostic.splitlines()
        if not line.lstrip().startswith("at ") and not line.startswith("Node.js v")
    ).strip()
    raise ScriptExtensionError(
        f"{label} failed Node's classic-script syntax check -- the JS is not valid "
        f"in a browser, so it was not appended to arklight.js:\n{diagnostic}"
    )


class ScriptExtension:
    """
    Subclass this and set `script` (or override `render_script()` for
    content computed at build time) to add hand-written JS to
    `arklight.js`. See module docstring for the full contract.

    Example::

        #include <expapilib.ARKlight>
        class Analytics(ScriptExtension):
            script = '''
            <script>
              document.addEventListener("click", (e) => {
                if (e.target.matches("[data-track]")) {
                  navigator.sendBeacon("/t", e.target.dataset.track);
                }
              });
            </script>
            '''
    """

    script: str = ""

    # Parse the lowered JS with Node as a classic script (see `check_js_syntax`).
    # On by default; set `check_syntax = False` on a subclass to skip it.
    check_syntax: bool = True

    def render_script(self) -> str:
        """Override for script content computed at build time instead
        of a fixed class attribute. Default returns `self.script`."""
        return self.script

    def lower(self) -> str:
        """
        Parse `render_script()`'s Svelte-script-only source down to
        the plain JS text appended to `arklight.js`. Accepts a full
        `<script>...</script>` wrapper or bare JS with no wrapper;
        raises `ScriptExtensionError` for a `<template>`/`<style>`
        block anywhere, or for content that lowers to nothing.
        """
        raw = self.render_script()
        if _FORBIDDEN_BLOCK_RE.search(raw):
            raise ScriptExtensionError(
                f"{type(self).__name__}.script may only contain a Svelte "
                f"<script> block (or bare JS) -- <template> and <style> "
                f"blocks are not part of ScriptExtension's surface and are "
                f"never lowered."
            )
        match = _SCRIPT_BLOCK_RE.search(raw)
        body = (match.group("body") if match else raw).strip("\n")
        if not body.strip():
            raise ScriptExtensionError(
                f"{type(self).__name__}.script lowered to nothing -- add "
                f"JS inside <script>...</script> (or as bare JS)."
            )
        return body


def _has_required_marker(cls: type) -> bool:
    """Best-effort source scan for `REQUIRED_MARKER` in `cls`'s
    *source file* -- file-level, matching the convention a C
    `#include` follows (a directive about the file, not about one
    declaration inside it). Reads the file directly via
    `inspect.getsourcefile` rather than `inspect.getmodule` +
    `getsource`, since the latter depends on the module being
    registered in `sys.modules` under its `__module__` name --
    true for normally-imported code, not guaranteed for a class
    loaded via `importlib.util.spec_from_file_location` without also
    being added to `sys.modules`. Returns `False` (never raises) when
    the source file can't be found or read at all -- e.g. a class
    defined interactively -- so a missing marker only ever adds a
    warning, never blocks registration."""
    try:
        source_file = inspect.getsourcefile(cls)
        if source_file is None:
            return False
        with open(source_file, encoding="utf-8") as f:
            file_source = f.read()
    except (OSError, TypeError):
        return False
    return REQUIRED_MARKER in file_source


def register(site, extension: "ScriptExtension | type[ScriptExtension]") -> ScriptExtension:
    """
    Register `extension` (an instance, or a bare subclass --
    instantiated with no args) on `site`. Wires through the exact same
    `site.raw_postprocessors` list `Site.raw_postprocess(fn)` used to
    populate before it was deprecated (`arklight/api.py`) -- same
    pipeline hook, same build-order guarantees -- but appends only the
    lowered JS to `arklight.js` instead of handing back a whole
    rewritten output dict. This is the sole surviving successor
    `raw-postprocess`'s own `legacy_note` (`arklight/experimental.py`)
    points JS-injection callers toward.

    Never blocks on a missing `#include <expapilib.ARKlight>` marker --
    only `warnings.warn`s about it, on top of the normal experimental
    banner every use of this feature records via `experimental.emit`.

    DOES block on JS that fails the classic-script syntax check: raises
    `ScriptExtensionError` at registration (and again from the compile
    step if appending would break the combined `arklight.js`). A machine
    with no Node only gets a warning -- see `check_js_syntax`.
    """
    if isinstance(extension, type):
        if not issubclass(extension, ScriptExtension):
            raise TypeError(
                f"register(site, extension) needs a ScriptExtension "
                f"subclass or instance, got {extension!r}."
            )
        instance = extension()
    elif isinstance(extension, ScriptExtension):
        instance = extension
    else:
        raise TypeError(
            f"register(site, extension) needs a ScriptExtension "
            f"subclass or instance, got {extension!r}."
        )

    lowered = instance.lower()
    name = type(instance).__name__

    # Fragment check, at registration: fails fast with the extension's
    # own name and the line numbers of the JS the author actually wrote.
    if instance.check_syntax and not check_js_syntax(lowered, label=f"{name}.script"):
        warnings.warn(
            f"{name}: JS syntax was NOT checked -- `{NODE_EXECUTABLE}` was not "
            f"found on PATH (or could not run). The script will be appended "
            f"to arklight.js unchecked; install Node.js to have it validated "
            f"with Node's parser at build time.",
            stacklevel=2,
        )

    from arklight.backend.js.render import SCRIPT_PATH  # local import: avoid a hard import cycle

    def _append_script(output_files: dict[str, str]) -> dict[str, str]:
        existing = output_files.get(SCRIPT_PATH, "")
        separator = "\n" if existing and not existing.endswith("\n") else ""
        combined = (
            f"{existing}{separator}\n"
            f"/* ScriptExtension: {name} */\n"
            f"{lowered}\n"
        )
        # Combined check, at compile time: the fragment parsed alone, but
        # appended to the runtime it can still break the file (a top-level
        # `const` that collides with one already there is a SyntaxError).
        # An unavailable Node was already warned about at register().
        if instance.check_syntax:
            check_js_syntax(combined, label=f"{SCRIPT_PATH} (after appending {name})")
        output_files[SCRIPT_PATH] = combined
        return output_files

    site.raw_postprocessors.append(_append_script)
    site.experimental_usages.append(
        experimental.emit("script-extension", component=type(instance).__name__)
    )

    if not _has_required_marker(type(instance)):
        warnings.warn(
            f"{type(instance).__name__} does not contain the required "
            f"'{REQUIRED_MARKER}' marker in its source file. Not blocked -- "
            f"it still runs -- but add the marker so anyone scanning this "
            f"file's diff can tell at a glance that it opts into the "
            f"experimental script API.",
            stacklevel=2,
        )

    return instance
