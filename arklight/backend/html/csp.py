"""
Runtime policy enforcement: the Content-Security-Policy `<meta>` tag.

`WHAT-ARKLIGHT-IS.md`'s "Closed-vocabulary" point is, today, a purely
*compile-time* guarantee: nothing ARKlight's own compiler emits ever
constructs a function from a string, confirmed directly against
`arklight/backend/js/render.py`, `runtime/dispatch.py`, and `attrs.py`.
That says nothing about *runtime* -- once a build is loaded in a real
browser, nothing previously stopped a compromised dependency, a
malicious browser extension, or a future ARKlight bug from calling
`eval`/`new Function`, writing an untrusted string into `innerHTML`, or
calling `document.write`. This module is the browser-enforced backstop
for that gap: a strict CSP the browser itself refuses to let any of
those three sinks execute against, regardless of what JS ends up
running on the page.

What this module deliberately does NOT touch, and why:

- **`style-src` -- never set.** Inline `style="..."` is a first-class,
  already-documented escape hatch (`CONFIGURABILITY.md`'s own
  `--ark-grid-min` example: reachable via `style=` before it ever got a
  `Site(...)` kwarg). Restricting `style-src` here would break that
  existing mechanism for every site using it -- a regression, not
  hardening. CSS injection is also a categorically smaller-severity
  concern than code execution, which is what this policy exists to
  close.
- **`connect-src` -- never set.** HTMX's own boosted-nav XHR already
  self-restricts to same-origin requests (`selfRequestsOnly: true` in
  its vendored config, `arklight/backend/js/htmx.py`); ARKlight's
  closed vocabulary has no fetch/HTTP primitive an author could reach
  in the first place (`WHAT-ARKLIGHT-IS.md`). Nothing here needs a
  second, redundant restriction.
- **`default-src` -- never set.** Setting it would silently cascade a
  restriction onto every *other* fetch directive (`img-src`,
  `style-src`, `connect-src`, ...) this module hasn't reasoned about --
  exactly the kind of blast-radius surprise a policy like this should
  never introduce as a side effect. Only `script-src`/`object-src`/
  `base-uri`/the Trusted Types pair below are ever declared.
- **`css-import` (`Site.import_style(url)`, EXPERIMENTAL-APIS.md) is
  unaffected** for the same reason: an `@import` URL is a `style-src`
  concern, and `style-src` is never restricted here.

What it does set, and why each line is safe for every existing site:

- `script-src 'self'` (+ `Site(trusted_script_origins=[...])`, if any)
  -- no `'unsafe-eval'`, no `'unsafe-inline'`. ARKlight's own compiler
  never emits an inline `<script>` or an eval/Function call (confirmed
  above), so this is a no-op restriction for anything the compiler
  itself generates -- it only closes a door nothing legitimate was
  using.
- `object-src 'none'` -- standard hardening; ARKlight never emits
  `<object>`/`<embed>`.
- `base-uri 'self'` -- prevents a `<base>` tag (injected some other
  way) from silently rewriting every relative URL on the page.
- `trusted-types default; require-trusted-types-for 'script'` -- the
  actual browser mechanism for locking down `innerHTML`/`outerHTML`/
  `insertAdjacentHTML`/`document.write`/etc: once declared, the browser
  refuses to let a *plain string* flow into any of those sinks at all,
  from any script, unless it was produced by a registered
  `TrustedTypePolicy`. ARKlight's vendored HTMX (`htmx.py`) already
  avoids the covered sinks for its core swap path (it parses via
  `DOMParser`, not `innerHTML=`, and `Q.config.includeIndicatorStyles =
  false` -- see `arklight/backend/js/render.py` -- removes the one
  remaining `insertAdjacentHTML` call it would otherwise make), so no
  default policy needs registering here: there's nothing left in
  ARKlight's own runtime for one to allow.

**Graceful degradation is the browser's job, not this module's.** CSP
directives degrade per-directive by spec: a browser that doesn't
recognize `require-trusted-types-for` (Trusted Types is Chromium-only
as of this writing; Firefox/Safari don't yet implement it) simply
ignores that one directive and enforces the rest -- it never breaks the
page, and this module needs no feature-detection or fallback logic of
its own to get that behavior. Same for the whole tag on an ancient
browser that doesn't parse `<meta http-equiv="Content-Security-
Policy">` at all: the tag is inert, the page renders exactly as if it
weren't there.

**`raw_postprocess` interaction -- historical note (see
`docs/EXPERIMENTAL-APIS.md`, `arklight/experimental.py`'s
`raw-postprocess` entry for the full deprecation text).**
`Site.raw_postprocess(fn)` is officially deprecated and no longer runs
anything, so it can no longer inject an inline `<script>` that this
policy's `script-src 'self'` (no `'unsafe-inline'`) would then block.
Its replacement, `site.register_script_extension(...)`
(`arklight.backend.script_extension.ScriptExtension`), doesn't have
this problem at all: it only ever appends to `arklight.js`, an
*external* script this policy already allows under `script-src 'self'`
by default -- no inline `<script>`, no CSP conflict, no need for
`Site(strict_csp=False)`. `Site(strict_csp=False)` remains available
as a general, explicit, all-or-nothing opt-out for anything else that
still needs it.
"""

from __future__ import annotations

from html import escape


def _render_csp_meta_tag(trusted_script_origins: list[str] | None = None) -> str:
    """
    Build the `<meta http-equiv="Content-Security-Policy" ...>` tag.

    `trusted_script_origins` (from `Site(trusted_script_origins=[...])`)
    is appended to `script-src` verbatim, space-separated, after `'self'`
    -- for a genuinely trusted external script (an analytics snippet, a
    third-party embed SDK) a site needs to load. Empty/`None` (the
    default) emits just `'self'`, matching a site that hasn't opted
    into any external script origin.
    """
    script_src = "'self'"
    if trusted_script_origins:
        script_src += " " + " ".join(trusted_script_origins)

    directives = [
        f"script-src {script_src}",
        "object-src 'none'",
        "base-uri 'self'",
        "trusted-types default",
        "require-trusted-types-for 'script'",
    ]
    policy = "; ".join(directives)
    return f'  <meta http-equiv="Content-Security-Policy" content="{escape(policy, quote=True)}">\n'
