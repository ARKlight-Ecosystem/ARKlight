"""
`arkNotify`: a self-contained, inline-styled on-page notice for
runtime edge cases the fixed behavior/action vocabulary didn't
anticipate. Deliberately inline-styled rather than class-based so it
still renders correctly if the page's own stylesheet is implicated in
the failure, and wrapped in its own try/catch so a notification
failure can never itself become a second, worse error.

Split out of `arklight/backend/js/render.py`'s old `_NOTIFY_JS`
constant (`refactor-0`). Pure move, no JS output change.

`0.06505` (runtime error handling) adds two
siblings that ship in the same fragment, under the same gating:

- `arkReportError(message, err)` -- the one funnel every runtime
  *error* path goes through (the per-element guards in the render
  passes, `recomputeAll`, `wireModelBinding`, the v0.041 dispatch/
  watch/`initState` guards, and the page-level boundary below). It
  logs to the console (a guarded failure is no longer an uncaught
  exception, so without this the developer would see nothing), calls
  the site author's optional `window.ARKLIGHT_ON_ERROR(message, err)`
  hook if one exists, and then calls `arkNotify(message)` unless the
  hook returned exactly `false`. `arkNotify` itself is unchanged.
  Feature-availability notices (clipboard/geolocation/paste
  unavailable, `PlatformAPI.notify`'s fallback) are not errors and
  still call `arkNotify` directly.
- `wireErrorBoundary()` -- registers `window` `error` and
  `unhandledrejection` listeners once, as the floor under everything
  the per-element guards don't cover. Browser-generated `ResizeObserver
  loop` notices are ignored (benign, and not a page fault).

The hook is a closed interface with no shipped implementation: ARKlight
never defines `ARKLIGHT_ON_ERROR`, never sends anything anywhere, and
every call into it is inside its own `try`/`catch` so a broken override
can never become a second, worse failure. Messages passed to it are
fixed, compiler-chosen strings -- no site-authored text reaches
`arkNotify`.

Two more siblings close a gap specific to `Site(app_shell=True)`
(htmx-4): HTMX's own request/swap lifecycle can fail -- a broken link,
an offline visitor, a 500 from wherever the shell is hosted -- and
until now nothing on the page ever surfaced that to the visitor. HTMX
dispatches its own `htmx:*Error`-shaped events when this happens (see
`fe()`, "trigger error event", in `arklight/backend/js/htmx.py`'s
vendored source) but never shows anything on its own; a boosted link
that fails just... does nothing.

- `wireHtmxErrorHandling()` -- the HTMX-specific counterpart to
  `wireErrorBoundary()` above: one delegated listener per failure-
  shaped HTMX event (`htmx:responseError`/`htmx:sendError`/
  `htmx:timeout`/`htmx:swapError`/`htmx:targetError`/
  `htmx:invalidPath`), registered once on `document.body` (never
  replaced by a boosted swap), each funnelling into `arkReportError` so
  a failed request gets the same console-log + on-page-notice +
  optional-hook treatment every other runtime failure already does.
  Shipped and wired wherever HTMX itself is (`needs_htmx` in
  `arklight/backend/js/render.py`), which already covers every
  `app_shell` site -- see that module's `needs_htmx` docstring.
- `fallBackToPlainNavigation()` (inside `wireHtmxErrorHandling`) -- a
  boosted link swallows the browser's own navigation
  (`preventDefault`) before its XHR runs, so if that XHR or the swap
  then fails, the link is dead. On `htmx:sendError`, `htmx:swapError`
  and `htmx:onLoadError` for a boosted GET, the handler re-issues the
  same URL as one real navigation (`location.assign`) -- the
  JavaScript counterpart of what the Android host already does for a
  failed boosted request (`android/runtime.py`,
  `isBoostedNavigationRequest`). It fires once per page, never for
  non-GET requests (a form POST is never replayed), and never for
  `htmx:sendAbort`/`htmx:timeout`.
- `disableBoostOnFileProtocol()` and
  `warnIfAppShellServedFromFileProtocol()` -- the one failure mode
  the fallback above shouldn't have to rely on: opening an `app_shell`
  page directly from disk (`file://.../index.html`). Boosted
  navigation issues its swaps via `XMLHttpRequest`, which browsers
  refuse outright against a `file://` URL (there is no origin to
  authorize the request against), and some browsers never dispatch
  HTMX's own error events for it. So on `file:` the runtime removes
  `hx-boost` from `<body>` *before HTMX's DOMContentLoaded init reads
  it* (`disableBoostOnFileProtocol`, emitted as a top-level statement
  right after HTMX loads, not from the DOMContentLoaded handler --
  HTMX's own listener is registered first and would win the race),
  so every link is an ordinary page load, and
  `warnIfAppShellServedFromFileProtocol` tells the visitor once, via
  `console.warn` and an on-page notice, that HTMX is unavailable and
  navigation is falling back to plain page loads. Shipped only for
  `app_shell` sites -- a plain site never boosts navigation, so
  `file://` is a perfectly normal way to open one.
"""

