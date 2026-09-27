"""
`arkNotify`: a self-contained, inline-styled on-page notice for
runtime edge cases the fixed behavior/action vocabulary didn't
anticipate. Deliberately inline-styled rather than class-based so it
still renders correctly if the page's own stylesheet is implicated in
the failure, and wrapped in its own try/catch so a notification
failure can never itself become a second, worse error.

Split out of `arklight/backend/js/render.py`'s old `_NOTIFY_JS`
constant (`refactor-0`). Pure move, no JS output change.

`0.06505` (docs/Proposals/RUNTIME-ERROR-HANDLING-PROPOSAL.md) adds two
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
