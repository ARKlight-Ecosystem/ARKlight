<table width="100%">
<tr>
<td width="180" valign="middle" align="center">

<img src="ARKlight-logo.png" alt="Rei" width="160" height="160">

</td>
<td valign="middle">
<div align="center">

# ARKlight Compiler Framework

**A Python-first compiler for building static websites where developers work
with a structured component API, while the output remains ordinary, dependency-free `Hyper Text Markup Language` `Casscading Style Sheets` `JavaScript`.**

</div>
</td>
</tr>
</table>

Write your site in Python. ARKlight compiles it to standard HTML with CSS and
vanilla JavaScript. The browser never executes Python — you get predictable,
inspectable, portable output that works anywhere static files are hosted.

No Python runtime in production. No framework bloat. Just Python ergonomics at
authorship time, and clean web artifacts at deployment time.

## New here?

If you're new to ARKlight or evaluating whether it fits your needs, start with the
documentation in this order:

1. **[The Pitch](docs/Foundational/PITCH.md)** — the problem ARKlight is trying to solve,
   its intended use, and the larger idea behind the project.

2. **[What is ARKlight?](docs/Foundational/WHAT-ARKLIGHT-IS.md)** — a concise
   explanation of what ARKlight is, how it works, and what it currently provides.

3. **[Foundational Documentation](docs/Foundational/)** — the deeper technical
   documentation covering ARKlight's architecture, compiler model, capabilities,
   design decisions, limitations, and roadmap.

Start with the pitch if you want to understand the *why*. Read *What is ARKlight?*
for the practical picture. If you're still interested, the foundational
documentation is the place to understand ARKlight in enough depth to decide
whether it fits your project.

## Status

```text
[Rei] Hey just a heads-up from the maintained.
[Rei] ARKlight is tool He has been working on
[Rei] for a while, personal reasons. It's
[Rei] clearly not ready for anything involving
[Rei] ⚠️ Production and until the compiler
[Rei] reaches a stable stage. ARKlight is only recommended
[Rei] for informal, personal, hobby projects.
[Rei] So if there's an audience waiting for it?
[Rei] Showing their support (eg: Stars, Forks, and such?)
[Rei] it motivates him. 
```

ARKlight is in active alpha development. Status lives in exactly one
place per kind of record: [`CHANGELOG.md`](CHANGELOG.md) for version
history, [`PROGRESS.md`](PROGRESS.md) for the current snapshot and
what's next, and [`docs/Foundational/ARCHITECTURE.md`](docs/Foundational/ARCHITECTURE.md)
for the milestone roadmap.

Refer to [`docs/Foundational/EXPERIMENTAL-APIS.md`](./docs/Foundational/EXPERIMENTAL-APIS.md) if you wished to use escape hatches.

## Install

```bash
pip install -e .
```

A runnable example, the Debian/Ubuntu package, upgrading an existing
checkout, and everything else needed to get running:
[`docs/Foundational/GETTING-STARTED.md`](docs/Foundational/GETTING-STARTED.md).

## Documentation

Everything else -- the CLI, the compiler pipeline, the full authoring
API, the repository layout, running the tests, non-goals, backends,
proposals, and version history -- is rooted in
[`docs/README.md`](docs/README.md). It is the single index for all of
it, so it's the only place documentation can go stale, and the only
place you need to check.

If you found a bug or have a question, please open an issue.
