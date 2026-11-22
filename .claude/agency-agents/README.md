# Agency Agents roles used in this repository

The Markdown files in `.claude/agents/` whose names start with `engineering-`, `security-` or `testing-` are copies of role definitions from Agency Agents. They are project-local Claude Code subagents. The file `loop-verifier.md` in the same folder is not from Agency Agents; it belongs to the Loop Engineering setup described in [`LOOP.md`](../../LOOP.md).

## Source and licence

- Upstream: https://github.com/msitarzewski/agency-agents
- Pinned revision: `8ae6164602c95ca78828b148b9052460ee426885` (upstream `main`, committed 2026-11-09)
- Licence: MIT, "Copyright (c) 2025 AgentLand Contributors". The upstream licence text at the pinned revision is kept unchanged in [`LICENSE`](LICENSE) next to this file (SHA-256 `9a45258434d5cedf0af73c9ad4771373701225038d246c49219026c33677f66f`). It covers only the copied role files, not the rest of this repository.
- Fetched with `gh api -H "Accept: application/vnd.github.raw" "repos/msitarzewski/agency-agents/contents/<path>?ref=<revision>"`.

## Installed roles

"Upstream SHA-256" is the hash of the file as fetched at the pinned revision. Reviewer roles have one added frontmatter line, `tools: Read, Grep, Glob`, so they cannot edit files or run commands. Nothing else in any file was changed.

| File in `.claude/agents/` | `name:` | Upstream path | Upstream SHA-256 | Local change |
|---|---|---|---|---|
| `engineering-software-architect.md` | Software Architect | `engineering/engineering-software-architect.md` | `b85121691776147bacde26673e68fbbacd6a7f0816d1ca8e203c264d25ce1d30` | added `tools: Read, Grep, Glob` |
| `engineering-code-reviewer.md` | Code Reviewer | `engineering/engineering-code-reviewer.md` | `7509fcc3ea1dda46511b2801996305bf3d4a125576f9655ff0b63df25602f446` | added `tools: Read, Grep, Glob` |
| `engineering-codebase-onboarding-engineer.md` | Codebase Onboarding Engineer | `engineering/engineering-codebase-onboarding-engineer.md` | `07aa548b45887c3ad768efad5fdbf6e57bea639df4f1b74c7e383142f454e2a1` | added `tools: Read, Grep, Glob` |
| `security-appsec-engineer.md` | Application Security Engineer | `security/security-appsec-engineer.md` | `a19f0bda46f4adca5737365dbc3c7ed93e9d93b71349536d92ff055dcf4e3b83` | added `tools: Read, Grep, Glob` |
| `testing-reality-checker.md` | Reality Checker | `testing/testing-reality-checker.md` | `6d32fcdb114233e13902ec6372d50293b120e85d490b5e81d372c29808f988a1` | added `tools: Read, Grep, Glob` |
| `engineering-rust-refactoring-specialist.md` | Rust Refactoring Specialist | `engineering/engineering-rust-refactoring-specialist.md` | `06ca53dbd12694560bf01feb94cbbd8c428e4abe6ac92c8a72eeb277ce179a78` | none |
| `engineering-developer-tooling-engineer.md` | Developer Tooling Engineer | `engineering/engineering-developer-tooling-engineer.md` | `948d44fddfa47e2363236de150f9dc948edd79599609a92af8bf6b72b5b9b609` | none |
| `engineering-backend-architect.md` | Backend Architect | `engineering/engineering-backend-architect.md` | `ac717bde4848d7663fff8a3c7edc711fd119256de6a7ce38c036619372f42c99` | none |
| `engineering-frontend-developer.md` | Frontend Developer | `engineering/engineering-frontend-developer.md` | `1ae4cc10b2e0163bd3ed921ad54080b865cd02e591becd8919b64b73fab06dad` | none |

## Why these roles

