# Rei Language (RS1): A Java-Syntax Source Language for ARKlight

## Status

**Not accepted. Filed for maintainer review.** Belongs in `docs/Proposals/`.
If accepted it would be a **second authoring frontend** for ARKlight. Python
stays the reference frontend; nothing here replaces it.

**Version-number note.** No slot is requested. `v0.079` is held by Miko Stage A
and `v0.080` by the Android backend. The ladder in section 11 uses `R0`-`R6` and
receives real versions only if a maintainer accepts it. "RS1" means **Rei Script,
language level 1**: the first frozen surface of the language, not a compiler
version.

**Origin:** an `index.rei` mock plus direction from the author. The direction
that shaped this document, in the author's words as closely as they can be
paraphrased: Rei is its own language, not Python and not HTML in a different
shape; it uses basic Java syntax (classes and OOP, no annotations); input and
output follow the Java way, with `index.out` a printer that has many methods
(`println` is one, `heading` is another, and so on); HTML is abstracted away;
JavaScript is "just a function"; UI, CSS and scripts are Kotlin-inspired; and
source flows `.rei` files -> Rei AST -> ARK AST -> the existing ARKlight
pipeline.

Read against `PITCH.md`, `WHAT-ARKLIGHT-IS.md`, `ARCHITECTURE.md`,
`SYSTEM-DESIGN-AGREEMENTS.md`, `AUTHORING-GUIDE.md`, `arklight/ast/nodes.py`,
`arklight/parser/loader.py`, `arklight/compiler/pipeline.py` and
`arklight/ir/schema.py` on `alpha` (commit `409af0c`).

## TL;DR

ARKlight already has a small, closed, checkable vocabulary and a compiler that
owns everything after the ARK AST. What it lacks is a way to author it that is
not Python. RS1 is a Java-family language whose semantics are ARKlight's, not
the DOM's:

- **Fields are state, methods are actions, getters are derivations.** A field
  on a page class lowers to `State(...)`; a method that changes fields lowers to
  the closed `Action.*` vocabulary; an expression over fields lowers to
  `Derive.*` / `Predicate.*`.
- **Output is a stream.** A page writes itself through `out`, the way a Java
  program writes to `System.out`. There is no node tree in the author's hands.
- **"JS is just a function" is a compiler contract.** A method that runs in the
  browser must fit the closed vocabulary. If it does, it lowers; if it does not,
  the build fails with a message that says which rule it broke.
- **The compiler never executes author code.** The Python frontend runs the
  author's module with `exec` (`arklight/parser/loader.py`). A `.rei` file is
  only ever parsed, checked and lowered.

```text
 index.rei ─▶ lexer ─▶ parser ─▶ Rei AST ─▶ check ─▶ lower ─▶ ARK AST (+ Site registrations)
   (source)                        │           │                    │
                                   │           │                    └▶ normalize ─▶ validate ─▶ IR ─▶ backends
                                   │           └ names, types, phase, "is it in the vocabulary?"
                                   └ what the author wrote, with spans
```

Everything to the right of "ARK AST" is the existing pipeline, unchanged.

## 1. What is decided and what is proposed

| Item | Source |
|---|---|
| Separate language; not Python; not HTML reshaped | Author |
| Basic Java syntax, classes and OOP, **no annotations** | Author |
| Java-way I/O; `out` is a printer with many methods (`println`, `heading`, ...) | Author |
| HTML abstracted away; JS is "just a function" | Author |
| UI, CSS and scripts are Kotlin-inspired | Author (exact meaning: see Q3) |
| Pipeline `.rei` -> Rei AST -> ARK AST -> existing pipeline | Author |
| Route comes from the filename (`index.rei` is `/`); `import stdlib.ARKlight;` | Author's mock |
| Everything else: phase model, lowering table, type system, package layout, ladder | **This proposal** |

The proposal tries to be strict about that line. Sections 4-9 are design
suggestions, not settled facts.

## 2. Why "HTML in a different shape" is the risk

The pasted mock is Java-flavored, but several of its constructs are HTML
concepts wearing Java syntax:

