# Android Identity and System Bars: Derive What the Site Already Says

## Status

**Proposal. First slice (§2) implemented in the accompanying patch;
everything from §3 on is not built.** Unversioned: the patch carries no
version bump and no `PROGRESS.md` row, so the maintainer picks the slot,
the same way the `0.06504` draft row was left for confirmation.

Written after reading `arklight/backend/android/runtime.py`,
`arklight/cli/android.py`, `docs/Proposals/ANDROID-BACKEND-HARDENING-PROPOSAL.md`
and `docs/Foundational/DESIGN-NOTES.md`'s "App identity metadata" section,
then building `examples/hello_site` and scaffolding it.

**What was and wasn't verified.** The patch is covered by 136 new tests
(the full suite passes: 2,738). The generated project *text* is checked --
Kotlin package lines, Gradle `applicationId`, `themes.xml`/`colors.xml`
content, and that every generated resource file is well-formed XML. The
result was **not built with the Android SDK and not run on a device or
emulator.** The one thing worth eyeballing on a phone is §2.3's bar
colours. The `status_bar_color = "material"` setting was diffed against
the previous generator's output and is byte-identical to it.

## 0. Scope boundary this sits inside

`ANDROID-BACKEND-HARDENING-PROPOSAL.md` §0 sorts Android work into
Bucket A (Kotlin/Gradle/manifest/WebView configuration, no JS-to-native
bridge) and Bucket B (anything where the page and native code talk at
runtime). It filed per-page status-bar sync under Bucket B.

- **§2 (implemented) is Bucket A.** Every value is decided at scaffold time
  from files `arklight build` already wrote, and lands in ordinary manifest,
  string, colour and theme resources. No new Kotlin.
- **§3.1 (runtime, per-page sync) is the borderline case.** It needs no
  `addJavascriptInterface` and no page-visible API: native code asks the
  WebView a read-only question (`evaluateJavascript`) after a page loads. I
  think that is not a bridge in the sense `DESIGN-NOTES.md` reserves, but it
  is the maintainer's line to draw, so it stays a proposal.

## 1. What a scaffold does today

For a site built with `Site("Recipe Box")`:

- **The app is called "ARKlight App"**, whatever the site is called. The name
  is already in the build output (`<title>`), but nothing reads it.
- **Every scaffold gets `com.arklight.app`.** Android identifies an app by
  its `applicationId`, so two different ARKlight sites installed on one phone
  are, to Android, the same app: the second install replaces the first (or
  fails on a signature mismatch). This is the strongest reason to fix
  identity, not just a cosmetic one.
- **The bars don't match the page.** The status bar is transparent over the
  *Material* window background (`#FBFDFA` light, `#191C1A` dark), not over the
  site. A white page under a slightly-off-white or near-black band is the
  visible result.
- **`edge_to_edge = True` picks icon colour from the phone's dark-mode
  setting, not from the page.** A site is one colour in both modes (the stock
  stylesheet has no dark variant), so a white page on a dark-mode phone gets
  light status-bar icons drawn over white. Read off the templates, not
  observed on a device.

## 2. Implemented in the patch

All of it lives in the scaffold step and reads the *build directory*, so it
works for a site built by any means and needs no compiler changes.

### 2.1 App name

Resolved in this order; the first that yields something wins:

1. `android.app_name` in `arklight.config.py` (unchanged behaviour).
2. `name` in the build's PWA `manifest.json`, if `arklight pwa` has run.
3. The home page's `<title>`. For a page with no title this is the
   `Site(name=...)`, so `Site("Recipe Box")` names the app "Recipe Box".
4. `"ARKlight App"`. The compiler's own placeholder site name
   (`arklight-site`) counts as "not named" and is skipped.

`<title>` is parsed from `index.html`'s `<head>` only, entities decoded once,
whitespace collapsed. The value is XML-escaped in `strings.xml` as before.

### 2.2 Package id

If `android.package_id` is set it wins, validated exactly as before.
Otherwise: `com.arklight.<slug>`, where the slug comes from the app name:

- accents folded to ASCII, everything non-alphanumeric becomes `_`;
- `2048` becomes `app_2048` (a segment must start with a letter);
- `New`, `Class`, `Fun`, `In` and the other Java/Kotlin keywords get an
  `_app` suffix, since an unescaped keyword in the generated `package` line
  is a compile error;