| Role | Use in this repository |
|---|---|
| Software Architect (read-only) | Review a ticket's design against the boundaries in [`docs/architecture.md`](../../docs/architecture.md) before code is written: which Rust module owns a rule, what the JSON contract between the checker and the wrapper carries, whether a change needs a `schema_version` bump, how a long-lived checker process is supervised. |
| Code Reviewer (read-only) | Review a diff for correctness, missed edge cases and broken rules (exact spans, one syntax diagnostic per statement, deterministic output, bounded recursion, no evaluation of input, limits kept in step on both sides of the process boundary). |
| Codebase Onboarding Engineer (read-only) | Trace a code path and report facts with file and line citations. |
| Application Security Engineer (read-only) | Review everything that handles text or paths the person chose: the tokenizer and parser on hostile input (depth, size and count limits, no panic), import specifiers and project directories (no `..`, no absolute path, no symlink out of the root), the subprocess call (argument list, no shell, time and output caps) and the request guards in `ts_checker_web/server.py`. |
| Reality Checker (read-only) | Compare claimed evidence with what was actually run before a ticket or the epic is called done. This matters here because the Rust checks cannot run on every machine: a claim that `cargo test` passed must point at a CI run or a pasted local run. |
| Rust Refactoring Specialist | Implement work in `src/` and `tests/*.rs`: splitting `src/checker.rs` into a parser, a syntax tree, name resolution and type rules, and keeping the public contract (JSON shape, codes, spans, exit codes) unchanged while doing so. |
| Developer Tooling Engineer | Implement command-line and tooling work: new flags and modes of `ts_subset_check`, exit codes and error text, the CI workflow and the pinned toolchain, the offline comparison and timing harness. |
| Backend Architect | Implement work in `ts_checker_web/*.py` (routes, request validation, checker process supervision). |
| Frontend Developer | Implement work in `ts_checker_web/static/` (the workbench page). |

Most of these roles are written for larger stacks. Rust Refactoring Specialist assumes `cargo`, Clippy and rustfmt are available and tells the agent never to claim a command passed unless it ran; on a machine without a Rust toolchain it must say so and point at CI instead. Backend Architect, Frontend Developer and Application Security Engineer mention frameworks, cloud services, scanners and pipelines. In this repository the rules in [`CLAUDE.md`](../../CLAUDE.md) win: Rust standard library only (no crates), Python standard library only, native HTML, CSS and JavaScript, `unittest`, no pip or npm dependencies in the product, no external requests.

Roles that were considered and left out:

- DevOps Automator (`engineering/engineering-devops-automator.md`): written for cloud infrastructure and deployment pipelines. This repository needs one small CI workflow, which the Developer Tooling Engineer role and `CLAUDE.md` cover; nothing is deployed.
- Performance Benchmarker (`testing/testing-performance-benchmarker.md`): written for load tests and web performance budgets. The timing report planned here measures a local command-line process a fixed number of times; its method is fixed in the ticket.
- Test Automation Engineer and API Tester: their methods need tools this repository does not allow (browser automation frameworks, external services). Browser checks here are manual and recorded.
- WebAssembly Engineer, Technical Writer and Minimal Change Engineer: no planned work targets WebAssembly, and the repository rules in `CLAUDE.md` already cover what the other two would add.

## Name collision with user-level agents

A developer who has installed Agency Agents in `~/.claude/agents/` already has agents with the same `name:` values. Claude Code gives the project-level definition precedence, so inside this repository the copies here are used, including the read-only tool limits. The upstream names were kept on purpose so that the roles stay recognisable and can be compared with upstream.

A Claude Code session that was already running when these files were added keeps the definitions it loaded at start. Start a new session to pick up the project copies.

## Check that the roles load

From the repository root, in a new session:

```text
claude -p "List the project-level subagents defined in .claude/agents with the tools each one may use. Then run the Reality Checker subagent and ask it which tools it has."
```

The five reviewer roles and `loop-verifier` must report exactly `Read, Grep, Glob`.

## Updating

Fetch the same paths at a newer revision, re-apply the `tools:` line to the five reviewer roles, and update the revision and hashes in this file in the same commit.