| In the mock | What it really is | RS1 replacement |
|---|---|---|
| `new Container(new Link(...), new Link(...))` returned as a `Node` | A DOM tree built with constructors | `out` calls in order; no tree value the author holds |
| `.target("#more-details")` | A CSS selector string aimed at another element | A method reference on the same class: `this::toggleDetails` |
| `.toggleClass("hidden")` | Behavior expressed as a CSS class flip | A boolean field and an `if` that shows or hides content |
| `.className("nav")` | A CSS class name as a string | A named style resolved by the compiler |
| `Map.of("padding", "16px", ":hover:background", ...)` | CSS property strings in a map | Typed style assignments (section 8) |

None of these is wrong for the Python frontend, where the vocabulary is exactly
this. They are wrong for a language whose point is to have its own model. The
test applied throughout this proposal: **if a construct only makes sense
because HTML has it, it does not belong in RS1.**

## 3. Pipeline and integration

### 3.1 Where it plugs in

Today `arklight/compiler/pipeline.py` calls `load_site(entry_path)` and receives
`(Site, DiscoveredSite)`. `load_site` reads the file, discovers pages
statically, then executes the module to build `ARKNode(type, props, children)`
trees. A Rei frontend must produce the same result for `.rei` input: a populated
`Site` whose pages hold ARK AST trees, plus styles and state registrations.
Everything downstream (`normalize`, `validate`, IR, backends, `.arklight`
binary, SBOM) is untouched.

Proposed layout (a new package, deliberately **not** `arklight/compiler/rei/`,
which is already the compiler narrator from
`REI-COMPILER-NARRATOR-PROPOSAL.md`):

```text
arklight/frontend/rei/
    lexer.py     tokens with spans
    parser.py    hand-written recursive descent -> Rei AST
    ast.py       Rei AST node definitions
    check.py     names, types, phase analysis, vocabulary check
    lower.py     Rei AST -> ARK AST + Site registrations
    stdlib.py    what `import stdlib.ARKlight;` resolves to
```

`pyproject.toml` declares no runtime dependencies today, and a hand-written
parser keeps it that way (no parser-generator dependency).

### 3.2 Discovery and routing

The file is the page. `index.rei` is `/`, `about.rei` is `/about`, nested
folders become nested routes. This mirrors what `@site.page("/")` declares in
Python. Site-wide settings (title, styles shared across pages) need a home; see
Q5.

### 3.3 The narrator

The compile-time voice already exists: `arklight/compiler/rei/` renders
diagnostics as `[Rei]` sentences under `--narrate`. RS1 diagnostics should flow
through the same renderer, so a `.rei` error reads like the rest of the
toolchain. That the language and the narrator share a name is a feature to keep
deliberately (Q7), not an accident to tidy away.

## 4. Language surface (RS1)

**In:** classes, fields, methods, constructors, `static`, `this`, `new`,
`import`, single inheritance from library base classes (`Page`), `boolean`,
`int`, `double`, `String`, built-in `List` and `Map`, `if`/`else`, `for`,
`while`, `return`, method references (`this::name`), Java-style comments.

**Out (RS1):** annotations (an author decision), user-defined generics,
interfaces, exceptions, threads, reflection, static initializer blocks, operator
overloading, inner classes, and any way to call arbitrary Java, JavaScript or
Python.

A small, closed subset is the point. Each thing left out is a thing the compiler
does not have to prove safe.

## 5. Input and output the Java way

### 5.1 `out`, the printer

A page is written by calling methods on `index.out` (or `out` inside a `Page`
subclass). `println` is one method among many; the printer is a typed surface,
not a tree builder. Draft mapping (names are illustrative):

| `out` method | Lowers to |
|---|---|
| `println(String)` | `Text(...)` |
| `heading(String)` / `heading(String, int level)` | `Heading(...)` |
| `text(String)` | `Text(...)` |
| `link(String label, String href)` | `Link(label, href=...)` |
| `button(String label, Runnable action)` | `Button(label, on_click=<ActionRef>)` |
| `card { ... }` / `section { ... }` | `Container(...)` / `Section(...)` with children |

Nesting is a **block**, not a constructor argument, so structure comes from
control flow the author already reads top to bottom.

### 5.2 `in`, the input side (proposed)

The counterpart to `out` is `index.in`: the source of values a visitor supplies.
A text field is declared through `in` and read like a value:

```java
Field draft = in.textField("draft");   // lowers to State + bound input
...
tasks.add(draft.value);                 // lowers to Action.append("tasks", <state ref>)
```

