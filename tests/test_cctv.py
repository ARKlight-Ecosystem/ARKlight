"""
Regression tests for `arklight.cli.cctv`.

Deliberately unit-level, same philosophy as test_live_streaming.py:
these lock the pieces most likely to silently break (state merge/bump
semantics, SSE broadcast + one-way field exclusion, page selection)
rather than spinning up a real server/socket in every test -- that's
covered by manual end-to-end verification.

`cctv` is no longer its own CLI subcommand -- its port-binding and
argparse wiring moved into `arklight.cli.live_streaming` as the
`--channel` flag (see test_live_streaming.py's `--channel` tests for
that coverage). This module still owns the state/hub/backend/
page-selection building blocks `live_streaming` imports and drives.
"""

from __future__ import annotations

import pytest

from arklight.cli import cctv
from arklight.ir.build import IRPage, IRNode, WebsiteIR


# --------------------------------------------------------------------
# _State
# --------------------------------------------------------------------


def test_state_snapshot_is_a_copy_not_a_live_view():
    state = cctv._State({"count": 0})
    snap = state.snapshot()
    snap["count"] = 999
    assert state.snapshot()["count"] == 0


def test_state_merge_returns_only_changed_keys():
    state = cctv._State({"count": 0, "name": "a"})
    changed = state.merge({"count": 0, "name": "b"})
    assert changed == {"name": "b"}
    assert state.snapshot() == {"count": 0, "name": "b"}


def test_state_merge_adds_new_keys():
    state = cctv._State({})
    changed = state.merge({"count": 1})
    assert changed == {"count": 1}


def test_state_merge_no_op_returns_empty_dict():
    state = cctv._State({"count": 5})
    assert state.merge({"count": 5}) == {}


def test_state_bump_adds_to_numeric_field():
    state = cctv._State({"count": 3})
    changed = state.bump("count", 2)
    assert changed == {"count": 5}
    assert state.snapshot()["count"] == 5


def test_state_bump_defaults_missing_field_to_zero():
    state = cctv._State({})
    changed = state.bump("count", 1)
    assert changed == {"count": 1}


def test_state_bump_rejects_non_numeric_field():
    state = cctv._State({"name": "abc"})
    with pytest.raises(TypeError):
        state.bump("name", 1)


def test_state_bump_rejects_bool_field():
    # bool is technically an int subclass in Python -- explicitly excluded
    # since "bumping" a flag field is almost certainly a mistake, not intent.
    state = cctv._State({"flag": True})
    with pytest.raises(TypeError):
        state.bump("flag", 1)


# --------------------------------------------------------------------
# _SSEHub
# --------------------------------------------------------------------


def test_hub_broadcast_state_reaches_all_state_subscribers():
    hub = cctv._SSEHub()
    sub_a = hub.subscribe("state", "a")
    sub_b = hub.subscribe("state", "b")
    notified = hub.broadcast_state({"count": 1})
    assert notified == 2
    assert sub_a.queue.get_nowait() == ("state", {"count": 1})
    assert sub_b.queue.get_nowait() == ("state", {"count": 1})


def test_hub_broadcast_fragment_skips_empty_after_exclusion():
    hub = cctv._SSEHub()
    sub = hub.subscribe("fragment", "a")
    hub.exclude_fields("a", ["count"])
    notified = hub.broadcast_fragment({"count": 1})
    assert notified == 0
    assert sub.queue.empty()


def test_hub_broadcast_fragment_delivers_unexcluded_fields():
    hub = cctv._SSEHub()
    sub = hub.subscribe("fragment", "a")
    hub.exclude_fields("a", ["count"])
    notified = hub.broadcast_fragment({"count": 1, "name": "x"})
    assert notified == 1
    assert sub.queue.get_nowait() == ("fragment", {"name": "x"})


def test_hub_exclude_fields_is_one_way():
    hub = cctv._SSEHub()
    hub.subscribe("fragment", "a")
    hub.exclude_fields("a", ["count"])
    hub.exclude_fields("a", [])  # no-op call shouldn't un-exclude anything
    notified = hub.broadcast_fragment({"count": 1})
    assert notified == 0


def test_hub_exclude_fields_returns_false_for_unknown_client():
    hub = cctv._SSEHub()
    assert hub.exclude_fields("nope", ["count"]) is False


