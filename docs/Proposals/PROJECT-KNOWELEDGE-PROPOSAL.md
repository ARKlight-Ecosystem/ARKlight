# `Project Knowledge`: Persistent Compiler Context via `.arklight/`

## Status

**Proposal — not yet accepted, not yet staged.** Follows the format and
conventions of the existing proposal documents under
`docs/Proposals/`.

**Origin:** ARKlight already operates on substantially more context than
the contents of a single Python source file: the project tree,
configuration, dependencies, filesystem state, and compiler state all
participate in compilation. A Git checkout contains another useful layer
of locally available project information inside `.git/`, but ARKlight
currently has no compiler-owned place to retain the knowledge it can
derive from that information.

This proposal introduces a small, inspectable, compiler-owned directory:

```text
.arklight/
```

`.arklight/` is a persistent **Project Knowledge** surface for ARKlight.
It contains derived information that the compiler can write, read, and
update across builds.

Git is one source of knowledge for this system. It is not the purpose of
the feature and Git is not required for it to function.

The important distinction is:

> `.git/` tells ARKlight about repository state. `.arklight/` lets
> ARKlight remember what it learned and what it has observed while
> compiling the project.

This gives ARKlight a local, persistent project context without turning
it into a VCS, requiring a network connection, or introducing a database
as a prerequisite.

## TL;DR

Introduce `.arklight/` as ARKlight's own local knowledge directory.

The compiler may:

1. inspect available project context;
2. read Git metadata when `.git/` exists;
3. derive useful facts and observations;
4. persist selected information into `.arklight/`;
5. retrieve that information on later compiler runs.

Conceptually:

```text
             project
                │
       ┌────────┼─────────┐
       │        │         │
    source    config     .git/
       │        │         │
       └────────┼─────────┘
                │
                ▼
        Project Knowledge
                │
                ▼
            .arklight/
                │
                ▼
        subsequent builds
```

The first useful information could include:

- repository identity when Git is available;
- current revision and branch/ref;
- clean/dirty working-tree state;
- relevant changed paths;
- recent repository history;
- shallow-clone state;
- previous ARKlight build results;
- compiler version;
- discovered project/component information;
- previous diagnostics and observations.

The compiler can then use that context for:

- richer build logs;
- better diagnostics;
- last-known-good information;
- historical debugging;
- provenance;
- incremental-analysis groundwork;
- future compiler tooling.

`.arklight/` is **derived knowledge**, not a replacement for source,
configuration, or Git.

Deleting it must never make a project unbuildable.

---

## 1. Why ARKlight needs its own knowledge surface

A compiler normally sees the current project state.

That answers:

> What is here right now?

A repository can additionally answer:

> What was here before, what changed, and how did we get here?

ARKlight can answer another question:

> What has ARKlight itself already learned about this project?

Those are three different information sources.

```text
Current project
    ↓
What exists now?

Git
    ↓
What changed over time?

ARKlight
    ↓
What has the compiler observed about this project?
```

The missing piece is a place where the third category can persist.

`.arklight/` fills that gap.

This is deliberately not framed as "Git integration." Git is useful
because many projects already have `.git/` sitting in the project root,
containing valuable information that the compiler can consume without
network access or credentials.

But ARKlight's knowledge should outlive the presence of Git metadata.

For example:

```text
git clone ...
arklight build
```

can populate `.arklight/`.

Later:

```text
rm -rf .git
```

or:

```text
unzip project.zip
```

does not erase ARKlight's accumulated compiler knowledge.

The repository disappeared.

The compiler's observations did not.

---

## 2. `.arklight/` is compiler-owned state

The directory should be treated as an ARKlight-managed project-local
state directory.

Conceptually:

```text
project/
├── src/
├── arklight.config.py
├── .git/
└── .arklight/
```

The ownership boundary is:

```text
.git/
    owned by Git

source/
    owned by the project

configuration/
    owned by the project

.arklight/
    owned by ARKlight
```

ARKlight should never modify `.git/`.

Git should never be required to understand `.arklight/`.

`.arklight/` is where ARKlight stores **derived compiler knowledge**.

That means it should not become another source-of-truth for the project.

If it is deleted:

```bash
rm -rf .arklight
arklight build ...
```

the compiler may lose historical context, cached observations, or
diagnostic enrichment, but it must still be capable of discovering the
project again from its authoritative inputs.

The invariant is:

> `.arklight/` enriches project understanding; it does not define what
> the project is.

---

## 3. The knowledge model

