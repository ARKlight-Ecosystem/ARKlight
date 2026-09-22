# Far Future Concern

## Overview

Speculative/backlog material for backends that aren't a near-term
priority (KaiOS, Windows Phone). Kept around in case the project
picks them up later, not because work on them is active now.

**These are working references only, nothing more.** Each file exists
to hold design thinking for a backend that may or may not ever be
built. If a backend here is picked up, its doc graduates into an
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
| [`AVM-WASM-SANDBOX-PROPOSAL..md`](<AVM-WASM-SANDBOX-PROPOSAL..md>) | Not accepted, filed for maintainer review: a curated-package WebAssembly sandbox ("AVM") that would let ARKlight consume existing JavaScript libraries, from a maintainer-curated catalog only, in isolated, discardable WASM sandboxes -- without ever exposing JavaScript or npm to the site author. Requests no version slot; its own ladder uses placeholder `A0`-`A6` labels pending acceptance. |
