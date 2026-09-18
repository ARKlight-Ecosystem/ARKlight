# Authoring Guide

The full public component/behavior/state API reference: routing, head
metadata, layout, styling, behaviors, the component vocabulary, the
ARK Bundle format, and `arklight.config.py`. The root
[`README.md`](../../README.md) keeps only the quickstart example and
points here, via its Documentation section, for everything else.

## Preamble directives (`# include`, `# define`)

`from arklight import *` still works exactly as it always has. But a
site file can instead open with reserved-shape *comments* -- ARKlight
reads these itself, before your code runs, rather than delegating to
Python's own `from X import *`:

```python
# include <stdlib.ARKlight>

site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"))
```

`# include <stdlib.ARKlight>` binds ARKlight's own public vocabulary
(`Page`, `Button`, `State`, everything `from arklight import *` gives
you today) -- but ARKlight resolves and binds every name itself,
remembering which include supplied each one, rather than handing the
job to Python's star-import statement.

That distinction matters once a second source is in play, e.g. an ACC
collection:

```python
# include <stdlib.ARKlight>
# include <acc.some_collection>
```

If both sources try to bind the same name to two genuinely different
objects, ARKlight raises a `PreambleCollisionError` naming both
sources, at load time -- instead of silently keeping whichever
`from ... import *` happened to run last, which is exactly what plain
Python import semantics would otherwise do with zero diagnostic. This
is the same "fail loudly, no silent winner" doctrine the compiler
already applies to duplicate `@component` registration
(`DuplicateComponentError`) and duplicate ACC capability identities
(`CapabilityError`) -- `# include` closes the one remaining gap, the
step that gets names into the namespace in the first place.

A collision is resolved explicitly with `# define`:

```python
# define Button -> acc.some_collection.Button
```

`# define <alias> -> <target>` binds `<alias>` to whichever object
`<target>` resolves to. A bare target (`# define Btn -> Button`) must
be unambiguous across everything included so far; a dotted target
(`<include-label>.<name>`, using the exact label from that
`# include <label>` line) picks one specific include's copy by name,
for exactly the case where two sources disagree about what a name
means.

Only `<stdlib.ARKlight>` and `<acc.<dotted.module.path>>` are
recognized include labels today. An `acc.` include must point at a
real, importable module that defines `__all__` -- the same contract
`arklight.__all__` itself follows -- otherwise ARKlight doesn't know
what vocabulary that module is meant to contribute, and raises rather
than guessing. See `arklight/parser/preamble.py` for the full
resolution rules and `arklight/parser/loader.py` for how the resolved
bindings land in a site file's namespace before its own code executes.

## Internal links are relative, not root-absolute

`Link("About", href="/about")` refers to the *route* `"/about"`, the
same string you'd pass to `@site.page(...)`. The HTML backend resolves
this to the correct relative file path at build time (`about.html`,
`../about.html`, etc., depending on where the linking page lives), so
navigation works whether you open the file directly from disk or
deploy the `ARK/` folder as-is. External URLs, `#fragments`, and
`mailto:`/`tel:` links are left untouched.

## Head metadata (title, description, favicon, Open Graph, meta/links)

`Page(...)` already accepted `title` (falls back to the site name if
omitted). Seven more optional props extend the same pattern -- read
straight off `Page`'s props, nothing new to import:

```python
Page(
    Heading("ARKlight"),
    title="ARKlight",
    description="A Python-first compiler for building static websites.",
    favicon="assets/favicon.ico",
    og_image="assets/social.png",
    meta={"theme-color": "#0f0f0f"},
    links=[{"rel": "preconnect", "href": "https://fonts.gstatic.com"}],
)
```