The architecture should distinguish between **providers**, **facts**,
and **observations**.

```text
Knowledge Providers
       │
       ├── filesystem
       ├── project configuration
       ├── Git
       └── ARKlight's own history
       │
       ▼
     Facts
       │
       ▼
   Observations
       │
       ▼
    .arklight/
       │
       ▼
 future compiler runs
```

### 3.1 Providers

Providers answer questions using information already available to the
compiler.

The first providers can be:

```text
Filesystem
Project configuration
Git
ARKlight build state
```

Additional providers can be added later without changing the concept of
Project Knowledge.

### 3.2 Facts

Facts are information directly established by a provider.

For example:

```text
git.present = true
git.head = 8f31c2a
git.branch = alpha
git.dirty = true
git.shallow = false
```

Or:

```text
build.result = success
build.compiler_version = 0.4.0-alpha
```

Facts should be simple, explicit, and inspectable.

### 3.3 Observations

Observations are conclusions ARKlight derives from multiple facts.

For example:

```text
last_successful_revision = 71a8e4d
changed_since_last_success = [...]
current_state_reproducible = false
component_previously_resolved = true
```

These are not Git facts.

They are compiler knowledge.

Keeping facts and observations separate prevents provider-specific
details from becoming mysterious compiler behavior.

---

## 4. Proposed `.arklight/` structure

The exact file names should remain open during staging, but the initial
shape should favor simple text files over a mandatory database.

A possible layout:

```text
.arklight/
├── PROJECT
├── COMPILER
├── CONTEXT
├── BUILD
├── HISTORY
└── KNOWLEDGE/
    ├── COMPONENTS
    ├── DEPENDENCIES
    └── OBSERVATIONS
```

The format can remain intentionally boring.

For example:

```text
BUILD

last_result=success
last_revision=71a8e4d
last_timestamp=2026-09-16T18:42:11
compiler_version=0.4.0-alpha
```

Or:

```text
CONTEXT

repository.present=true
repository.root=.
git.head=8f31c2a
git.branch=alpha
git.dirty=true
git.shallow=false
```

The exact serialization format is an implementation decision.

The architectural requirement is:

> A developer should be able to open `.arklight/` with an ordinary text
> editor and understand what ARKlight knows.

No special database browser should be required merely to discover why
the compiler thinks something happened.

---

## 5. Why text files instead of SQLite

ARKlight already benefits from a philosophy of explicit, inspectable
state.

A text-based knowledge directory provides:

- easy inspection;
- easy debugging;
- easy deletion;
- simple corruption diagnosis;
- straightforward format versioning;
- no database dependency;
- compatibility with ordinary command-line tools;
- a clear relationship between stored information and compiler behavior.

SQLite may eventually be appropriate for a genuinely large queryable
history, but it should not be the default architectural assumption.

The first version should not turn:

```text
remember something about this project
```

into:

```text
introduce a database subsystem
```

That would be a remarkably elaborate solution to a directory.

If history eventually becomes large enough to justify indexing, that can
be staged separately without changing the Project Knowledge abstraction.

---

## 6. Git is an input, not a requirement

When `.git/` exists, ARKlight can use it as a knowledge provider.

Useful initial information includes:

### 6.1 Repository identity

- repository root;
- `HEAD`;
- current branch/ref;
- detached-HEAD state;
- commit identifier;
- nearest reachable tag where available;
- shallow-clone state.

### 6.2 Working-tree state

- clean/dirty state;
- staged changes;
- unstaged changes;
- untracked paths;
- relevant changed paths.

### 6.3 Temporal information

- recent commits;
- commit timestamps;
- parent relationships;
- recent `HEAD` movement from the reflog where available.

### 6.4 Change information

- changed paths;
- additions;
- deletions;
- renames;
- differences between useful revisions.

The provider should prefer stable Git command interfaces for repository
operations where practical instead of implementing Git's object database,
index, packfiles, and related plumbing inside ARKlight.

The point is to extract project knowledge.

The point is not to recreate Git in Python because apparently one version
control system was not enough.

---

## 7. `.arklight/` survives without Git

This is one of the central reasons for having a compiler-owned knowledge
directory.

Suppose the initial build occurs in a normal Git checkout:

```text
.git/
.arklight/
```

ARKlight observes:

```text
revision = abc123
branch = alpha
build = success
```

and persists useful information.

Later the same project is distributed without `.git/`:

```text
source/
config/
.arklight/
```

ARKlight can still retrieve:

