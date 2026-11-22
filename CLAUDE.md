# CLAUDE.md

Instructions for work in this repository. Read this before changing anything.

## What this is

`ts_subset_check` is a dependency-free Rust checker for a small, documented subset of TypeScript. It reads source text, reports diagnostics as JSON and never executes the input. `ts_checker_web` is a Python standard-library web wrapper that serves a one-page workbench on `127.0.0.1` and runs the Rust binary once per check. The wrapper does not reimplement the checker.

Milestone M1 (primitive `let`/`const` declarations) is the baseline. Everything after it is planned work under epic #1.

## Sources of truth

| Question | Where |
|---|---|
| What the product must do, contracts, codes, limits, milestones | [docs/PRD.md](docs/PRD.md) |
| How the code is built, one traced request, invariants, what was verified, PRD drift | [docs/architecture.md](docs/architecture.md) |
| How to build, run and smoke-test by hand | [README.md](README.md) |
| What to build next, in which order | Epic issue #1 and its sub-issues on GitHub |
| Agent roles available in this repository | [.claude/agency-agents/README.md](.claude/agency-agents/README.md) |
| Issue triage loop (manual, report-only) | [LOOP.md](LOOP.md) |

If the PRD and the code disagree, do not pick one silently: say so in the pull request and fix the wrong one in the same change.

## Setup and commands

Requirements: a Rust toolchain with `cargo` (stable; the README records 1.100.0) and Python 3. No other packages.

Run everything from the repository root.

| Purpose | Command | Seen working during preparation (2026-11-22, Windows 11, Python 3.13.14)? |
|---|---|---|
| Python tests (wrapper) | `python -m unittest discover -s tests` (`python3` on Linux) | Yes: 69 tests, `OK` |
| Start the workbench | `python -m ts_checker_web --data-dir ./data --port 8765` (port `0` picks a free port) | Yes: printed `Listening on http://127.0.0.1:<port>/`; health, page and static files answered; checks answered `checker_unavailable` because no binary was built |
| Build the checker | `cargo build --release` | **No. Not run: the preparation machine has no Rust toolchain** |
| Rust tests (checker and binary) | `cargo test` | **No. Not run, same reason** |
| Use the checker directly | `printf 'const ready: boolean = 2;\n' \| ./target/release/ts_subset_check; echo $?` | **No. Not run, same reason** |

