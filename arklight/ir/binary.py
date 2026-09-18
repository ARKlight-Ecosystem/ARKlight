"""
`.arklight` -- the binary encoding of the Website IR.

Ported from the design draft in C_ARKlight's `docs/ADDENDUM.md` §2 and
`docs/TERMINOLOGY.md` (carklight's from-scratch C reimplementation --
see the ARKlight/carklight repo split). Those docs frame `.arklight`
as *carklight's* on-disk contract for non-C language frontends; that
framing is out of date here (this is ARKlight-py, not a carklight
frontend), but the underlying idea -- a small, portable, versioned
binary artifact for the compiled IR, distinct from the human-facing
in-memory `WebsiteIR`/`IRNode` tree -- stands on its own and is useful
right here: a `.arklight` file is a build-once, ship-anywhere snapshot
of a compiled site's IR that doesn't require re-running the Python
compiler pipeline to read back.

Per TERMINOLOGY.md's "IR is for humans, `.arklight` is for machines"
split: `WebsiteIR`/`IRNode` (arklight.ir.build) stay the legible,
in-process form; this module is the one place that ever turns that
into bytes on disk, and the one place that ever reads those bytes
back.

Format (little-endian throughout), matching ADDENDUM.md §2's
requirements:

    magic bytes           4   b"ARKL"
    format version        u16 FORMAT_VERSION (independent of
                               ARKlight's own __version__)
    schema generation tag str "arklight v{__version__} ({CHANNEL})"
                               -- self-declares which ARKlight build
                               produced the file, so a future reader
                               can tell "older/newer schema" apart
                               from "corrupt file"
    string table           u32 count, then `count` length-prefixed
                               UTF-8 strings -- every string used
                               anywhere below (site name, routes,
                               node types, JSON-encoded props/state
                               blobs, text content) is stored once
                               here and referenced everywhere else by
                               u32 index, since component props and
                               text content dominate file size
                               otherwise (ADDENDUM.md §2)
    body                       site_name, lang, app_shell flag, then
                               page count and each page's IR tree

This is a hand-rolled, zero-dependency binary encoding, matching the
house style ADDENDUM.md §2 calls out (`arklight.packer`'s `.ark`
bundle format is the same discipline) rather than reaching for
protobuf/flatbuffers/etc.

Scope note: this v1 covers the structural IR tree (site/page/node
shape -- the part TERMINOLOGY.md calls "IR" proper) plus each page's
route, `state`, and `computed_initial`, which is enough to rebuild
what a backend actually renders from. The long tail of page-level
bookkeeping on `WebsiteIR`/`IRPage` (watch/persist/media/query specs,
site-wide style registrations, raw postprocessors, ...) is not yet
round-tripped -- left for a follow-up once this format has soaked,
same staged-rollout discipline the rest of the schema-generation
model already uses.
"""

from __future__ import annotations

import dataclasses
import json
import struct
from dataclasses import dataclass, field
from typing import Any

from arklight.ir.build import IRNode, IRPage, WebsiteIR

# Deliberately *not* `from arklight import CHANNEL, __version__` at
# module scope: `arklight/__init__.py` -> `arklight.api` ->
# `arklight.backend` -> `arklight.ir.build` -> `arklight.ir` (this
# package's own `__init__.py`) -> here, so importing the top-level
# `arklight` package from this module while it's still mid-import
# would be a circular import. Reading `CHANNEL`/`__version__` off the
# module object inside `encode_arklight` instead (by which point
# `arklight/__init__.py` has always finished executing) sidesteps
# that without breaking the import chain above.

MAGIC = b"ARKL"
FORMAT_VERSION = 1


class ArklightFormatError(ValueError):
    """Raised when `.arklight` bytes are corrupt, truncated, or carry
    magic bytes/a format version this reader doesn't understand --
    kept as one dedicated exception type so callers can distinguish
    "this isn't a valid .arklight file" from an ordinary decoding bug.
    """


# --------------------------------------------------------------------------
# Low-level primitives
# --------------------------------------------------------------------------


