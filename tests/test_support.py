"""Shared helpers for the Python tests (contains no test cases).

The fake checker is a tiny Python script run as `[sys.executable, "-I",
script, "--max-bytes", "65536"]`; markers in the source text select its
behavior. This avoids needing the Rust binary or a platform-specific wrapper.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

FAKE_CHECKER_SOURCE = r'''
import json, sys, time
data = sys.stdin.buffer.read().decode("utf-8")
if "CRASH" in data:
    sys.stderr.write("SECRETSTDERR /secret/path\n")
    sys.exit(3)
if "SLEEP" in data:
    time.sleep(30)
if "GARBAGE" in data:
    sys.stdout.write("this is not json")
    sys.exit(0)
if "BIGOUT" in data:
    sys.stdout.write("x" * (2 * 1024 * 1024))
    sys.exit(0)
if "WRONGSCHEMA" in data:
    print(json.dumps({"schema_version": 2, "ok": True, "summary": {}, "diagnostics": []}))
    sys.exit(0)
if "TOOLERR" in data:
    print(json.dumps({"schema_version": 1, "ok": False, "error": {"code": "SC0001", "message": "x"}}))
    sys.exit(2)
bad = "bad" in data
diags = []
if bad:
    diags.append({"code": "SC2001", "severity": "error", "message": "m",
                  "span": {"start": {"line": 1, "column": 1}, "end": {"line": 1, "column": 2}}})
out = {
    "schema_version": 1,
    "ok": not bad,
    "summary": {"declarations": 1, "diagnostics": len(diags)},
    "diagnostics": diags,
    "exit_code": 99,  # must be overwritten and moved last by the wrapper
    "argv": sys.argv[1:],
    "stdin_len": len(data.encode("utf-8")),
}
print(json.dumps(out))
sys.exit(1 if bad else 0)
'''


def write_fake_checker(directory):
    """Write the fake checker script; return its path."""
    path = os.path.join(directory, "fake_checker.py")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(FAKE_CHECKER_SOURCE)
    return path


def fake_resolver(script_path):
    return lambda: [sys.executable, "-I", script_path]