This is the least settled part of the proposal (Q2). It follows the Java habit
of pairing an output stream with an input stream, but ARKlight's input is
event-driven, not blocking, so `in` returns handles rather than reading.

## 6. State, methods, and "JS is just a function"

This is the core of the language, and the part most likely to need revision.

### 6.1 Two phases, decided by data dependence

The compiler distinguishes code that runs **once, at build time** from code that
runs **in the browser**, and it does so from what the code touches, not from
keywords or annotations:

- **Build phase.** Code that depends only on constants and other build-phase
  values is **evaluated by the compiler**: loops that unroll, `if`s over
  constants that fold, helper methods like `nav(out)` that emit fixed content.
  This is what Python does today by executing the author's module. RS1 gets the
  same power from a small, deterministic, sandboxed evaluator (no I/O, no clock,
  no network, step and recursion limits), so nothing the author wrote ever runs
  as real code.
- **Runtime phase.** Code that depends on **state** (a field the visitor can
  change) must exist in the browser, so it is **lowered**, not evaluated:
  - an `if` whose condition reads a state field becomes `Show(<Predicate>, ...)`;
  - a `for` over a state list becomes `Repeat(...)`;
  - a handler method (one passed as `this::name`) becomes a closed action.

Because the phase follows the data, the author never writes "this is runtime
code." The cost is that an error message must be excellent when the inference
surprises them (Q4).

### 6.2 What lowers, exactly

RS1 runtime code is limited to what the existing registries already accept.
Current vocabulary (from `arklight/ir/schema.py`):

- Actions: `append`, `decrement`, `geolocate`, `increment`, `remove`, `reset`,
  `set`, `toggle_bool`
- Predicates: `and`, `equals`, `falsy`, `gt`, `in_range`, `is_empty`,
  `is_not_empty`, `is_null`, `lt`, `not`, `one_of`, `or`, `truthy`
- Derivations: about fifty, covering arithmetic (`sum`, `subtract`, `multiply`,
  `divide`, `min`, `max`, ...), rounding, and string operations (`uppercase`,
  `trim`, `title_case`, `starts_with`, `replace_all`, ...)
- Modifiers: `debounce`, `once`, `prevent`, `stop`, `throttle`

| RS1 source | Lowers to |
|---|---|
| `int count = 0;` (field) | `State("count", initial=0)` |
| `count++;` | `Action.increment("count")` |
| `count--;` | `Action.decrement("count")` |
| `open = !open;` | `Action.toggle_bool("open")` |
| `name = "x";` / `count = 0;` | `Action.set(...)` / `Action.reset(...)` |
| `tasks.add(draft.value);` | `Action.append("tasks", <state ref>)` |
| `tasks.remove(item);` | `Action.remove(...)` |
| `if (open) { ... }` | `Show(Predicate.truthy("open"), ...)` |
| `String label() { return name.toUpperCase(); }` | `Computed(...)` via `Derive.uppercase` |
| `for (Task t : tasks) { ... }` | `Repeat(...)` |

A handler body is a **straight-line sequence of these**. A conditional or a loop
inside a handler has no closed-action equivalent today, so the compiler rejects
it and says so. That is a real limit of the current vocabulary, not a choice
this proposal makes lightly; widening it is the job of the existing JS
vocabulary addenda, not of the language.

### 6.3 Third-party code

RS1 has no foreign-function interface. Third-party logic arrives through
ARKlight's own extension routes: ACC capabilities today, and, if it is ever
accepted, the AVM catalog from `AVM-WASM-SANDBOX-PROPOSAL.md`. That proposal's
three-state async value would need a matching Rei type (`Async<T>`), which is
out of scope for RS1.

## 7. A worked example

The mock's home page, rewritten to follow sections 2-6. It differs from the
mock on purpose: `page(Page index)` becomes a class that owns its state, the
shared piece prints instead of returning a node, and the toggle is a field
instead of a selector.

