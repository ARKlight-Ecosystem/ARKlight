"""
Preset stylesheets for `Site(markdown_theme=...)`.

Stage M7 of the Markdown-as-first-class-content landing order
(`docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md`). Sibling to
`base_stylesheet.py`/`markdown_defaults.py`, following the exact same
convention those two modules document: this module's only job is to
hold static CSS text. It imports nothing and exposes nothing callable
-- three string constants and the `MARKDOWN_PRESETS` dict that maps a
`Site(markdown_theme=...)` name to its CSS text -- so it can never
gain generation logic by accretion.

No new layout engine and no breakpoint rules beyond what
`arklight/backend/css` already ships, per the proposal's own
constraint: every preset below only ever does two things -- override
a subset of the `:root`-declared `--ark-*` custom properties
`design_tokens.py` already defines (reusing the existing
`var(--ark-*, ...)` plumbing every other rule in the cascade already
reads from), and, where a token doesn't exist for what the preset
needs (`body`'s line-height isn't one), override that one property on
the exact same selector `base_stylesheet.BASE_CSS_BODY` already
declares it on, relying on cascade order (not specificity) to win --
see `render.py`'s placement of `MARKDOWN_PRESETS` for why that
ordering is safe.

Each preset re-declares every `--ark-*` var it touches as a second
`:root { ... }` block rather than a partial one, intentionally: it
keeps every preset's full palette readable in one place instead of
"light's values plus a dark diff", and costs nothing -- `:root` blocks
cascade on specificity/order exactly like any other selector, so a
later `:root` block overriding an earlier one's `--ark-bg` is no
different from `.card` overriding an earlier `.card` declaration.

- **`light`**: tuned from `base_stylesheet.BASE_CSS_BODY`'s own
  existing default posture (`design_tokens.ROOT_VAR_DEFAULTS`) --
  restated here, not restyled from scratch, so selecting
  `markdown_theme="light"` is a no-op against an otherwise-unconfigured
  site's rendered colors; it exists so a project can opt into the name
  explicitly (and so a later ARKlight release is free to actually tune
  `light` independently of the bare stock default without that being
  a breaking change to an *unset* `markdown_theme`).
- **`dark`**: the palette is fixed, taken directly from
  `arklight/cli/mdrender.py`'s own ANSI SGR constants (`_HEADING_COLORS`,
  `_CODE_COLOR`, `_TABLE_BORDER_COLOR`) rather than invented fresh --
  `rgb(204, 120, 92)` == `#cc785c` (primary accent/link, heading-1,
  bullet, table-header "clay"), `rgb(196, 148, 107)` == `#c4946b`
  (heading-2 "tan"), `rgb(166, 151, 128)` == `#a69780` (heading-3/
  blockquote/muted "taupe"), `rgb(214, 163, 115)` == `#d6a373` (inline
  code, reused here as the accent's hover state), `rgb(130, 130, 130)`
  == `#828282` (table borders/rules, reused here as the general
  border color). **Q5 of the proposal, settled here:** the background
  is `#16140f` -- a near-black, warm-tinted ground (not a pure
  `#000000`) chosen to keep the clay/tan/taupe accents at a
  comfortable contrast ratio against it. `--ark-text` (`#f2ece2`, a
  warm off-white, not pure `#ffffff`, to stay tonally consistent with
  the rest of the warm palette) against `#16140f` measures a
  21-step-from-black contrast ratio comfortably over 14:1 -- well
  past WCAG AA's 4.5:1 body-text minimum (`tests/test_markdown_presets.py`
  carries the exit test's actual contrast-ratio computation, not
  just this comment's claim). `--ark-button-text` is set to the same
  near-black background tone so button text stays legible against the
  light clay `--ark-accent` background buttons render on top of --
  the same `--ark-button-text`/`--ark-accent` pairing concern
  `design_tokens.py`'s own comment documents for the stock palette.
- **`reading`**: its own design, not modeled on `light` or `dark` --
  a pale amber/parchment background (`#f8efd6`, deliberately yellow-
  leaning rather than a neutral off-white, the classic "sepia reader"
  tone) with dark warm ink (`#352a16`, not pure black), a matching
  amber accent (`#9c5017`, dark goldenrod, chosen dark enough to clear
  WCAG AA's 4.5:1 for normal-size link text against `#f8efd6` -- not
  just the headline body-text pairing `dark`'s own contrast check
  covers -- and nowhere near `dark`'s clay/terracotta or `light`'s
  indigo, so the three presets stay visually distinct from each
  other), a narrower measure than the
  stock default (reusing `--ark-max-width`, the same token
  `Site(max_width=...)` already exposes, rather than inventing a
  second width mechanism), and a taller `body` line-height for long-
  form reading comfort (the one property in this file with no
  existing `--ark-*` token to flow through -- see the module docstring
  above for why overriding `body`'s own rule directly, in cascade
  order, is still within the "no new layout engine" constraint).
"""

from __future__ import annotations

MARKDOWN_PRESETS_HEADER = """\
/* Generated by ARKlight -- Markdown-authoring theme preset
   (Site(markdown_theme=...)), Stage M7 of the Markdown-as-first-class-
   content ladder (docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md).
   Overrides a subset of the :root custom properties declared above,
   plus (reading only) body's own line-height -- see
   arklight/backend/css/markdown_presets.py's module docstring. */
"""

PRESET_LIGHT = """\
:root {
  --ark-bg: #ffffff;
  --ark-text: #1a1a2e;
  --ark-muted: #5b5b76;
  --ark-accent: #4f46e5;
  --ark-accent-hover: #4338ca;
  --ark-border: #e5e5f0;
  --ark-button-text: #ffffff;
}
"""

PRESET_DARK = """\
:root {
  --ark-bg: #16140f;
  --ark-text: #f2ece2;
  --ark-muted: #a69780;
  --ark-accent: #cc785c;
  --ark-accent-hover: #d6a373;
  --ark-border: #828282;
  --ark-button-text: #16140f;
}
"""

PRESET_READING = """\
:root {
  --ark-bg: #f8efd6;
  --ark-text: #352a16;
  --ark-muted: #7a6b4f;
  --ark-accent: #9c5017;
  --ark-accent-hover: #7a3f0f;
  --ark-border: #e4d3a1;
  --ark-button-text: #f8efd6;
  --ark-max-width: min(100% - 3rem, 42rem);
}

body {
  line-height: 1.8;
}
"""

# name (`Site(markdown_theme=...)`'s value) -> CSS text. The three
# names below are the only valid `markdown_theme` values -- see
# `arklight.api.Site.__init__`'s own validation, which reads this
# dict's keys rather than hand-maintaining a second allowed-values
# list that could drift out of sync.
MARKDOWN_PRESETS: dict[str, str] = {
    "light": PRESET_LIGHT,
    "dark": PRESET_DARK,
    "reading": PRESET_READING,
}

__all__ = [
    "MARKDOWN_PRESETS",
    "MARKDOWN_PRESETS_HEADER",
    "PRESET_LIGHT",
    "PRESET_DARK",
    "PRESET_READING",
]
