"""
`highlightActiveNavLink`: adds `is-active` to any `.nav a` whose
resolved URL matches the current page. Runs unconditionally (every
site with a `nav()` gets this for free), independent of whether the
page declares `State(...)`.

Split out of `arklight/backend/js/render.py`'s old
`_NAV_HIGHLIGHT_JS` constant (`refactor-0`). Pure move, no JS output
change.
"""

from __future__ import annotations

NAV_HIGHLIGHT_JS = """  function highlightActiveNavLink() {
    document.querySelectorAll(".nav a").forEach(function (link) {
      // `/` and `/index.html` are the same page: compare both with the
      // fragment and a trailing "index.html" stripped, so a nav link
      // built as ".../index.html" (the compiler rewrites internal
      // links that way) is still highlighted when the visited URL is
      // the bare directory root.
      var here = location.href.replace(/#.*$/, "").replace(/index\\.html$/, "");
      var there = link.href.replace(/#.*$/, "").replace(/index\\.html$/, "");
      if (there === here) {
        link.classList.add("is-active");
      }
    });
  }"""
