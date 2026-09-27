# Deployment Design

**Status: implemented for Cloudflare Workers, alpha-only so far** (`arklight deploy`,
`arklight/cli/deploy.py`, shipped as `0.06515`; not yet on `main`). Cloudflare
Workers is the only provider. Every other target below is still a spec for
future work. Flags, defaults and exit codes are in
[`CLI-REFERENCE.md`](CLI-REFERENCE.md); "As implemented" below records the
decisions this spec left open and what was deliberately not built.
See [`PROGRESS.md`](../../PROGRESS.md)'s Snapshot table for the current state.

## Goal

`arklight deploy` provides a thin deployment interface for built static
sites.

Cloudflare Workers is the default deployment target. ARKlight does not implement provider-specific deployment infrastructure. It delegates deployment to the provider's official CLI.

## CLI

### Default: Cloudflare Workers

```bash
arklight deploy
````

Equivalent to:

```bash
arklight deploy cloudflare
```

The Cloudflare deployment path:

1. Build the ARKlight site.
2. Verify that Wrangler is available.
3. Invoke the appropriate `wrangler deploy` command.
4. Hand control to Wrangler.
5. Do not reimplement Cloudflare authentication, uploading, configuration, or deployment management.

Wrangler is responsible for the actual Cloudflare deployment.

### Explicit provider

```bash
arklight deploy cloudflare
```

### Future providers

Other deployment targets must be exposed through explicit provider flags or subcommands, for example:

```bash
arklight deploy --github
arklight deploy --netlify
arklight deploy --vercel
```

The exact providers and flags are not part of the current implementation and should only be added when their deployment integrations are designed.
None of these flags exist today: `arklight deploy --github` is an
"unrecognized arguments" error, and `arklight deploy netlify` is refused as
an invalid provider choice.

## Provider Boundary

ARKlight owns:

```text
Python source
    ↓
ARKlight compilation/build
    ↓
static site / deployment artifact
```

The deployment provider owns:

```text
deployment artifact
    ↓
provider CLI
    ↓
hosting platform
```

ARKlight must remain a thin orchestration layer.

Do not embed provider APIs, authentication systems, upload protocols, or provider-specific deployment logic into the core compiler.

## Wrangler Requirement

ARKlight must not silently install Wrangler.

If Wrangler is unavailable, fail with a clear message explaining that Wrangler is required and that the user must install/configure it separately.

Once ARKlight invokes Wrangler, Wrangler owns the deployment process and its output should be forwarded normally.

## As implemented

The five numbered steps under "Default: Cloudflare Workers" are what a run
does, in that order. Where the spec left a detail open, this is what was
decided.

**Command shape.**

```bash
arklight deploy [cloudflare] [entry] [-o OUTPUT_DIR] [--name NAME] [--skip-build] [--dry-run]
```

`entry` defaults to `site.py`, the file `arklight new` scaffolds. The provider
is a positional that is named *before* the site file, so
`arklight deploy site.py` is an error (the message lists `cloudflare`) rather
than a guess. That leaves `--github`-style flags free on `deploy` itself for
later providers, as this spec anticipates.

**Step 1, build.** `deploy` runs `arklight build <entry> -o <output> --no-open`
by calling the CLI's own build command, not a copy of it, so a deploy build
has the same project config, warnings and errors as a manual one. A failed
build stops the run; Wrangler is never started. `--skip-build` deploys an
existing output directory as-is (it must exist and be non-empty).

**Step 2, Wrangler check.** `wrangler` is looked up on `PATH` with
`shutil.which` and nothing else. ARKlight does not fall back to `npx`, `npm`,
`pnpm` or `yarn`, because `npx` will download a package it can't find, which
is exactly the silent install the section above forbids. The check runs
*after* the build, as the numbered steps say, so a missing Wrangler leaves you
with a built site and instructions rather than nothing. A test installs
`npm`/`npx`/`pnpm`/`yarn`/`corepack` stand-ins that record any call and
asserts none happens.

**Step 3, the command.** The project directory is the directory of the site
file (the same rule `arklight build` uses to find `arklight.config.py`).

- *No* `wrangler.jsonc`/`wrangler.json`/`wrangler.toml` there: ARKlight
  supplies the minimum Wrangler needs, using Cloudflare's documented
  static-assets form:
  `wrangler deploy --assets <abs output dir> --name <name> --compatibility-date <today>`.
  The name is `--name` if given (passed through untouched; Cloudflare's rules
  are Cloudflare's to enforce), otherwise the project directory's name
  reduced to lowercase `a-z0-9` and `-`. If nothing usable is left,
  ARKlight asks for `--name` instead of inventing one, since a Worker name
  becomes part of a public URL.
- A Wrangler config *is* there: plain `wrangler deploy` from the project
  directory. The config is the user's; ARKlight does not read it, override
  it, or generate one. `--name` is forwarded only if the user passed it.
  ARKlight does not check that the config's `assets.directory` is the
  directory it just built, and says so when it prints the command.

**Steps 4 and 5, hand-off.** stdin, stdout and stderr are inherited, not
captured, so `wrangler login` prompts, progress and the deployed URL appear
exactly as Wrangler wrote them. ARKlight reads no credentials, makes no
network request, and does not interpret Wrangler's output. Its exit code is
Wrangler's, unchanged (a signal death is reported as `128 + signal`, Ctrl-C as
`130`). A structural test keeps `urllib`, `http.client`, `requests`,
`socket`, `os.environ` and `getpass` out of `deploy.py`.

**`--dry-run`** (not in the original spec) runs steps 1 and 2, prints the
command, and stops. It requires Wrangler, so a passing dry run means a real
run would get as far as invoking it.

**Deliberately not built.**

- Any provider other than Cloudflare Workers, and any provider flag.
- A `deploy` section in `arklight.config.py`. `--name` is the only
  project-level setting and it has a stable default; a config key can be added
  if that turns out to be tedious.
- A Wrangler version check. Wrangler owns its own compatibility; the command
  form was verified against Wrangler 4.135.0 (`--dry-run`) and is the one
  Cloudflare documents.
- Generating or editing a `wrangler.jsonc`, or adding `.wrangler/` to a
  `.gitignore`. Wrangler keeps a scratch `.wrangler/` directory in the
  directory it runs in; ignoring it is left to the project.
- Cloudflare Pages (`wrangler pages deploy`). The spec names Workers.
- Anything that needs a Cloudflare account: no real deploy was run while
  building this, only the command form against a real Wrangler's own
  `--dry-run` and a real Wrangler's unauthenticated failure passing through.

## Design Principle

`arklight deploy` should make deployment convenient without making ARKlight responsible for operating every hosting platform.

Cloudflare Workers is the default because it is the primary supported deployment target, not because ARKlight should become a Cloudflare SDK.

```
