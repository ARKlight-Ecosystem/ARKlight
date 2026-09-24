# CLI Reference

Full reference for every `arklight` subcommand: flags, defaults, and
worked examples. This is the canonical CLI reference -- linked from
the root [`README.md`](../../README.md)'s Documentation section, which
keeps no CLI content of its own and points here for all of it.

`build`, `pack`, `unpack`, `search`, `new`, `pwa`, `live-streaming`,
`--version`, and `--upgrade-alpha` below are implemented and shipped.
`android`, `desktop` and `deploy` (below) are implemented, but
alpha-only so far -- see the note in their own sections.

**One-time license gate.** The first time any `arklight <command>`
runs on a machine, it prints the ARKlight Additional Terms and asks
for a typed `agree` before continuing; acceptance is then recorded in
`~/.arklight/license-accepted` (override with `ARKLIGHT_HOME`) so it
only happens once. `ARKLIGHT_ACCEPT_LICENSE=1` skips the prompt for
CI/Docker/scripted use -- set it only after actually reading the
terms in `LICENSE`. If stdin isn't a TTY and the env var isn't set,
the command refuses to proceed rather than hanging on a prompt that
can never be answered.

```bash
arklight build <entry.py> [-o OUTPUT_DIR] [--open | --no-open] [--verbose] [--debug] [--narrate]
    [--max-width VALUE] [--bg VALUE] [--font-family VALUE] [--button-text VALUE] [--lang TAG]
    [--emit-arklight[=PATH]]
```

- `entry.py` -- your site file (must define `site = Site()` and at
  least one `@site.page("/route")`-decorated function).
- `-o, --output` -- output directory, default `ARK/`.
- If a top-level `assets/` folder sits next to `entry.py`, it is
  copied (recursively) into `<output>/assets` automatically.
- `--open` (default) -- opens `index.html` in your default browser
  after building. `--no-open` disables this.
- `--verbose` -- prints a `[ARKlight] ...` line as each pipeline stage
  starts (discovering the site, expanding user-defined `component(...)`
  calls, normalizing, validating, building the IR, each backend's
  render/postprocess, any `Site.raw_postprocess(...)` functions,
  writing files, copying assets), e.g.:

  ```
  [ARKlight] Discovering site and compiling AST trees...
  [ARKlight] Expanding user-defined components...
  [ARKlight] Normalizing AST...
  [ARKlight] Running validation...
  [ARKlight] Building website IR...
  [ARKlight] Rendering backend 'html'...
  [ARKlight] Postprocessing backend 'html'...
  [ARKlight] Writing 3 file(s) -> ARK/...
  [ARKlight] Copying assets...
  ```

  Useful for seeing exactly which stage a build reached before it
  failed or hung. (If a project doesn't use `component(...)` at all,
  that stage still runs -- it's a no-op expansion pass, not a
  conditional step -- so it still prints under `--verbose`.)
- `--debug` -- implies `--verbose`, and on failure prints the full
  chained Python traceback instead of the short one-line error
  message, so you can trace a compiler error back to the exact file
  and line that raised it.
