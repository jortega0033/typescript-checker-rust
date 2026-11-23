"""Tests for ts_checker_web.server and __main__ using a fake checker script.

A real server is started on an ephemeral 127.0.0.1 port in a thread; the data
dir and static files live in a disposable temp directory.
"""

import contextlib
import http.client
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_support import fake_resolver, write_fake_checker  # noqa: E402

from ts_checker_web import __main__ as web_main  # noqa: E402
from ts_checker_web import server as server_mod  # noqa: E402
from ts_checker_web.checker import CheckerRunner  # noqa: E402

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tscw-srv-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.data_dir = os.path.join(self.tmp, "data", "nested")
        self.static_dir = os.path.join(self.tmp, "static")
        os.makedirs(self.static_dir)
        for name, text in {
            "index.html": "<!doctype html><title>t</title>",
            "tokens.css": ":root{}",
            "app.css": "body{}",
            "app.js": "//js",
            "fixtures.json": '{"fixtures":[]}',
            "secret.txt": "TOPSECRET",
        }.items():
            with open(os.path.join(self.static_dir, name), "w", encoding="utf-8") as handle:
                handle.write(text)
        patcher = mock.patch.object(server_mod, "STATIC_DIR", self.static_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.script = write_fake_checker(self.tmp)
        self.runner = CheckerRunner(resolver=fake_resolver(self.script), timeout=5.0, busy_wait=0.3, max_concurrent=2)
        self.start_server()

    def start_server(self, runner=None):
        self.server = server_mod.create_server(self.data_dir, 0, runner=runner or self.runner)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server, self.server, self.thread)

    @staticmethod
    def stop_server(server, thread):
        server.shutdown()
        server.server_close()
        thread.join(5)

    # ---- raw client ----

    def request(self, method, path, body=None, headers=None, host="default"):
        """Low-level request: caller controls Host and every other header."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            if host == "default":
                host = "127.0.0.1:%d" % self.port
            if host is not None:
                conn.putheader("Host", host)
            for key, value in (headers or {}).items():
                conn.putheader(key, value)
            conn.endheaders(body)
            resp = conn.getresponse()
            data = resp.read()
            return resp.status, {k.lower(): v for k, v in resp.getheaders()}, data
        finally:
            conn.close()

    def post(self, payload, headers=None, host="default", raw=None):
        body = raw if raw is not None else json.dumps(payload).encode("utf-8")
        hdrs = {"Content-Type": "application/json", "Content-Length": str(len(body))}
        hdrs.update(headers or {})
        hdrs = {k: v for k, v in hdrs.items() if v is not None}
        return self.request("POST", "/api/v1/check", body, hdrs, host)

    def check(self, source, **kwargs):
        status, headers, data = self.post({"source": source}, **kwargs)
        return status, json.loads(data)

    def assertError(self, status_body, status, code):
        got_status, body = status_body
        self.assertEqual(got_status, status, body)
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(set(body), {"error"})
        self.assertNotIn(self.tmp, json.dumps(body))


class HealthAndHeaderTests(ServerTestCase):
    def test_health_available(self):
        status, headers, data = self.request("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(data), {"status": "ok", "schema_version": 1, "checker": {"available": True}}
        )
        self.assertTrue(headers["content-type"].startswith("application/json"))
        self.assertNotIn(self.tmp.encode(), data)
        self.assertNotIn(sys.executable.encode(), data)

    def test_health_unavailable_and_check_503(self):
        self.runner.resolver = lambda: None
        _, _, data = self.request("GET", "/api/v1/health")
        self.assertEqual(json.loads(data)["checker"], {"available": False})
        self.assertError(self.check("x"), 503, "checker_unavailable")

    def test_checker_resolved_per_request(self):
        self.runner.resolver = lambda: None
        self.assertError(self.check("x"), 503, "checker_unavailable")
        self.runner.resolver = fake_resolver(self.script)
        status, body = self.check("x")
        self.assertEqual(status, 200)

    def test_security_headers_on_every_kind_of_response(self):
        responses = [
            self.request("GET", "/"),
            self.request("GET", "/api/v1/health"),
            self.request("GET", "/nope"),
            self.request("GET", "/static/secret.txt"),
            self.request("POST", "/api/v1/health"),
            self.request("OPTIONS", "/api/v1/check"),
            self.request("GET", "/", host="evil.example"),
            self.post({"source": "x"}),
            self.post({"bad": 1}),
        ]
        for status, headers, _ in responses:
            self.assertEqual(headers["cache-control"], "no-store", status)
            self.assertEqual(headers["x-content-type-options"], "nosniff")
            self.assertEqual(headers["content-security-policy"], CSP)
            self.assertEqual(headers["referrer-policy"], "no-referrer")
            self.assertFalse([h for h in headers if h.startswith("access-control-")], headers)

    def test_listens_on_loopback_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")


class StaticTests(ServerTestCase):
    def test_allowlisted_files(self):
        expected = {
            "/": ("text/html; charset=utf-8", b"<!doctype html><title>t</title>"),
            "/static/tokens.css": ("text/css; charset=utf-8", b":root{}"),
            "/static/app.css": ("text/css; charset=utf-8", b"body{}"),
            "/static/app.js": ("text/javascript; charset=utf-8", b"//js"),
            "/static/fixtures.json": ("application/json; charset=utf-8", b'{"fixtures":[]}'),
        }
        for path, (ctype, body) in expected.items():
            status, headers, data = self.request("GET", path)
            self.assertEqual(status, 200, path)
            self.assertEqual(headers["content-type"], ctype, path)
            self.assertEqual(data, body, path)

    def test_everything_else_under_static_is_404(self):
        for path in [
            "//static/app.css",
            "/static/secret.txt",
            "/static/",
            "/static",
            "/static/index.html",
            "/static/../server.py",
            "/static/%2e%2e/server.py",
            "/static/..%2fserver.py",
            "/static/%2e%2e%5cserver.py",
            "/static/app.css/",
            "/static/APP.CSS",
            "/static//app.css",
            "/index.html",
            "/../../etc/passwd",
            "/static/app.css%00.txt",
        ]:
            status, _, data = self.request("GET", path)
            self.assertEqual(status, 404, path)
            self.assertNotIn(b"TOPSECRET", data)
            self.assertEqual(json.loads(data)["error"]["code"], "not_found")

    def test_query_string_ignored_for_known_path(self):
        self.assertEqual(self.request("GET", "/static/app.css?v=1")[0], 200)

    def test_missing_static_file_is_404(self):
        os.remove(os.path.join(self.static_dir, "app.js"))
        self.assertEqual(self.request("GET", "/static/app.js")[0], 404)


class RoutingTests(ServerTestCase):
    def test_not_found_shape(self):
        status, headers, data = self.request("GET", "/api/v1/nothing")
        self.assertEqual(status, 404)
        body = json.loads(data)
        self.assertEqual(set(body), {"error"})
        self.assertEqual(set(body["error"]), {"code", "message"})

    def test_wrong_method_405_with_allow(self):
        status, headers, _ = self.request("POST", "/api/v1/health", b"{}", {"Content-Length": "2"})
        self.assertEqual((status, headers["allow"]), (405, "GET"))
        status, headers, _ = self.request("GET", "/api/v1/check")
        self.assertEqual((status, headers["allow"]), (405, "POST"))
        status, headers, _ = self.request("DELETE", "/")
        self.assertEqual((status, headers["allow"]), (405, "GET"))
        status, headers, _ = self.request("POST", "/", b"", {"Content-Length": "0"})
        self.assertEqual((status, headers["allow"]), (405, "GET"))

    def test_options_is_405_without_cors(self):
        for path in ("/", "/api/v1/check", "/nope"):
            status, headers, _ = self.request(
                "OPTIONS", path, headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"}
            )
            self.assertEqual(status, 405, path)
            self.assertFalse([h for h in headers if h.startswith("access-control-")])

    def test_unknown_method_gets_json_error(self):
        status, headers, data = self.request("BREW", "/")
        self.assertIn(status, (405, 501))
        self.assertIn("error", json.loads(data))
        self.assertEqual(headers["cache-control"], "no-store")

    def test_head_on_get_route_is_405(self):
        self.assertEqual(self.request("HEAD", "/")[0], 405)


class HostOriginTests(ServerTestCase):
    def test_bad_host_rejected_on_get(self):
        for host in ["evil.example", "127.0.0.1", "localhost", "127.0.0.1:1", "localhost:%d.evil" % 1, "", None,
                     "evil.example:%d" % 0]:
            status, _, data = self.request("GET", "/api/v1/health", host=host)
            self.assertEqual(status, 403, host)
            self.assertEqual(json.loads(data)["error"]["code"], "forbidden_origin")
        self.assertEqual(self.request("GET", "/", host="evil.example")[0], 403)

    def test_bad_host_rejected_on_post(self):
        self.assertError(self.check("x", host="evil.example"), 403, "forbidden_origin")
        self.assertError(self.check("x", host="127.0.0.1:%d" % (self.port + 1)), 403, "forbidden_origin")

    def test_good_hosts(self):
        for host in ("127.0.0.1:%d" % self.port, "localhost:%d" % self.port):
            self.assertEqual(self.request("GET", "/api/v1/health", host=host)[0], 200)
            self.assertEqual(self.check("x", host=host)[0], 200)

    def test_origin_validation(self):
        for origin in ["http://evil.example", "null", "http://127.0.0.1", "https://127.0.0.1:%d" % self.port,
                       "http://127.0.0.1:%d.evil.example" % self.port, "http://localhost:1", ""]:
            self.assertError(self.check("x", headers={"Origin": origin}), 403, "forbidden_origin")
        for origin in ("http://127.0.0.1:%d" % self.port, "http://localhost:%d" % self.port):
            self.assertEqual(self.check("x", headers={"Origin": origin})[0], 200)

    def test_no_origin_header_is_allowed(self):
        self.assertEqual(self.check("x")[0], 200)


class CheckRequestTests(ServerTestCase):
    def test_success_valid_source(self):
        status, body = self.check("let a: number = 1;")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["schema_version"], 1)
        self.assertEqual(body["exit_code"], 0)
        self.assertEqual(list(body)[-1], "exit_code")
        self.assertEqual(body["argv"], ["--max-bytes", "65536"])

    def test_diagnostics_are_still_http_200(self):
        status, body = self.check("bad")
        self.assertEqual(status, 200)
        self.assertFalse(body["ok"])
        self.assertEqual(body["exit_code"], 1)
        self.assertEqual(list(body)[-1], "exit_code")

    def test_content_type_with_params_is_accepted(self):
        status, _, _ = self.post({"source": "x"}, headers={"Content-Type": "application/json; charset=utf-8"})
        self.assertEqual(status, 200)
        status, _, _ = self.post({"source": "x"}, headers={"Content-Type": "Application/JSON"})
        self.assertEqual(status, 200)

    def test_wrong_or_missing_content_type_415(self):
        for ctype in ["text/plain", "application/x-www-form-urlencoded", "application/jsonx", None]:
            status, _, data = self.post({"source": "x"}, headers={"Content-Type": ctype})
            self.assertEqual(status, 415, ctype)
            self.assertEqual(json.loads(data)["error"]["code"], "unsupported_media_type")

    def test_missing_content_length_411(self):
        status, _, data = self.post(None, raw=b'{"source":"x"}', headers={"Content-Length": None})
        self.assertEqual(status, 411)
        self.assertEqual(json.loads(data)["error"]["code"], "length_required")

    def test_chunked_is_411(self):
        status, _, data = self.post(None, raw=b'{"source":"x"}',
                                    headers={"Content-Length": None, "Transfer-Encoding": "chunked"})
        self.assertEqual(status, 411)

    def test_bad_content_length_400(self):
        for value in ["abc", "-1", "1 2", "0x10"]:
            status, _, data = self.post(None, raw=b"{}", headers={"Content-Length": value})
            self.assertEqual(status, 400, value)

    def test_declared_body_over_cap_413(self):
        # A declared (not sent) length beyond the drain limit is refused up front.
        status, _, data = self.request(
            "POST", "/api/v1/check", None,
            {"Content-Type": "application/json", "Content-Length": "10000000"},
        )
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(data)["error"]["code"], "too_large")

    def test_actual_body_over_cap_413(self):
        raw = b'{"source":"' + b"a" * 262200 + b'"}'
        status, _, data = self.post(None, raw=raw)
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(data)["error"]["code"], "too_large")

    def test_short_body_is_400(self):
        # Content-Length larger than the bytes actually sent, then EOF.
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            conn.putrequest("POST", "/api/v1/check", skip_host=True, skip_accept_encoding=True)
            conn.putheader("Host", "127.0.0.1:%d" % self.port)
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", "50")
            conn.endheaders(b'{"source"')
            conn.sock.shutdown(1)  # SHUT_WR: tell the server no more bytes are coming
            resp = conn.getresponse()
            self.assertEqual(resp.status, 400)
            resp.read()
        finally:
            conn.close()

    def test_source_size_limit_in_utf8_bytes(self):
        self.assertEqual(self.check("a" * 65536)[0], 200)
        self.assertError(self.check("a" * 65537), 413, "too_large")
        # 32769 two-byte characters = 65538 bytes though only 32769 characters.
        self.assertError(self.check("é" * 32769), 413, "too_large")
        self.assertEqual(self.check("é" * 32768)[0], 200)

    def test_invalid_shapes_400(self):
        bad_bodies = [
            b"",
            b"not json",
            b"[]",
            b'"source"',
            b"null",
            b"{}",
            b'{"source":1}',
            b'{"source":null}',
            b'{"source":["x"]}',
            b'{"source":"x","extra":1}',
            b'{"src":"x"}',
            b'{"source":"a","source":"b"}',
            b'{"source":NaN}',
            b'{"source":"\\ud800"}',
            b"\xff\xfe",
            b"[" * 100000,
        ]
        for raw in bad_bodies:
            status, _, data = self.post(None, raw=raw)
            self.assertEqual(status, 400, raw[:40])
            body = json.loads(data)
            self.assertEqual(body["error"]["code"], "invalid_request")
            self.assertNotIn(self.tmp, data.decode())

    def test_empty_source_is_allowed(self):
        self.assertEqual(self.check("")[0], 200)

    def test_checker_failures_map_to_statuses(self):
        self.assertError(self.check("CRASH"), 502, "checker_failed")
        self.assertError(self.check("GARBAGE"), 502, "checker_failed")
        self.assertError(self.check("BIGOUT"), 502, "checker_failed")
        self.assertError(self.check("WRONGSCHEMA"), 502, "checker_failed")
        self.assertError(self.check("TOOLERR"), 502, "checker_failed")

    def test_error_responses_never_leak_stderr_or_paths(self):
        _, _, data = self.post({"source": "CRASH"})
        self.assertNotIn(b"SECRET", data)
        self.assertNotIn(b"/secret/path", data)

    def test_timeout_504(self):
        self.runner.timeout = 0.8
        self.assertError(self.check("SLEEP"), 504, "checker_timeout")
        self.runner.timeout = 5.0
        self.assertEqual(self.check("x")[0], 200)  # server still healthy

    def test_busy_503(self):
        sem = self.runner._sem
        held = [sem.acquire(timeout=1) for _ in range(2)]
        self.assertTrue(all(held))
        try:
            self.assertError(self.check("x"), 503, "busy")
        finally:
            for _ in held:
                sem.release()
        self.assertEqual(self.check("x")[0], 200)

    def test_concurrent_requests(self):
        results = []

        def work():
            results.append(self.check("x")[0])

        threads = [threading.Thread(target=work) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        self.assertEqual(sorted(results), [200] * 6)


class DataDirAndLifecycleTests(ServerTestCase):
    def test_data_dir_created_and_left_empty(self):
        self.assertTrue(os.path.isdir(self.data_dir))
        self.check("x")
        self.request("GET", "/api/v1/health")
        self.assertEqual(os.listdir(self.data_dir), [])

    def test_existing_data_dir_reused(self):
        server = server_mod.create_server(self.data_dir, 0, runner=self.runner)
        server.server_close()

    def test_data_dir_validation(self):
        file_path = os.path.join(self.tmp, "a-file")
        with open(file_path, "w") as handle:
            handle.write("x")
        for bad in ["", "   ", file_path, os.path.join(file_path, "child")]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                server_mod.create_server(bad, 0, runner=self.runner)

    def test_port_validation(self):
        for bad in (-1, 65536, "80", None, True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                server_mod.create_server(self.data_dir, bad, runner=self.runner)

    def test_create_server_with_checker_path_uses_default_runner(self):
        server = server_mod.create_server(self.data_dir, 0, os.path.join(self.tmp, "missing"))
        try:
            self.assertFalse(server.runner.available())
        finally:
            server.server_close()

    def test_shutdown_and_close_free_the_port(self):
        server = server_mod.create_server(self.data_dir, 0, runner=self.runner)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        self.stop_server(server, thread)
        self.assertFalse(thread.is_alive())
        self.assertTrue(server.daemon_threads)


class MainArgumentTests(unittest.TestCase):
    def run_main(self, argv):
        err = io.StringIO()
        out = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            try:
                code = web_main.main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tscw-main-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_missing_required_args_exit_2(self):
        self.assertEqual(self.run_main([])[0], 2)
        self.assertEqual(self.run_main(["--port", "0"])[0], 2)
        self.assertEqual(self.run_main(["--data-dir", self.tmp])[0], 2)

    def test_bad_port_exit_2(self):
        for port in ["abc", "-1", "65536", "", "1.5", "99999999999"]:
            self.assertEqual(self.run_main(["--data-dir", self.tmp, "--port", port])[0], 2, port)

    def test_empty_data_dir_exit_2(self):
        self.assertEqual(self.run_main(["--data-dir", "", "--port", "0"])[0], 2)

    def test_data_dir_that_is_a_file_exit_2(self):
        path = os.path.join(self.tmp, "f")
        with open(path, "w") as handle:
            handle.write("x")
        code, _, err = self.run_main(["--data-dir", path, "--port", "0"])
        self.assertEqual(code, 2)
        self.assertTrue(err)

    def test_unknown_and_abbreviated_args_exit_2(self):
        self.assertEqual(self.run_main(["--data-dir", self.tmp, "--port", "0", "--bogus"])[0], 2)
        self.assertEqual(self.run_main(["--data-dir", self.tmp, "--po", "0"])[0], 2)

    def test_startup_prints_listening_line_and_ctrl_c_exits_0(self):
        data_dir = os.path.join(self.tmp, "new", "dir")
        real_create = web_main.create_server
        servers = []

        def create(*args):
            server = real_create(*args)
            servers.append(server)
            server.serve_forever = mock.Mock(side_effect=KeyboardInterrupt)
            return server

        with mock.patch.object(web_main, "create_server", create):
            code, out, _ = self.run_main(["--data-dir", data_dir, "--port", "0"])
        self.assertEqual(code, 0)
        port = servers[0].server_address[1]
        self.assertEqual(out, "Listening on http://127.0.0.1:%d/\n" % port)
        self.assertTrue(os.path.isdir(data_dir))
        self.assertEqual(os.listdir(data_dir), [])
        self.assertEqual(servers[0].socket.fileno(), -1)  # server_close() ran


if __name__ == "__main__":
    unittest.main()