from __future__ import annotations

NOTIFY_JS = """  function arkNotify(message) {
    // Self-contained on-page notice for runtime edge cases the fixed
    // behavior/action vocabulary didn't anticipate -- deliberately
    // inline-styled (not a `.stack`/`.card`/etc. class) so it renders
    // correctly even on a page whose stylesheet this failure might
    // itself be related to, and wrapped in its own try/catch so a
    // notification failure can never become a second, worse error.
    try {
      var el = document.getElementById("ark-notify");
      if (!el) {
        el = document.createElement("div");
        el.id = "ark-notify";
        el.setAttribute("role", "alert");
        el.style.cssText =
          "position:fixed;bottom:1rem;right:1rem;left:auto;max-width:22rem;" +
          "background:#111827;color:#f9fafb;padding:0.75rem 1rem;" +
          "border-radius:0.5rem;font:14px/1.4 system-ui,sans-serif;" +
          "box-shadow:0 4px 12px rgba(0,0,0,.35);z-index:2147483647;";
        document.body.appendChild(el);
      }
      el.textContent = message;
      el.style.display = "block";
      clearTimeout(el._arkNotifyTimer);
      el._arkNotifyTimer = setTimeout(function () {
        el.style.display = "none";
      }, 6000);
    } catch (notifyErr) {
      /* notification is best-effort; never let it throw */
    }
  }"""

ERROR_REPORT_JS = """  function arkReportError(message, err) {
    // Single funnel for every runtime error path. Order matters:
    // console first (the guards swallow the exception, so this is the
    // developer's only trace), then the optional site-author hook,
    // then the default on-page notice unless the hook returned exactly
    // `false`. Each step is independently guarded -- a broken console,
    // a throwing hook, or a failing notice never blocks the next step.
    try {
      if (typeof console !== "undefined" && console.error) {
        console.error("[ARKlight] " + message, err);
      }
    } catch (logErr) { /* best-effort */ }
    var suppress = false;
    try {
      if (typeof window !== "undefined" && typeof window.ARKLIGHT_ON_ERROR === "function") {
        suppress = window.ARKLIGHT_ON_ERROR(message, err) === false;
      }
    } catch (hookErr) { /* a broken override must never become a second failure */ }
    if (!suppress) { arkNotify(message); }
  }"""

ERROR_BOUNDARY_JS = """  function wireErrorBoundary() {
    // Floor under the per-element guards: anything that still escapes
    // as an uncaught error or unhandled promise rejection. Registered
    // once (window is never replaced by an hx-boost swap).
    var boundaryMessage = "Something unexpected went wrong on this page -- some features may not work.";
    window.addEventListener("error", function (event) {
      try {
        var text = String((event && event.message) || "");
        // Benign browser chatter, not a page fault.
        if (text.indexOf("ResizeObserver loop") === 0) return;
        arkReportError(boundaryMessage, event && event.error);
      } catch (boundaryErr) { /* the boundary itself must never throw */ }
    });
    window.addEventListener("unhandledrejection", function (event) {
      try {
        arkReportError(boundaryMessage, event && event.reason);
      } catch (boundaryErr) { /* the boundary itself must never throw */ }
    });
  }"""

