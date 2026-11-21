"""Runs the Rust checker binary. No checking logic lives here.

The source text is only ever passed to the binary on stdin; no shell is used
and nothing is evaluated.
"""

import json
import os
import subprocess
import threading

EXE_NAME = "ts_subset_check.exe" if os.name == "nt" else "ts_subset_check"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAX_SOURCE_BYTES = 65536
MAX_OUTPUT_BYTES = 1024 * 1024
CHECKER_TIMEOUT = 5.0
MAX_CONCURRENT = 4
BUSY_WAIT = 5.0


class CheckerError(Exception):
    """An error that maps directly to an HTTP error response."""

    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _is_executable_file(path):
    try:
        return os.path.isfile(path) and os.access(path, os.X_OK)
    except (OSError, ValueError):
        return False


def find_default_checker(repo_root=None):
    """First existing of target/release then target/debug, else None."""
    root = repo_root or REPO_ROOT
    for profile in ("release", "debug"):
        candidate = os.path.join(root, "target", profile, EXE_NAME)
        if _is_executable_file(candidate):
            return candidate
    return None


def resolve_checker(explicit=None, repo_root=None):
    """Return the checker path to use right now, or None if unavailable."""
    if explicit:
        return explicit if _is_executable_file(explicit) else None
    return find_default_checker(repo_root)


def _reject_constant(name):
    raise ValueError("non-standard JSON constant: " + name)


class CheckerRunner:
    """Invokes the checker with bounded concurrency, time and output.

    `resolver` (tests) is a callable returning the base command list (without
    the --max-bytes arguments) or None when unavailable. Without it the
    binary path is re-resolved on every call.
    """

    def __init__(
        self,
        checker_path=None,
        resolver=None,
        timeout=CHECKER_TIMEOUT,
        busy_wait=BUSY_WAIT,
        max_concurrent=MAX_CONCURRENT,
        max_output=MAX_OUTPUT_BYTES,
        repo_root=None,
    ):
        self.checker_path = checker_path
        self.resolver = resolver
        self.timeout = timeout
        self.busy_wait = busy_wait
        self.max_output = max_output
        self.repo_root = repo_root
        self._sem = threading.BoundedSemaphore(max_concurrent)

    def command(self):
        """Base command list, or None if the checker is unavailable."""
        if self.resolver is not None:
            base = self.resolver()
            return list(base) if base else None
        path = resolve_checker(self.checker_path, self.repo_root)
        return [path] if path else None

    def available(self):
        return self.command() is not None

    def run_check(self, source):
        """Check `source`; returns the schema dict with exit_code appended.

        Raises CheckerError for every failure.
        """
        try:
            data = source.encode("utf-8")
        except UnicodeEncodeError:
            raise CheckerError(400, "invalid_request", "Source is not valid text.")
        if len(data) > MAX_SOURCE_BYTES:
            raise CheckerError(413, "too_large", "Source is too large.")

        base = self.command()
        if base is None:
            raise CheckerError(503, "checker_unavailable", "The checker is not available.")

        if not self._sem.acquire(timeout=self.busy_wait):
            raise CheckerError(503, "busy", "The checker is busy; retry shortly.")
        try:
            try:
                proc = subprocess.run(
                    base + ["--max-bytes", str(MAX_SOURCE_BYTES)],
                    input=data,
                    capture_output=True,
                    timeout=self.timeout,
                    shell=False,
                )
            except subprocess.TimeoutExpired:
                raise CheckerError(504, "checker_timeout", "The checker timed out.")
            except OSError:
                # Missing/not executable/permission denied at launch.
                raise CheckerError(503, "checker_unavailable", "The checker is not available.")
        finally:
            self._sem.release()

        return self._parse(proc.returncode, proc.stdout)

    def _parse(self, returncode, stdout):
        failed = CheckerError(502, "checker_failed", "The checker failed.")
        if returncode not in (0, 1):
            raise failed
        if len(stdout) > self.max_output:
            raise failed
        try:
            result = json.loads(stdout.decode("utf-8"), parse_constant=_reject_constant)
        except (ValueError, RecursionError):
            raise failed
        if not isinstance(result, dict):
            raise failed
        version = result.get("schema_version")
        if type(version) is not int or version != 1:
            raise failed
        if (
            not isinstance(result.get("ok"), bool)
            or not isinstance(result.get("summary"), dict)
            or not isinstance(result.get("diagnostics"), list)
            or result["ok"] != (returncode == 0)
        ):
            raise failed
        result.pop("exit_code", None)
        result["exit_code"] = returncode
        return result