```text
last known build
compiler observations
project metadata
previous diagnostics
```

Git-derived information can remain useful as **historical knowledge**,
even though Git is no longer available as a live provider.

The provider state and the stored knowledge therefore have different
lifetimes:

```text
.git/
    live repository state

.arklight/
    persisted ARKlight knowledge
```

This is a major architectural distinction.

---

## 8. Build history

The first genuinely compiler-specific information worth persisting is
ARKlight's own build history.

Git can tell ARKlight:

```text
commit = 8f31c2a
```

Git cannot tell ARKlight:

```text
ARKlight successfully compiled 8f31c2a yesterday.
```

Only ARKlight knows that.

A minimal record might be:

```text
revision=71a8e4d
result=success
timestamp=...
compiler_version=0.4.0-alpha
```

A later failure can therefore establish:

```text
current revision:
    8f31c2a

last successful ARKlight build:
    71a8e4d
```

If Git is currently available, ARKlight can then inspect the changes
between those states.

This creates a useful relationship:

```text
Git revision
     │
     ▼
source changes
     │
     ▼
ARKlight build
     │
     ▼
success / failure
```

The relationship is more valuable than any individual piece of metadata.

---

## 9. Last-known-good diagnostics

One of the first compelling uses of `.arklight/` would be historical
diagnostic context.

Instead of:

```text
ERROR: component `NavBar` could not be resolved
```

ARKlight could eventually report:

```text
ERROR: component `NavBar` could not be resolved.

Current project state:
  revision: 8f31c2a
  working tree: dirty

Last successful ARKlight build:
  revision: 71a8e4d

Source paths changed since that build:
  components/nav.py
  pages/index.py
```

This does not claim that `components/nav.py` caused the failure.

It simply exposes the evidence ARKlight has.

That distinction is important.

The compiler should help someone investigate the failure, not invent a
causal story because three filenames happened to change.

---

## 10. Historical build knowledge

With multiple records, ARKlight can observe transitions such as:

```text
71a8e4d  success
75bc912  success
7e31a44  failure
8f31c2a  failure
```

This allows derived observations such as:

```text
last_known_good = 75bc912
first_recorded_failure = 7e31a44
```

The compiler can then inspect repository changes around that boundary.

This creates a deterministic historical debugging surface:

```text
What is wrong?
    current diagnostics

When did it start failing?
    build history

What changed around then?
    repository history

Did ARKlight previously build this state?
    .arklight/ build history
```

No network service or AI system is necessary.

The compiler simply remembers its own observations.

---

## 11. Compiler logs

Project Knowledge should appear in logs as compact context rather than
dumping repository internals into every build.

For example:

```text
ARKlight build
  entry: pages/index.py
  revision: 8f31c2a
  branch: alpha
  working tree: dirty

[1/5] Discovering components
[2/5] Executing ARK AST
[3/5] Normalizing IR
[4/5] Validating
ERROR: unresolved component `NavBar`

Context:
  last successful build: 71a8e4d
  changed since last success:
    components/nav.py
    pages/index.py
```

Normal logs should remain concise.

Verbose/debug output can expose the complete available knowledge context.

This keeps the feature useful without turning every compilation into a
Git archaeology expedition.

---

## 12. Interaction with the compiler pipeline

Project Knowledge should be established during project discovery and
made available through compiler context.

Conceptually:

```text
Python Source
      │
      ▼
Project discovery
      │
      ├── filesystem knowledge
      ├── configuration knowledge
      ├── Git knowledge
      └── persisted .arklight knowledge
      │
      ▼
Python AST static discovery
      │
      ▼
ARK AST execution
      │
      ▼
Normalization
      │
      ▼
Validation
      │
      ▼
Website IR
      │
      ▼
HTML / CSS / JS backends
```

Project Knowledge should not be threaded through every compiler phase
merely because it exists.

A phase consumes a fact only when it has a legitimate reason to use it.

For example:

```text
diagnostics       -> repository + build history
build reports     -> repository + compiler state
incremental work  -> changed paths
normalization     -> no repository dependency
HTML backend      -> no repository dependency
```

This prevents repository awareness from contaminating otherwise pure
compiler stages.

---

## 13. Build-output boundaries

`.arklight/` must not silently turn repository metadata into generated
website output.

By default:

```text
same source + same configuration
    => same generated output
```

should remain true regardless of whether `.git/` exists.

Project Knowledge primarily affects:

- diagnostics;
- logs;
- debug reports;
- compiler history;
- optional provenance;
- future incremental analysis.

