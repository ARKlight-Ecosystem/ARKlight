# ARKlight

**A Python-first compiler for building static websites where developers work
with a structured component API, while the output remains ordinary, dependency-free HTML.**

Write your site in Python. ARKlight compiles it to standard HTML with CSS and
vanilla JavaScript. The browser never executes Python — you get predictable,
inspectable, portable output that works anywhere static files are hosted.

No Python runtime in production. No framework bloat. Just Python ergonomics at
authorship time, and clean web artifacts at deployment time.

```python
from arklight import *

site = Site()

@site.page("/")
def home():
    return Page(
        Heading("ARKlight"),
        Text("Build websites with Python."),
        Button("Get Started"),
    )
```

```
arklight build site.py
```

produces `ARK/index.html` -- plain, dependency-free HTML.

## Status

ARKlight is in active alpha development. Status, by design, lives in
exactly one place per kind of record, not here as a second copy that
can drift out of sync:

- [`CHANGELOG.md`](./CHANGELOG.md) -- plain, version-by-version history
  of what shipped.
- [`PROGRESS.md`](./PROGRESS.md) -- the canonical **Snapshot** table
  (what's DONE / IN PROGRESS / PLANNED, including what's next) plus the
  narrative decision log behind each entry.
- [`docs/Foundational/ARCHITECTURE.md`](./docs/Foundational/ARCHITECTURE.md)
  -- the canonical milestone roadmap table.

Check `PROGRESS.md`'s Snapshot table first for "what's the current
state and what's next" -- it's updated at the end of every work
session, which the sections that used to live in this README were not.

## Install

```bash
pip install -e .
```

This installs the `arklight` package and the `arklight` CLI command
(defined in `pyproject.toml`).

```
curl -fsSL https://rae-ark.github.io/ARKlight/pubkey.gpg | sudo gpg --dearmor -o /usr/share/keyrings/arklight.gpg
sudo rm -f /etc/apt/sources.list.d/arklight.list
echo "deb [signed-by=/usr/share/keyrings/arklight.gpg] https://rae-ark.github.io/ARKlight/ stable main" | sudo tee /etc/apt/sources.list.d/arklight.list
sudo apt update
sudo apt install arklight-installer
```

This takes and installs the install for debian linux devices. Which be updated by sudo apt update

## CLI

```bash
arklight build <entry.py> [-o OUTPUT_DIR] [--open | --no-open]
```

Compiles `entry.py` to `<output>/index.html` (default `ARK/`) and
opens it in your browser. `arklight` also ships `pack`/`unpack` (the
`.ark` bundle format), `search` (component lookup and doc-tree
retrieval), `new` (project scaffolding), `pwa`, and `live-streaming`
(the alpha-only dev server).

Full flags, defaults, and worked examples for every subcommand:
[`docs/Foundational/CLI-REFERENCE.md`](./docs/Foundational/CLI-REFERENCE.md).

## Compiler pipeline

ARKlight compiles a site in clearly separated stages, each in its own
part of the package -- Python Source → Python AST → ARK AST →
Normalization → Validation → Website IR → Backend Interface → HTML/CSS/JS
Backends → `index.html`/`styles.css`/`arklight.js`. The full diagram,
annotated with the exact file each stage lives in, is the single
canonical copy in
[`docs/Foundational/ARCHITECTURE.md`](./docs/Foundational/ARCHITECTURE.md#compiler-pipeline)
-- kept there rather than duplicated here, alongside the `Backend`
extension-point details (`postprocess(...)`, custom `backends=[...]`
lists).

## Authoring guide

Routing, page `<head>` metadata, site-wide layout width/background,
styling (`class_name`/`style`/`site.style(...)`), the no-`@media`
responsive layout classes, client-side behaviors, the full component
vocabulary, the ARK Bundle (`.ark`) format, and
`arklight.config.py` project settings are documented in
[`docs/Foundational/AUTHORING-GUIDE.md`](./docs/Foundational/AUTHORING-GUIDE.md)
-- kept out of this README so this stays an entry point rather than a
second copy that can drift out of sync with itself.

## Repository layout

```
arklight-framework/
  arklight/
    api.py            Public component functions + Site class
    config.py          `arklight.config.py` project-config loader
                        (optional, per-project settings file -- see
                        docs/Foundational/AUTHORING-GUIDE.md#configuration-arklightconfigpy)
    ast/               ARK AST node type (ARKNode)
    parser/            Python Source -> Python AST -> (loaded) ARK AST
    ir/                Normalization, Validation, Website IR
    backend/
      base.py          Backend interface
      html/            HTML backend (the only backend in v0.001)
      js/
        behaviors/     v0.0035 behavior fragments (toggle, scroll-to,
                        copy, dismiss) -- one file per
                        BEHAVIOR_REGISTRY entry
        actions/       v0.0035 action fragments (set, increment,
                        toggle_bool) -- one file per ACTION_REGISTRY
                        entry
    compiler/          Pipeline orchestration
    cli/               `arklight` command-line entry point
      templates/       `simple`/`production` scaffolds for
                        `arklight new` (v0.004a; see docs/Foundational/DESIGN-NOTES.md)
    packer/            `arklight pack` -- ARK Bundle (.ark) packaging,
                        reads already-built output only, never touches
                        the compiler pipeline
  examples/
    hello_site/        Example site matching this README
  tests/               Unit + end-to-end tests for every pipeline stage
  docs/                Additional design notes
  PROGRESS.md          What's done, what's next
  CHANGELOG.md         Version history
```

## Running tests

```bash
pip install pytest
pytest
```

## Non-goals

Browser-side Python, a virtual DOM, runtime Python execution in the
browser, feature creep beyond the milestone roadmap below -- the full
list lives in
[`docs/Foundational/ARCHITECTURE.md`](./docs/Foundational/ARCHITECTURE.md#non-goals-v0001-and-for-the-foreseeable-future),
the single canonical copy.

## Roadmap

Full milestone table, current status, and the renumbering/amendment
history behind it live in
[`docs/Foundational/ARCHITECTURE.md`](./docs/Foundational/ARCHITECTURE.md)
-- kept as the single canonical copy rather than duplicated here, in
`PROGRESS.md`, or in `CHANGELOG.md`.