`cargo fmt --check` and `cargo clippy` are not documented or configured in the repository yet, and there is no CI. The first ticket of the batch (#7) adds a pinned toolchain and a CI workflow; after it, the CI run is the reference result for every Rust check.

Notes:

- Set `PYTHONDONTWRITEBYTECODE=1` if you do not want `__pycache__` folders (they are ignored by Git either way).
- The Python tests do not need the Rust binary. They use a stand-in script (`tests/test_support.py`), so a green Python run says nothing about the checker.
- On Windows, stop the server with Ctrl+C. If it was started in the background, stop it by process id (`taskkill /PID <pid> /F`; from Git Bash write `//PID` and `//F`) and confirm the port is free. `kill` from Git Bash can leave it running.
- `data/`, `target/` and `.prep/` are ignored by Git. Do not commit them.
- There is no `.gitattributes` yet. On Windows with `core.autocrlf=true` the fixtures under `tests/fixtures/` are checked out with CRLF line endings, and the checker counts `\r` as a column. Do not "fix" an expected file to match a CRLF checkout; #7 pins line endings.

### If your machine has no Rust toolchain

Do not install one unless the owner asked for it. You can still read the code, run the Python tests and start the wrapper. For anything in `src/`, `tests/*.rs`, `tests/fixtures/`, `Cargo.toml` or `Cargo.lock`:

- say plainly in the pull request that the Rust checks were not run locally;
- rely on the CI run of the pull request (once #7 is merged) and link it;
- never write "tests pass" for a command you did not see pass.

## Architecture boundaries

The full list with file and line references is in [docs/architecture.md](docs/architecture.md), section 4. The short form:

- Language rules live in `src/` only. The wrapper and the page never decide what is valid TypeScript.
- Input is tokenized and parsed, never executed. No `eval`, no shelling out with source text, no running a compiler on user input inside the product.
- The contract between the two processes is one JSON document plus the exit code (PRD sections 5.2 and 5.3). Codes are never reused. New codes and newly supported syntax keep `schema_version`; a changed field shape bumps it, and then `ts_checker_web/checker.py` and `ts_checker_web/static/app.js` change in the same pull request.
- Spans are one-based, columns count Unicode scalar values, `end` is exclusive.
- Output is deterministic: same input, same bytes.
- Every recursive structure has a stated depth limit and a test one step past it. A panic or a stack overflow on any input is a bug.
- Limits that exist on both sides (the 65536-byte source cap) change together: `src/lib.rs`, `ts_checker_web/checker.py`, `ts_checker_web/server.py`, the page text, the PRD and the README.
- The wrapper binds `127.0.0.1` only, sends no CORS headers, serves static files from an exact table, and starts the checker with an argument list, no shell, and time, output and concurrency limits.
- Text from the checker or the user reaches the page through `textContent` only.
- No dependencies: no crates, no pip or npm packages, no build step for the page, no external requests, no CDN.
- No statement about speed anywhere in the repository until the timing report of issue #6 has measured it.

Changing any of these needs the owner's decision first; see the human gates in [LOOP.md](LOOP.md).

## When behaviour changes

- The examples exist in three places that must agree: `tests/fixtures/*.ts` with their `.expected.json`, `ts_checker_web/static/fixtures.json`, and the table in PRD section 6. Update all three in the same pull request, and the README smoke steps if they quote the output.
- Add the grammar you now support to PRD section 5 and move the item's status marker. Everything outside the documented grammar must still produce an explicit diagnostic with a span; nothing is silently accepted.
- Expected JSON for earlier fixtures stays byte-identical unless newly supported syntax changes it. List every such change in the pull request.

## Git workflow

- The default branch is `main`. It is not protected, so the rules here are the protection.
- One branch and one pull request per issue. Branch from the tip of `origin/main`. Name it after the issue, for example `issue-2-parser-ast`.
- Keep commits small and their messages in the imperative, in English. Reference the issue in the pull request body (`Closes #N` only when every acceptance criterion is met).
- Open pull requests as drafts. The owner merges. Do not push to `main`, force-push a shared branch, publish the crate (`publish = false`), deploy or tag a release.
- Do not edit the owner's working checkout or local files such as `.prep/`.

## Evidence before calling a ticket done

Put this in the pull request, as pasted output or a link, not as a summary:

1. The Rust checks: `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo build --locked --release` and `cargo test --locked`, either from the linked CI run or pasted from a local run with the `rustc --version` line. Until #7 is merged, a local run is the only source; if you could not run them, the ticket is not done.
2. `python -m unittest discover -s tests`: the final lines with the test count.
3. The verification commands and fixtures named in the issue, each with its observed result.
4. For each acceptance criterion: the test name or fixture that shows it.
5. For anything that changes the page: the README smoke steps, run in a local browser against a server on `127.0.0.1` with the real binary, with what was seen at each step. Browser checks are manual; there is no browser automation in this repository.
6. `git diff --stat` against `origin/main`, and a line confirming no dependency was added (`[dependencies]` in `Cargo.toml` is empty, `Cargo.lock` lists only this package, no `requirements` or `package.json` file appeared).
7. What was not verified, and why.

## Agents

Project-local roles are in `.claude/agents/` and described in [.claude/agency-agents/README.md](.claude/agency-agents/README.md). The reviewer roles (Software Architect, Code Reviewer, Codebase Onboarding Engineer, Application Security Engineer, Reality Checker) and `loop-verifier` are limited to `Read, Grep, Glob`. Use Rust Refactoring Specialist for work in `src/`, Developer Tooling Engineer for command-line, CI and harness work, Backend Architect for `ts_checker_web/*.py`, and Frontend Developer for `ts_checker_web/static/`. Where a role text conflicts with this file, this file wins.

## Loop

Issue triage runs by hand at L1, report-only: it rewrites `issue-triage-state.md` and appends to `loop-run-log.md`, and does nothing else. No scheduler exists. See [LOOP.md](LOOP.md).
