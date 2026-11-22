# Architecture, verification record and PRD drift

Written during repository preparation on 2026-11-22 against commit `5899b0f` (the only commit on `main`). It records how the code is built today, what was actually run, where the code and [PRD.md](PRD.md) disagree, and what is only planned. The PRD stays the product source of truth; this file is the engineering map.

Status words used below:

- **Implemented and run**: the behaviour was seen on 2026-11-22 during preparation.
- **Implemented, needs verification**: the code was read, but it could not be compiled or run on the preparation machine.
- **Planned**: no code exists; an issue describes it.

## 1. What was run, and what was not

The preparation machine (Windows 11, Git Bash) has Python 3.13.14 and no Rust toolchain (`cargo`, `rustc` and `rustup` are not on the path, and none was installed).

| Check | Result on 2026-11-22 |
|---|---|
| `cargo build --release` | **Not run.** No Rust toolchain. |
| `cargo test` | **Not run.** 38 test functions exist (25 in `tests/checker.rs`, 13 in `tests/cli.rs`). |
| `cargo clippy`, `cargo fmt --check` | **Not run.** Neither is documented or configured in the repository. |
| `python -m unittest discover -s tests` | Ran: `Ran 69 tests`, `OK`. These tests use a stand-in checker script (`tests/test_support.py`), not the Rust binary. |
| `python -m ts_checker_web --data-dir <scratch> --port 0` | Ran: printed `Listening on http://127.0.0.1:<port>/`. `GET /api/v1/health` answered `{"status":"ok","schema_version":1,"checker":{"available":false}}`. `POST /api/v1/check` answered 503 `checker_unavailable`. `/`, `/static/app.js`, `/static/app.css`, `/static/fixtures.json` answered 200. `/static/../x` answered 404. A POST with a foreign `Origin` answered 403 `forbidden_origin`. The data directory stayed empty. |
| Browser check of the page | **Not run.** |
| The full path: page, wrapper, Rust binary, diagnostics on the page | **Not run.** There was no binary to call. |