- a name with nothing ASCII in it (`日本語`) becomes `app`;
- at most 40 characters.

**A note on the hyphen.** The natural form, `com.arklight.site-name`, isn't
a legal `applicationId`: segments allow letters, digits and underscores
only, and Gradle rejects the rest. So `site-name` becomes
`com.arklight.site_name`.

If nothing named the app, the id stays `com.arklight.app`, so a nameless
project is unchanged.

### 2.3 System bars follow the page

New config key, `android.status_bar_color`:

| Value | Meaning |
| --- | --- |
| `"auto"` (default) | Match the site: a `theme-color` meta tag if there is one, else the stylesheet's `--ark-bg`. |
| `"material"` | The Material theme colours, exactly as before. |
| any CSS colour | Use it (`"#1a1a2e"`, `"rgb(26, 26, 46)"`, `"white"`, `hsl(...)`). |

When a colour is resolved it drives, in both the day and night theme files:
the status bar, the navigation bar, the **window background** (so the frame
that shows before the WebView paints, and on overscroll, matches) and the
**splash background**. It is written once as a `ark_site_background` colour
resource, so it is easy to tweak by hand.

**Icon lightness follows the colour, not the day/night theme**: dark icons
when the colour's WCAG luminance is above 0.179 (the point where black and
white text have equal contrast), light icons below. Both modes get the same
answer, because the page doesn't change with the phone's setting.

With `edge_to_edge = True` the bars stay transparent (the page already draws
behind them and its own background shows through); only the icon lightness
and the window background change.

**Only opaque solid colours are understood** (hex, `rgb()`, `hsl()`, the 16
basic names plus `orange`). A gradient, image, `var(...)`, translucent value
or other named colour makes `"auto"` fall back to the Material colours and
*say so* in the scaffold output, naming the value it couldn't use. A bar
painted a colour the page doesn't have is worse than an unmatched one.

**What "dominant colour" means here.** This is the page's *background*
colour: what fills the top and bottom edges of the screen. It isn't a pixel
average of the rendered page, which would need a browser at build time and
would answer a different question anyway. It is one colour for the whole
app, taken from the stylesheet every page shares.

### 2.4 The scaffold says what it decided

Real output for `examples/hello_site`, scaffolded with no android config:

```
ARKlight v0.67 scaffolded an Android project for 'ARKlight' (com.arklight.arklight) -> proj/ (28 file(s))
  name:        'ARKlight' (from index.html <title>)
  package id:  com.arklight.arklight (derived from app name)
  system bars: #FFFFFF (from stylesheet --ark-bg)
  Set android.app_name / android.package_id in arklight.config.py to choose
  your own. The com.arklight.* id is fine for testing on your own device; use
  a package id you control before publishing anywhere.
```

Note the name here is the home page's `Page(..., title="ARKlight")`, which
the example sets explicitly. `Site(name=...)` only reaches `<title>` on a page
that sets no title of its own -- see §5.2.

The reminder is printed only when the id wasn't set in config. See §5.1 for why.

## 3. Not built

### 3.1 Per-page bar colour at runtime

§2.3 uses one colour for the whole app. A multi-page site whose pages have
different backgrounds (a dark landing page, a light docs page) needs the bars
to change as the user navigates.

Sketch: in the existing `WebViewClient`, `onPageFinished` (and
`doUpdateVisitedHistory`, so back-navigation is covered) calls
`evaluateJavascript` for the page's `theme-color` meta tag, falling back to
`getComputedStyle(document.documentElement).backgroundColor`, parses the
result and updates the window through `WindowInsetsControllerCompat`. The
build-time colour of §2.3 stays as the value used before the first page
reports, so there's no flash from a default.

