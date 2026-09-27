"""
PWA (Progressive Web App) support -- v0.038.

Incremental, opt-in post-build step: turns an existing `arklight
build` output directory into an installable PWA by generating a Web
App Manifest and a Service Worker, then injecting the small tags each
page needs to pick them up (`<link rel="manifest">` and a service-
worker registration) into every already-built HTML file.

Like `arklight.packer.bundle`, this module only ever reads files a
normal build already produced -- it does not import or touch the
compiler pipeline (parser/ir/backend). That keeps PWA-enabling a step
*after* `arklight build`, not a new pipeline stage fused into it, and
it's what makes it safe to run repeatedly: `enable_pwa()` re-scans
`build_dir` every time and rewrites `manifest.json`/`sw.js`/`ark-pwa.js`
plus the injected tags in place -- nothing is appended twice, and edits
to the build (new pages, changed assets) are picked up on the next run
without cleaning anything up by hand first. That's the "incremental"
part: there's no separate PWA build mode to keep in sync, just re-run
`arklight pwa <build-dir>` after any `arklight build`.

    build-dir/
      index.html, about.html, ...   <- get manifest link/meta + SW
                                        registration injected in place
      manifest.json                 <- generated
      sw.js                         <- generated, precaches every file
                                        found in build-dir at run time
      ark-pwa.js                    <- generated, external runtime for
                                        SW registration + the optional
                                        install button (see below)

The service worker is a small, dependency-free, cache-first precache:
every file `enable_pwa()` finds in `build_dir` (HTML/CSS/JS/assets/
anything else) is listed and precached on install; `CACHE_NAME` embeds
a content hash of that file list, so any change to the build (added,
removed, or edited file) yields a new cache name -- that's what
actually triggers the browser to fetch the update on the next visit,
via the generated `sw.js`'s own `activate` handler dropping any
differently-named cache. An unchanged re-run produces the same cache
name and is a no-op for anyone with it already installed.

**Everything this module injects is an external `<script src=...>`,
never an inline `<script>` block.** `Site(strict_csp=True)` (the
default, `arklight/backend/html/csp.py`) bakes a `script-src 'self'`
policy -- no `'unsafe-inline'`, no way to add one post-build, since a
nonce baked into a static build is publicly readable and therefore not
trustworthy -- into every page the compiler emits, and this module has
no way to know, from a bare build directory, whether the site that
produced it opted out with `strict_csp=False`. Earlier versions
injected the SW-registration call and the install-button's event
wiring as inline `<script>` blocks, which that default policy then
silently blocked in the browser -- the service worker never actually
registered, and the install button never actually worked, on any site
still running the (correctly strict) default. `ark-pwa.js` -- one
shared external file, generated alongside `manifest.json`/`sw.js` --
carries both pieces of logic instead; each page's injected `<script
src="...">` tag is a `script-src 'self'`-friendly *external* load, same
as `arklight.js` already is for the compiler's own runtime. The one
per-page value the registration call needs (`sw_href`, whose relative
path depends on how deep the page sits under `build_dir`) travels as a
`data-ark-sw-href` attribute on that same tag rather than as inlined JS
-- `ark-pwa.js` reads it off `document.currentScript` at load time.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from dataclasses import dataclass, field
from pathlib import Path

from arklight import experimental

MANIFEST_NAME = "manifest.json"
SERVICE_WORKER_NAME = "sw.js"
# External runtime this module generates for SW registration and the
# optional install button -- see the module docstring's CSP note for
# why this can never be inlined into each page instead.
PWA_RUNTIME_NAME = "ark-pwa.js"

# Injected verbatim into every page's <head>/<body>, wrapped in these
# marker comments so re-running enable_pwa() finds and replaces its
# own prior injection instead of appending a second copy each time.
_HEAD_MARKER_START = "<!-- arklight:pwa:head -->"
_HEAD_MARKER_END = "<!-- /arklight:pwa:head -->"
_SW_MARKER_START = "<!-- arklight:pwa:sw -->"
_SW_MARKER_END = "<!-- /arklight:pwa:sw -->"
# EXPERIMENTAL (docs/Foundational/EXPERIMENTAL-APIS.md, feature id
# "experimental-install-pwa") -- markers for the opt-in native
# install-prompt button (`arklight pwa ... --install-button`), same
# find-and-replace-on-rerun pattern as the two pairs above.
_INSTALL_MARKER_START = "<!-- arklight:pwa:install -->"
_INSTALL_MARKER_END = "<!-- /arklight:pwa:install -->"

_HEAD_BLOCK_RE = re.compile(
    re.escape(_HEAD_MARKER_START) + r".*?" + re.escape(_HEAD_MARKER_END) + r"\n?",
    re.DOTALL,
)
_SW_BLOCK_RE = re.compile(
    re.escape(_SW_MARKER_START) + r".*?" + re.escape(_SW_MARKER_END) + r"\n?",
    re.DOTALL,
)
_INSTALL_BLOCK_RE = re.compile(
    re.escape(_INSTALL_MARKER_START) + r".*?" + re.escape(_INSTALL_MARKER_END) + r"\n?",
    re.DOTALL,
)
_HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
_BODY_CLOSE_RE = re.compile(r"</body>", re.IGNORECASE)


class PWAError(Exception):
    """Raised when a build directory can't be turned into a PWA."""