class _Writer:
    """Accumulates the body's bytes plus a deduped string table, so a
    string that appears more than once (a repeated node `type`, a
    repeated prop key inside JSON-encoded props, ...) is only ever
    written to the file once.
    """

    def __init__(self) -> None:
        self._strings: list[str] = []
        self._index: dict[str, int] = {}
        self.body = bytearray()

    def intern(self, s: str) -> int:
        idx = self._index.get(s)
        if idx is not None:
            return idx
        idx = len(self._strings)
        self._strings.append(s)
        self._index[s] = idx
        return idx

    def u8(self, value: int) -> None:
        self.body += struct.pack("<B", value)

    def u32(self, value: int) -> None:
        self.body += struct.pack("<I", value)

    def str_ref(self, s: str) -> None:
        self.u32(self.intern(s))

    def json_ref(self, value: Any) -> None:
        # Props/state/computed_initial are typed `Any` on the Python
        # side (see IRNode/IRPage), and in practice hold more than
        # plain JSON scalars -- e.g. an `on_click=Action.increment(...)`
        # prop is a frozen `ActionRef` dataclass, not a dict. `_json_
        # default` below tags those (and any other dataclass) so they
        # round-trip as a plain dict on decode instead of crashing
        # `json.dumps`; anything else with no dataclass shape falls
        # back to `repr()` so encoding a prop value ARKlight-py adds
        # in the future never hard-fails a build just because this
        # module doesn't know its type yet.
        self.str_ref(
            json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)
        )

    def finish(self, schema_tag: str) -> bytes:
        out = bytearray()
        out += MAGIC
        out += struct.pack("<H", FORMAT_VERSION)
        tag_bytes = schema_tag.encode("utf-8")
        out += struct.pack("<I", len(tag_bytes))
        out += tag_bytes
        out += struct.pack("<I", len(self._strings))
        for s in self._strings:
            s_bytes = s.encode("utf-8")
            out += struct.pack("<I", len(s_bytes))
            out += s_bytes
        out += self.body
        return bytes(out)


class _Reader:
    def __init__(self, data: bytes, strings: list[str]) -> None:
        self._data = data
        self._strings = strings
        self._pos = 0

    def u8(self) -> int:
        (value,) = struct.unpack_from("<B", self._data, self._pos)
        self._pos += 1
        return value

    def u32(self) -> int:
        (value,) = struct.unpack_from("<I", self._data, self._pos)
        self._pos += 4
        return value

    def str_ref(self) -> str:
        idx = self.u32()
        try:
            return self._strings[idx]
        except IndexError as exc:  # pragma: no cover -- corrupt file
            raise ArklightFormatError(
                f"string table index {idx} out of range (table has "
                f"{len(self._strings)} entries)"
            ) from exc

    def json_ref(self) -> Any:
        return json.loads(self.str_ref())

    def at_end(self) -> bool:
        return self._pos >= len(self._data)