```java
// index.rei -- route "/" comes from the filename.
import stdlib.ARKlight;

public class Index extends Page {

    boolean detailsOpen = false;                 // State("detailsOpen", initial=False)

    void toggleDetails() {                       // -> Action.toggle_bool("detailsOpen")
        detailsOpen = !detailsOpen;
    }

    static void nav(Out out) {                   // build phase: emits fixed content
        out.link("Home", "/");
        out.link("About", "/about");
    }

    public void build() {
        style("card") {
            padding = 16.px;
            border = "1px solid var(--ark-border)";
            hover { background = "#f5f5ff"; }
        }

        nav(out);
        out.heading("Rei");
        out.text("Build websites with Rei.").style("muted");

        out.card {
            out.text("No JavaScript ships except a tiny, fixed runtime.");
            out.button("Show details", this::toggleDetails);
            if (detailsOpen) {                   // reads state -> Show(...)
                out.text("This text starts hidden.");
            }
        }
    }
}
```

Lowered to the ARK AST (shape only):

```text
State("detailsOpen", initial=False)
Page(route="/")
 ├ Container(Link("Home", href="/"), Link("About", href="/about"))      # from nav(out)
 ├ Heading("Rei")
 ├ Text("Build websites with Rei.", class_name="muted")
 └ Container(class_name="card")
     ├ Text("No JavaScript ships except a tiny, fixed runtime.")
     ├ Button("Show details", on_click=Action.toggle_bool("detailsOpen"))
     └ Show(Predicate.truthy("detailsOpen"), Text("This text starts hidden."))
```

The `.arklight` output, the HTML, the Android and Desktop builds all follow from
the existing pipeline. The author wrote no HTML, no CSS selector, no class
flip, and no JavaScript.

## 8. Styling and scripts, Kotlin-inspired (proposed reading)

RS1 stays Java except in three places, all chosen to keep UI code readable:

1. **Trailing blocks** for nesting and styling: `out.card { ... }`,
   `style("card") { ... }`, `hover { ... }`.
2. **Named arguments** where a call has several optional parts:
   `out.button(label = "Save", action = this::save)`.
3. **Typed units and property assignment** in style blocks: `padding = 16.px`,
   not a string key in a map.

Style blocks lower to the existing style API (`Site.style(name, rules)` and its
pseudo-class key form, e.g. `":hover:background"`). "Scripts" in this reading
are the handler methods of section 6, not a separate embedded language. This is
my interpretation of "Kotlin-inspired" and should be confirmed (Q3).

## 9. Costs and consequences

- **Identity text must change.** `WHAT-ARKLIGHT-IS.md` says ARKlight is
  "Python-authored -- not templated, not a DSL with its own syntax" and describes
  the site as a Python module the compiler executes. Rei is a DSL with its own
  syntax and is never executed. The bullet needs to become "Python-first, with a
  second, non-executing frontend," and `pyproject.toml`'s description ("A
  Python-first compiler...") is already compatible.
- **A real compiler is a real commitment.** Parser, type checker, phase
  analysis, evaluator, diagnostics and (eventually) editor support are a large,
  permanent surface. Python authoring gets much of this for free from Python.
- **Two frontends must agree.** The conformance rule in section 10 exists so
  they cannot drift.
- **A smaller build-time attack surface.** Because the compiler never executes a
  `.rei` file, a malicious or careless site cannot run code during `arklight
  build`. The Python frontend cannot claim this. It is a genuine advantage and
  should be stated plainly, without overselling: it says nothing about the
  runtime, which is already closed.

## 10. Conformance: Python as the oracle

For every RS1 feature, the repository keeps a **Python twin**: an equivalent
`site.py` producing the same page. The acceptance test is that both compile to an
identical IR (and therefore identical output). This makes the existing, shipped
compiler the specification for lowering, and turns "does RS1 mean what we said"
into an automated check rather than a review opinion.

## 11. Staged ladder

Same rung discipline as `PROVIDER-SDK-ADDENDUM.md`: each rung is independently
shippable and the language stays experimental until RS1 is frozen.

| Rung | What ships | Done when |
|---|---|---|
| **R0** | Grammar spec, file/route model, `.rei` discovery in the pipeline; no compiler | Spec reviewed; pipeline recognizes `.rei` and reports "not implemented" |
| **R1** | Lexer, parser, Rei AST; syntax errors through the narrator | Every RS1 example parses; malformed input gives spanned, narrated errors |
| **R2** | Static pages: `out.heading/text/link`, blocks, `nav(out)` (build-phase evaluator), shared routes | Static `hello_site` home compiles to the same IR as its Python twin |
| **R3** | Fields -> `State`; handler methods -> actions; `if` over state -> `Show`; method references | The section 7 example matches its Python twin |
| **R4** | Getters and expressions -> `Computed`/`Predicate`; `for` over state -> `Repeat`; `in` fields | A todo-list example matches its Python twin |
| **R5** | Styling blocks, typed units, stdlib surface | Style output matches `Site.style` twin |
| **R6** | Multi-file projects and imports; Android and Desktop parity; docs graduation | Backend matrix verified, `WHAT-ARKLIGHT-IS.md` updated |

