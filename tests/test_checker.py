"""Unit tests for ts_checker_web.checker (runner, error mapping, resolution)."""

import os
import shutil
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_support import fake_resolver, write_fake_checker  # noqa: E402

from ts_checker_web import checker  # noqa: E402
from ts_checker_web.checker import CheckerError, CheckerRunner  # noqa: E402


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tscw-chk-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.script = write_fake_checker(self.tmp)
        self.runner = CheckerRunner(resolver=fake_resolver(self.script), timeout=5.0, busy_wait=0.2)

    def assertCheckerError(self, source, status, code):
        with self.assertRaises(CheckerError) as ctx:
            self.runner.run_check(source)
        self.assertEqual((ctx.exception.status, ctx.exception.code), (status, code))
        return ctx.exception

    def test_success_exit_0_appends_exit_code_last(self):
        result = self.runner.run_check("let a: number = 1;")
        self.assertTrue(result["ok"])
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(list(result)[-1], "exit_code")
        self.assertEqual(result["argv"], ["--max-bytes", "65536"])
        self.assertEqual(result["stdin_len"], len("let a: number = 1;"))

    def test_success_exit_1_with_diagnostics(self):
        result = self.runner.run_check("bad")
        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(list(result)[-1], "exit_code")

    def test_non_ascii_source_sent_as_utf8(self):
        result = self.runner.run_check("é\U0001F600")
        self.assertEqual(result["stdin_len"], 6)

    def test_crash_maps_to_502_without_stderr(self):
        err = self.assertCheckerError("CRASH", 502, "checker_failed")
        self.assertNotIn("SECRET", err.message)

    def test_exit_2_tool_error_maps_to_502(self):
        self.assertCheckerError("TOOLERR", 502, "checker_failed")

    def test_unparseable_output_maps_to_502(self):
        self.assertCheckerError("GARBAGE", 502, "checker_failed")

    def test_oversize_output_maps_to_502(self):
        self.assertCheckerError("BIGOUT", 502, "checker_failed")

    def test_wrong_schema_version_maps_to_502(self):
        self.assertCheckerError("WRONGSCHEMA", 502, "checker_failed")

    def test_timeout_maps_to_504_and_releases_slot(self):
        runner = CheckerRunner(resolver=fake_resolver(self.script), timeout=0.8, busy_wait=0.2, max_concurrent=1)
        with self.assertRaises(CheckerError) as ctx:
            runner.run_check("SLEEP")
        self.assertEqual((ctx.exception.status, ctx.exception.code), (504, "checker_timeout"))
        runner.timeout = 5.0
        self.assertEqual(runner.run_check("ok")["exit_code"], 0)  # slot was released

    def test_unavailable_when_resolver_returns_none(self):
        runner = CheckerRunner(resolver=lambda: None)
        self.assertFalse(runner.available())
        with self.assertRaises(CheckerError) as ctx:
            runner.run_check("x")
        self.assertEqual((ctx.exception.status, ctx.exception.code), (503, "checker_unavailable"))

    def test_unlaunchable_binary_maps_to_503(self):
        missing = os.path.join(self.tmp, "does-not-exist")
        runner = CheckerRunner(resolver=lambda: [missing])
        with self.assertRaises(CheckerError) as ctx:
            runner.run_check("x")
        self.assertEqual((ctx.exception.status, ctx.exception.code), (503, "checker_unavailable"))
        self.assertNotIn(self.tmp, ctx.exception.message)

    def test_busy_when_all_slots_taken(self):
        runner = CheckerRunner(resolver=fake_resolver(self.script), busy_wait=0.2, max_concurrent=1)
        self.assertTrue(runner._sem.acquire(timeout=1))
        try:
            with self.assertRaises(CheckerError) as ctx:
                runner.run_check("x")
            self.assertEqual((ctx.exception.status, ctx.exception.code), (503, "busy"))
        finally:
            runner._sem.release()
        self.assertEqual(runner.run_check("x")["exit_code"], 0)

    def test_concurrency_never_exceeds_limit(self):
        runner = CheckerRunner(resolver=fake_resolver(self.script), busy_wait=10.0, max_concurrent=2)
        results = []

        def work():
            results.append(runner.run_check("ok")["exit_code"])

        threads = [threading.Thread(target=work) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        self.assertEqual(results, [0] * 5)

    def test_source_limits_enforced_in_runner(self):
        self.assertCheckerError("a" * 65537, 413, "too_large")
        self.assertEqual(self.runner.run_check("a" * 65536)["exit_code"], 0)
        self.assertCheckerError("\ud800", 400, "invalid_request")


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tscw-root-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def make(self, profile):
        directory = os.path.join(self.root, "target", profile)
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, checker.EXE_NAME)
        with open(path, "wb") as handle:
            handle.write(b"")
        os.chmod(path, 0o755)
        return path

    def test_none_when_nothing_built(self):
        self.assertIsNone(checker.find_default_checker(self.root))

    def test_debug_found_and_release_preferred(self):
        debug = self.make("debug")
        self.assertEqual(checker.find_default_checker(self.root), debug)
        release = self.make("release")
        self.assertEqual(checker.find_default_checker(self.root), release)

    def test_explicit_path(self):
        debug = self.make("debug")
        self.assertEqual(checker.resolve_checker(debug, self.root), debug)
        self.assertIsNone(checker.resolve_checker(os.path.join(self.root, "nope"), self.root))
        # An explicit but missing path does not fall back to the defaults.
        self.make("release")
        self.assertIsNone(checker.resolve_checker(os.path.join(self.root, "nope"), self.root))

    def test_directory_is_not_a_checker(self):
        self.assertIsNone(checker.resolve_checker(self.root, self.root))

    def test_re_resolved_per_call(self):
        runner = CheckerRunner(repo_root=self.root)
        self.assertFalse(runner.available())
        self.make("debug")
        self.assertTrue(runner.available())

    def test_exe_name_matches_platform(self):
        self.assertEqual(checker.EXE_NAME.endswith(".exe"), os.name == "nt")


if __name__ == "__main__":
    unittest.main()
