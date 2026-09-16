# CLI Reference

Full reference for every `arklight` subcommand: flags, defaults, and
worked examples. This is the canonical CLI reference -- linked from
the root [`README.md`](../../README.md#cli), which keeps only a short
teaser and points here for the rest.

`build`, `pack`, `unpack`, `search`, `new`, `pwa`, `live-streaming`,
`--version`, and `--upgrade-alpha` below are implemented and shipped.
`arklight deploy` is **not** one of them -- it's a design-only,
not-yet-implemented subcommand; see
[`DEPLOYMENT-CLI.md`](DEPLOYMENT-CLI.md) for its spec and status.

```bash
arklight build <entry.py> [-o OUTPUT_DIR] [--open | --no-open] [--verbose] [--debug]
```

- `entry.py` -- your site file (must define `site = Site()` and at
  least one `@site.page("/route")`-decorated function).
- `-o, --output` -- output directory, default `ARK/`.
- If a top-level `assets/` folder sits next to `entry.py`, it is
  copied (recursively) into `<output>/assets` automatically.
- `--open` (default) -- opens `index.html` in your default browser
  after building. `--no-open` disables this.
- `--verbose` -- prints a `[ARKlight] ...` line as each pipeline stage
  starts (discovering the site, normalizing, validating, building the
  IR, each backend's render/postprocess, writing files, copying
  assets), e.g.:

  ```
  [ARKlight] Discovering site and compiling AST trees...
  [ARKlight] Normalizing AST...
  [ARKlight] Running validation...
  [ARKlight] Building website IR...
  [ARKlight] Rendering backend 'html'...
  ...
  [ARKlight] Build complete -> ARK/index.html
  ```

  Useful for seeing exactly which stage a build reached before it
  failed or hung.
- `--debug` -- implies `--verbose`, and on failure prints the full
  chained Python traceback instead of the short one-line error
  message, so you can trace a compiler error back to the exact file
  and line that raised it.

Both flags are off by default -- a plain `arklight build` is
unchanged.

Try the bundled example -- this builds the site AND opens it in your
browser:

```bash
arklight build examples/hello_site/site.py -o ARK
```

```bash
arklight pack <build-dir> [-o OUTPUT.ark] [--plain] [--passphrase PASSPHRASE]
```

- `build-dir` -- an existing `arklight build` output directory (e.g.
  `ARK`).
- `-o, --output` -- output bundle path, default `site.ark`.
- Packs the build directory into a single `.ark` file: an HTML/archive
  polyglot (see "ARK Bundle" below), carrying over every file in
  `build-dir` including `assets/`.
- **Sealed by default** -- the archive half is encrypted, opaque to
  generic archive tools. `--passphrase PASSPHRASE` derives the key from
  a passphrase instead of an embedded one, for real confidentiality
  (the same passphrase is then required to unpack). `--plain` skips
  sealing entirely and produces a plain, freely-openable ZIP tail
  (the original v1 behavior).

```bash
arklight unpack <bundle.ark> [-o OUTPUT_DIR] [--passphrase PASSPHRASE]
```

- `bundle.ark` -- a `.ark` file produced by `arklight pack`.
- `-o, --output` -- output directory, default `ARK`.
- Extracts the archive half back into a normal build directory.
  Auto-detects sealed vs. plain bundles; `--passphrase` is only needed
  if the bundle was sealed with one.

```bash
arklight build examples/hello_site/site.py -o ARK --no-open
arklight pack ARK -o hello_site.ark
arklight unpack hello_site.ark -o restored
```

```bash
arklight search <name>
```

- `name` -- a built-in component name, e.g. `Picture`.
- Prints that component's schema: required props, whether it allows
  children, and whether it's a `Bind(...)`-able target (i.e.
  `text_only_children`). Case-insensitive exact match wins; if nothing
  matches, prints up to 5 typo-tolerant "did you mean" suggestions
  (or says plainly that nothing was close enough).

```bash
arklight search Picture
arklight search pictur   # -> "Did you mean: Picture, PictureSource?"
```

- `--limit N` -- max number of "did you mean" suggestions on a miss
  (default: 5).
- `--near NAME` -- bias suggestion ranking toward components used
  structurally close to `NAME` in this project's own usage.
- `--accept` -- on an exact match, record it in the usage store so
  future searches rank it higher.
- `--serve` -- start a long-lived line-delimited JSON stdio server
  instead of a single lookup (for an editor/IDE extension to launch as
  a subprocess, the same way an LSP client launches a language
  server). Mutually exclusive with `name`; runs until stdin closes.

```bash
arklight search Picture --near Heading --accept
arklight search --serve
```

```bash
arklight search --retrieve-doc [index | --<folder> [--file NAME]]
```

- `--retrieve-doc` -- switches `search` from component lookup into
  **doc-tree retrieval**: prints exact, unmodified file contents from
  `docs/`, nothing invented or summarized. Mutually exclusive with a
  component `name` lookup (the literal `index` is accepted in its
  place, meaning the same as the bare form) and with `--serve`. Only
  works from an ARKlight source checkout -- `docs/` isn't shipped in
  the installed package.
- No folder flag -- prints the root `docs/README.md`, plus a footer
  listing the folder flags below.
