# Rei Compiler Narrator -- Implementation Addendum (`v0.065`)

Single-version implementation entry for the accepted
[`docs/Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md`](../Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md)
-- one stage, no ladder, sharing `v0.065` with JS vocabulary addendum
stage 5 and `Provider` stage 1 of 6 (see that proposal's Status
section for the version-number history).

## What lands in `v0.065`

- `--narrate` flag on `arklight build` (`arklight/cli/main.py`),
  mutually exclusive with `--verbose`/`--debug`.
- A renderer module (proposed home: `arklight/compiler/rei/`) that
  hooks the same stage-completion points `--verbose` already prints
  from, producing one narrated sentence (occasionally two) per stage
  instead of a `[ARKlight] ...` line. Pure Python, stdlib only -- no
  new dependency.
- A vendored, read-only reference copy of a classic ELIZA
  implementation (proposed home: `docs/reference/eliza/` or similar,
  clearly marked as reference material, not imported by any shipping
  code) -- studied during design, not linked against at runtime. This
  addendum should record exactly where it ends up and confirm no
  `import` in `arklight/` ever reaches into it.
- `rei` section added to `arklight/config.py`'s `_KNOWN_SECTIONS`, one
  key (`default_mode`, values `"plain"`/`"verbose"`/`"narrate"`),
  following the existing section's schema-and-docstring pattern.
- First-compile introduction: a check for "output directory doesn't
  exist, or exists and is empty" at the top of the build command,
  gating a one-time banner (Rei's introduction + the resolved `rei`
  config) before the first narrated stage line.
- `arklight search <name>` pointer on a schema violation (proposal
  §5): when the `ValidationError` narrated on build failure originates
  from either of `arklight/ir/validate.py`'s two
  `SCHEMA.get(node.type) is None` sites (unknown component type) or a
  required-prop-shape check against a known `node.type`, Rei's
  renderer extracts the literal offending name already present in the
  error (no re-parsing of free text -- these sites should carry the
  name as structured data reaching the renderer, not force it to be
  regex-scraped back out of a formatted string) and appends exactly
  one fixed line: `Try: arklight search <name>`. No other validation
  failure category (state/action/behavior/predicate/derivation
  registries) gets a tool pointer -- see the proposal's own scope
  note for why. Rei does not import or call
  `arklight.search.engine`/`arklight.cli.search` herself; the pointer
  is a static template with substitution, not an invocation. Also not
  in scope: `DuplicateComponentError`/`DuplicateStyleNameError`
  (`arklight.ir.components`/`arklight.api`) from a same-name
  `register_component`/`register_backend_render`/`Site.style(...)`
  re-registration -- these are import-time errors, not
  `ValidationError`s narrated by this renderer at all (see the
  proposal's §5 scope note).
- `docs/Foundational/CLI-REFERENCE.md` updated to document `--narrate`
  alongside `--verbose`/`--debug`, once actually shipped -- **not**
  before, per that file's own "implemented and shipped only" scope
  note at its top. Do not add `--narrate` there while this addendum
  is still PLANNED.

## Tests

- Flag parsing: `--narrate` and `--verbose` are mutually exclusive;
  `--debug` still implies `--verbose` and is unaffected by `--narrate`
  existing.
- Config: `rei.default_mode` sets the no-flag-passed default; an
  explicit CLI flag always overrides it; an absent `rei` section
  behaves exactly like today (`"plain"`).
- Determinism: the same site file, built twice with `--narrate`,
  produces byte-identical narrated output (no timestamps, no
  nondeterministic phrasing selection without a fixed seed if
  variation is added later).
- First-compile banner: appears when the output directory is missing
  or empty, does not appear on a second build into the same
  non-empty output directory, reappears if the output directory is
  deleted and rebuilt.
- No import from any shipping `arklight/` module reaches into the
  vendored ELIZA reference material.
- `arklight search` pointer: appears verbatim, with the correct
  literal name substituted, on both unknown-component-type and
  missing/malformed-required-prop failures; does **not** appear on a
  `Bind`/`on_click`/modifier/behavior validation failure, even though
  those are also `ValidationError`s narrated by the same renderer.
  A regression test should assert the *absence* of the pointer line
  on at least one of those other-registry failures, not just its
  presence on the schema-violation cases.
- Import-time registration errors are untouched by this addendum:
  a site file whose own `component(...)`/`site.style(...)` calls
  raise `DuplicateComponentError`/`DuplicateStyleNameError` (a
  same-name re-registration without `allow_redefine=True` -- see
  `arklight.ir.components`/`arklight.api`) still surfaces as a plain
  Python traceback, identically under `--narrate`, `--verbose`, and no
  flag at all, since the failure happens before `arklight build`
  reaches any of the narrated pipeline stages. A regression test
  should confirm `--narrate` produces no Rei output (banner or
  otherwise) for this case, not just that no `arklight search` pointer
  is appended.

## Explicitly not part of this addendum

Everything §6 of the proposal lists as out of scope: no structured
event bus, no diagnostic redesign, no `--trace`, no
`arklight explain <event-id>`, no IDE integration, no additional
narrator personas.

## Status

**PLANNED -- not yet started.** Update this addendum and roll its
outcome into `docs/version history/v0.065.md` (replacing the PLANNED
marker on this section) once actually implemented, following the
same convention `v0.061.md`-`v0.064.md` already set for their own
stages.