def test_hub_unsubscribe_stops_further_broadcasts():
    hub = cctv._SSEHub()
    sub = hub.subscribe("state", "a")
    hub.unsubscribe("state", "a")
    notified = hub.broadcast_state({"count": 1})
    assert notified == 0
    assert sub.queue.empty()


def test_hub_subscriber_count():
    hub = cctv._SSEHub()
    assert hub.subscriber_count("state") == 0
    hub.subscribe("state", "a")
    hub.subscribe("state", "b")
    assert hub.subscriber_count("state") == 2


# --------------------------------------------------------------------
# select_page -- single-root scaffold (CCTV-BACKEND-PROPOSAL.md SS6)
# --------------------------------------------------------------------


def _fake_ir(*routes: str) -> WebsiteIR:
    pages = [IRPage(route=r, root=IRNode(type="Page"), state={"count": 0}) for r in routes]
    return WebsiteIR(site_name="test", pages=pages)


def test_select_page_defaults_to_first_page():
    ir = _fake_ir("/", "/about")
    page = cctv.select_page(ir, None)
    assert page is not None
    assert page.route == "/"


def test_select_page_finds_explicit_route():
    ir = _fake_ir("/", "/about")
    page = cctv.select_page(ir, "/about")
    assert page is not None
    assert page.route == "/about"


def test_select_page_raises_on_unknown_route():
    ir = _fake_ir("/", "/about")
    with pytest.raises(ValueError, match="no page with route"):
        cctv.select_page(ir, "/missing")


def test_select_page_returns_none_for_empty_site():
    ir = WebsiteIR(site_name="empty", pages=[])
    assert cctv.select_page(ir, None) is None


# --------------------------------------------------------------------
# _CCTVBackend -- render() contract (Backend.render never touches disk)
# --------------------------------------------------------------------


def test_backend_render_emits_client_js_and_schema():
    ir = _fake_ir("/")
    backend = cctv._CCTVBackend()
    out = backend.render(ir)
    assert cctv._CLIENT_JS_PATH.lstrip("/") in out
    assert "__cctv_schema__.json" in out
    assert "EventSource" in out[cctv._CLIENT_JS_PATH.lstrip("/")]


def test_backend_render_schema_reflects_selected_page_state():
    ir = _fake_ir("/", "/about")
    backend = cctv._CCTVBackend(route="/about")
    out = backend.render(ir)
    assert '"route": "/about"' in out["__cctv_schema__.json"]


def test_backend_render_on_empty_site_still_returns_files():
    ir = WebsiteIR(site_name="empty", pages=[])
    backend = cctv._CCTVBackend()
    out = backend.render(ir)
    assert cctv._CLIENT_JS_PATH.lstrip("/") in out
    assert '"route": null' in out["__cctv_schema__.json"]


# --- cross-origin writes (review finding: dev channel had no Origin check) ---

import http.client as _http_client  # noqa: E402
import json as _json  # noqa: E402
import threading as _threading  # noqa: E402

from arklight.cli import cctv as _cctv  # noqa: E402


def _serve(bind_host="127.0.0.1", initial=None):
    state = _cctv._State(initial if initial is not None else {"minutes": 25})
    hub = _cctv._SSEHub()
    handler = _cctv._make_handler(state, hub, bind_host=bind_host)
    server = _cctv._CCTVHTTPServer(("127.0.0.1", 0), handler)
    thread = _threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, state


def _request(server, method, path, body=None, headers=None):
    conn = _http_client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, (_json.loads(raw) if raw else None)
    finally:
        conn.close()


def test_cross_origin_text_plain_post_is_refused_and_changes_nothing():
    """The review's reproduction: the no-preflight request shape a
    browser sends from another origin used to set minutes = 1."""
    server, state = _serve()
    try:
        status, payload = _request(
            server,
            "POST",
            "/state",
            body=_json.dumps({"minutes": 1}),
            headers={"Origin": "http://evil.example", "Content-Type": "text/plain"},
        )
        assert status == 403
        assert "cross-origin" in payload["error"]
        assert state.snapshot() == {"minutes": 25}
    finally:
        server.shutdown()
        server.server_close()


def test_cross_origin_bump_is_refused_too():
    server, state = _serve()
    try:
        status, _ = _request(
            server,
            "POST",
            "/state/bump",
            body=_json.dumps({"field": "minutes", "by": 5}),
            headers={"Origin": "http://evil.example", "Content-Type": "text/plain"},
        )
        assert status == 403
        assert state.snapshot() == {"minutes": 25}
    finally:
        server.shutdown()
        server.server_close()