- `--narrate` -- like `--verbose`, but the same pipeline progress is
  told by Rei, ARKlight's compiler narrator, as short natural-language
  sentences instead of `[ARKlight] ...` lines, e.g.:

  ```
  [Rei] Reading your site file and turning it into an AST tree.
  [Rei] Expanding any @component(...)-registered pieces you used.
  [Rei] Normalizing the tree into a consistent shape.
  [Rei] Checking everything against the known component schema.
  [Rei] Building the Website IR from the validated tree.
  [Rei] Rendering the html backend.
  ...
  [Rei] All done -- open ARK/index.html whenever you're ready.
  ```

  Mutually exclusive with `--verbose` and `--debug`: combining
  `--narrate` with either one fails the build immediately, naming the
  conflicting flag, rather than silently picking one. Rei is pure
  Python and deterministic -- the same build always produces
  byte-identical narration; no network access, no LLM.

  - **First-build introduction.** The first narrated build into an
    output directory that doesn't exist yet, or exists and is empty,
    starts with a two-line `[Rei]` greeting that also says *why*
    narration is on (the `--narrate` flag, or `arklight.config.py`).
    It is not repeated on later builds into the same directory, and
    comes back if you delete/clear the output directory.
  - **On failure**, the error prints as `[Rei] Compilation halted.`
    followed by the same error text the plain build prints -- without
    its `ARKlight build failed:` prefix and its `Re-run with --debug`
    hint, since `--debug` can't be combined with `--narrate` (drop
    `--narrate` and add `--debug` to get the full traceback). When
    the failure is an unknown component type, or a known component
    missing a required prop, one extra fixed line is appended --
    `Try: arklight search <Name>`, pointing at the existing `search`
    subcommand below. No other kind of failure gets that line.
  - Experimental-feature banners (see below) print exactly as under
    `--verbose`; Rei never rewords them.
  - **Pinning it per project.** Instead of passing the flag on every
    build, set `CONFIG = {"rei": {"default_mode": "narrate"}}` in the
    project's `arklight.config.py`. `default_mode` is one of
    `"plain"` (the default, and what a missing `rei` section means),
    `"verbose"` or `"narrate"`; any other value fails the build. It
    only decides what a build with *no* `--verbose`/`--debug`/
    `--narrate` flag does -- a flag on the command line always wins
    for that invocation.
- **Overdrive** (`arklight.config.py`, no flag). Before writing anything,
  `build` halts on internal links and assets it can't resolve. Two of
  those findings are *unverifiable* rather than provably wrong -- an
  `href` naming no registered page (`/api/login`), and a `src`/`url(...)`
  outside `assets/` that nothing generates (`/api/avatar`), either of
  which a server might legitimately supply. To let those through, add
  one line: `CONFIG = {"overdrive": True}`. Every reference it lets
  through is still listed on stderr on every build, and a missing or
  wrong-case file *inside* `assets/`, a dead `#fragment`, and a path that
  escapes the output folder stay fatal. The value must be exactly `True`
  or `False`; anything else fails the build. It applies to
  `arklight build`, `live-streaming`, and library `build()` calls alike
  (`build(..., overdrive=True/False)` overrides the file).
- `--max-width VALUE` -- overrides the page's max content width
  (`--ark-max-width`), e.g. `90rem`, `1400px`, `100%`. Takes
  precedence over `Site(max_width=...)` in the site file, without
  requiring an edit to it.
- `--bg VALUE` -- overrides the page background (`--ark-bg`), e.g.
  `#0f0f1a`. Takes precedence over `Site(bg=...)`.
- `--font-family VALUE` -- overrides the page font stack
  (`--ark-font-family`), e.g. `'Georgia, serif'`. Takes precedence
  over `Site(font_family=...)`. Default: ARKlight's stock system-font
  stack.
- `--button-text VALUE` -- overrides button text color
  (`--ark-button-text`), e.g. `#111827`. Takes precedence over
  `Site(button_text=...)`. Default `#ffffff` -- worth setting
  explicitly alongside a light `--ark-accent`, since button background
  follows accent.
- `--lang TAG` -- overrides the `<html lang="...">` tag, e.g. `es`,
  `ta`, `fr-CA`. Overrides `Site(lang=...)` without a site-file edit
  -- a page's own `Page(lang=...)`, if set, still wins for that page.
  Default: `en`.

  These five flags exist specifically so CI (or a one-off variant
  build) can override a design token without editing the site file's
  `Site(...)` call; leaving all of them off changes nothing.
