"""
Content shared across more than one `arklight new` template.

Currently just the scaffolded `arklight.config.py` -- every template
writes the same one, so it lives here once rather than being
duplicated per-template and risking drift between copies.
"""

from __future__ import annotations

ARKLIGHT_CONFIG_PY = '''\
"""
ARKlight project configuration -- optional.

ARKlight works fine without this file; every section below is
commented out and only takes effect once you uncomment it. Full
reference: `arklight/config.py` in the ARKlight source (there is no
separate "Configuration" section in the README).

This file must be named exactly `arklight.config.py` and sit next to
`site.py` -- it is not searched for in parent directories, and other
names (`config.py`, `config.js`, `arklight.config.json`) are ignored.
Section and key names must match exactly: an unrecognized one prints a
build-time warning ("did you mean ...?") rather than silently doing
nothing, but is never rejected outright.
"""

CONFIG = {
    # Settings for `arklight live-streaming` (the dev server that
    # rebuilds and live-reloads on save). Only read when you use
    # `--subscribe`; irrelevant to a plain `arklight build`.
    # "live_streaming": {
    #     "host": "127.0.0.1",
    #     "port": 8347,          # int, 1-65535
    #     "poll_interval": 0.5,  # seconds between file checks
    # },

    # Force the Content-Security-Policy on/off for every build from
    # this project, regardless of what any individual `Site(strict_csp
    # =...)` says. `None` (the default) means "no override".
    # "csp": {"strict_csp": None},

    # Default build narration when no --verbose/--narrate flag is
    # passed: "plain", "verbose", or "narrate".
    # "rei": {"default_mode": "plain"},

    # Warnings about experimental APIs (docs/Foundational/
    # EXPERIMENTAL-APIS.md) -- silence them once you've made peace
    # with leaning on an escape hatch.
    # "experimental": {
    #     "heavy_reliance_nudge": True,
    #     "devtools_console_reminder": True,
    # },

    # `arklight android scaffold` app identity.
    # "android": {
    #     "app_name": "My App",
    #     "package_id": "com.example.myapp",
    #     "version_name": "1.0.0",
    #     "version_code": 1,
    #     "orientation": "portrait",
    # },

    # `arklight desktop scaffold` / `build` (Linux, GTK + WebKit).
    # "desktop": {
    #     "app_name": "My App",
    #     "app_id": "com.example.myapp",
    #     "width": 1024,
    #     "height": 768,
    # },
}
'''