@dataclass
class PWAResult:
    build_dir: Path
    manifest_path: Path
    service_worker_path: Path
    updated_pages: list[str] = field(default_factory=list)
    cached_paths: list[str] = field(default_factory=list)
    cache_name: str = ""
    # EXPERIMENTAL (docs/Foundational/EXPERIMENTAL-APIS.md): populated with one
    # `ExperimentalUsage` when `install_button=True` was passed to
    # `enable_pwa()`, empty otherwise. The CLI drains this the same
    # way `arklight build` drains `WebsiteIR.experimental_usages`.
    experimental_usages: list = field(default_factory=list)


def _cache_name(paths: list[Path], build_dir: Path) -> str:
    """
    Content hash of every precached file's relative path *and* bytes,
    so any change to the build -- a new file, a removed one, an edited
    one -- changes the cache name. See the module docstring for why
    that's what makes a re-run an effective cache-bust.
    """
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(build_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return f"arklight-pwa-{digest.hexdigest()[:16]}"


def _render_manifest(
    *,
    name: str,
    short_name: str | None,
    start_url: str,
    theme_color: str,
    background_color: str,
    display: str,
    icons: list[dict[str, str]],
) -> str:
    manifest = {
        "name": name,
        "short_name": short_name or name[:12],
        "start_url": start_url,
        "scope": "./",
        "display": display,
        "theme_color": theme_color,
        "background_color": background_color,
        "icons": icons,
    }
    return json.dumps(manifest, indent=2) + "\n"


def _render_service_worker(cache_name: str, precache_paths: list[str]) -> str:
    precache_json = json.dumps(sorted(set(precache_paths + [MANIFEST_NAME])), indent=2)
    return (
        "// Generated by `arklight pwa` -- do not edit by hand. Re-run\n"
        "// `arklight pwa <build-dir>` after your next `arklight build`\n"
        "// instead; this file (including CACHE_NAME) is fully\n"
        "// regenerated every time, not patched in place.\n"
        f'const CACHE_NAME = "{cache_name}";\n'
        f"const PRECACHE_URLS = {precache_json};\n"
        "\n"
        'self.addEventListener("install", (event) => {\n'
        "  event.waitUntil(\n"
        "    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))\n"
        "  );\n"
        "  self.skipWaiting();\n"
        "});\n"
        "\n"
        'self.addEventListener("activate", (event) => {\n'
        "  event.waitUntil(\n"
        "    caches.keys().then((names) =>\n"
        "      Promise.all(\n"
        "        names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))\n"
        "      )\n"
        "    )\n"
        "  );\n"
        "  self.clients.claim();\n"
        "});\n"
        "\n"
        'self.addEventListener("fetch", (event) => {\n'
        "  event.respondWith(\n"
        "    caches.match(event.request).then((cached) => cached || fetch(event.request))\n"
        "  );\n"
        "});\n"
    )


def _relative_href(target_name: str, page_rel_path: str) -> str:
    """`target_name` (e.g. "manifest.json", root-level) relative to a
    page's own directory -- same approach the HTML backend already
    uses for stylesheet/script hrefs, see
    `arklight.backend.html.render._relative_asset_path`."""
    current_dir = posixpath.dirname(page_rel_path) or "."
    return posixpath.relpath(target_name, current_dir)


def _render_pwa_runtime() -> str:
    """
    The external file `<script src="...">` tags point at instead of an
    inline `<script>` block -- see the module docstring's CSP note.
    One shared file for every page, generated fresh on each
    `enable_pwa()` run exactly like `sw.js` is.

    Reads its own `<script>` tag's `data-ark-sw-href` attribute (via
    `document.currentScript`, which is only reliable during the
    script's own synchronous initial execution -- captured into a
    local up front rather than read lazily inside the `load` handler
    below, where `currentScript` would already be `null` again) for
    the one page-specific value SW registration needs: `sw_href`'s
    relative path depends on how deep the page sits under `build_dir`,
    the same reason `_relative_href` exists at all.

    The install-button wiring (identical on every page, so it needs no
    per-page data at all) always runs too, but is a no-op wherever
    `#ark-pwa-install` doesn't exist -- i.e. every page, unless
    `enable_pwa(..., install_button=True)` also injected the button
    markup (`_render_install_block`) into it.
    """
    return (
        "// Generated by `arklight pwa` -- do not edit by hand. Re-run\n"
        "// `arklight pwa <build-dir>` after your next `arklight build`\n"
        "// instead; this file is fully regenerated every time, not\n"
        "// patched in place. Loaded as an external <script src=...> by\n"
        "// every page (never inlined) so it works under the default\n"
        "// strict Content-Security-Policy -- see arklight/pwa.py's\n"
        "// module docstring and arklight/backend/html/csp.py.\n"
        "(function () {\n"
        "  var swHref = document.currentScript && document.currentScript.getAttribute(\"data-ark-sw-href\");\n"
        '  if (swHref && "serviceWorker" in navigator) {\n'
        '    window.addEventListener("load", function () {\n'
        "      navigator.serviceWorker.register(swHref);\n"
        "    });\n"
        "  }\n"
        "\n"
        "  var deferredPrompt = null;\n"
        '  var btn = document.getElementById("ark-pwa-install");\n'
        '  window.addEventListener("beforeinstallprompt", function (event) {\n'
        "    event.preventDefault();\n"
        "    deferredPrompt = event;\n"
        '    if (btn) { btn.style.display = ""; }\n'
        "  });\n"
        "  if (btn) {\n"
        '    btn.addEventListener("click", function () {\n'
        "      if (!deferredPrompt) { return; }\n"
        '      btn.style.display = "none";\n'
        "      deferredPrompt.prompt();\n"
        "      deferredPrompt.userChoice.then(function () {\n"
        "        deferredPrompt = null;\n"
        "      });\n"
        "    });\n"
        "  }\n"
        '  window.addEventListener("appinstalled", function () {\n'
        '    if (btn) { btn.style.display = "none"; }\n'
        "  });\n"
        "})();\n"
    )


def _render_install_block() -> str:
    """
    EXPERIMENTAL (docs/Foundational/EXPERIMENTAL-APIS.md, "experimental-install-pwa")
    -- a small, dependency-free button that surfaces the browser's
    native install prompt via `beforeinstallprompt`. Hidden by default
    (`display: none` inline, matching the rest of ARKlight's "no
    inline <style> block" avoidance being the exception rather than
    the rule here -- there's no generated stylesheet hook to reach
    from a post-build injection step, unlike `arklight build`'s own
    CSS backend) and only shown if the browser actually fires the
    event -- browsers that never fire it (most non-Chromium engines,
    notably) leave the page with no button at all rather than a dead
    one. See `arklight.experimental.FEATURES["experimental-install-pwa"]`
    for the full caveat this trades off.

    Markup only -- the click/`beforeinstallprompt`/`appinstalled`
    wiring lives in `_render_pwa_runtime`'s external `ark-pwa.js`
    instead of an inline `<script>` here, so this button actually
    works under the default strict CSP. See the module docstring.
    """
    return (
        f"{_INSTALL_MARKER_START}\n"
        '  <button id="ark-pwa-install" type="button" style="display:none">Install</button>\n'
        f"{_INSTALL_MARKER_END}\n"
    )


def _inject_page(
    html: str,
    *,
    manifest_href: str,
    sw_href: str,
    runtime_href: str,
    theme_color: str,
    install_button: bool,
) -> str:
    head_block = (
        f"{_HEAD_MARKER_START}\n"
        f'  <link rel="manifest" href="{manifest_href}">\n'
        f'  <meta name="theme-color" content="{theme_color}">\n'
        f"{_HEAD_MARKER_END}\n"
    )
    # External script, not an inline block -- `data-ark-sw-href` is how
    # `ark-pwa.js` learns this page's relative path to `sw.js` without
    # any inline JS to carry it. See the module docstring's CSP note.
    sw_block = (
        f"{_SW_MARKER_START}\n"
        f'  <script src="{runtime_href}" data-ark-sw-href="{sw_href}"></script>\n'
        f"{_SW_MARKER_END}\n"
    )

    # Strip any previously-injected blocks first -- re-running enable_pwa()
    # replaces its own output rather than piling up duplicate copies.
    html = _HEAD_BLOCK_RE.sub("", html)
    html = _SW_BLOCK_RE.sub("", html)
    html = _INSTALL_BLOCK_RE.sub("", html)

    if not _HEAD_CLOSE_RE.search(html):
        raise PWAError("Could not find </head> to inject the PWA manifest link into.")
    if not _BODY_CLOSE_RE.search(html):
        raise PWAError("Could not find </body> to inject the service worker registration into.")

    html = _HEAD_CLOSE_RE.sub(head_block + "</head>", html, count=1)
    body_block = sw_block + (_render_install_block() if install_button else "")
    html = _BODY_CLOSE_RE.sub(body_block + "</body>", html, count=1)
    return html


def enable_pwa(
    build_dir: str | Path,
    *,
    name: str,
    short_name: str | None = None,
    start_url: str = "index.html",
    theme_color: str = "#000000",
    background_color: str = "#ffffff",
    display: str = "standalone",
    icons: list[dict[str, str]] | None = None,
    install_button: bool = False,
) -> PWAResult:
    """
    Turn `build_dir` (an existing `arklight build` output directory)
    into a PWA: writes `manifest.json` + `sw.js` + `ark-pwa.js` into it
    and injects the tags every `.html` page needs to pick them up.

    `install_button` (EXPERIMENTAL, see docs/Foundational/EXPERIMENTAL-APIS.md) --
    when True, also injects a native install-prompt button into every
    page (see `_render_install_block`). Off by default; every call
    made with it on is recorded in the returned `PWAResult.
    experimental_usages` so the CLI can print the same two-tier
    warning `arklight build` prints for `site.media_query(...)`.

    Safe to call repeatedly on the same directory -- see the module
    docstring's "incremental" note. Raises PWAError if `build_dir`
    doesn't exist or contains no `.html` files (i.e. doesn't look like
    an `arklight build` output directory).
    """
    build_dir = Path(build_dir)
    if not build_dir.is_dir():
        raise PWAError(f"Build directory not found: {build_dir}")

    html_paths = sorted(build_dir.rglob("*.html"))
    if not html_paths:
        raise PWAError(
            f"No .html files found in {build_dir} -- run `arklight build` first, "
            f"then enable PWA on its output directory."
        )

    manifest_path = build_dir / MANIFEST_NAME
    sw_path = build_dir / SERVICE_WORKER_NAME
    runtime_path = build_dir / PWA_RUNTIME_NAME

    # Inject/write every page *before* computing the precache hash, so
    # the hash always covers each page's final (post-injection) bytes
    # -- otherwise a first run (hashing pre-injection pages) and a
    # second run (hashing the first run's already-injected pages)
    # would produce different cache names for what is, from the
    # outside, an unchanged build. See the module docstring.
    updated_pages: list[str] = []
    for page_path in html_paths:
        page_rel = page_path.relative_to(build_dir).as_posix()
        manifest_href = _relative_href(MANIFEST_NAME, page_rel)
        sw_href = _relative_href(SERVICE_WORKER_NAME, page_rel)
        runtime_href = _relative_href(PWA_RUNTIME_NAME, page_rel)
        original = page_path.read_text(encoding="utf-8")
        updated = _inject_page(
            original,
            manifest_href=manifest_href,
            sw_href=sw_href,
            runtime_href=runtime_href,
            theme_color=theme_color,
            install_button=install_button,
        )
        if updated != original:
            page_path.write_text(updated, encoding="utf-8")
        updated_pages.append(page_rel)

    # Precache list/hash is computed from whatever's in build_dir now
    # (post-injection), excluding this run's own manifest.json/sw.js/
    # ark-pwa.js -- avoids hashing sw.js's own not-yet-written bytes
    # into its own cache name, and re-including a stale manifest.json/
    # ark-pwa.js from a prior run in the new one's hash. Both are still
    # added to the precache list explicitly below, same as manifest.json
    # already was -- ark-pwa.js is as essential offline as arklight.js
    # itself, since it's what the service worker registration (and the
    # install button, if used) run from.
    precache_sources = sorted(
        p
        for p in build_dir.rglob("*")
        if p.is_file() and p not in (manifest_path, sw_path, runtime_path)
    )
    cache_name = _cache_name(precache_sources, build_dir)
    precache_rel = [p.relative_to(build_dir).as_posix() for p in precache_sources]

    manifest_path.write_text(
        _render_manifest(
            name=name,
            short_name=short_name,
            start_url=start_url,
            theme_color=theme_color,
            background_color=background_color,
            display=display,
            icons=icons or [],
        ),
        encoding="utf-8",
    )
    runtime_path.write_text(_render_pwa_runtime(), encoding="utf-8")
    sw_path.write_text(
        _render_service_worker(cache_name, precache_rel + [PWA_RUNTIME_NAME]), encoding="utf-8"
    )

    return PWAResult(
        build_dir=build_dir,
        manifest_path=manifest_path,
        service_worker_path=sw_path,
        updated_pages=updated_pages,
        cached_paths=sorted(set(precache_rel + [MANIFEST_NAME, PWA_RUNTIME_NAME])),
        cache_name=cache_name,
        experimental_usages=(
            [experimental.emit("experimental-install-pwa", component="Button")]
            if install_button
            else []
        ),
    )
