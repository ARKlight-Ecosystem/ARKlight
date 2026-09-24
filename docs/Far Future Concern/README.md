# Far Future Concern

## Overview

Speculative/backlog material that isn't a near-term priority: two
backends (KaiOS, Windows Phone) and one post-`v1.0` data-service idea
designated `v1.2`. Kept around in case the project picks them up
later, not because work on them is active now.

**These are working references only, nothing more.** Each file exists
to hold design thinking for something that may or may not ever be
built. If an item here is picked up, its doc graduates into an
active working reference (and eventually into the permanent record
once shipped); if not, it's cleared out once it no longer reflects a
concern worth tracking. Either way, nothing in this folder is meant to
be kept indefinitely as-is.

## Index

| File | Covers |
| --- | --- |
| [`KAIOS-BACKEND-IMPLEMENTATION.md`](KAIOS-BACKEND-IMPLEMENTATION.md) | Staged implementation plan for a potential KaiOS packaging backend. |
| [`kaios-app-design-doc.md`](kaios-app-design-doc.md) | Systems-level design doc for building real applications on KaiOS. |
| [`WINDOWS-PHONE-BACKEND.md`](WINDOWS-PHONE-BACKEND.md) | Notes on a (very) speculative Windows Phone backend. |
| [`POCKETBASE-REIMPLEMENTATION-PROPOSAL.md`](POCKETBASE-REIMPLEMENTATION-PROPOSAL.md) | Proposal, designated `v1.2` (after `v1.0` ships), for a PocketBase-shaped, standard-library-only data service -- collections, records API, auth, files, realtime, admin -- whose *definition* layer is authorable in Python or Rei with identical meaning. Records the 57,000-line scale of the target, the client-side fetch gap that blocks the beginner story, and which Provider scope lines acceptance would have to amend. **Not accepted, holds no version slot.** |