[README.md](../README.md#baseline-verification) records the owner's earlier runs: 38 Cargo tests and a locked release build on Ubuntu 24.04 under WSL with Rust 1.100.0, 69 Python tests on Windows and WSL, and a Chrome 157 session against the real binary. Those runs were not repeated during preparation. Until a CI run or a local run is attached to a ticket, treat everything in `src/` as **implemented, needs verification**.

No test in the repository starts the wrapper with the real binary. The two halves are tested separately: Rust tests call the library and the binary; Python tests call the wrapper with the stand-in script.

Line numbers in this file refer to commit `5899b0f`.

## 2. Shape of the system

Two processes with one narrow seam.

```
browser page                Python wrapper                     Rust checker
ts_checker_web/static/  ->  ts_checker_web/server.py       ->  target/release/ts_subset_check
(app.js, fetch)             ts_checker_web/checker.py          src/main.rs, src/lib.rs,
                            (HTTP, validation, one child       src/lexer.rs, src/checker.rs,
                             process per check)                src/json.rs
```

- **The Rust crate `ts_subset_check` owns every language rule.** It reads source text on standard input and writes one JSON document and an exit code. It has no dependencies (`Cargo.toml` has an empty `[dependencies]` table) and is built as both a library and a binary of the same name.
- **The Python package `ts_checker_web` is an adapter.** It serves the page, validates requests, starts the checker binary once per request and passes its answer through. It does not reimplement any checking (`ts_checker_web/checker.py:1-5`; PRD section 2). It uses the standard library only.
- **The page is static.** No framework and no build step. It talks only to its own origin.
- **Nothing is stored.** `--data-dir` is validated and created (`ts_checker_web/server.py:60-72`) and nothing is written into it.

### The seam between the processes

`ts_checker_web/checker.py:117-123` runs `[<binary>, "--max-bytes", "65536"]` with the source as UTF-8 bytes on standard input, `shell=False`, a 5 second timeout and captured output. The answer is accepted only if all of this holds (`_parse`, `checker.py:134-158`):

- the exit code is 0 or 1;
- standard output is at most 1 MiB and is one JSON object;
- `schema_version` is the integer 1;
- `ok` is a boolean equal to "exit code is 0", `summary` is an object, `diagnostics` is an array.

The wrapper then adds `exit_code` as the last key and answers HTTP 200. Anything else becomes 502 `checker_failed`; a timeout becomes 504; a missing binary becomes 503. Unknown extra keys in the checker's answer pass through unchanged, so an additive field needs no wrapper change. A changed `schema_version` or a third exit code needs `checker.py` and `valid()` in `static/app.js:112-114` changed in the same pull request.

## 3. One request, traced: "Check source"

1. `static/app.js:116-156`: the **Check source** button (`app.js:158`) or Ctrl/Cmd+Enter (`app.js:159-164`) calls `check()`, which sends `POST /api/v1/check` with `{"source": <text>}` and aborts after 10 seconds.
2. `server.py:214-236` (`_dispatch`): for a POST the body is read first (`_prefetch_body`, `server.py:184-212`); the `Host` header must be `127.0.0.1:<port>` or `localhost:<port>` (`_host_ok`, `server.py:168-173`); the raw path must be in the route table (`ROUTES`, `server.py:30-32`) with the right method.
3. `server.py:280-332` (`_read_source`): `Origin`, if present, must be this server; the content type must be `application/json`; exactly one numeric `Content-Length` is required; the body may be at most 262144 bytes; the JSON must be one object with the single key `source` holding a string, with no duplicate keys; the source may be at most 65536 UTF-8 bytes.
4. `checker.py:97-132` (`run_check`): the binary path is resolved on every call (`resolve_checker`, `checker.py:49-53`: the `--checker` path if given, else `target/release`, else `target/debug`); a semaphore allows 4 checker processes at once and waits up to 5 seconds for a slot; then the child process runs as described above.
5. `src/main.rs:16-53`: the binary parses `--max-bytes N` and `--help`, reads at most `N + 1` bytes of standard input, and calls `process_input` (`src/lib.rs:23-53`). Input longer than the cap gives the tool error `SC0001`, invalid UTF-8 gives `SC0002`, both with exit code 2. Otherwise `check(text)` runs.
6. `src/checker.rs:204-242` (`check`): `tokenize` (`src/lexer.rs:262-317`) turns the text into tokens with spans. The tokenizer never fails; text it cannot classify becomes an error token. `Parser::run` (`checker.rs:89-93`) calls `declaration` (`checker.rs:131-200`) until the end of input.
7. `declaration` accepts exactly `(let|const) IDENT : (string|number|boolean) = literal ;`. On the first unexpected token it calls `fail` (`checker.rs:97-120`), which records one diagnostic and skips through the next `;`. That gives at most one syntax diagnostic per statement. Only a complete statement counts as a declaration; for those, a repeated name gives `SC2002` and a literal whose kind differs from the annotation gives `SC2001` (`checker.rs:180-198`).
8. `check` sorts the diagnostics by line, column and code, and cuts the list at 50 plus one `SC9001` notice (`checker.rs:216-236`). `src/json.rs:25-50` writes the report with a fixed key order; `src/json.rs:53-59` writes tool errors.
9. Back in the page, `app.js:134-147` shows the status line and `renderDiagnostics` (`app.js:71-103`) builds the list with `textContent` only. Selecting an entry selects its span in the editor; `toIndex` (`app.js:45-60`) converts the checker's code-point columns to the UTF-16 indexes the browser needs.

There is no storage step and no state between requests.

## 4. Boundaries and invariants

An implementer must keep these unless a ticket says otherwise and the PRD is changed in the same pull request.

1. **Input is never executed.** The checker tokenizes and parses. Nothing in either process evaluates source text (PRD sections 2 and 10).
2. **Language rules live in Rust only.** The wrapper and the page never inspect source text to decide what is valid.
3. **The contract is the JSON document plus the exit code** (PRD sections 5.2 and 5.3): `schema_version`, `ok`, `summary`, `diagnostics`, with codes that are never reused. New codes and newly supported syntax do not change `schema_version`; a changed field shape does (PRD section 9).
4. **Spans are one-based, columns count Unicode scalar values, `end` is exclusive, and no span is empty** (`src/lexer.rs:7-8`, `lexer.rs:16`). Only `\n` starts a new line; `\r` is whitespace that occupies a column.
5. **Output is deterministic.** The same input gives the same bytes. Diagnostics are sorted and capped at 50 plus `SC9001`.
6. **At most one syntax diagnostic per statement**, and text skipped during recovery is silent (`src/lexer.rs:3-5`).
7. **Limits exist on both sides of the seam and must stay in step.** The 65536-byte source cap is written in `src/lib.rs:10`, `ts_checker_web/checker.py:15` and `ts_checker_web/server.py:17`, and appears in the page's error text (`static/app.js:22`). There is no shared definition.
8. **The wrapper listens on `127.0.0.1` only** (`server.py:14`), sends no CORS headers, serves static files from an exact table with no path built from the request (`server.py:22-27`), and adds `nosniff`, `no-store`, a restrictive Content-Security-Policy and `no-referrer` to every response (`server.py:34-43`).
9. **The checker is started with an argument list and no shell**, with time, output and concurrency limits (`checker.py:15-19`, `checker.py:117-123`). Error responses never contain the child's standard error or a file path.
10. **Text from the checker reaches the page through `textContent` only.**
11. **No dependencies.** No crates, no pip packages, no npm packages, no build step for the page, no external requests.

## 5. Where things are

| Path | Role |
|---|---|
| `src/lexer.rs` | `Pos`, `Span`, `Token`, `TokenKind`, `tokenize`. |
| `src/checker.rs` | `Diagnostic`, `Report`, the statement parser and the two type rules in one pass. There is no syntax tree: the parser decides and reports as it reads. |
| `src/json.rs` | Hand-written JSON writer: `escape`, `report_to_json`, `error_to_json`. |
| `src/lib.rs` | `process_input`, `Outcome`, `DEFAULT_MAX_BYTES`. |
| `src/main.rs` | Command line: arguments, bounded read, exit code. |
| `tests/checker.rs` | 25 library tests: fixtures, one or more tests per code, recovery, truncation, columns, line endings, determinism. |
| `tests/cli.rs` | 13 tests that run the built binary: exit codes, exact JSON, the size cap, usage errors. |
| `tests/fixtures/` | `valid`, `mismatch`, `duplicate`, `unsupported`, each a `.ts` file with an `.expected.json` compared byte for byte by `fixtures_match_expected_output` (`tests/checker.rs:93-109`). |
| `ts_checker_web/__main__.py` | Arguments, start-up line, exit codes 0, 1 (cannot bind) and 2 (bad argument). |
| `ts_checker_web/server.py` | Routes, request validation, security headers, static files. |
| `ts_checker_web/checker.py` | Finding and running the checker, mapping failures to HTTP errors. |
| `ts_checker_web/static/` | `index.html`, `app.js`, `app.css`, `fixtures.json` (three examples for the page). |
| `tests/test_checker.py` | 20 tests of the runner with the stand-in script. |
| `tests/test_server.py` | 49 tests of the HTTP layer on an ephemeral port. |
| `tests/test_support.py` | The stand-in checker script. No test cases. |

## 6. PRD compared with the code

| PRD item | Status | Evidence |
|---|---|---|
| 5.1 grammar; 5.3 codes `SC1001` to `SC1006`, `SC2001`, `SC2002`, `SC9001`; recovery | Implemented, needs verification | `src/checker.rs:97-200`, `src/lexer.rs`; tests in `tests/checker.rs` were not run here |
| 5.2 command line, exit codes; `SC0001`, `SC0002` | Implemented, needs verification | `src/main.rs:16-53`, `src/lib.rs:23-53`, `tests/cli.rs` |
| 5.4 HTTP API, error codes, Host and Origin checks, security headers | Implemented and run | 69 Python tests passed; health, check, static, traversal and foreign-origin requests were sent to a running server |
| 5.5 page contract | Implemented, read only | `static/app.js`, `static/index.html`; no browser was used during preparation |
| 6 fixtures `valid`, `golden`, `unsupported`, `duplicate`, `empty` | Implemented, needs verification | `tests/fixtures/` holds four of them (`golden` is named `mismatch`); `empty` is a test, not a file (`tests/checker.rs:68`) |
| 7 layout and accessibility | Not verified | needs a browser |
| 8 missing checker gives 503 and the path is resolved per request | Implemented and run | seen on the running server; `test_checker_resolved_per_request` |
| 11 A1 to A5, A10 | Needs verification | depend on the Rust build |
| 11 A6 to A8 | Implemented and run | Python tests |
| 11 A9 | Not verified | needs a browser |
| 14 P1 to P5 | Planned | issues #2 to #6 under epic #1; no code |
| `--data-dir` storage | Reserved | created, never written |

## 7. Drift and gaps found

1. **PRD section 13 contradicted the README.** It said no test was recorded as passing, while the README records the owner's runs. The status line in section 13 now points at both records. (Corrected in the same change as this file.)
2. **Source comments point at a document that is not in the repository.** `src/lib.rs:2` says "See the M1 contract" and `src/json.rs:24` and `src/json.rs:52` cite "Section 4.1" and "Section 4.2". The contract they mean was a working file that is ignored by Git (`.prep/`). The matching text in the repository is PRD sections 5.1 to 5.3. Fix the comments when the files are next changed.
3. **The examples exist in three hand-kept copies:** `tests/fixtures/*.ts`, `ts_checker_web/static/fixtures.json` and the table in PRD section 6. Nothing checks that they agree. Any change to checker behaviour must update all three; `#NEW-A` adds a test for the first two.
4. **No automated check joins the two halves.** A change to the JSON shape can pass both test suites and still break the page. `#NEW-A` adds that check.
5. **No continuous integration, no pinned toolchain, no lint or format configuration.** There is no `.github/` directory and no `rust-toolchain.toml`. On a machine without Rust nothing in `src/` can be verified. `#NEW-A` closes this first.
6. **Known, documented divergence from TypeScript** (PRD section 5.1): numbers with leading zeros such as `007` are accepted, and comments are reported as `SC1004`. Issue #2 makes comments supported; the leading-zero case stays until the comparison in issue #6 lists it.
7. **The page's text is tied to milestone M1.** The lead paragraph in `static/index.html:13` and the status text `No issues (N declarations)` in `static/app.js:140` describe declarations only. Each language ticket that widens the subset must check this text.

## 8. Risks for the planned work

1. **The parser has no syntax tree.** Issue #2 replaces `src/checker.rs` rather than extending it. The M1 fixtures `valid`, `mismatch` and `duplicate` must stay byte-identical through that rewrite; `unsupported` changes on purpose.
2. **Recursion on hostile input.** A recursive-descent parser on 64 KiB of `(` or `{` overflows the stack unless nesting is limited. Every ticket that adds a recursive structure (blocks, parentheses, nested types, instantiation) must state its limit and test one step past it.
3. **The wrapper is stateless: one request, one process, one string.** Multi-file projects and a long-lived incremental service (issue #5, `#NEW-B`, `#NEW-C`) need new request shapes and a supervised child process. Path handling is new attack surface.
4. **The comparison with the reference compiler (issue #6) needs an external tool.** The PRD requires the owner's approval before it is staged, and its version is an open choice (PRD section 15). That ticket cannot start without the decision.
5. **Windows process handling.** The server sets `allow_reuse_address = False` (`server.py:91`). A server stopped with `kill` from Git Bash can keep running; stop it with Ctrl+C or by process id (`taskkill /PID <pid> /F`) and confirm the port is free.

## 9. Planned work

The backlog is epic #1. Its child issues, in dependency order: `#NEW-A` (pinned toolchain, CI and an end-to-end check of the baseline), #2 (parser, syntax tree, names), #3 (objects, arrays, unions), #4 (generics), #5 (multi-file project mode), `#NEW-B` (incremental check service), `#NEW-C` (project view in the workbench), #6 (reference-compiler comparison and timing report), `#NEW-D` (release check). Each issue carries its own scope, acceptance criteria and verification commands. Nothing in that list is implemented.
