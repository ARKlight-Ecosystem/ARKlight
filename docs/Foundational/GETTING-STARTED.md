# Getting Started

_Current as of **v0.063** (latest shipped milestone) -- see
[`PROGRESS.md`](../../PROGRESS.md)'s Snapshot table if a referenced
detail might have moved since this was last updated._

Everything a newcomer needs once they've read the root
[`README.md`](../../README.md)'s pitch: installing `arklight`, a
runnable example, the annotated repository layout, and running the
test suite. Kept here rather than in the README so the README stays a
landing page -- a short pitch and a pointer, not a restated copy that
drifts out of sync with the real component API -- per
[`docs/README.md`](../README.md)'s "Adding a new doc" rule.

## Install

```bash
pip install -e .
```

This installs the `arklight` package and the `arklight` CLI command
(defined in `pyproject.toml`).

### Debian/Ubuntu package

```bash
curl -fsSL https://rae-ark.github.io/ARKlight/pubkey.gpg | sudo gpg --dearmor -o /usr/share/keyrings/arklight.gpg
sudo rm -f /etc/apt/sources.list.d/arklight.list
echo "deb [signed-by=/usr/share/keyrings/arklight.gpg] https://rae-ark.github.io/ARKlight/ stable main" | sudo tee /etc/apt/sources.list.d/arklight.list
sudo apt update
sudo apt install arklight-installer
```

This installs `arklight` on Debian-based Linux systems and registers
the APT source, so future updates are a plain `sudo apt update`.

Already on a git checkout or editable (`pip install -e .`) install?
`arklight --upgrade-alpha` switches it over in place -- see
[`CLI-REFERENCE.md`](CLI-REFERENCE.md) for what that does and when to
reach for it instead.

## Example

```python
# include <stdlib.ARKlight>

site = Site()

@site.page("/")
def home():
    return Page(
        Heading("ARKlight"),
        Text("Build websites with Python."),
        Button("Get Started"),
    )
```

```bash
arklight build site.py
```

produces `ARK/index.html` -- plain, dependency-free HTML. A fuller
version of this same site, with a shared nav bar and a real behavior
wired up, lives in
[`examples/hello_site/site.py`](../../examples/hello_site/site.py).

## Repository layout

```
arklight-framework/
  arklight/
    api.py            Public component functions + Site class
    config.py          `arklight.config.py` project-config loader
                        (optional, per-project settings file -- see
                        docs/Foundational/AUTHORING-GUIDE.md#configuration-arklightconfigpy)
    capabilities.py    ACC (ARKlight Component Collections) capability-
                        discovery hook -- scans the `arklight.capabilities`
                        entry-point group; zero effect on a build with no
                        ACC packages installed -- see
                        docs/Foundational/ACC-CAPABILITIES.md
    experimental.py    Registry + CLI-warning contract for opt-in,
                        outside-the-intrinsic-model features -- see
                        docs/Foundational/EXPERIMENTAL-APIS.md
    pwa.py             `arklight pwa` -- manifest/service-worker
                        generation for an existing build directory
    ast/               ARK AST node type (ARKNode)
    parser/            Python Source -> Python AST -> (loaded) ARK AST
    ir/                Normalization, Validation, Website IR
                        (`schema.py` holds the closed action/derivation/
                        component registries every backend reads from)
    backend/
      base.py          Backend interface
      html/            HTML backend
      css/              Default stylesheet + `Site.style(...)`/
                        `responsive_style=`/`@media` compilation
      js/               Stateful JS runtime -- `behaviors/`/`actions/`/
                        `derivations/` (one file per registry entry) and
                        `runtime/` (the shared vdom/dispatch/state core)
      android/          `arklight android` packaging backend -- see
                        docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md
                        (alpha-only so far, not yet on `main`)
      desktop/          `arklight desktop` packaging backend, Linux
                        only so far -- see
                        docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md
                        (alpha-only so far, not yet on `main`)
    compiler/          Pipeline orchestration
    cli/               `arklight` command-line entry point (incl.
                        `deploy.py`, the `arklight deploy` -> Wrangler hand-off)
      templates/       `simple`/`production` scaffolds for
                        `arklight new` (v0.004a; see docs/Foundational/DESIGN-NOTES.md)
    packer/            `arklight pack`/`unpack` -- ARK Bundle (.ark)
                        packaging and sealing, reads/writes
                        already-built output only, never touches the
                        compiler pipeline
    search/            `arklight search` -- built-in/user-component
                        schema lookup, typo-tolerant suggestions, and
                        doc-tree retrieval (`--retrieve-doc`)
  examples/
    hello_site/        Fuller version of this doc's "Example" section
  tests/               Unit + end-to-end tests for every pipeline stage
  docs/                Documentation tree -- see docs/README.md
  PROGRESS.md          What's done, what's next
  CHANGELOG.md         Version history
```

## Running tests

```bash
pip install pytest
pytest
```

`pyproject.toml`'s `[tool.pytest.ini_options]` points `pytest` at
`tests/` already, so no extra flags are needed from a repo checkout.
