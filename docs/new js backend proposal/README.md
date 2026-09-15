# New JS Backend Proposal

## Overview

Competing proposals for a redesigned JS backend, prototyped against
the same `oop-blog/` sample app: one with a hand-cloned virtual DOM
(snabbdom-style), one without.

**These are working references only, nothing more.** They exist to
support a decision that hasn't been made yet. Once one direction is
chosen and implemented (or the comparison is otherwise resolved and
recorded), these files have served their purpose and will be removed
— they are not meant to be kept as permanent documentation.

## Index

| File | Covers |
| --- | --- |
| [`ARCHITECTURE-VDOM.md`](ARCHITECTURE-VDOM.md) | Proposal using a hand-cloned snabbdom (virtual DOM) core. |
| [`ARCHITECTURE no vdom.md`](<ARCHITECTURE no vdom.md>) | Alternative proposal with no virtual DOM — direct node patching. |