| Prop              | Renders as                                    |
|-------------------|------------------------------------------------|
| `title`           | `<title>` (already existed)                    |
| `description`     | `<meta name="description">`                    |
| `favicon`         | `<link rel="icon">` -- resolved relative, same as the stylesheet/script links |
| `og_title`        | `<meta property="og:title">` -- defaults to `title` |
| `og_description`  | `<meta property="og:description">` -- defaults to `description` |
| `og_image`        | `<meta property="og:image">` -- resolved relative, like `favicon` |
| `meta`            | `dict[str, str]` of name -> content pairs, each a `<meta name="..." content="...">` (v0.048 Stage A) |
| `links`           | `list[dict[str, str]]`, each dict an attribute -> value map rendered as one `<link ...>` tag -- for preconnect, webfonts, or extra icon sizes beyond `favicon` (v0.048 Stage A) |

All eight are optional and additive: a page that sets none of them
renders identically to before this feature existed. Open Graph tags
specifically only appear once `description` or any `og_*` prop is
supplied, so `title`-only pages (the common case) don't get an
unsolicited `og:title`. `meta`/`links` are structured input only --
no raw HTML string escape hatch, matching every other extension point
in the project -- and, unlike `favicon`/`og_image`, `links` entries
are emitted verbatim rather than resolved as a relative build asset,
since a `links` entry is at least as likely to point at an external
origin (e.g. a webfont host) as a local one.

## Site-wide layout width & background

Two more optional `Site(...)` constructor kwargs, alongside `name`:

```python
site = Site(max_width="90rem", bg="#0f0f1a")
```

