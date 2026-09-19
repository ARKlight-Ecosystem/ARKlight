# Bug fix: `trusted_script_origins` CSP directive injection

## Status

Implemented, alpha. Out-of-band, numbered bug fix per
`docs/Foundational/V1-DEFINITION.md`'s "Issue triage during Alpha"
section -- a broken contract, not a missing feature, so it doesn't
wait for whichever milestone is already in flight.

## The broken contract

`arklight/backend/html/csp.py` exists to give every ARKlight-built
site a strict `script-src` -- no `'unsafe-eval'`, no `'unsafe-inline'`
-- and says so directly, twice: in the module's own docstring, and
again in `arklight/api.py`'s `Site.__init__`, where the comment above
`trusted_script_origins` states "there's no kwarg that reintroduces
`'unsafe-eval'` or `'unsafe-inline'`."

That promise wasn't kept. `_render_csp_meta_tag` (`csp.py`) splices
every `trusted_script_origins` entry verbatim, space-separated,
straight into the `script-src` directive's value. The only validation
`Site.__init__` did (`api.py`) was "non-empty string" -- nothing
checked *what* the string contained. Two ways that let the promise
break, both confirmed with a direct repro against `_render_csp_meta_tag`
before the fix:

- `Site(trusted_script_origins=["'unsafe-inline'"])` put
  `'unsafe-inline'` straight into `script-src`, silently undoing the
  entire guarantee this module exists to provide.
- `Site(trusted_script_origins=["https://cdn.example.com; frame-ancestors *"])`
  used the `;` to close `script-src` early and open a brand-new
  `frame-ancestors` directive -- a directive this kwarg was never
  supposed to be able to add at all.

## Stage 1 -- root cause + fix (this patch)

`Site.__init__` (`arklight/api.py`) now rejects, at `Site()`
construction, any `trusted_script_origins` entry that:

- contains whitespace or a `;` (either splits one entry into what
  renders as multiple `script-src` sources, or terminates the
  directive early and injects an unrelated one), or
- is `'unsafe-inline'`/`'unsafe-eval'` (quoted or not), the two
  keywords this kwarg's own documented contract says can never reach
  `script-src`.

This is a build-time `ValueError`, per this project's fails-loudly-at-
build-time-or-not-at-all rule (`docs/README.md`'s Philosophy section)
-- the bad value is caught at `Site()` construction, not discovered
later as a weakened policy in a real browser. `csp.py` itself is
unchanged: the fix is entirely "never let a bad value reach it" rather
than "sanitize it on the way out," so every existing caller that only
ever passed clean origins sees no behavior change.

## Stage 2 -- regression tests (this patch)

`tests/test_csp.py` gained five tests: the two injection repros above,
a bare-whitespace two-origins-in-one-string case, and a
same-list-of-clean-origins case confirming the fix doesn't reject
anything legitimate. Full suite: 1502 -> 1507 passing, no existing
test's behavior changed.

## Stage 3 -- changelog / version-history entry

Not included in this patch -- left for whoever cuts the next numbered
release to fold in alongside its own entry, per this project's
one-entry-per-shipped-version convention (`docs/version history/`,
`CHANGELOG.md`).
