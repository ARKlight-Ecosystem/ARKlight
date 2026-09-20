# New JS Backend Proposal

## Overview

Proposal for a redesigned JS backend, prototyped against the same
`oop-blog/` sample app with a hand-cloned virtual DOM (snabbdom-style)
core. A competing no-vdom alternative was prototyped alongside it and
considered; the vdom direction was chosen and this folder now tracks
only the accepted direction.

**This is a working reference only, nothing more.** It exists to
support the design until the direction is fully implemented and the
comparison is captured elsewhere (`CHANGELOG.md`/`PROGRESS.md` or a
Foundational doc). Once that happens, this file has served its
purpose and will be removed — it is not meant to be kept as permanent
documentation.

## Index

| File | Covers |
| --- | --- |
| [`ARCHITECTURE-VDOM.md`](ARCHITECTURE-VDOM.md) | Proposal using a hand-cloned snabbdom (virtual DOM) core -- the chosen direction. |