| Kwarg | Overrides | Default when omitted |
|---|---|---|
| `max_width` | `--ark-max-width` (`body`'s own `max-width`) | `min(100% - 3rem, 75rem)` -- fluid, caps around 1200px |
| `bg` | `--ark-bg` (`body`'s and `html`'s own `background`) | `#ffffff` |

Both exist specifically because `body` reads these two `--ark-*`
variables *directly* on its own rule -- unlike `--ark-accent`/
`--ark-border`/etc., which only descendants (links, buttons, borders)
read, a per-node `style={...}` or a custom `site.style(...)` class
can't reach `body`'s own box: a CSS custom property only cascades
downward, and `body` already resolved its rule from `:root` before any
site-authored element exists in the tree. `Site(max_width=...,
bg=...)` sets the variable at `:root` scope instead, which *is* an
ancestor of `body`, so it's picked up correctly. `docs/CONTAINER-WIDTH-BUG.md`
was cited here historically but never actually made it into the repo
-- see [`CHANGELOG.md`](../../CHANGELOG.md) ("Documentation fix: the
container-width bug fix itself was never documented") for the full
history of why this needed its own dedicated kwargs rather than
reusing `site.style(...)`.

## Styling components

Any component accepts two extra props for styling, on top of the
default stylesheet:

```python
Text("Careful now", class_name="muted")
Container(..., style={"background": "#f5f5ff", "padding": "1rem"})
```

`class_name` renders as the HTML `class` attribute (avoiding the
`class` keyword clash); `style` accepts a dict of CSS properties and
is rendered as an inline `style` attribute. Built-in utility classes
from the default stylesheet: `.nav`, `.card`, `.muted`, `.page`,
`.hidden` (pairs with the `toggle` behavior below).

## Custom CSS classes

`style={...}` is per-node and `class_name="..."` alone only reaches
the fixed utility classes above -- neither lets you define a *new*,
reusable class. `site.style(name, rules)` does:

```python
site = Site()
site.style("pull-quote", {"font-style": "italic", "border-left": "4px solid purple"})

@site.page("/")
def home():
    return Page(Text("A quote worth repeating.", class_name="pull-quote"))
```

`rules` is a plain `{css-property: value}` dict -- the same shape as
the per-node `style={...}` prop, never a raw CSS string, so this
doesn't reopen the "no arbitrary CSS/HTML strings" boundary the rest
of ARKlight holds. Registered classes are appended to the generated
stylesheet after the fixed defaults, so they can override base rules
by cascade order. Calling `site.style()` again with an already-used
name overwrites its rules (last call wins).

## Responsive layout, without `@media` (platform-independent by construction)

`Page` never gets a `<head>` hook (see
[`DESIGN-NOTES.md`](DESIGN-NOTES.md)), so a generated site
has no `@media`/`@container` query available to it at all -- there is
no "desktop breakpoint" or "mobile breakpoint" to hand-tune, and
nothing keyed to a specific screen width, device, or platform. Layouts
still adapt, but from the *content's own* available width using plain
flexbox/grid sizing keywords (`minmax`, `auto-fit`, `flex-wrap`,
`clamp`) -- the same technique goes by "intrinsic web design." Opt in
with `class_name`, same mechanism as `.nav`/`.card` above:

| Class             | What it does                                                                 |
|-------------------|-------------------------------------------------------------------------------|
| `.stack`          | Consistent vertical rhythm between block children                            |
| `.cluster`        | A row of items that wraps as a group once it runs out of width                |
| `.sidebar`        | Two panels side-by-side once there's room, stacked when there isn't           |
| `.switcher`       | Children stay in a row until each would drop below a minimum width, then stack |
| `.grid`           | An auto-filling card/tile grid with no explicit column count                  |
| `.center`         | Constrains and horizontally centers content, with optional gutters            |
| `.reel`           | A horizontally-scrolling row that never wraps or overflows the page           |
| `.fluid-heading`  | Font size scales smoothly with available width via `clamp()`                  |

For a layout that's three columns on a wide viewport and a single
column on a narrow one -- the classic "desktop vs. mobile" case --
`.switcher` is usually the right tool: give it three children and it
lays them out in a row as long as each stays above a minimum width
(`--ark-switcher-threshold`, default `30rem`), and stacks them
vertically the moment they'd drop below that, with no device or
browser ever queried:

```python
Container(
    Container(Heading("Fast"), Text("...", class_name="muted"), class_name="card"),
    Container(Heading("Simple"), Text("...", class_name="muted"), class_name="card"),
    Container(Heading("Portable"), Text("...", class_name="muted"), class_name="card"),
    class_name="switcher",
)
```

This adapts identically on any platform that renders CSS at all --
desktop browser, phone browser, embedded webview -- because the
decision is made from the container's own measured width, not from
`user-agent`, viewport metadata, or a hard-coded pixel breakpoint.
`.grid` is the equivalent choice when the number of items is open-ended
rather than a fixed three (a card feed, a tag list), auto-filling as
many `minmax()`-wide columns as the available width allows. All
`--ark-*` custom properties above (space, thresholds, widths) can be
overridden per-instance via the `style` prop shown earlier.

## Behaviors (client-side interactivity, no JS written by hand)

Any component accepts `on_click` + `behavior_target` (a CSS selector)
to opt into a small, closed set of built-in behaviors, implemented by
the tiny runtime the JS backend generates:

```python
Button(
    "Show details",
    on_click="toggle",              # or "scroll-to"
    behavior_target="#more-details",
    toggle_class="hidden",          # optional, default "is-open"
)
Container(Text("..."), id="more-details", class_name="hidden")
```

| Behavior     | What it does                                                   |
|--------------|-------------------------------------------------------------------|
| `toggle`     | Toggles a CSS class (`toggle_class`, default `is-open`) on every element matching `behavior_target` |
| `scroll-to`  | Smooth-scrolls the element matching `behavior_target` into view    |

`on_click` is validated against this fixed vocabulary at the
Validation stage -- an unknown behavior name (or a missing
`behavior_target`) fails the build with a clear message rather than
silently doing nothing in the browser. There is deliberately no way to
pass arbitrary JavaScript: see
[`DESIGN-NOTES.md`](DESIGN-NOTES.md) for why that boundary
is a design choice, not a gap.

The current page's nav link is also highlighted automatically (an
`is-active` class added to any `<a>` inside `.nav` whose target matches
the current page) -- no props needed for that one.

## Public API (v0.003)

Components -- every one of these is a plain Python function that
returns an `ARKNode`:

| Component   | Notes                                              |
|-------------|-----------------------------------------------------|
| `Page`      | Root node every page function must return           |
| `Container` | Generic grouping element (renders as `<div>`)        |
| `Heading`   | Text-only. `level=1..6` prop controls `<h1>`-`<h6>`  |
| `Text`      | Text-only. Renders as `<p>`                          |
| `Button`    | Text-only. Renders as `<button>`                     |
| `Link`      | Text-only. Requires `href` prop. Renders as `<a>`    |
| `Image`     | No children allowed. Requires `src` prop             |
| `List`      | Renders as `<ul>`                                    |
| `Item`      | Text-only. Renders as `<li>`                         |

"Text-only" components may only contain plain strings, not other
components -- this is enforced by the Validation stage.

The table above is the original v0.001 core. Two vocabulary
addenda (still v0.003, no new pipeline stage -- see CHANGELOG.md) add
~79 more components on top of it, purely as data in
`arklight.ir.schema.SCHEMA` (the single source of truth every stage
reads from):

- **First addendum:** semantic layout (`Header`, `Footer`, `Main`,
  `Nav`, `Section`, `Article`, `Aside`, `Figure`/`FigCaption`,
  `Details`/`Summary`), text-level semantics (`Strong`, `Em`, `Small`,
  `Mark`, `Code`, `Cite`, `Abbr`, `Sub`, `Sup`, `Span`, `Time`,
  `HorizontalRule`, `LineBreak`, `Pre`, `Blockquote`), forms (`Form`,
  `Input`, `Textarea`, `Select`, `Option`, `OptGroup`, `Label`,
  `FieldSet`, `Legend`), tables (`Table`, `TableHead`, `TableBody`,
  `TableFoot`, `TableRow`, `TableHeaderCell`, `TableCell`, `Caption`),
  and media (`Video`, `Audio`, `Source`).
- **Second addendum ("even more vocabulary"):** numbered/description
  lists (`OrderedList`, `DescriptionList`/`DescriptionTerm`/
  `DescriptionDetails`), art-directed responsive images (`Picture`/
  `PictureSource`, plus `loading`/`decoding` attributes), native
  widgets (`Progress`, `Meter`, `Datalist`, `Output`), a zero-JS
  `Dialog`, more text semantics including bidi and ruby (`Kbd`,
  `Samp`, `Var`, `Data`, `Ins`, `Del`, `Q`, `Dfn`, `Address`, `Wbr`,
  `Bdi`, `Bdo`, `Ruby`, `Rt`, `Rp`), table column grouping
  (`ColGroup`, `Col`), video/audio captions (`Track`), image maps
  (`Map`, `Area`), `IFrame` embeds, and a `NoScript` fallback.

See [`CHANGELOG.md`](../../CHANGELOG.md) for the rationale behind each
group and `arklight.ir.schema.SCHEMA` for the authoritative list of
every component's required props, text-only-children rule, and
whether it allows children at all.

`Site`:

```python
site = Site()

@site.page("/some/route")
def page_fn():
    return Page(...)
```

Any keyword prop passed to a component that isn't recognized (e.g.
`id`, `class`, `href`, `src`, `style`, ...) is emitted as a `data-*`
HTML attribute, so nothing you write is silently dropped.

