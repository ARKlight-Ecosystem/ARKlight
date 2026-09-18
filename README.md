# <img src="ARKlight-logo.png" alt="ARKlight logo" width="40" height="40" align="middle"> ARKlight Framework

**A Python-first compiler for building static websites where developers work
with a structured component API, while the output remains ordinary, dependency-free HTML.**

Write your site in Python. ARKlight compiles it to standard HTML with CSS and
vanilla JavaScript. The browser never executes Python — you get predictable,
inspectable, portable output that works anywhere static files are hosted.

No Python runtime in production. No framework bloat. Just Python ergonomics at
authorship time, and clean web artifacts at deployment time.

## Install

```bash
pip install -e .
```

A runnable example, the Debian/Ubuntu package, upgrading an existing
checkout, and everything else needed to get running:
[`docs/Foundational/GETTING-STARTED.md`](docs/Foundational/GETTING-STARTED.md).

## Status

ARKlight is in active alpha development. Status lives in exactly one
place per kind of record: [`CHANGELOG.md`](CHANGELOG.md) for version
history, [`PROGRESS.md`](PROGRESS.md) for the current snapshot and
what's next, and [`docs/Foundational/ARCHITECTURE.md`](docs/Foundational/ARCHITECTURE.md)
for the milestone roadmap.

## Documentation

Everything else -- the CLI, the compiler pipeline, the full authoring
API, the repository layout, running the tests, non-goals, backends,
proposals, and version history -- is rooted in
[`docs/README.md`](docs/README.md). It is the single index for all of
it, so it's the only place documentation can go stale, and the only
place you need to check.

If you found a bug or have a question, please open an issue.
