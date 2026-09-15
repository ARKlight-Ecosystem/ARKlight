# hello_desktop

There's no `site.py` in here -- this example reuses
[`examples/hello_site`](../hello_site) and shows it packaged as a
native desktop app instead, using `arklight desktop scaffold` (Stage
1) and `arklight desktop build` (Stage 2, see
[`docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`](../../docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md)).

Everything this example produces -- the `arklight build` output, the
scaffolded GTK3 + WebKit2GTK project (`main.c`, `Makefile`,
`assets.gen.c`, ...), and the compiled `bin/hello-desktop` binary --
is generated on demand from these three commands, not committed to
the repository. Regenerate it any time with:

```sh
# From the repository root.
arklight build examples/hello_site/site.py -o examples/hello_desktop/build
arklight desktop scaffold examples/hello_desktop/build -o examples/hello_desktop/app
arklight desktop build examples/hello_desktop/app --run
```

The first command compiles the example site to static HTML/CSS/JS
(Stage 0, the regular web build). The second templates a native host
project around it (Stage 1 -- no C toolchain needed for this step).
The third shells out to that project's own `make` for you (Stage 2)
and, with `--run`, launches the freshly built window immediately
after.

Needs a C compiler, `pkg-config`, and the GTK3 + WebKit2GTK dev
headers -- see the generated `app/README.md` (written by `arklight
desktop scaffold`) for the exact packages per distro.

On success, `arklight desktop build` also prints:

```
ARKlight supports cross-platform targets as well -- try it with this cmd:
  arklight android scaffold <build-dir> -o <project-dir>
```

-- the same `examples/hello_desktop/build` output from the first
command above works as `<build-dir>` there too, e.g.:

```sh
arklight android scaffold examples/hello_desktop/build -o examples/hello_desktop/android
```

`examples/hello_desktop/build/`, `app/`, and `android/` are all
build-time generated and gitignored -- see `.gitignore` in this
directory.