- `--emit-arklight[=PATH]` -- also writes the compiled Website IR as a
  binary `.arklight` file (`arklight.ir.binary` -- magic bytes, format
  version, schema generation tag, deduped string table; see
  [`ARCHITECTURE.md`](ARCHITECTURE.md#binary-ir-arklight) for the full
  format). Bare flag writes `<output>/site.arklight`; pass a path to
  choose your own, e.g. `--emit-arklight=build/site.arklight`. A
  standalone, versioned snapshot of the IR that can be read back
  (`arklight.ir.binary.decode_arklight`) without re-running the
  compiler pipeline. Off by default -- a plain `arklight build` never
  writes one.

After a successful build (`--verbose` or not), the CLI always prints
a one-line summary and every file it wrote:

```
ARKlight v0.063 built 3 file(s) -> ARK/
  ARK/index.html
  ARK/styles.css
  ARK/arklight.js
```

Two more things print unconditionally after that, never gated behind
`--verbose`/`--debug`, if they apply:

- **Experimental-feature warnings** -- if the site uses any API from
  `arklight/experimental.py` (`Site.media_query(...)`,
  `responsive_style=...`, `Site.import_style(...)`,
  `Site.raw_postprocess(...)`, or `arklight pwa --install-button`),
  both an inline banner at the point of use and an end-of-build
  summary are printed. See
  [`EXPERIMENTAL-APIS.md`](EXPERIMENTAL-APIS.md)'s "CLI contract" for
  the exact format and why these aren't gated like ordinary stage
  narration.
- **Alpha-limitation warnings** -- any `[ARKlight ALPHA]`-marked
  warning raised during the build (a known, non-fatal alpha-branch
  limitation, not a build failure) is collected and printed as a
  `NOTE: this alpha build is under active maintenance...` block.

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

- `name` -- a built-in component name (e.g. `Picture`), a project's
  own registered `@component(...)` name, or a name from any other
  closed JS vocabulary: an `on_click=`/`on_reveal=` behavior (`toggle`,
  `reveal`), an `Action.*` name (`Action.increment` or bare
  `increment`), an event-modifier token (`debounce`), a `Derive.*`
  name (`Derive.sum` or bare `sum`), a `Predicate.*` name
  (`Predicate.truthy` or bare `truthy`), or a `PlatformAPI.*` name
  (`PlatformAPI.notify` or bare `notify`). The `Action.`/`Derive.`/
  `Predicate.`/`PlatformAPI.` prefix, if given, is matched
  case-insensitively and stripped -- both the dotted authoring form
  and the bare registry key resolve to the same entry.
- Checked in this order: built-in components (`SCHEMA`) -> a
  project's own registered components (`COMPONENT_REGISTRY`) ->
  `on_click`/`on_reveal` behaviors -> `Action.*` -> event modifiers ->
  `Derive.*` -> `Predicate.*` -> `PlatformAPI.*`. Built-ins win a
  component-name collision with a registered component; the
  JS-vocabulary registries don't in practice collide with component
  names at all (PascalCase vs. snake_case).
- For a component match, prints its schema: required/optional props,
  whether it allows children, and whether it's a `Bind(...)`-able
  target (i.e. `text_only_children`). For a JS-vocabulary match,
  prints its closed shape instead -- extra props for a behavior, args
  for an action, name-count/extra-args for a derivation or predicate,
  whether an event modifier takes a value, or (for a `PlatformAPI.*`
  match) its args, required permissions, and which backend(s), if any,
  currently implement the capability.
- Case-insensitive exact match wins outright, in any of the above. If
  nothing matches anywhere, prints up to 5 typo-tolerant "did you
  mean" suggestions (or says plainly that nothing was close enough) --
  drawn from the component vocabulary only; the ranking pipeline
  behind "did you mean" doesn't yet cover the JS-vocabulary registries
  (only their *exact*-match lookup is wired up so far), so a typo of a
  JS-vocabulary name doesn't yet get its own suggestion.

```bash
arklight search Picture
arklight search pictur   # -> "Did you mean: Picture, PictureSource?"
arklight search increment
arklight search Action.increment   # same result, dotted authoring form
arklight search Derive.sum
arklight search toggle             # on_click behavior, not Action.toggle_bool
arklight search notify             # PlatformAPI.notify, incl. permissions + implementing backends
```

- `--limit N` -- max number of "did you mean" suggestions on a miss
  (default: 5).
- `--near NAME` -- bias suggestion ranking toward components used
  structurally close to `NAME` in this project's own usage.
- `--accept` -- on an exact *component* match, record it in the usage
  store so future searches rank it higher. Has no effect on a
  JS-vocabulary match (behavior/action/modifier/derivation/predicate)
  -- the usage store the ranking pipeline reads back from only ever
  scores component names, so there's nothing for it to record there.
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
  `docs/`, nothing invented or summarized -- now rendered as styled
  Markdown (see `--color`) rather than raw bytes. Mutually exclusive
  with a component `name` lookup (the literal `index` is accepted in
  its place, meaning the same as the bare form) and with `--serve`.
  Only works from an ARKlight source checkout -- `docs/` isn't shipped
  in the installed package.
- No folder flag -- prints the root `docs/README.md`, plus a footer
  listing the folder flags below.
- A folder flag (`--foundational`, `--backends`, `--proposals`,
  `--implementation`, `--far-future`,
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
- `--section QUERY`, scoped to a preceding folder flag + `--file NAME`
  -- prints just one `##` section of that file instead of the whole
  thing. `QUERY` is a section number (the heading's own `## N. Title`
  numbering if the file uses one, else its 1-based position in the
  file), a heading-text fragment (matched the same way `--file`
  matches filenames, with a "did you mean" on a near miss), or both
  together (`--section '3 terminology'`).
- `--color {auto,always,never}` -- controls ANSI styling of the
  printed Markdown. `auto` (default) styles it when stdout is a
  terminal and `NO_COLOR` isn't set; `always` forces styling (e.g.
  piping to `less -R`); `never` prints the raw Markdown bytes
  untouched.
- `--limit`/`--near`/`--accept` are component-lookup-only and are
  ignored (with a notice) alongside `--retrieve-doc`.

```bash
arklight search --retrieve-doc
arklight search --retrieve-doc --foundational
arklight search --retrieve-doc --foundational --file architecture
arklight search --retrieve-doc --foundational --file architecture --section '3 terminology'
arklight search --retrieve-doc --foundational --file architecture --color always | less -R
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
  [`EXPERIMENTAL-APIS.md`](EXPERIMENTAL-APIS.md)):
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
arklight android scaffold <build-dir> -o OUTPUT_DIR [--debug-keystore PATH] [--release]
arklight desktop scaffold <build-dir> -o OUTPUT_DIR [--target linux]
arklight desktop build <project-dir> [--run]
```

**Alpha-only so far -- not yet on `main`.** `android` and `desktop`
are real, implemented subcommands, but
they're part of the in-progress Android/Desktop backend work (see
`PROGRESS.md`'s Snapshot table -- `v0.080`/`v0.100`, both IN
PROGRESS) and haven't landed on the stable `main` branch yet. Full
design and staging detail:
[`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`](../Backends/ANDROID-BACKEND-IMPLEMENTATION.md)
and
[`docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`](../Backends/DESKTOP-BACKEND-IMPLEMENTATION.md).

