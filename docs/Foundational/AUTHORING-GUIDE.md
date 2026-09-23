# Authoring Guide

The full public component/behavior/state API reference: routing, head
metadata, layout, styling, behaviors, the component vocabulary, the
ARK Bundle format, and `arklight.config.py`. The root
[`README.md`](../../README.md) keeps only the quickstart example and
points here, via its Documentation section, for everything else.

## Preamble directives (`# include`, `# define`)

`from arklight import *` is **retired**. It still works, but the
compiler now logs a notice for it (file, line, and what to write
instead) on every build. A site file opens with reserved-shape
*comments* instead -- ARKlight reads these itself, before your code
runs, rather than delegating to Python's own `from X import *`:

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

There is deliberately no directive that picks a winner. Drop one of
the includes, or have one side export a different name.

### `# define` -- replace a name with text, at compile time

```python
# include <stdlib.ARKlight>
# define LEVEL -> 2
# define Btn -> Button

Heading("Hi", level=LEVEL)   # runs as Heading("Hi", level=2)
Btn("Go")                    # runs as Button("Go")
```

`# define <name> -> <text>` is lifted straight from C's `#define`: the
left-hand name is replaced by the right-hand text before the file
runs. Both sides are strings -- the right side is *whatever the rest of
the line says* (a number, a string literal, another name, any text
that is valid Python where it lands). That makes `# define` different
in kind from `# include`: an include binds vocabulary, a define
rewrites the file's own source. It binds nothing, resolves nothing, and
needs no include.

The rules are small on purpose:

- **The left side is one Python identifier** (not a keyword), matched
  as a whole name in the file's *code*. `Btn` never touches `Btn2`,
  and nothing inside a string literal (f-strings included) or a
  comment is ever replaced -- C's rule for identifiers. An attribute
  or keyword-argument name is code too, so `# define size -> 12` also
  rewrites `f(size=1)`.
- **The right side is taken verbatim**, from after `->` to the end of
  the line, trimmed. It can't be empty.