- A folder flag (`--foundational`, `--backends`, `--proposals`,
  `--implementation`, `--js-backend`, `--far-future`,
  `--version-history`, one per `docs/README.md`'s own Folder Guide) --
  prints that folder's own `README.md` index, plus a footer listing
  the files available inside it.
- `--file NAME`, scoped to a preceding folder flag -- appends that
  file's full contents after the folder index. Matched
  case-insensitively by filename stem, with spaces/hyphens/underscores
  normalized (`--file architecture`, `--file Architecture`, and
  `--file ARCHITECTURE` all resolve to `ARCHITECTURE.md`); an
  unmatched name gets a typo-tolerant "did you mean" list, the same
  posture as component lookup's own suggestions. `--file` without a
  preceding folder flag is a hard error naming the folder the file
  actually lives in, if one matches.
- `--limit`/`--near`/`--accept` are component-lookup-only and are
  ignored (with a notice) alongside `--retrieve-doc`.

```bash
arklight search --retrieve-doc
arklight search --retrieve-doc --foundational
arklight search --retrieve-doc --foundational --file architecture
```

```bash
arklight new <name> [--template simple|production] [--dir PATH] [--explain-architecture]
```

- `name` -- name of the new project (also the directory created for
  it). Optional only when used with `--explain-architecture` alone.
- `--template` -- `simple` (default; a single `site.py`) or
  `production` (a `site.py` + `components/` + `pages/` + `content/` +
  `assets/` layout for sites that outgrow one file).
- `--dir` -- directory to create the project in (default: current
  directory).
- `--explain-architecture` -- print guidance on structuring an
  ARKlight project as service-oriented, separated-by-concern modules.
  Run alone (no `name`) to just read the guide, or alongside a
  `--template production` scaffold to print it right after.

```bash
arklight new my-site
arklight new my-blog --template production --explain-architecture
arklight new --explain-architecture
```

```bash
arklight pwa <build-dir> --name "My Site" [--short-name NAME] [--start-url URL]
    [--theme-color COLOR] [--background-color COLOR]
    [--display standalone|fullscreen|minimal-ui|browser]
    [--icon SRC:SIZES[:TYPE]]... [--install-button]
```

- `build-dir` -- an existing `arklight build` output directory.
- Turns that directory into an installable PWA: writes a
  `manifest.json` and a service worker, and injects the manifest
  link/SW registration into every already-built page.
- `--icon` is repeatable, e.g.
  `--icon assets/icon-192.png:192x192 --icon assets/icon-512.png:512x512`.
- `--install-button` is EXPERIMENTAL (see
  [`docs/Foundational/EXPERIMENTAL-APIS.md`](./docs/Foundational/EXPERIMENTAL-APIS.md)):
  injects a native install-prompt button on every page.
- Idempotent -- safe to re-run after every `arklight build` to keep
  the manifest/service worker/precache list in sync.

```bash
arklight build examples/hello_site/site.py -o ARK --no-open
arklight pwa ARK --name "Hello Site" --icon assets/icon-192.png:192x192
```

```bash
arklight live-streaming --subscribe <entry.py> [-o OUTPUT_DIR] [--host HOST] [--port PORT]
    [--channel [PORT]] [--route ROUTE]
arklight live-streaming --status [entry.py] [--status-pin]
arklight live-streaming --unsubscribe [entry.py]
```

Alpha-only dev tool (see `arklight.CHANNEL`): watches the entry file's
directory and rebuilds automatically, pushing a browser reload over
Server-Sent Events after each rebuild. **Development only -- do not
run in production/CI.**

- `--subscribe ENTRY` -- start a session for `ENTRY` (e.g. `site.py`).
  Blocks the terminal, streaming rebuild logs, until `Ctrl-C` or
  `--unsubscribe`.
- `-o, --output` -- output directory for `--subscribe` (default:
  `ARK`).
- `--host` / `--port` -- bind address for the dev server (defaults:
  `127.0.0.1` / `8347`, or `arklight.config.py`'s
  `live_streaming.host`/`live_streaming.port`).
- `--channel [PORT]` -- also serve the selected page's live
  `State(...)` over SSE, on a second port (a specific `PORT`, e.g.
  `--channel 2172`, or an OS-assigned free port with bare `--channel`).
- `--route ROUTE` -- with `--channel`, which page's `State(...)` to
  serve (default: the site's first page).
- `--status [ENTRY]` -- show whether a session is running.
  `--status-pin` prints verbose session details. `ENTRY` may be
  omitted if exactly one session is running.
- `--unsubscribe [ENTRY]` -- stop a running session.

```bash
arklight live-streaming --subscribe examples/hello_site/site.py
arklight live-streaming --subscribe examples/hello_site/site.py --channel
arklight live-streaming --status
arklight live-streaming --unsubscribe
```

```bash
arklight --version
arklight --upgrade-alpha
```

- `--version` -- print the installed ARKlight version and exit.
- `--upgrade-alpha` -- switch a git-checkout/editable install over to
  the `alpha` branch (fetch, switch/create the local branch, pull, and
  `pip install -e .` again in place) so the CLI reflects it
  immediately. Only works for a git-checkout/editable install. A
  standalone action, like `--version` -- it doesn't require (or use) a
  subcommand.

`arklight --help` (or a bare `arklight` with no subcommand) prints the
full list of subcommands with a short description of each.
