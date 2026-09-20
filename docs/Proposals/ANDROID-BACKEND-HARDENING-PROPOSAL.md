# Android Backend Hardening: Native-Shell Quality, Without a Bridge

## Status

**Partially accepted; first slice implemented as of `0.06507`.**
Accepted and shipped: §2.1 (external-link handling) with the
`android.allow_navigation` key it needs, §2.2 (a load-error page, as fixed
behavior), §2.3 (predictive back), §2.4 (WebView state save/restore) and
§3's `webContentsDebuggingEnabled`-follows-build-type. Still a proposal,
unscheduled: §2.5 (documentation-only), §2.6 (`WebChromeClient`), §2.7 (the
WebView-version floor), the `append_user_agent` key and the WebView
background-colour key. See "Implementation notes" at the end. Originally:
**Proposal -- not yet accepted, not yet scheduled against a version.**
Written after a source-level audit of `arklight/backend/android/
runtime.py` and `arklight/cli/android.py` against `docs/Backends/
ANDROID-BACKEND-IMPLEMENTATION.md` (Stages 0-4 done, 5-7 not started)
and `docs/Foundational/DESIGN-NOTES.md`'s "v0.0438: Android backend"
section, plus a comparative pass against Capacitor's `capacitor.
config.json` surface for prior art. No code has been written against
this proposal; it is scoped narrowly on purpose (see §0) so it can be
accepted, rejected, or partially accepted per item without dragging
the deferred native-bridge question into it.

## 0. Scope boundary this whole proposal sits inside

`docs/Foundational/WHAT-ARKLIGHT-IS.md` states plainly that ARKlight
is **"not a general-purpose native-app framework. No native plugin
API, no camera/Bluetooth/sensor bridge, by explicit design choice."**
`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`'s "Explicitly out of
scope" list is equally direct: **"any native-plugin/push/deep-link
bridge beyond serving assets"** is not in scope for Stages 0-7.
`DESIGN-NOTES.md` leaves the door open a crack -- a generalized,
capability-based JS-to-native bridge is *deferred, not ruled out*,
explicitly waiting on the Desktop backend to exist as a second data
point before it earns its own design doc.

Everything below was sorted against that line before being written
down, into two buckets:

- **Bucket A -- pure Kotlin/Gradle/manifest/WebView-configuration
  work. No JS-to-native bridge, no new capability surface.** Native
  shell maturity: the app behaves like a well-built Android app, full
  stop. Nothing here conflicts with the current scope doc. This is
  what this proposal actually proposes.
- **Bucket B -- anything requiring the WebView to talk to native code
  at runtime** (a JS interface for status-bar color, `ark.*`
  capabilities, deep links). Explicitly **not** proposed here --
  called out only where relevant, and left for the deferred bridge
  design `DESIGN-NOTES.md` already reserves a slot for.

A reader who wants Bucket B's status-bar-sync design (per-page
`theme-color`, a `window.ArkNative.*` interface, the `WebViewClient`
timing options) should look for it as its own, separately-decided
proposal once/if the bridge question is picked up -- deliberately not
folded in here.

## 1. What's already solid (confirmed, not assumed)

Worth stating up front so this doesn't read as "the Android backend is
full of gaps" -- most of the native-identity work is already real:

- Material You dynamic color is wired app-wide (`ArkApplication.kt`,
  `DynamicColors.applyToActivitiesIfAvailable`), a no-op below API 31
  so it's safe across the full `minSdk 24` range.
- A real adaptive icon *and* an API-33+ monochrome/themed-icon layer
  already exist (`<monochrome android:drawable=.../>` inside the
  adaptive-icon XML) -- this was flagged as a plausible gap from web
  research last round and turned out to already be shipped.
- Light/dark `themes.xml`/`values-night/themes.xml` split, a real
  `androidx.core.splashscreen` splash flow, and `edge_to_edge` as an
  existing, working config toggle.
- No `INTERNET` permission declared -- correct and deliberate for a
  fully offline, baked-in-assets app; not a gap, a feature, and worth
  keeping that way by default (see §4).

## 2. Findings: Bucket A gaps, confirmed against the source

Each item below was checked directly against `arklight/backend/
android/runtime.py` (`grep` for the relevant Android API surface
turned up nothing for any of these -- not "under-configured," genuinely
absent) before being listed.

### 2.1 No `shouldOverrideUrlLoading` -- external links load inside the app

`MainActivity.kt`'s `WebViewClient` overrides `shouldInterceptRequest`
(for `WebViewAssetLoader`) but nothing else. Once *any* custom
`WebViewClient` is attached, Android stops doing its own default link
handling -- every tapped link, including a link to a completely
external domain, loads **inside the app's own WebView** instead of
handing off to the system browser. This is a well-documented, common
real-world bug (confirmed against multiple independent open-source
issue trackers hitting exactly this during this session's research),
not a hypothetical edge case.

**Proposed fix**, modeled on Capacitor's `server.allowNavigation`
default behavior (external URLs open in the browser *unless*
explicitly allowlisted): default to same-origin (the app's own
`WebViewAssetLoader` origin) staying inside the WebView, everything
else routed out via `Intent.ACTION_VIEW` wrapped in a
`try/catch (ActivityNotFoundException)` so a device with no handler
for a scheme can't crash the activity. A new `android.allow_navigation:
list[str]` config key lets a site opt specific external hosts (an
OAuth redirect domain, a payment subdomain) back into in-WebView
navigation -- see §4 for why this clears the reachability rule.

### 2.2 No offline / load-error handling

No `onReceivedError` override anywhere. A failed navigation currently
falls through to Chromium's own raw system error page, not anything
ARKlight-branded. Low-stakes today (a baked-in-assets app has little
reason to hit a real network error on its own pages) but becomes a
real gap the moment a `Provider`-backed site does a `fetch()` against
a flaky connection.

### 2.3 `onBackPressed()` is deprecated; predictive back isn't wired up

Every scaffolded project ships `@Suppress("DEPRECATION") override fun
onBackPressed()`. Confirmed against current Android guidance: Android
13+'s predictive-back gesture (default-enabled since Android 15,
developer-option toggle removed entirely) expects an
`OnBackPressedCallback`/`OnBackInvokedCallback` registered through the
`OnBackPressedDispatcher`, not the legacy override -- without it, the
in-WebView "go back" action doesn't participate in the predictive
preview animation the rest of the OS now does by default.

### 2.4 No WebView state save/restore across configuration changes

`AppCompatActivity` recreates by default on rotation. Nothing in
`MainActivity.kt` calls `webView.saveState()`/`restoreState()` in
`onSaveInstanceState`/`onCreate`, so a rotation silently reloads the
page from scratch -- losing scroll position and any client-side
`State` that isn't `persist=True`. Cheap, mechanical fix; no bridge
involved.

### 2.5 Edge-to-edge is opt-in today; it stops being optional

`edge_to_edge` is a real, working `false`-by-default config key.
Confirmed during this session's research: **Android 16 removes the
ability to opt out of edge-to-edge entirely.** Not an immediate defect
-- `false` is a legitimate default today -- but worth recording now so
the config key's eventual deprecation isn't a surprise later. Filed
here as a documented, not-yet-actionable fact rather than a fix.

### 2.6 No `WebChromeClient` at all

Misses two independent, non-bridge wins:

- `onConsoleMessage` -- surfacing JS console errors somewhere a
  developer can see them in a debug build (today, a JS error inside
  the packaged app is invisible unless someone's plugged in `chrome://
  inspect`).
- `onShowFileChooser` -- currently, any future page using `<input
  type="file">` silently does nothing when tapped, since no
  `WebChromeClient` exists to field the file-chooser intent.

### 2.7 No static WebView-version floor

`androidx.webkit:webkit:1.11.0` and `WebViewAssetLoader` assume a
reasonably modern system WebView. Nothing today checks
`WebView.getCurrentWebViewPackage()`'s version at launch. On an old or
stripped-down device with a genuinely ancient WebView, the failure
mode today is a silently broken or blank render -- directly against
`WHAT-ARKLIGHT-IS.md`'s own stated posture, "fail loudly at build time
[or, here, launch time], never silently broken behavior discovered
only ... after the fact." Capacitor's ecosystem solves this with a
full plugin (`@capgo/capacitor-webview-version-checker`, runtime
events, a native prompt) -- overkill for what ARKlight needs. A static
check-and-redirect-to-a-plain-error-page at `onCreate` time covers the
real risk without touching the bridge question at all.

## 3. Findings: WebView-configuration ideas surfaced by the Capacitor comparison

Deliberately filtered to the subset of `capacitor.config.json` that is
pure native WebView configuration, not bridge/plugin infrastructure --
see §5 for the explicit rejects.

- **`loggingBehavior` (none/debug/production).**
  `setWebContentsDebuggingEnabled(true)` should be tied to build type
  (debug builds get it, release builds don't), not a manual flag
  someone has to remember to turn off before shipping. Per `docs/
  Foundational/CONFIGURABILITY.md`'s "safety-critical, deliberately
  fixed behavior" category, this probably shouldn't be a config key at
  all -- just correct-by-construction behavior keyed off the existing
  debug/release build type distinction Gradle already has.
- **`overrideUserAgent`/`appendUserAgent`.** Lets a site's own JS
  distinguish "running inside the wrapped app" from "running in mobile
  Chrome" (feature-detection, analytics, an install-prompt banner
  that should hide itself once already installed). A real,
  site-specific want; nothing today reaches it; a one-line
  `WebSettings.userAgentString` change at scaffold time. Clears the
  reachability rule the same way `android.allow_navigation` does (§4).
- **WebView background color.** Independent of the harder, explicitly
  out-of-scope-here status-bar-color-sync question (Bucket B) --
  `webView.setBackgroundColor(...)`, set once from a config value,
  removes the white/black flash before first paint. No per-page logic,
  no meta-tag reading required.

## 4. Config surface: which of these actually earn a kwarg

Run against `docs/Foundational/CONFIGURABILITY.md`'s reachability rule
(a value becomes configurable only when *both* "a real site could
plausibly want it different" and "nothing today already reaches it"
hold) before being proposed as new `android.*` keys:

| Candidate | Real site wants it different? | Reachable today? | Verdict |
|---|---|---|---|
| `allow_navigation: list[str]` | Yes -- an OAuth/payment subdomain a real site needs to keep in-WebView | No -- nothing reaches this today | **New config key** |
| `append_user_agent: str \| None` | Yes -- site JS wants to detect "inside the app" | No | **New config key** |
| WebView background color | Yes -- matches a brand's dark/light default | No | **New config key**, small, same shape as the existing `icon`/`splash` path handling |
| Link-handling default itself (same-origin in, everything else out) | No -- one correct default, not a per-site preference | N/A | **Fixed behavior, not config** |
| Error-page *presence* (an `onReceivedError` handler existing at all) | No -- every app should have one | N/A | **Fixed behavior, not config** |
| Error-page *content/branding* | Yes -- a site may want its own offline message | No | **Plausible future config key, not proposed here** -- smaller win, listed for completeness, not bundled into this proposal's scope |
| `webContentsDebuggingEnabled` | No -- there's one correct answer per build type | Already reachable via build type once wired | **Fixed behavior, tied to Gradle build type, not config** |
| Predictive-back / state-save-restore / min-WebView-version check | No -- these are correctness fixes, not preferences | N/A | **Fixed behavior, not config** |

Net new surface if this proposal is accepted as scoped: **two new
`android.*` config keys** (`allow_navigation`, `append_user_agent`),
plus one small existing-shape extension (a WebView background-color
value, following the same "relative to build-dir root" / simple-value
convention `icon`/`splash` already established). Everything else in
§2 is a fixed-behavior correctness fix with zero new config surface --
consistent with `CONFIGURABILITY.md`'s instruction that a smell (a
bare literal with no comment explaining why it's fixed) is a signal to
run the rule, not a license to expose everything touched along the
way.

## 5. Explicitly rejected from the Capacitor comparison, and why

Named directly rather than silently skipped, since the value of the
comparison is as much in what it rules out as what it confirms:

- **The plugin bridge itself** (`@PluginMethod`, the JSON-serialized
  message-queue architecture, first-party Camera/Geolocation/
  Filesystem/Notifications plugins). This *is* the "general-purpose
  native-app framework" `WHAT-ARKLIGHT-IS.md` states ARKlight isn't,
  by explicit design choice -- adopting it would remove the actual
  differentiator `WHAT-ARKLIGHT-IS.md` Section 5 names: "there's no
  second, independently-trusted layer of arbitrary native code,
  because there isn't a mechanism to introduce one." Out of this
  proposal's scope by definition (§0), not by oversight.
- **`handleApplicationNotifications`, deep-link handling.** Both land
  directly in `ANDROID-BACKEND-IMPLEMENTATION.md`'s existing
  "Explicitly out of scope" list. Capacitor treats these as table
  stakes; ARKlight's stated audience (Python-only developers,
  education/classroom use) mostly doesn't need them, and the sites
  that do aren't presently who this backend is built for.
- **Custom `androidScheme`/`hostname`.** Capacitor lets you rename the
  local WebView origin scheme/host. Deliberately *not* proposed here
  even though it's pure config, no bridge involved: `_ASSET_ORIGIN`
  being fixed is what makes `State(persist=True)` -> `localStorage`
  behave identically across every scaffolded ARKlight app. Letting a
  site change it risks silently breaking persistence semantics between
  builds for a convenience with no concrete forcing use case --
  exactly the kind of thing `CONFIGURABILITY.md` says to leave
  internal even when a generic mechanism to expose it would be easy to
  add.

## 6. Explicitly out of scope for this proposal (restated, not new)

Everything `ANDROID-BACKEND-IMPLEMENTATION.md`'s own "Explicitly out
of scope" section already excludes still applies unchanged: iOS, any
native-plugin/push/deep-link bridge beyond serving assets, Play Store
signing/publishing automation, and any change to the HTML/CSS/JS
backends themselves. This proposal adds nothing to that list and
removes nothing from it -- see §0.

## 7. Open questions

- **Where do the two new config keys live?** Following the existing
  `android.*` section shape in `arklight.config.py`'s `CONFIG` dict
  (`app_name`, `package_id`, ... already there) is the obvious
  default -- no new section, no new file, same read path `arklight.
  cli.android` already uses via `arklight.config.section`.
- **Does `allow_navigation` need validation beyond "is this a
  syntactically plausible hostname"?** Worth deciding whether malformed
  entries should hard-fail `arklight android scaffold` (consistent
  with `package_id`'s existing regex-validated hard failure) or warn
  and skip.
- **Sequencing.** §2's items are independent and additive (same
  discipline `ANDROID-BACKEND-IMPLEMENTATION.md`'s staged-order table
  already uses) -- nothing here requires a particular order, but
  `shouldOverrideUrlLoading` + `allow_navigation` (§2.1 + §3's
  `allow_navigation` row) are the same code path and most naturally
  land as one change, not two.
- **Does the offline/error-page *content* config key (flagged as
  plausible-but-not-proposed in §4's table) belong in a follow-up to
  this proposal, or is it small enough to fold in once someone's
  already touching `onReceivedError`?** Left open rather than
  pre-decided.

## 8. Implementation notes (`0.06507`)

What landed, and where it departs from the text above:

- **§2.1 / `allow_navigation`.** As proposed: same-origin and listed hosts
  stay in the WebView, other `http(s)` links go out via `Intent.ACTION_VIEW`
  inside a `try/catch (ActivityNotFoundException)`. Additions: `mailto:`,
  `tel:` and `sms:` go out the same way; only main-frame navigations are
  intercepted (an iframe is left alone); every other scheme keeps the
  WebView's default. Entries are bare hostnames, `*.` matches subdomains but
  not the bare domain, in-WebView loading is `https` only, and a malformed
  entry hard-fails `arklight android scaffold` -- this settles §7's
  validation question the same way `package_id` already works.
- **`INTERNET` permission.** §1 says to keep the app permission-free by
  default, and it is. §2.1 didn't say that `allow_navigation` can't work
  without the permission; the manifest now adds it when, and only when, the
  list is non-empty.
- **§2.4 correction.** `saveState`/`restoreState` preserve the WebView's
  back/forward history and scroll position. They do not preserve JavaScript
  state, so a rotation still resets a `State` that isn't `persist=True`; the
  proposal's "any client-side State" phrasing overstated the win.
- **§2.2.** A fixed string page loaded on a main-frame error; no URL or error
  text is interpolated into it. Error-page *content* stays unconfigurable,
  as §4 left it.
- **§3 debugging.** Keyed to `ApplicationInfo.FLAG_DEBUGGABLE`, not
  `BuildConfig.DEBUG`, because AGP 8 doesn't generate `BuildConfig` by
  default and the scaffold doesn't turn it on.
- **Unverified on a device.** The Kotlin was compiled (1.9.24) against stubs
  and its routing logic exercised, not built with the Android SDK; the
  scaffolded CI workflow is the first real build.