HTMX_ERROR_HANDLING_JS = """  function wireHtmxErrorHandling() {
    // HTMX-specific counterpart to wireErrorBoundary() above: HTMX
    // dispatches its own error-shaped events on every failed request
    // or swap (see `fe()`, "trigger error event", in vendored
    // htmx.js) but never shows the visitor anything on its own -- a
    // failed boosted link just does nothing. Funnelling each one
    // through arkReportError gives it the same console-log +
    // on-page-notice + optional ARKLIGHT_ON_ERROR() hook treatment
    // every other runtime failure already gets. Registered exactly
    // once, on document.body (an hx-boost swap never replaces it),
    // same lifetime contract as wireErrorBoundary().
    var message = "A page request failed -- some content may not have loaded.";
    var failureEvents = [
      "htmx:responseError",
      "htmx:sendError",
      "htmx:timeout",
      "htmx:swapError",
      "htmx:targetError",
      "htmx:invalidPath",
      "htmx:onLoadError"
    ];
    // The failures after which a boosted link is provably dead (the
    // browser's own navigation was already cancelled, and HTMX could not
    // finish the swap): degrade to one real page load instead. Not
    // htmx:responseError (the server answered; a real load would just
    // show the same answer), not htmx:timeout/htmx:sendAbort.
    var fallbackEvents = {
      "htmx:sendError": true,
      "htmx:swapError": true,
      "htmx:onLoadError": true
    };
    var navigating = false;
    function fallBackToPlainNavigation(event) {
      var detail = (event && event.detail) || {};
      var config = detail.requestConfig || {};
      // Only a boosted navigation, and only an idempotent one: never
      // replay a form POST.
      if (!detail.boosted) return;
      if (String(config.verb || "get").toLowerCase() !== "get") return;
      var info = detail.pathInfo || {};
      var link = detail.elt;
      var target =
        (link && link.tagName === "A" && link.href) ||
        info.finalRequestPath ||
        info.requestPath;
      if (!target) return;
      navigating = true;
      window.location.assign(target);
    }
    failureEvents.forEach(function (eventName) {
      document.body.addEventListener(eventName, function (event) {
        // A swap failure fires htmx:swapError and then htmx:onLoadError
        // for the same click; once we're already navigating there is
        // nothing left to report or redo.
        if (navigating) return;
        try {
          arkReportError(message, event && event.detail && event.detail.error);
        } catch (handlerErr) {
          /* the handler itself must never throw */
        }
        try {
          if (fallbackEvents[eventName]) { fallBackToPlainNavigation(event); }
        } catch (fallbackErr) {
          /* the fallback itself must never throw */
        }
      });
    });
  }"""

APP_SHELL_FILE_PROTOCOL_BOOST_OFF_JS = """  (function disableBoostOnFileProtocol() {
    // Site(app_shell=True) puts hx-boost on <body>. From file:// every
    // boosted click would be cancelled and then its XMLHttpRequest
    // refused by the browser, leaving a dead link. Removing the
    // attribute here -- synchronously, at script evaluation, i.e.
    // before HTMX's own DOMContentLoaded init reads it -- makes each
    // link an ordinary page load instead. The visitor is told once by
    // warnIfAppShellServedFromFileProtocol().
    try {
      if (window.location.protocol === "file:" && document.body) {
        document.body.removeAttribute("hx-boost");
      }
    } catch (bootErr) {
      /* best-effort */
    }
  })();"""

APP_SHELL_FILE_PROTOCOL_CHECK_JS = """  function warnIfAppShellServedFromFileProtocol() {
    // Companion to disableBoostOnFileProtocol(): app-shell navigation
    // (hx-boost, htmx-4) is an in-place XMLHttpRequest-driven swap, which
    // browsers refuse to issue at all against a page opened directly
    // from disk (file://...) -- there is no origin to authorize an XHR
    // against. On file: the boost has already been switched off, so
    // links are plain page loads; this says so once, instead of leaving
    // the visitor to wonder why the page reloads. Checked directly via
    // window.location.protocol, not via HTMX's own events.
    try {
      if (window.location.protocol === "file:") {
        var notice =
          "Opened from file:// -- htmx is unavailable here, so navigation " +
          "is falling back to plain page loads. Serve the site over " +
          "http(s) for app-shell mode.";
        if (typeof console !== "undefined" && console.warn) {
          console.warn("[ARKlight] " + notice);
        }
        arkNotify(notice);
      }
    } catch (checkErr) {
      /* best-effort, same as arkNotify itself */
    }
  }"""
