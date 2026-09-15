# Picked up automatically by `arklight desktop scaffold` (it looks
# for this file next to the `-o build` output directory the README's
# commands use, i.e. right here) -- see arklight/config.py's
# `load_config` and `arklight.cli.desktop`'s own `_DEFAULTS`. Without
# this file, `arklight desktop scaffold` still works, it just falls
# back to the generic "ARKlight App" / "arklight-app" identity those
# defaults describe.
CONFIG = {
    "desktop": {
        "app_name": "Hello Desktop",
        "app_id": "com.arklight.hello_desktop",
    },
}
