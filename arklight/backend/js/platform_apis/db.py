"""
`db` platform API fragment -- the Web backend's own implementation of
the `db` interface registered in
`arklight.ir.platform_api.PLATFORM_API_REGISTRY`. See `notify.py` in
this same package for the sibling shape this mirrors: a per-capability
module exporting `NAME` and `JS_FRAGMENT`, only shipped when a site's
IR actually uses it.

**One interface, two engines.** The author writes
`PlatformAPI.db.set(...)`/`get`/`delete`/`keys` and never learns which
engine served it. This fragment picks one at call time:

- **Inside an ARKlight Android app**, the generated `MainActivity`
  registers a `WebMessageListener` named `arkDbBridge`, restricted to
  the app's own asset origin (`arklight.backend.android.runtime`,
  `ArkDb.kt`), which backs the interface with SQLite. When
  `window.arkDbBridge` exists, every operation is one JSON message to
  it and one JSON reply back.
- **Everywhere else** (a browser, or an older WebView without
  `WEB_MESSAGE_LISTENER`), it uses IndexedDB directly: a database named
  `arklight` with one out-of-line-key object store, `kv`.

Both engines hold the same thing -- `key` (string) -> `value` (the
JSON *text* of whatever the author stored) -- so a value round-trips
identically on either, and the bridge protocol never needs to know
what a value contains. `keys` deliberately fetches every key and does
the prefix filter and sort *here*, in JavaScript, for both engines:
the prefix match and ascending UTF-16 ordering the interface promises
(`DB_OPERATIONS`'s docstring) are then the same by construction
instead of by a SQL collation and an IndexedDB comparator happening to
agree.

Every operation is asynchronous. A `get`/`keys` result is written into
the `State(...)` named by `into` when it arrives. Any failure -- no
IndexedDB (some private modes), a quota error, a bridge error -- shows
ARKlight's own in-page `arkNotify` notice rather than throwing, the
same "never a thrown error, always a visible fallback" posture
`notify.py`/`clipboard_write.py` hold.

Bridge wire format (also implemented, mirrored, by `ArkDb.kt`):

    request: {"id": <int>, "op": "set"|"get"|"delete"|"keys",
              "key": <string>, "value": <JSON text>}
    reply:   {"id": <int>, "ok": true,  "result": <see below>}
             {"id": <int>, "ok": false, "error": <string>}
    result:  set/delete -> null; get -> the stored JSON text or null;
             keys -> a JSON array of every stored key.
"""

from __future__ import annotations

NAME = "db"

JS_FRAGMENT = """    db: (function () {
      var DB_NAME = "arklight";
      var STORE_NAME = "kv";
      var idbPromise = null;
      var bridgePending = {};
      var bridgeNextId = 1;
      var bridgeWired = false;

      function idbOpen() {
        if (idbPromise) return idbPromise;
        idbPromise = new Promise(function (resolve, reject) {
          if (typeof indexedDB === "undefined") {
            reject(new Error("IndexedDB is not available"));
            return;
          }
          var request = indexedDB.open(DB_NAME, 1);
          request.onupgradeneeded = function () {
            request.result.createObjectStore(STORE_NAME);
          };
          request.onsuccess = function () { resolve(request.result); };
          request.onerror = function () { reject(request.error); };
        });
        idbPromise.catch(function () { idbPromise = null; });
        return idbPromise;
      }

      function idbRun(mode, work) {
        return idbOpen().then(function (database) {
          return new Promise(function (resolve, reject) {
            var transaction = database.transaction(STORE_NAME, mode);
            var request = work(transaction.objectStore(STORE_NAME));
            transaction.oncomplete = function () { resolve(request.result); };
            transaction.onerror = function () {
              reject(transaction.error || new Error("IndexedDB transaction failed"));
            };
            transaction.onabort = function () {
              reject(transaction.error || new Error("IndexedDB transaction aborted"));
            };
          });
        });
      }

      var idbBackend = {
        set: function (key, json) {
          return idbRun("readwrite", function (s) { return s.put(json, key); })
            .then(function () { return null; });
        },
        get: function (key) {
          return idbRun("readonly", function (s) { return s.get(key); })
            .then(function (found) { return found === undefined ? null : found; });
        },
        remove: function (key) {
          return idbRun("readwrite", function (s) { return s.delete(key); })
            .then(function () { return null; });
        },
        keys: function () {
          return idbRun("readonly", function (s) { return s.getAllKeys(); });
        }
      };

      function bridgeCall(op, key, json) {
        return new Promise(function (resolve, reject) {
          var bridge = window.arkDbBridge;
          if (!bridgeWired) {
            bridge.onmessage = function (event) {
              var reply;
              try { reply = JSON.parse(event.data); } catch (err) { return; }
              var waiting = bridgePending[reply.id];
              if (!waiting) return;
              delete bridgePending[reply.id];
              if (reply.ok) waiting.resolve(reply.result);
              else waiting.reject(new Error(reply.error || "storage error"));
            };
            bridgeWired = true;
          }
          var id = bridgeNextId++;
          bridgePending[id] = { resolve: resolve, reject: reject };
          bridge.postMessage(JSON.stringify({ id: id, op: op, key: key, value: json }));
        });
      }

      var bridgeBackend = {
        set: function (key, json) { return bridgeCall("set", key, json); },
        get: function (key) { return bridgeCall("get", key, null); },
        remove: function (key) { return bridgeCall("delete", key, null); },
        keys: function () { return bridgeCall("keys", null, null); }
      };

      return function (args, store) {
        var backend = window.arkDbBridge ? bridgeBackend : idbBackend;
        var op = args.op;
        var key = args.key;
        if (op !== "keys") {
          if (key === undefined || key === null || key === "") {
            arkNotify("Can't use an empty storage key.");
            return;
          }
          key = String(key);
        }
        var work;
        if (op === "set") {
          work = backend.set(key, JSON.stringify(args.value === undefined ? null : args.value));
        } else if (op === "get") {
          if (!store) return;
          work = backend.get(key).then(function (json) {
            store.set(args.into, json === null ? null : JSON.parse(json));
          });
        } else if (op === "delete") {
          work = backend.remove(key);
        } else if (op === "keys") {
          if (!store) return;
          work = backend.keys().then(function (all) {
            var prefix = args.prefix === undefined || args.prefix === null ? "" : String(args.prefix);
            var found = [];
            for (var i = 0; i < all.length; i++) {
              if (all[i].indexOf(prefix) === 0) found.push(all[i]);
            }
            found.sort();
            store.set(args.into, found);
          });
        } else {
          return;
        }
        work.catch(function () {
          arkNotify("Couldn't reach this app's local storage -- try again.");
        });
      };
    })()"""
