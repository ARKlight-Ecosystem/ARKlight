"""
Reference ELIZA implementation -- STUDY MATERIAL ONLY.

Vendored per `docs/Foundational/DESIGN-NOTES.md` ("Design record: Rei
compiler narrator") §4:
read as a
design reference for how a minimal keyword/pattern -> templated-
response engine (Joseph Weizenbaum's 1966 ELIZA, in its classic
DOCTOR-script shape) is structured, then set aside. This file is
**not imported by any shipping `arklight/` code** -- `arklight`'s
actual compiler narrator (`arklight.compiler.rei`) is an original
implementation purpose-built for structured compiler stage events
(fixed-format strings with named groups), not free conversational
text, and does not reuse anything from this file.

This is an original, from-scratch reimplementation of the publicly
documented ELIZA algorithm (decomposition/reassembly rules keyed by
keyword, plus pronoun-swapping reflection), written for this repo --
not a copy of Weizenbaum's original MAD-SLIP source or of any other
project's ELIZA port. Kept deliberately small: enough to see the
technique's shape (a keyword table, a decomposition regex per
keyword, a set of reassembly templates cycled deterministically, and
a reflection step for "I"/"you" swaps), not a faithful, complete
DOCTOR script.

Run standalone for a quick look: `python eliza.py`. Not a dependency
of anything -- safe to delete, and deliberately kept out of
`arklight/`'s own package tree.
"""

from __future__ import annotations

import re

# "Reflection" swaps first- and second-person language when a
# fragment of the user's own sentence is echoed back inside a reply
# template (e.g. "I am tired" -> "you are tired" gets embedded in
# "How long have you been tired?"). Order matters: longer phrases
# first, so "yourself" doesn't get partially eaten by an "your" rule.
_REFLECTIONS: tuple[tuple[str, str], ...] = (
    ("yourself", "myself"),
    ("myself", "yourself"),
    ("your", "my"),
    ("my", "your"),
    ("you're", "I am"),
    ("i'm", "you are"),
    ("you", "I"),
    ("i", "you"),
    ("were", "was"),
    ("was", "were"),
    ("me", "you"),
)


def _reflect(fragment: str) -> str:
    words = fragment.lower().split()
    swapped = [dict(_REFLECTIONS).get(word, word) for word in words]
    return " ".join(swapped)


# keyword -> (decomposition regex, [reassembly templates, cycled in
# order]). `{0}` in a template is replaced by the reflected remainder
# the regex captured. This is the entire technique: no understanding,
# just "does this keyword appear, and if so, which canned shape of
# reply fits the fragment around it."
_SCRIPT: dict[str, tuple[re.Pattern[str], list[str]]] = {
    "i need": (re.compile(r"i need (.*)", re.I), ["Why do you need {0}?", "Would getting {0} really help you?"]),
    "i am": (re.compile(r"i am (.*)", re.I), ["How long have you been {0}?", "Why do you say you are {0}?"]),
    "i feel": (re.compile(r"i feel (.*)", re.I), ["Do you often feel {0}?", "What makes you feel {0}?"]),
    "because": (re.compile(r"because (.*)", re.I), ["Is that the real reason?", "Does {0} explain anything else?"]),
    "sorry": (re.compile(r"sorry(.*)", re.I), ["No need to apologize.", "Apologies aren't necessary."]),
}

_DEFAULT_REPLIES = ["Tell me more about that.", "Why do you say that?", "Go on."]


def respond(text: str, *, _counters: dict[str, int] = {}) -> str:  # noqa: B006 -- intentional, see below
    """One reply for one line of input. `_counters` is a deliberately
    mutable default (keyed per-keyword) purely so this toy driver
    cycles through a keyword's templates across a session instead of
    always giving the first one -- fine for a ~40-line study script
    that's never imported, not a pattern to copy into real code.
    """
    lowered = text.lower()
    for keyword, (pattern, templates) in _SCRIPT.items():
        if keyword in lowered:
            match = pattern.search(lowered)
            fragment = _reflect(match.group(1)) if match and match.groups() else ""
            i = _counters.get(keyword, 0)
            _counters[keyword] = i + 1
            return templates[i % len(templates)].format(fragment)
    i = _counters.get("_default", 0)
    _counters["_default"] = i + 1
    return _DEFAULT_REPLIES[i % len(_DEFAULT_REPLIES)]


def _main() -> None:  # pragma: no cover -- manual/interactive only
    print("eliza (reference only, not used by arklight): 'quit' to exit")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if line.strip().lower() in {"quit", "exit"}:
            break
        print(respond(line))


if __name__ == "__main__":  # pragma: no cover
    _main()