- **One pass.** Replaced text is not scanned again (C rescans; here a
  define whose text mentions another define's name is refused, so the
  missing rescan can't turn into a surprise).
- **Per file.** A define never leaks into another module.
- **It can't take the name of included vocabulary.** `# define Button
  -> 5` next to `# include <stdlib.ARKlight>` is an error -- replacing
  `Button` everywhere would silently override the API.
- **Two defines for one name must agree** (repeating the same one is
  harmless).
- **The file must still parse afterwards.** If it doesn't, the error
  lists the defines in effect rather than pointing at rewritten code
  you never wrote. Line numbers never move.

**What counts as the preamble.** Only recognised directive comments
*above the file's contents* -- the scan ends at the first line of
actual code (a docstring counts as code). The same comment between
statements, or at the end of the file, is an ordinary comment to
ARKlight and is never acted on.

**Normalization records, validation raises.** ARKlight handles the
preamble in the same three steps as the rest of the compiler: it reads
the directives, *normalizes* them (includes fill the name table;
defines fill the define table), then *validates* the result.
Normalization never fails on its own; validation is where problems
surface -- an unresolvable include, a malformed or conflicting define,
a name still bound to two different objects.

**Names your own file defines.** Python lets a `def Button(...)`,
`Button = ...`, `from x import Button`, or a leftover `from x import
*` further down the file silently replace a name the preamble already
bound. ARKlight checks for that after your file runs, and a name that
was rebound is the same kind of collision as two includes disagreeing:
the load fails, naming the include the name came from and the line
that rebound it. Rename yours. (Re-importing the *same* object is
harmless, and a `@component(..., allow_redefine=True)` is a deliberate
override, so neither is flagged.) The same rule applies to
`@component` names themselves: one that matches a built-in
(`Button`, `Container`, ...) is refused at registration unless
`allow_redefine=True`, since it would otherwise silently take over
every built-in of that name in the site.

**Scope: every Python file ARKlight takes in.** The site file, each
project module it imports (`pages/`, `components/`, `content/`, an ACC
module that lives in your project), and `arklight.config.py` all get
their preamble read, each on its own -- a file needs its own
`# include <stdlib.ARKlight>` line, exactly like a C file needs its own
`#include`. This is done with an import hook that exists only while the
site loads and only covers files inside the site file's own directory;
the standard library and pip-installed packages (ACC packages
included) are imported by Python exactly as before. The retirement
notice for `from arklight import *` covers every one of those files
too.

**`# include <stdlib.ARKlight>` is the whole public API**: everything
`arklight.api` defines, including the errors it raises
(`CSSSyntaxError`, `DuplicateStyleNameError`, `ComponentError`,
`DuplicateComponentError`). A test keeps it that way.

Only `<stdlib.ARKlight>` and `<acc.<dotted.module.path>>` are
recognized include labels today. An `acc.` include must point at a
real, importable module that defines `__all__` -- the same contract
`arklight.__all__` itself follows -- otherwise ARKlight doesn't know
what vocabulary that module is meant to contribute, and raises rather
than guessing.

**`# use` is reserved, not implemented.** A `# use <...>` line in the
preamble is refused with an error pointing at the proposal
([`USE-PREAMBLE-PROPOSAL.md`](../Proposals/USE-PREAMBLE-PROPOSAL.md),
*not accepted*), because silently ignoring it would let you write it
believing it does something. More directives can be added later: each
is one recogniser plus one handler in `arklight/parser/preamble.py`.
See that file for the full resolution rules and
`arklight/parser/loader.py` for how the resolved bindings land in each
file's namespace before its own code executes.

## Bracket-nesting indentation is checked, not just style

Python doesn't care how a continuation line inside an open `(`, `[`,
or `{` is indented -- everything up to the matching bracket is one
logical line, so this compiles under plain Python even though it
reads as a flat, unnested column:

```python
Page(
Button("ok"),
Text("hi"),
)
```

ARKlight is stricter: a line continuing an open bracket must be
indented *further* than the line that opened it, or the build fails
with a `BracketIndentationError` naming the file and line. A line that
only closes the bracket (a lone `)`, `]`, `}`, or a run of those,
optionally with a trailing comma) must be flush with the opener's own
indentation -- that's the one indentation such a line is allowed to
have, not just the recommended one:

```python
Page(
    Button("ok"),
    Text("hi"),
)
```

A closer that drifts off that line -- even by one space, even though
it's still "just closing brackets" -- is rejected too:

```python
page(
       container(
             ...
      )                 # <- BracketIndentationError: not flush with
                         #    the `container(` on the line above
)
```

Nesting depth is capped as well: past 8 levels of `(`/`[`/`{`, the
build fails with `BracketIndentationError` (its
`TreeNestingTooDeepError` subclass) regardless of how carefully every
line is indented -- a tree that deep stops being readable no matter
what, and the fix is to pull a branch out into its own function, not
to indent it more carefully. A missing comma between siblings is a
different, ordinary `SyntaxError` from Python's own grammar and has
nothing to do with either of these checks.

This check runs on every build, right alongside preamble resolution
(`arklight.parser.preamble.prepare_source`), as its own diagnostic in
`arklight/parser/indentation.py` -- not a `PreambleError`, but a plain
`SyntaxError` subclass, since it has nothing to do with `# include`/
`# define` and both `arklight.parser.loader` and `arklight.config`
catch it separately alongside `PreambleError`.

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

## Passing live state to an action (`Bind(...)` as an argument)

`Action.set(...)` and `Action.append(...)` take a `value`. Give it
`Bind("name")` instead of a literal and it means "whatever `name` holds
when the click happens" -- which, next to an input bound with
`bind_value=`, is the usual `[type a task] [Add]` control:

```python
State("draft", "")
State("tasks", [])
Input(bind_value=Bind.model("draft"))
Button("Add", on_click=Action.append("tasks", Bind("draft")))
Watch("tasks", then=Action.reset("draft"))      # empty the input after adding
Repeat("tasks", template=lambda: Text(RepeatItem.value()))
```

The name must be a `State(...)` or `Computed(...)` on the same page, and
only `set`/`append`'s `value` accept it -- `increment`, `decrement` and
`remove` reject a `Bind(...)` at build time (an input's value is a string,
which would concatenate or never match rather than do arithmetic). Don't
put `debounce=` on the `Bind.model(...)` a submit button reads from: a
click inside the delay would read the previous value. Design record:
[`../Proposals/ACTION-VALUE-FROM-STATE-PROPOSAL.md`](../Proposals/ACTION-VALUE-FROM-STATE-PROPOSAL.md).

## Calling a user-defined component

A component registered with `@component(props={...})` is called with
**keyword props only**, unlike the built-ins, whose positional arguments
are children:

```python
@component(props={"label": Prop(), "value": Prop(default=0)})
def Stat(label, value=0):
    return Text(f"{label}: {value}")

Stat(label="Signups", value=42)   # ok
Stat("Signups", 42)               # build error, not a TypeError
```

The positional form fails the build with a message naming the component,
the rule, its declared props, a by-name example and the `file:line` of
the call. The same goes for a `props=` contract that disagrees with the
render function's parameters (a declared prop the function has no
parameter for, or a required parameter `props=` doesn't declare): one
`ComponentError` naming both sides. To put content inside a component,
pass it through a declared prop. Design record:
[`../Proposals/COMPONENT-CALL-DIAGNOSTICS-PROPOSAL.md`](../Proposals/COMPONENT-CALL-DIAGNOSTICS-PROPOSAL.md).

## Runtime errors (`ARKLIGHT_ON_ERROR`)

On a page that ships ARKlight's runtime (any `State(...)` or click
behavior), a failure in one binding, list, `Show(...)`, `Computed(...)`
or bound input no longer stops the rest of the page: that one thing
reports and everything else keeps updating. The report is a console
line (`[ARKlight] ...`) plus ARKlight's small on-page notice. A page-level
`error`/`unhandledrejection` listener catches anything that still
escapes. A page with no runtime JS ships none of this.

To log to your own analytics, restyle the notice, or silence it,
define `window.ARKLIGHT_ON_ERROR` in a script of your own (a strict-CSP
page can't take it inline):

```js
window.ARKLIGHT_ON_ERROR = function (message, err) {
  myLogger.send(message, err);
  return false;   // exactly `false` suppresses ARKlight's on-page notice
};
```

Anything other than `false` (or no hook at all) leaves the notice
showing. A throwing hook is ignored. The `message` is always one of
ARKlight's own fixed strings. The hook also sees every uncaught error on
the page, including from your own scripts. Design record:
[`../Proposals/RUNTIME-ERROR-HANDLING-PROPOSAL.md`](../Proposals/RUNTIME-ERROR-HANDLING-PROPOSAL.md).

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

