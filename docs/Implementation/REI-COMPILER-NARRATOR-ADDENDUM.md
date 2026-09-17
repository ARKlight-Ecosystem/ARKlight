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