## 12. Non-goals

Full Java; annotations; a JVM or any Java toolchain; running `.rei` in the
browser; replacing the Python frontend; arbitrary JavaScript, Python or Java
interop; IDE and language-server support (each needs its own proposal, as the
narrator's scope note requires).

## 13. Open questions

1. **Shared pieces.** `static void nav(Out out)` (Java-way, no node values) or a
   `Node`-returning method as in the mock? The first is more consistent with
   section 2; the second composes more easily.
2. **What `in` is.** Handles that bind fields (section 5.2), or something closer
   to the Java `Scanner` model? How do forms and validation fit?
3. **"Kotlin-inspired," precisely.** Are trailing blocks, named arguments and typed
   units the intended surface, or is something else meant (extension functions,
   lambdas with receivers, string templates)?
4. **Phase inference.** Should the compiler infer build versus runtime from data
   dependence (proposed), or should authors mark it? What is the error message
   when a method is ambiguous?
5. **Site-level settings.** Where do title, shared styles, theme and `Provider`
   configuration live? A `site.rei`, or class-level declarations?
6. **Type system depth.** How far do `List`, `Map` and user classes go, given
   that only what the registries can express reaches the browser?
7. **Naming.** "Rei" is already the compiler narrator. Keep the shared name and
   package them clearly (`arklight/compiler/rei/` versus
   `arklight/frontend/rei/`), or rename one?
8. **Async and extensions.** How does an AVM-style async value or a `Provider`
   surface as a type in a Java-syntax language?
9. **Registry growth.** Handler bodies are straight-line only because the action
   registry has no conditional action. Should the language wait for the
   vocabulary, or should the vocabulary follow the language?

## 14. Relationship to other proposals

- `REI-COMPILER-NARRATOR-PROPOSAL.md`: shipped; supplies the diagnostic voice
  and shares the name (Q7).
- `AVM-WASM-SANDBOX-PROPOSAL.md`: a possible source of third-party logic; needs a
  matching type (Q8).
- `PROVIDER-SDK-PROPOSAL.md` and `PLATFORM-API-IR-PROPOSAL.md`: external
  services and device APIs need a Rei-level declaration story; not designed here.
- `USER-DEFINED-ERROR-HANDLING-PROPOSAL.md`: no exceptions in RS1, so error
  handling would use its closed vocabulary, not `try`/`catch`.
- JS vocabulary addenda: they set the ceiling on what "JS is just a function" can
  mean (section 6.2).

## 15. Filing checklist (per `docs/README.md`'s one-pass rule)

1. This file, `docs/Proposals/REI-LANGUAGE-RS1-PROPOSAL.md`, with its Status line.
2. Its row in `docs/Proposals/README.md`'s Index.
3. Its row in `docs/README.md`'s Folder Guide for `docs/Proposals/`.
4. If accepted: `docs/Implementation/REI-LANGUAGE-ADDENDUM.md`, its rows in
   `docs/Implementation/README.md` and the Folder Guide, the `ARCHITECTURE.md`
   Milestones row, the `PROGRESS.md` Snapshot row, and the `WHAT-ARKLIGHT-IS.md`
   identity amendment from section 9.

Suggested Index row text:

> | [`REI-LANGUAGE-RS1-PROPOSAL.md`](REI-LANGUAGE-RS1-PROPOSAL.md) | Proposal for Rei Script (RS1), a Java-syntax source language and second ARKlight frontend: `.rei` -> Rei AST -> ARK AST -> the existing pipeline. Fields lower to `State`, methods to closed `Action.*`, expressions to `Derive.*`/`Predicate.*`; output is a Java-style `out` printer, not a node tree; the compiler parses and never executes author code. Two-phase model (build-time evaluation versus lowered runtime code), Python twins as the conformance oracle, ladder `R0`-`R6`. **Not accepted.** |