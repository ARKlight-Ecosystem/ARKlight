# Version history

## Overview

ARKlight's version history used to live as two files at the repo
root (`CHANGELOG.md`, `PROGRESS.md`), alongside `README.md` and the
`docs/` tree proper. As the project has grown, that made the repo
root noisier than it needed to be for something a typical user never
opens. Both files now live here instead:

| File | Covers |
| --- | --- |
| [`CHANGELOG.md`](./CHANGELOG.md) | The plain, Keep-a-Changelog-style version log -- what shipped in each version, grouped by milestone. |
| [`PROGRESS.md`](./PROGRESS.md) | The narrative record: what was tried, what was rejected, what broke, kept in reverse-chronological order. The snapshot table at its top is the fastest way to see what's DONE / IN PROGRESS / PLANNED right now. |

For the architecture-level roadmap (the numbered `v0.0xx` milestone
table itself, independent of what's landed so far), see
[`docs/Foundational/ARCHITECTURE.md`](../Foundational/ARCHITECTURE.md).

## Index

- [`CHANGELOG.md`](./CHANGELOG.md)
- [`PROGRESS.md`](./PROGRESS.md)

## Future direction

Both files are still single, ever-growing documents today. The
intent going forward is for each new version to get its own short
doc in this directory instead -- an overview of that version's
feature set and any other information worth calling out -- so that
`CHANGELOG.md`/`PROGRESS.md` stop accumulating unbounded detail per
entry. This README will keep acting as the overview and index for
whatever shape that takes; nothing has been split out yet, so for
now the two files above remain the complete, canonical record.