Open points: whether `evaluateJavascript` is unaffected by the site's strict
CSP and Trusted Types policy (it should be, as it runs from the embedder, but
this hasn't been tried); a colour change on the same page (a JS theme toggle)
wouldn't be seen without a `MutationObserver`, which would need a bridge and
so is out; and the §0 question.

### 3.2 Targeting SDK 35 changes how bar colours work

The project targets SDK 34, so `statusBarColor` works today. Google's
Android 15 behaviour-change notes say apps targeting SDK 35 are drawn
edge-to-edge by default, that `setStatusBarColor` / `R.attr#statusBarColor`
are deprecated and *have no effect*, and that the navigation bar colour no
longer applies to gesture navigation, only to three-button navigation.

So the `statusBarColor`/`navigationBarColor` lines in §2.3 will silently stop
painting the day `_TARGET_SDK` moves to 35 -- which the Play Store's target
API requirements will eventually force. The parts of §2.3 that survive are the
**window background** and the **luminance-driven icon flags**; the fix is then
transparent bars plus the WebView inset-padded over the site-coloured window
background. Nothing to do until the bump, but the bump should carry a note
that this is coming, and a test that fails when `_TARGET_SDK >= 35` while the
theme still relies on `statusBarColor`.

### 3.3 Other quality-of-life candidates

Roughly cheapest first. None is designed in detail.

- **WebView background colour.** `webView.setBackgroundColor` from the same
  resolved colour removes the white flash before first paint. Already listed
  as unscheduled in the hardening proposal; the value now exists to feed it.
  One Kotlin line.
- **Launcher icon from the site.** When `android.icon` is unset and the PWA
  `manifest.json` lists icons, use the largest instead of the generic
  ARKlight one. Today every app looks identical on the home screen until the
  author supplies an icon by hand.
- **Short launcher label.** Launchers truncate long labels; the manifest's
  `short_name` is a ready-made answer when present.
- **Refresh the site in an existing project.** `scaffold` refuses a non-empty
  directory, so every content change means clearing and regenerating. A
  narrow `arklight android sync` that replaces only `app/src/main/assets/`
  would make the iterate-and-rerun loop workable. (Distinct from a full
  re-scaffold, which would have to decide what to do about hand edits.)
- **Auto-increment `version_code`.** A stale `version_code` blocks an
  in-place update on a device.
- **Desktop parity.** `arklight/cli/desktop.py` has the same
  `"ARKlight App"` default. The resolution helpers are backend-neutral and
  could move to a shared module when the second backend adopts them; the
  patch keeps them in `cli/android.py` until then rather than guess the shape.

## 4. Compatibility

- **A named site gets a new default package id** the next time it is
  scaffolded. An APK installed from an earlier scaffold has id
  `com.arklight.app`; the new build has a different id, so Android installs it
  as a *separate app* rather than updating. Set `android.package_id =
  "com.arklight.app"` in config to keep the old identity. Alpha, so no
  deprecation window is proposed, but it belongs in the changelog.
- **Unnamed sites are unaffected.** No name means the old name and old id.
- **`"material"` reproduces the previous output byte for byte** (checked by
  diffing a scaffold from before and after). A site with no readable
  background colour falls back to it automatically.
- **The default for `android.app_name` and `android.package_id` changed from
  a string to `None`** ("the project didn't say"). Nothing else in the tree
  reads those defaults.
- **`android.status_bar_color` is a new key.** An invalid value is a
  build-time `AndroidError`, like `package_id` and `allow_navigation`, not a
  warning.

## 5. Open questions

1. **Is `com.arklight.*` the right namespace for a derived id?** Reverse-domain
   ids imply you own the domain. It's fine for a personal test install, but a
   Play Store id is permanent, and two unrelated sites both called "Notes"
   derive the same id. The patch prints a reminder to set your own; the
   alternatives are a distinct sub-namespace (`com.arklight.generated.<slug>`)
   that reads as a placeholder, or refusing `--release` while the id is derived.
2. **`<title>` is the site name only by accident of the compiler.** A home page
   titled "Welcome" names the app "Welcome". The clean fix is for the HTML
   backend to emit `<meta name="application-name">` from `Site(name=...)`, and
   for the scaffold to prefer it. That changes every site's HTML, so it is a
   compiler question, not a Bucket A one, and is left for the maintainer.
3. **Dark variants.** The stock stylesheet has no dark mode, so one colour
   serves both themes. `theme-color` tags with a dark `media` condition are
   currently ignored. If sites gain dark variants, `status_bar_color_dark`
   is the obvious counterpart.
4. **§3.1: does a read-only `evaluateJavascript` query cross the bridge line?**

## 6. Rejected

- **Sampling the rendered page (headless browser at build time).** Heavy new
  dependency for an answer, "the average colour", that isn't what a status bar
  wants.
- **A `window.ArkNative.setStatusBar(...)` interface.** The Bucket B design;
  §3.1 gets the same result without exposing native code to the page.
- **Hyphenated package ids.** Not legal; see §2.2.