If repository or compiler metadata is ever embedded into generated
HTML/CSS/JS, that should be an explicit feature.

Repository awareness should not become an accidental compilation input.

---

## 14. `.arklight/` should be safe to delete

A core invariant:

```bash
rm -rf .arklight
```

must not destroy the project.

After deletion, ARKlight may lose:

- build history;
- historical observations;
- cached project knowledge;
- previous diagnostics;
- repository-derived context that cannot be reconstructed.

But it must be able to rediscover the project from its authoritative
inputs.

The next build can reconstruct available knowledge:

```text
source
config
.git/
   ↓
Project Knowledge
   ↓
new .arklight/
```

If `.git/` is also absent:

```text
source
config
   ↓
Project Knowledge
   ↓
new .arklight/
```

with less historical information.

This gives `.arklight/` a clean role:

> Persistent enhancement, never persistent dependency.

---

## 15. Git metadata should not be copied wholesale

`.arklight/` should contain **derived information**, not a second
repository.

It should not copy:

```text
.git/objects/
.git/refs/
.git/index
.git/logs/
```

into its own storage.

Instead:

```text
.git/
    provider

ARKlight knowledge
    derived representation
```

For example, rather than storing an entire Git history, ARKlight might
store:

```text
last_successful_revision=71a8e4d
```

and retrieve the relevant Git history when Git is available.

If Git later disappears, the stored revision remains useful as an
identity and historical reference even if the complete diff can no
longer be reconstructed.

This keeps `.arklight/` small and prevents it from becoming a shadow
repository.

---

## 16. Privacy and information boundaries

`.arklight/` is local project state and can contain information about the
project.

The first implementation should therefore avoid collecting more than it
needs.

In particular:

- no network access;
- no GitHub API calls;
- no remote repository access;
- no source-file copies;
- no environment-variable dumps;
- no secrets;
- no repository object copies;
- no remote URLs in ordinary logs or stored knowledge unless explicitly
  required.

Repository remote information can be useful for identifying a project,
but remote URLs may contain private hostnames or other sensitive
information.

The initial design should therefore treat remote metadata as optional
and privacy-sensitive.

---

## 17. Versioning the knowledge format

Because `.arklight/` persists across compiler runs, the stored format
will eventually outlive the compiler version that created it.

The directory therefore needs a small format/version marker.

For example:

```text
PROJECT

knowledge_format=1
```

A future compiler can then determine whether an existing knowledge file
is:

- current;
- readable but outdated;
- incompatible;
- safely regeneratable.

The preferred recovery path for stale knowledge should be regeneration,
not a complicated migration framework.

Since `.arklight/` is derived state, rebuilding it is always an available
escape hatch.

---

## 18. Scope

### In scope (this proposal)

- `.arklight/` as an ARKlight-owned project-local knowledge directory.
- A `Project Knowledge` concept in the compiler architecture.
- Read-only project-context discovery.
- Git as the first external knowledge provider.
- Persistence of derived compiler knowledge.
- Plain-text, inspectable knowledge files as the initial storage model.
- Compiler-owned build history.
- Historical build observations.
- Repository-derived context for diagnostics and logs.
- Safe behavior when `.git/` is absent.
- Safe deletion and regeneration of `.arklight/`.
- Clear separation between authoritative project inputs and derived
  ARKlight knowledge.
- Privacy boundaries around stored repository information.

### Explicitly out of scope for this proposal

- Implementing Git or a Git-compatible VCS inside ARKlight.
- Creating commits, branches, tags, merges, rebases, or other VCS
  operations.
- Modifying `.git/`.
- GitHub API integration.
- Remote repository access.
- Authentication.
- Replacing Git tooling.
- Making Git mandatory for ARKlight builds.
- Copying `.git/` into `.arklight/`.
- Making `.arklight/` authoritative for source or project configuration.
- Making generated HTML/CSS/JS depend on Git state by default.
- Requiring a database for Project Knowledge.
- AI-generated diagnostics or an LLM dependency.
- Full incremental compilation.
- Full dependency-graph analysis.
- Automatic rollback or source recovery.
- Automatic project repair.

---

## 19. Suggested order

1. **`.arklight/` foundation**
   - Detect or create the directory.
   - Establish a minimal knowledge-format marker.
   - Provide safe read/write helpers.
   - Keep the format human-readable.

2. **Project Knowledge context**
   - Introduce the internal abstraction.
   - Separate providers, facts, and observations.
   - Make knowledge available through compiler context.

