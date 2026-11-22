# TypeScript Checker in Rust: PRD and Technical Spec

Status legend: **[Baseline]** = implemented in M1 (see [baseline verification](../README.md#baseline-verification)); **[Future]** = not implemented.

The engineering map (module boundaries, one traced request, invariants, and where this document and the code disagree) is in [architecture.md](architecture.md).

## 1. Purpose, user and workflow

**User:** one TypeScript developer working offline on their own machine who wants to see what a type checker does and compare deterministic diagnostics against a small, explicit subset.

**Workflow [Baseline]:**
1. Build the checker once (`cargo build --release`).
2. Start the local web workbench (`python -m ts_checker_web --data-dir <path> --port <port>`).
3. Open the printed `http://127.0.0.1:<port>/`, type or load an example, press **Check source**.
4. Read diagnostics (stable code, one-based span, message); select one to jump to its span in the editor.
5. Fix the text and re-check. The same input always yields the same output.

The checker is also usable alone: `ts_subset_check < file.ts` prints JSON and exits 0 (clean), 1 (diagnostics) or 2 (tool error).

## 2. Scope

**In scope (M1) [Baseline]:** Rust executable `ts_subset_check` (no dependencies), lexer and checker for one subset, JSON result with fixed schema, Python standard-library loopback wrapper `ts_checker_web`, original HTML workbench, Rust and Python tests, README.

**Out of scope:** running or evaluating input code, emit/transpile, full TypeScript, language server, paid services, sign-in, remote sync, deployment, model integration, saved documents (M1), external media. The wrapper does **not** reimplement the checker.

## 3. Milestones

| Milestone | Content | Status |
|---|---|---|
| M1 | Primitive declaration checker, CLI contract, web workbench | Baseline implemented and verified as described in README |
| P1 | Expanded parser/AST, name resolution, recovery | Future |
| P2 | Object/array/union structural assignability | Future |
| P3 | Generics, constraints, inference | Future |
| P4 | Multi-file diagnostics and incremental service | Future |
| P5 | Pinned reference-compiler oracle and offline timing report | Future |

## 4. System stack

- Checker: Rust (edition 2021), standard library only. Modules: `lexer`, `checker` (parser plus type rule), `json` (writer), `main` (CLI).
- Wrapper: Python 3 standard library: `http.server.ThreadingHTTPServer`, `subprocess` (list args, `shell=False`), `argparse`.
- UI: static HTML, CSS and JavaScript (no framework, no build step, system fonts) in `ts_checker_web/static/`.
- Persistence: none in M1. `--data-dir` is validated/created and reserved for future saved documents.

## 5. Contracts

### 5.1 Subset grammar [Baseline]
```
program   := statement*
statement := ("let" | "const") IDENT ":" ("string"|"number"|"boolean") "=" literal ";"
literal   := STRING | NUMBER | "true" | "false"
```
STRING uses `'` or `"` with escapes `\\ \' \" \n \t \r`. NUMBER is `-?digits(.digits)?`. IDENT is ASCII `[A-Za-z_$][A-Za-z0-9_$]*`. Everything else yields an explicit diagnostic. The literal kind must equal the annotation (no coercion). Known divergence from the reference compiler: NUMBER accepts leading zeros (`007`), and comments are unsupported (`SC1004`). P5 lists such divergences explicitly.

### 5.2 CLI [Baseline]
`ts_subset_check [--max-bytes N] [--help]`: reads UTF-8 stdin (cap default 65536 bytes), writes one JSON document and `\n` to stdout. Exit 0 clean, 1 diagnostics, 2 usage/UTF-8/size error.

### 5.3 Result schema (schema_version 1) [Baseline]
```json
{"schema_version":1,"ok":false,
 "summary":{"declarations":3,"diagnostics":1},
 "diagnostics":[{"code":"SC2001","severity":"error",
   "message":"Type 'number' is not assignable to type 'boolean'.",
   "span":{"start":{"line":2,"column":24},"end":{"line":2,"column":25}}}]}
```
Spans are 1-based; columns count Unicode scalar values; `end` is exclusive. Diagnostics are sorted by start position and capped at 50 (then `SC9001`). Tool errors: `{"schema_version":1,"ok":false,"error":{"code":"SC0001|SC0002","message":"..."}}`.

| Code | Meaning |
|---|---|
| SC0001 / SC0002 | input too large / not UTF-8 (exit 2) |
| SC1001 | invalid character |
| SC1002 | unterminated string |
| SC1003 | expected token |
| SC1004 | unsupported syntax |
| SC1005 | unsupported type annotation |
| SC1006 | unsupported literal |
| SC2001 | type mismatch |
| SC2002 | duplicate declaration |
| SC9001 | output truncated |

Recovery: after a syntax diagnostic, skip through the next `;` and resume; at most one syntax diagnostic per statement.

### 5.4 HTTP API [Baseline]
- `GET /` workbench; `GET /static/{app.css,app.js,fixtures.json}` (exact allowlist); `GET /api/v1/health` returns `{"status":"ok","schema_version":1,"checker":{"available":bool}}`.
- `POST /api/v1/check` with `{"source": string}` (JSON content type, source at most 65536 UTF-8 bytes, body at most 262144 bytes). Success is HTTP 200 with the checker object plus final key `exit_code`. Errors: 400 `invalid_request`, 403 `forbidden_origin`, 404 `not_found`, 405, 411 `length_required`, 413 `too_large`, 415 `unsupported_media_type`, 502 `checker_failed`, 503 `checker_unavailable`/`busy`, 504 `checker_timeout`, each as `{"error":{"code","message"}}`.
- The wrapper sends no CORS headers, binds 127.0.0.1 only, validates `Host` (and `Origin` when present), and applies a restrictive Content-Security-Policy.

### 5.5 UI contract [Baseline]
Textarea `source`, button **Check source** (also Ctrl/Cmd+Enter), example picker with explicit **Load example** and **Undo load**, polite live `status`, ordered `diagnostics` list rendered with `textContent` only. Selecting a diagnostic selects its span in the editor. Failures never clear the editor.

### 5.6 Algorithm [Baseline]
Single pass: lexer produces tokens with line/column; a statement parser consumes `(let|const) IDENT : type = literal ;`; the checker compares literal kind to annotation and records names for duplicate detection. No evaluation of any kind occurs.

## 6. Deterministic fixtures [Baseline]

| Fixture | Input | Expected |
|---|---|---|
| valid | `let count: number = 42;` / `const name: string = "Ada";` / `const done: boolean = false;` | exit 0, `ok:true`, declarations 3, no diagnostics |
| golden | `const attempts: number = 3;` / `const ready: boolean = 2;` / `const title: string = "Map";` | exit 1, one SC2001 at 2:24-2:25 |
| unsupported | `const items: string[] = ["a"];` / `let n: number = 1e3;` / `// note` / `let ok: boolean = true;` | exit 1; SC1003 at 1:20-1:21, SC1006 at 2:17-2:20, SC1004 at 3:1-3:2 (line 4 is skipped by recovery) |
| duplicate | `let a: number = 1;` / `const a: string = "x";` | exit 1, SC2002 at 2:7-2:8 |
| empty | (empty input) | exit 0, declarations 0 |

## 7. Responsiveness and accessibility [Baseline]
Two columns at 900px and above, one column below; no horizontal body overflow at 800x600 or 360px wide; labelled controls; visible `:focus-visible`; status in an `aria-live` region; keyboard-only operation; contrast at least WCAG AA; system fonts; reduced-motion respected.

## 8. Errors, retry, restart, concurrency
- Checker missing: health reports unavailable, check returns 503, UI says to build and retry; the path is re-resolved per request so no restart is needed.
- Timeout (5 s) and crashes map to 504/502 with retry text; editor text is kept.
- One UI request at a time. Server runs at most 4 checker processes concurrently; extras wait up to 5 s then get 503 `busy`.
- Restart: no state to recover in M1.
- Bad `--data-dir` or `--port` value: message on stderr, exit 2. Port already in use (bind failure): message on stderr, exit 1.

## 9. Versioning
`schema_version` is an integer in every checker and wrapper response. Additive diagnostic codes and newly supported syntax (which may change a diagnostic for previously unsupported input, with fixtures updated in the same change) do not bump it; changed field shapes do. Codes are never reused.

## 10. Security and validation
Input is only tokenized and parsed. Subprocess uses an argument list with `shell=False`, stdin cap, stdout cap (1 MiB), timeout. Static files use an exact allowlist, no path joining from requests. Responses carry `nosniff`, `no-store` and CSP. User text is only inserted with `textContent`. No secrets, accounts or network egress.

## 11. Acceptance matrix (M1)

| ID | Check | Measure |
|---|---|---|
| A1 | Golden example | exactly 1 diagnostic, SC2001, 2:24-2:25, exit 1 |
| A2 | Valid fixture | `ok:true`, exit 0 |
| A3 | Each of SC1001-SC1006, SC2002, SC9001 | at least one Rust test each |
| A4 | Determinism | two runs byte-identical |
| A5 | Oversize input | exit 2 with SC0001; HTTP 413 beyond 65536 bytes |
| A6 | Foreign Host/Origin on POST | 403 |
| A7 | Static traversal (`/static/../x`, encoded forms) | 404 |
| A8 | Missing checker | health `available:false`, check 503 |
| A9 | Layout | no horizontal overflow at 800x600 |
| A10 | Source never executed | no code path evaluates input (review) |

## 12. Sample demo
Start the server, load the **Type mismatch** example, press **Check source**: status reads `1 issue found`, list shows `SC2001 2:24-2:25 Type 'number' is not assignable to type 'boolean'.`; selecting it highlights `2` in line 2.

## 13. Test plan
- Rust integration tests: fixtures with expected JSON, code coverage per code, CRLF and non-ASCII columns, exit codes.
- Python `unittest` (`python -m unittest discover -s tests`): server on an ephemeral port with a temporary data directory, request validation, Host/Origin, static allowlist, checker failures through an injected command.
- Browser smoke: README steps, including an 800x600 viewport.
- Status: the runs the owner recorded for M1 are listed under [baseline verification](../README.md#baseline-verification). What was re-run during repository preparation on 2026-11-22, and what could not be run there (every Rust check: no toolchain on that machine), is recorded in [architecture.md](architecture.md), section 1.

## 14. Future work: one epic, five issues

**Epic:** Grow `ts_subset_check` from primitive declarations to a verified, incremental checker for a documented TypeScript subset. Full text is in the issue backlog; summary below.

| Key | Issue | Depends on | Key acceptance |
|---|---|---|---|
| P1 | Expanded parser, AST, name resolution and recovery | none | 5 independent syntax errors yield exactly 5 diagnostics and surrounding statements are still checked; 1,000 deterministic mutations never panic |
| P2 | Object/array/union structural assignability | P1 | at least 40-pair directional matrix; nested wrong property at depth 3 is one diagnostic with exact span and property path |
| P3 | Generics, constraints, inference | P2 | constraint violation span on the type argument; self-referential alias stops at depth 32 with one diagnostic |
| P4 | Multi-file diagnostics and incremental service | P3 | leaf edit in a 5-dependent chain re-checks exactly 6 files; 200 edit sequences match cold recomputation byte-for-byte |
| P5 | Pinned reference-compiler oracle and timing report | P4 | refuses unpinned compiler version; at least 95% line/category agreement with every disagreement explained; at least 30 timed runs per group, median and p95 |

**User stories (all as the single offline developer):**
- P1: As a developer, I see every independent syntax and name error in one pass, so I do not fix one error per run.
- P2: As a developer, I learn why a value is or is not assignable, with the exact property path, so I can compare against my mental model.
- P3: As a developer, I see how type arguments were inferred and which constraint failed.
- P4: As a developer, I edit one file and see only the affected files re-checked, with results identical to a full run.
- P5: As a developer, I see where the subset agrees or disagrees with the reference compiler and what the measured timings are.

Dependencies: P5 needs a reference compiler staged locally. It must be approved before staging and is never fetched at test time. No speed claim (including any "5x") is made until the P5 report measures it.

## 15. Open choices
- Whether `--data-dir` should hold saved documents (post-M1) in SQLite with migrations.
- Column units for future editors that count UTF-16 (currently scalar values).
- Which reference compiler version to pin for P5.