def test_another_localhost_port_is_a_different_origin_and_is_refused():
    server, state = _serve()
    try:
        status, _ = _request(
            server,
            "POST",
            "/state",
            body=_json.dumps({"minutes": 1}),
            headers={"Origin": "http://127.0.0.1:8347", "Content-Type": "text/plain"},
        )
        assert status == 403
        assert state.snapshot() == {"minutes": 25}
    finally:
        server.shutdown()
        server.server_close()


def test_the_opaque_null_origin_is_refused():
    server, state = _serve()
    try:
        status, _ = _request(
            server, "POST", "/state", body=_json.dumps({"minutes": 1}), headers={"Origin": "null"}
        )
        assert status == 403
    finally:
        server.shutdown()
        server.server_close()


def test_a_request_with_no_origin_header_still_works_like_curl():
    server, state = _serve()
    try:
        status, payload = _request(
            server,
            "POST",
            "/state",
            body=_json.dumps({"minutes": 50}),
            headers={"Content-Type": "application/json"},
        )
        assert status == 200 and payload == {"changed": {"minutes": 50}}
        status, payload = _request(
            server, "POST", "/state/bump", body=_json.dumps({"field": "minutes", "by": 5})
        )
        assert status == 200
        assert state.snapshot() == {"minutes": 55}
    finally:
        server.shutdown()
        server.server_close()


def test_a_same_origin_page_can_still_write():
    server, state = _serve()
    try:
        port = server.server_address[1]
        status, _ = _request(
            server,
            "POST",
            "/state",
            body=_json.dumps({"minutes": 40}),
            headers={"Origin": f"http://127.0.0.1:{port}", "Content-Type": "text/plain"},
        )
        assert status == 200
        assert state.snapshot() == {"minutes": 40}
    finally:
        server.shutdown()
        server.server_close()


def test_reads_still_work():
    server, _ = _serve()
    try:
        status, payload = _request(server, "GET", "/state")
        assert status == 200 and payload == {"minutes": 25}
    finally:
        server.shutdown()
        server.server_close()


def test_dns_rebinding_host_header_is_refused_when_bound_to_loopback():
    """An attacker hostname resolved to 127.0.0.1 is same-origin *to the
    browser*, so Origin alone can't stop it -- the Host header can."""
    server, state = _serve()
    try:
        for method, path, body in (
            ("GET", "/state", None),
            ("POST", "/state", _json.dumps({"minutes": 1})),
        ):
            headers = {"Host": "attacker.example:2172"}
            if method == "POST":
                headers["Origin"] = "http://attacker.example:2172"
            status, payload = _request(server, method, path, body=body, headers=headers)
            assert status == 403, (method, path)
            assert "Host" in payload["error"]
        assert state.snapshot() == {"minutes": 25}
    finally:
        server.shutdown()
        server.server_close()


def test_loopback_host_spellings_are_all_accepted():
    server, _ = _serve()
    try:
        port = server.server_address[1]
        for host in (f"localhost:{port}", f"127.0.0.1:{port}", f"[::1]:{port}", "localhost"):
            status, _ = _request(server, "GET", "/state", headers={"Host": host})
            assert status == 200, host
    finally:
        server.shutdown()
        server.server_close()


def test_host_check_is_skipped_when_deliberately_bound_to_a_lan_address():
    """`--host 0.0.0.0`/a LAN IP is an explicit choice to be reachable,
    and the Host header is then that address -- don't break it. The
    Origin check still applies."""
    server, state = _serve(bind_host="192.168.1.20")
    try:
        status, _ = _request(server, "GET", "/state", headers={"Host": "192.168.1.20:2172"})
        assert status == 200
        status, _ = _request(
            server,
            "POST",
            "/state",
            body=_json.dumps({"minutes": 1}),
            headers={"Host": "192.168.1.20:2172", "Origin": "http://evil.example"},
        )
        assert status == 403
        assert state.snapshot() == {"minutes": 25}
    finally:
        server.shutdown()
        server.server_close()


def test_host_of_parses_every_header_shape():
    assert _cctv._host_of("127.0.0.1:2172") == "127.0.0.1"
    assert _cctv._host_of("localhost") == "localhost"
    assert _cctv._host_of("[::1]:2172") == "::1"
    assert _cctv._host_of("LocalHost:9") == "localhost"
    assert _cctv._host_of(None) == ""