3. **Git provider**
   - Detect `.git/`.
   - Read repository identity.
   - Read working-tree state.
   - Gracefully report unavailable Git state.

4. **Persistent project context**
   - Write useful derived Git facts into `.arklight/`.
   - Preserve them when `.git/` is later unavailable.
   - Avoid copying repository internals.

5. **Compiler build history**
   - Record build results.
   - Associate results with available source/repository identity.
   - Store compiler version and timestamp.

6. **Diagnostics integration**
   - Surface compact project knowledge in useful compiler errors.
   - Add last-known-good information where available.
   - Keep verbose knowledge behind explicit debug output.

7. **Historical observations**
   - Compare known build states.
   - Identify last successful and first recorded failing states.
   - Correlate repository changes with build transitions.

8. **Future knowledge providers**
   - Add only when a concrete compiler feature needs them.
   - Do not create providers merely to populate `.arklight/`.

Each stage should remain useful without requiring every later stage.

---

## 20. Open questions for a maintainer

- What exact `.arklight/` file structure best fits ARKlight's existing
  conventions?
- Should `.arklight/` be automatically added to `.gitignore` when
  ARKlight creates it, or should the project explicitly choose that?
- Should all `.arklight/` files be ignored by default, or should some
  project-facing knowledge be intentionally committable?
- Which information is safe and useful in ordinary logs?
- Which information belongs only in verbose/debug output?
- Should `.arklight/` be created automatically on every build, or only
  when a feature actually needs persistent knowledge?
- What is the minimal knowledge-format versioning scheme?
- Should the first implementation use one file per category or one
  structured text file with sections?
- How should dirty working trees be represented when correlating a build
  with a Git revision?
- Should a build with uncommitted changes record the revision alone,
  revision plus a dirty marker, or a stronger working-tree identity?
- How much reflog information is useful before the stored knowledge
  becomes unnecessarily historical?
- How should shallow clones affect historical observations?
- Should remote repository information ever be persisted?
- What is the right retention policy for build history?
- Should old observations be pruned automatically, or should retention
  remain explicit?
- Should `.arklight/` be project-local only, or should there eventually
  be a separate user-level ARKlight knowledge store?
- Which future compiler feature should be the first consumer of
  persistent Project Knowledge beyond diagnostics?

---

## 21. Design principles

### 21.1 `.git/` is a knowledge source

Git provides useful context when it exists.

ARKlight does not become a VCS.

### 21.2 `.arklight/` is compiler-owned

ARKlight gets its own place to persist observations and derived project
knowledge.

### 21.3 Derived state must remain disposable

Deleting `.arklight/` may erase knowledge, but it must not erase the
ability to build the project.

### 21.4 Facts first, observations second

Provider facts should remain distinguishable from compiler-derived
interpretations.

### 21.5 Read what already exists

The feature should exploit project information that is already available
rather than rebuilding infrastructure unnecessarily.

### 21.6 No network required

The initial system should work entirely from local project state.

### 21.7 Inspectability matters

A developer should be able to open `.arklight/` and understand what the
compiler has stored.

### 21.8 Persistence must have a purpose

ARKlight should not collect information merely because it can.

Every stored fact should support an actual compiler or developer-facing
use case.

### 21.9 Knowledge should not silently affect output

Project context should enrich the compiler's understanding without
secretly changing generated website output.

### 21.10 The compiler should remember its own work

Git knows about repository history.

ARKlight should know about **ARKlight's history with the project**.

That is the part `.git/` cannot provide.

---

## 22. The larger direction

The immediate feature is small:

```text
.git/
   │
   ▼
Project Knowledge
   │
   ▼
.arklight/
   │
   ▼
better diagnostics and future compiler tooling
```

But the architecture creates a new dimension for ARKlight.

The compiler can eventually know:

```text
current source
      +
configuration
      +
filesystem
      +
repository state
      +
previous compiler observations
      +
build history
      +
compiler state
```

That makes questions like these possible:

```text
What failed?
When did it start failing?
What changed since it last worked?
Has ARKlight successfully compiled this project state before?
What did the compiler previously discover?
What project state produced this artifact?
What information is missing because the checkout is shallow?
```

The important part is that none of this requires ARKlight to become a
version-control system.

And none of it requires a network service.

The compiler simply gains a place to remember what it already knows.

`.git/` gives ARKlight historical context when available.

`.arklight/` gives ARKlight **memory of its own observations**.

That is the purpose of Project Knowledge.
