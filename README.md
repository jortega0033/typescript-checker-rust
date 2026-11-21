# TypeScript Checker in Rust

A small, dependency-free Rust type checker for one explicit TypeScript subset, plus a local browser workbench to see what it reports. Intended for learning what a checker does and comparing deterministic diagnostics against a known subset. Input is only parsed, never executed.

M1 checks a small declaration subset using the Rust CLI. See the baseline verification below.

## Supported subset (M1)

```
let|const name: string|number|boolean = <literal>;
```
Literals: quoted strings, decimal numbers (optional leading `-` and fraction), `true`, `false`. Anything else gets an explicit unsupported or syntax diagnostic (codes `SC1001`-`SC1006`); type mismatches are `SC2001`, redeclaration is `SC2002`. Spans are one-based (`line`, `column`, end exclusive). Full contracts are in [docs/PRD.md](docs/PRD.md).

## Requirements
Rust (stable, with `cargo`) and Python 3. No third-party packages.

## Build
```
cargo build --release
```
Produces `target/release/ts_subset_check` (`.exe` on Windows).

## Use the checker directly
Linux:
```
printf 'const ready: boolean = 2;\n' | ./target/release/ts_subset_check; echo $?
```
Windows (PowerShell):
```
'const ready: boolean = 2;' | .\target\release\ts_subset_check.exe; $LASTEXITCODE
```
Exit codes: `0` no diagnostics, `1` diagnostics, `2` usage, UTF-8 or size error (cap 65536 bytes, `--max-bytes N` to lower or change).

## Launch the web workbench
Run from the repository root. `--data-dir` is required and is created if missing (M1 stores nothing in it). Port `0` picks a free port.

Linux:
```
python3 -m ts_checker_web --data-dir ./data --port 8765
```
Windows:
```
python -m ts_checker_web --data-dir .\data --port 8765
```
Optional `--checker <path>` selects the binary; the default is `target/release/ts_subset_check`, then `target/debug/ts_subset_check`. The server binds `127.0.0.1` only and prints `Listening on http://127.0.0.1:<port>/`.

## M1 smoke steps
1. Build the checker and start the server as above; open the printed URL.
2. `GET /api/v1/health` shows `"checker":{"available":true}`.
3. Choose **Type mismatch** in the example list, press **Load example**, then **Check source**. Expect status `1 issue found` and one entry `SC2001 2:24–2:25 Type 'number' is not assignable to type 'boolean'.`.
4. Load **Valid declarations**, check: expect `No issues (3 declarations)`.
5. Load **Unsupported syntax**, check: expect `SC1003`, `SC1006`, `SC1004` entries (no silent acceptance).
6. Press **Undo load** to restore your previous text; select a diagnostic and confirm the span is highlighted in the editor.
7. Resize to 800x600: the page has no horizontal scrolling.
8. Rename the binary temporarily: the status reports the checker is unavailable and the editor text is kept; restore it and press **Check source** again.

## Limits
Source at most 65536 UTF-8 bytes; HTTP body at most 262144 bytes; checker timeout 5 s; at most 4 concurrent checker processes; at most 50 diagnostics per check (plus one `SC9001` truncation notice). One user, loopback only, no authentication, no CORS.

## Tests
```
cargo test
python -m unittest discover -s tests      # python3 on Linux
```
See the baseline verification below for the tested environment and results.

## Local persistence
None in M1. The `--data-dir` directory is validated and reserved for saved documents in a later milestone.

## Planned work
A single epic with five future issues: expanded parser and name resolution, object/array/union assignability, generics with inference, multi-file diagnostics with an incremental service, and a pinned offline comparison against the reference TypeScript compiler with a measured timing report. No speedup is claimed until measured. Details and acceptance criteria are in [docs/PRD.md](docs/PRD.md).

## License
See [LICENSE](LICENSE).

## Baseline verification

- Ubuntu 24.04 WSL with Rust and Cargo 1.100.0 passed 38 Cargo tests and an offline, locked release build. The compiled binary correctly reported a mismatch at line 2, column 24 and succeeded on a valid fixture.
- Windows with Python 3.13.14 and Ubuntu 24.04 WSL with Python 3.12.3 each passed 69 Python wrapper unit and API tests. Windows wrapper tests use a fixture checker.
- Windows Chrome 157 connected to the WSL server on loopback with external requests blocked. The browser rendered the real Rust diagnostic, the keyboard selected its offending character, and a valid input succeeded after a server restart.