def _json_default(obj: Any) -> Any:
    """`json.dumps(..., default=...)` hook -- see the `json_ref` call
    site above. A frozen dataclass (`ActionRef`, `ClassBindSpec`,
    `ModelBindSpec`, `DerivationRef`, ...) becomes a plain dict tagged
    with its class name; anything else falls back to `repr()` rather
    than raising, so an unrecognized prop value degrades to an opaque
    (but present, inspectable) string instead of failing the whole
    encode.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {"__ark_type__": type(obj).__name__, **dataclasses.asdict(obj)}
    return repr(obj)


# Node child tag bytes -- one byte ahead of each child telling the
# reader whether the next thing is a nested node or a bare text leaf
# (`IRNode.children` is `list["IRNode | str"]`).
_CHILD_NODE = 0
_CHILD_TEXT = 1


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------


def _write_node(w: _Writer, node: IRNode) -> None:
    w.str_ref(node.type)
    w.json_ref(node.props)
    w.u32(len(node.children))
    for child in node.children:
        if isinstance(child, str):
            w.u8(_CHILD_TEXT)
            w.str_ref(child)
        else:
            w.u8(_CHILD_NODE)
            _write_node(w, child)


def _write_page(w: _Writer, page: IRPage) -> None:
    w.str_ref(page.route)
    _write_node(w, page.root)
    w.json_ref(page.state)
    w.json_ref(dict(page.computed_initial))


def encode_arklight(ir: WebsiteIR) -> bytes:
    """Encode a compiled `WebsiteIR` to `.arklight` bytes.

    This is the one encode step per the two-tier consumption model
    ADDENDUM.md §1 describes for non-native frontends: build the tree
    in whatever's idiomatic (here, `arklight.ir.build.build_website_ir`),
    then emit the file. Nothing downstream needs to know ARKlight's
    Python object model to read it back -- see `decode_arklight`.
    """
    w = _Writer()
    w.str_ref(ir.site_name)
    w.str_ref(ir.lang)
    w.u8(1 if ir.app_shell else 0)
    w.u32(len(ir.pages))
    for page in ir.pages:
        _write_page(w, page)

    import arklight as _arklight  # local import -- see module-level note above

    schema_tag = f"arklight v{_arklight.__version__} ({_arklight.CHANNEL})"
    return w.finish(schema_tag)


# --------------------------------------------------------------------------
# Decoding
# --------------------------------------------------------------------------


@dataclass
class ArklightHeader:
    """Just the header -- magic/version/schema-tag/string-count --
    without walking the full body. Cheap enough to use for a quick
    "is this a `.arklight` file, and which ARKlight built it" check
    (e.g. a future `arklight inspect --arklight <path>`) without
    paying to decode every page.
    """

    format_version: int
    schema_tag: str
    string_count: int


@dataclass
class DecodedNode:
    type: str
    props: dict[str, Any] = field(default_factory=dict)
    children: list["DecodedNode | str"] = field(default_factory=list)


@dataclass
class DecodedPage:
    route: str
    root: DecodedNode
    state: dict[str, Any] = field(default_factory=dict)
    computed_initial: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecodedSite:
    site_name: str
    lang: str
    app_shell: bool
    pages: list[DecodedPage] = field(default_factory=list)


def _read_header(data: bytes) -> tuple[ArklightHeader, int]:
    if data[:4] != MAGIC:
        raise ArklightFormatError(
            f"not a .arklight file: bad magic bytes {data[:4]!r} (expected {MAGIC!r})"
        )
    pos = 4
    (format_version,) = struct.unpack_from("<H", data, pos)
    pos += 2
    if format_version != FORMAT_VERSION:
        raise ArklightFormatError(
            f"unsupported .arklight format version {format_version} "
            f"(this reader only understands version {FORMAT_VERSION})"
        )
    (tag_len,) = struct.unpack_from("<I", data, pos)
    pos += 4
    schema_tag = data[pos : pos + tag_len].decode("utf-8")
    pos += tag_len
    (string_count,) = struct.unpack_from("<I", data, pos)
    pos += 4
    return ArklightHeader(format_version, schema_tag, string_count), pos


def peek_header(data: bytes) -> ArklightHeader:
    """Read just the header, without decoding the string table or body."""
    header, _ = _read_header(data)
    return header


def _read_node(r: _Reader) -> DecodedNode:
    node_type = r.str_ref()
    props = r.json_ref()
    child_count = r.u32()
    children: list[DecodedNode | str] = []
    for _ in range(child_count):
        tag = r.u8()
        if tag == _CHILD_TEXT:
            children.append(r.str_ref())
        elif tag == _CHILD_NODE:
            children.append(_read_node(r))
        else:  # pragma: no cover -- corrupt file
            raise ArklightFormatError(f"unknown child tag byte {tag}")
    return DecodedNode(type=node_type, props=props, children=children)


def _read_page(r: _Reader) -> DecodedPage:
    route = r.str_ref()
    root = _read_node(r)
    state = r.json_ref()
    computed_initial = r.json_ref()
    return DecodedPage(route=route, root=root, state=state, computed_initial=computed_initial)


def decode_arklight(data: bytes) -> DecodedSite:
    """Decode `.arklight` bytes back into a plain, backend-model-free
    tree (`DecodedSite`/`DecodedPage`/`DecodedNode`) -- deliberately
    *not* `WebsiteIR`/`IRPage`/`IRNode` themselves, since those are
    ARKlight-py's own in-process dataclasses (component_origin,
    watch/persist/media/query, site-wide style registrations, ...)
    and a `.arklight` file is scoped to the structural subset this
    module actually writes (see the module docstring's scope note).
    """
    header, pos = _read_header(data)

    strings: list[str] = []
    for _ in range(header.string_count):
        (str_len,) = struct.unpack_from("<I", data, pos)
        pos += 4
        strings.append(data[pos : pos + str_len].decode("utf-8"))
        pos += str_len

    r = _Reader(data[pos:], strings)
    site_name = r.str_ref()
    lang = r.str_ref()
    app_shell = bool(r.u8())
    page_count = r.u32()
    pages = [_read_page(r) for _ in range(page_count)]

    if not r.at_end():  # pragma: no cover -- corrupt/truncated-oddly file
        raise ArklightFormatError("trailing bytes after the last page")

    return DecodedSite(site_name=site_name, lang=lang, app_shell=app_shell, pages=pages)
