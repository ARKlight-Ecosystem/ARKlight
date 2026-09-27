# Pitch for ARKlight

ARKlight is a Python-first compiler for building websites without writing HTML, CSS, or JavaScript, which sounds like a great way to make three programming languages angry at once.

The idea is pretty simple. You write ordinary Python, ARKlight discovers and executes that authoring code at build time, turns it into its own intermediate representation, validates it against a closed vocabulary, and then compiles it down to boring old HTML, CSS, and JavaScript.

The browser never runs Python.

Instead of stitching together a frontend from separate languages and frameworks, you describe the page directly in Python.

`Page( Text(Bind("count")), Button("Increment", on_click=Action.increment("count", 1)) )`

ARKlight then produces a static website that can be served by basically anything.

And now the compiler has its own little preamble too.

`# include <stdlib.ARKlight>`

`# define something -> something_else`

Python sees comments. ARKlight sees compiler directives. Humanity survives another abstraction.

But this isn't just Python-flavored HTML.

ARKlight is built around a compiler-first, runtime-last philosophy.

Things like routing, validation, dependency resolution, and CSS generation are handled as early as possible, while the browser runtime is reserved for things that genuinely require a browser, like user input, local storage, viewport state, reactive state, and URL state.

The vocabulary is intentionally closed. The compiler knows which components and behaviors can exist instead of evaluating arbitrary JavaScript expressions at runtime.

That makes the generated application more predictable, while avoiding the classic framework experience of accidentally summoning a small JavaScript civilization into your bundle.

ARKlight also supports user-defined components. Those components can be expanded during compilation and validated as part of the resulting ARKlight tree, meaning the abstraction itself doesn't need to survive into the generated website.

And because the compiler produces conventional web files, that output can also be packaged into things like PWAs, sealed `.ark` bundles, Android applications, and Linux desktop applications.

There's also ACC, the ARKlight Component Collections ecosystem, for distributing components, authoring capabilities, styles, templates, and compiler-recognized extensions.

So is this React written in Python?

Not really.

React is a JavaScript library and frontend runtime with a massive ecosystem built around flexible application logic.

ARKlight is deliberately narrower.

The goal is to give Python developers a web-development experience without requiring them to learn HTML, CSS, JavaScript, npm, and an entirely separate frontend ecosystem just to build a page.

It also has a compiler narrator called Rei, because apparently deterministic compiler diagnostics weren't emotionally complicated enough.

This has been ARKlight.

Your browser is still running JavaScript.

We just made Python responsible for getting it there.