## ARK Bundle (`.ark`) -- v0.037 (sealed by default, implemented)

A build's output (`index.html`, `styles.css`, `arklight.js`, `assets/`)
is a folder of separate files. `arklight pack` (see CLI section above)
packages that output as a single `.ark` file:

- The raw build files -- including an `assets/` folder, if present --
  are stored as-is inside an archive; no new file format, no
  re-encoding, nothing about how the HTML/CSS/JS backends generate
  files changes for this feature.
- The bundle is a **polyglot**: a fully self-contained, inlined
  rendering of the entry page is placed *before* the archive data, so
  the same file opens directly as a rendered page in a browser (no
  unzip step, no temp files, no server -- the same way an image viewer
  doesn't "extract" a `.png` before displaying it) regardless of what
  the archive half contains.
- **Sealed by default.** The archive half is encrypted (see
  `arklight.packer.seal`, stdlib `hmac`/`hashlib`/`secrets` only, no
  crypto dependency) so a generic archive tool, "rename to `.zip`", or
  hex editor sees only opaque bytes -- it can't be casually opened,
  inspected, or spliced/tampered with. `arklight unpack site.ark -o
  ARK` reverses this. Without a `--passphrase`, the encryption key
  travels embedded in the bundle so `arklight unpack` always works with
  no extra input -- this blocks generic tools, but is **not** secrecy
  from someone who also has ARKlight (the key is right there in the
  file). Pass `--passphrase` for real confidentiality: the key is then
  derived from it (PBKDF2-HMAC-SHA256) and never stored, and the same
  passphrase is required to unpack.
- **`--plain` opts back into the original v1 behavior**: a real,
  generically-openable ZIP tail, freely inspectable/re-editable by any
  archive tool without ARKlight installed at all.
- This is a packaging step that runs *after* `arklight build`, over
  files the existing pipeline already produces -- `arklight.packer`
  only reads already-written build output and never imports the
  parser/ir/backend internals.
- **Known limit, sealed or not:** only the *archive* half is protected.
  The *inlined front-matter page* -- what a browser actually renders --
  is always plain HTML/CSS/JS, because that's what makes the polyglot
  openable as a web page at all; view-source on the page you're
  currently looking at was never in scope to hide. Sealing protects the
  *other* pages/assets bundled alongside it, not the one on screen.

See [`DESIGN-NOTES.md`](DESIGN-NOTES.md) ("v0.036: ARK
Bundle spec v1" and "v0.037: sealed bundles") for the full byte layout,
packing algorithm, cipher construction, and known caveats.

## Configuration (`arklight.config.py`)

Optional, project-level settings that don't belong on the `Site(...)`
call because they're about how you work with a project locally, not
part of the compiled site itself -- currently just the
`live-streaming` dev server's bind address, with more sections planned
(see `docs/Foundational/DESIGN-NOTES.md`).

Create a file named `arklight.config.py` next to your site's entry
file (same directory as `site.py`), containing a single top-level
`CONFIG` dict:

```python
# arklight.config.py
CONFIG = {
    "live_streaming": {
        "host": "127.0.0.1",
        "port": 8347,
    },
}
```

- **Entirely optional.** No `arklight.config.py` in the entry file's
  directory -> every section falls back to its built-in default,
  exactly as if the file were `{}`.
- **Not searched up the directory tree.** A project's config lives
  directly next to its `site.py`, not somewhere an ancestor directory
  has to be searched for -- keeps "which config applies" unambiguous.
- **Loaded the same way a site file is** -- a plain `exec` of the
  file's source in its own namespace. A project's config file is
  exactly as trusted as its site file already is; this introduces no
  new trust boundary.
- **Fails loudly if present but broken.** A syntax error, a missing
  `CONFIG`, or a `CONFIG` that isn't a dict raises a clear error at
  load time rather than silently falling back to defaults -- a typo'd
  setting should never look like it's taking effect when it isn't.
- **Forward-compatible by section.** Each top-level key in `CONFIG`
  (`"live_streaming"` today) is owned by whichever part of ARKlight
  reads it; a section this version of ARKlight doesn't know about yet
  is preserved as-is rather than rejected, so a config file written
  against a newer ARKlight still loads on an older one.

See `arklight/config.py` for the loader itself, and
`docs/Foundational/DESIGN-NOTES.md` for how this same mechanism is
planned to grow (an `"android"` section for the Android backend's
app-identity metadata -- icon, splash, package ID, orientation -- and
a `"desktop"` section for the Desktop backend, each read the same way
`"live_streaming"` is today).