- `arklight android scaffold <build-dir> -o OUTPUT_DIR` -- generates
  an Android Studio / Gradle project (Application mode) from an
  `arklight build` output directory. Templating only -- no JDK/Android
  SDK required to run this command. Includes a GitHub Actions workflow
  that builds a debug APK and smoke-tests it (install + launch on an
  emulator) in CI, no local toolchain needed.
  - `--debug-keystore PATH` -- pin a shared debug signing key (copied
    in as `app/debug.keystore`) so debug APKs built on different
    machines/CI runs share a signature and can be installed as updates
    over each other. Without it, every machine auto-generates its own.
  - `--release` -- also generate a signed release-build job. Off by
    default; it's a no-op until you set the
    `RELEASE_KEYSTORE_BASE64`/`RELEASE_KEYSTORE_PASSWORD`/
    `RELEASE_KEY_ALIAS`/`RELEASE_KEY_PASSWORD` repo secrets (see the
    generated project's own README).
  - `arklight android build`, `--install`, and local (on-this-machine)
    release builds are staged as later stages of the same ladder and
    are **not implemented yet**.
- `arklight desktop scaffold <build-dir> -o OUTPUT_DIR [--target linux]`
  -- generates a native GTK3 + WebKit2GTK host project. Templating +
  asset-embedding only -- no C toolchain required to run this command
  itself. `--target` only supports `linux` so far (the default);
  Windows/macOS aren't implemented. Includes a GitHub Actions workflow
  that builds the project and smoke-tests it under a headless Xvfb
  display, no local toolchain or display server needed.
- `arklight desktop build <project-dir> [--run]` -- builds an
  already-scaffolded project by shelling out to its own `make`. Needs
  a C compiler, `pkg-config`, and the GTK3/WebKit2GTK dev headers on
  this machine. `--run` launches the built binary once `make`
  succeeds.

```bash
arklight android scaffold ARK -o android-project --release
arklight desktop scaffold ARK -o desktop-project
arklight desktop build desktop-project --run
```

```bash
arklight deploy [cloudflare] [entry] [-o OUTPUT_DIR] [--name NAME] [--skip-build] [--dry-run]
```

**Alpha-only so far -- not yet on `main`.** Builds the site, then hands
the build directory to the hosting provider's own CLI. Cloudflare
Workers (static assets), deployed by [Wrangler](https://developers.cloudflare.com/workers/wrangler/),
is the only provider so far, and bare `arklight deploy` means
`arklight deploy cloudflare`. Spec and the reasoning behind the
boundary: [`DEPLOYMENT-CLI.md`](DEPLOYMENT-CLI.md).

- `provider` -- where to deploy. Only `cloudflare` exists. Name it
  *before* the site file: `arklight deploy cloudflare my_site.py`
  (`arklight deploy my_site.py` is refused rather than guessed at).
- `entry` -- the site file to build (default: `site.py`, what
  `arklight new` scaffolds). Its directory is the *project directory*:
  where a `wrangler.jsonc` is looked for and where Wrangler runs.
- `-o, --output` -- the build directory to deploy (default: `ARK`).
- `--name NAME` -- Cloudflare Worker name, passed to Wrangler as-is
  (Wrangler validates it). Without it, and with no Wrangler config in
  the project, the name is the project directory's name, lowercased
  with anything outside `a-z0-9` turned into `-`; if nothing usable is
  left, `deploy` asks for `--name` instead of inventing one.
- `--skip-build` -- deploy the existing `--output` directory as-is,
  without running `arklight build`. The directory must exist and not
  be empty; the site file is not needed.
- `--dry-run` -- build (unless `--skip-build`) and check for Wrangler,
  then print the command that would run instead of running it.
  Nothing is deployed.

What a run does, in order:

1. Runs `arklight build <entry> -o <output> --no-open` -- the same
   build, with the same output and warnings, as running it yourself.
   If it fails, `deploy` stops there and Wrangler is never started.
2. Looks for `wrangler` on your `PATH`. If it's missing, `deploy`
   stops with install instructions. **ARKlight never installs
   Wrangler** (and never runs `npm`/`npx`, which could) -- run
   `npm install --global wrangler` and `wrangler login` yourself.
3. Prints the exact command, then runs it, from the project directory:
   - **No Wrangler config** (`wrangler.jsonc`, `wrangler.json` or
     `wrangler.toml`) in the project directory:
     `wrangler deploy --assets <output> --name <name> --compatibility-date <today>`
     -- Cloudflare's documented zero-config form for a static site.
   - **A Wrangler config is there:** plain `wrangler deploy` (plus
     `--name` only if you passed one). Your config decides what is
     deployed; ARKlight does not read it, and does not check that its
     `assets.directory` is the directory it just built.
4. Wrangler owns the rest: sign-in prompts, upload, the deployed URL
   and any error message are shown exactly as Wrangler prints them
   (its output is not captured or filtered).

Exit code: `0` on success; a failed build's own code; `1` for a
problem ARKlight itself found (Wrangler missing, missing build
directory, missing site file); otherwise **Wrangler's own exit code,
unchanged** (`130` on Ctrl-C). In CI, Wrangler reads its credentials
from `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID` -- ARKlight never
touches them.

Wrangler keeps a scratch `.wrangler/` directory in the directory it runs
in; add it to your `.gitignore`.

```bash
arklight deploy
arklight deploy cloudflare my_site.py -o public --name my-portfolio
arklight deploy --dry-run
arklight deploy --skip-build
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
  subcommand. Works with or without a virtualenv: on a system Python
  with no venv, where pip refuses to install into an "externally
  managed" environment (PEP 668), the reinstall step retries once with
  `--break-system-packages` and prints a note when it does.

`arklight --help` (or a bare `arklight` with no subcommand) prints the
full list of subcommands with a short description of each.
