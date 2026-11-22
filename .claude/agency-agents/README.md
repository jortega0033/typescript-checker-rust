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

### What was observed, and what was not

Observed on 2026-11-22 with Claude Code 2.1.323, headless (`claude -p`, model requested: haiku, no MCP servers), from the repository root, one run, on a machine that also has a user-level Agency Agents install (303 files, all nine names present there, none with a `tools:` line):

- All ten names were listed (the nine roles above and `loop-verifier`). Software Architect, Code Reviewer, Codebase Onboarding Engineer, Application Security Engineer, Reality Checker and `loop-verifier` were listed with `Read, Grep, Glob`. Rust Refactoring Specialist, Developer Tooling Engineer, Backend Architect and Frontend Developer were listed with all tools.
- A launched Reality Checker and a launched Application Security Engineer each reported exactly `Read`, `Grep`, `Glob`. The user-level copies have no `tools:` line, so the tool limits show that the project copies were the ones loaded.
- A launched Rust Refactoring Specialist quoted the first sentence of its defining rule ("Execute the complete, coherent change set required by the requested refactoring objective."), so the role loads and carries the role text.
- **Not shown:** which copy of the four implementer roles was loaded. The user-level copies of Rust Refactoring Specialist and Developer Tooling Engineer on that machine are byte-identical to the project copies, so no answer can tell them apart; Backend Architect and Frontend Developer were listed, not launched. Also not shown: behaviour in an interactive session, and behaviour on a machine without a user-level install (there the names must simply be listed).
- The listing gives names and tools only, not the file a definition comes from. The statement above about which reviewer copies were loaded rests on the tool limits.

## Updating

Fetch the same paths at a newer revision, re-apply the `tools:` line to the five reviewer roles, and update the revision and hashes in this file in the same commit.

## Local change: automatic delegation (2026-11-22)

One sentence beginning "Use proactively" was appended to the `description:` line of every Agency Agents role in `.claude/agents/` (not to `loop-verifier`). Claude Code uses that field to decide when to delegate, so the roles now run during ticket work without being named.

A section headed `## In this repository` was then inserted directly after the frontmatter of every Agency Agents role (not into `loop-verifier`), before the upstream text. It is project-specific text written for this repository, not upstream text. It states the project's stack and constraints, the files the role owns or reviews, its commands (or, for a read-only role, the output it must be given), the invariants it checks with the document each comes from, the parts of the generic text that do not apply here, and what the role hands back. It ends with the sentence "This section and CLAUDE.md override the generic text below wherever they differ." The frontmatter and the upstream text below the section were not changed by the insertion.

This supersedes any statement above that a role file is unmodified or that the `tools:` line is the only local change. To compare a role with the pinned upstream file, first remove three things: the "Use proactively" sentence, the `tools:` line where one was added, and the whole "In this repository" section (from its heading up to, but not including, the upstream title line that starts with `# `). When updating to a newer upstream revision, re-apply all three and check every statement of the section against the repository as it is then.

The steps at which each role runs are in `.claude/skills/implement-ticket/SKILL.md` and in `CLAUDE.md`, section "Agents and ticket work".

Verification, 2026-11-22 (after the "In this repository" sections were inserted): one headless run from the repository root with Claude Code 2.1.323, `claude -p "List every project subagent defined in .claude/agents with its exact name and tools, say for each whether its instructions begin with a section titled In this repository, and say whether a skill named implement-ticket is available. Plain list, no commentary." --model haiku`, exit code 0. The answer listed all ten names. Code Reviewer, Codebase Onboarding Engineer, Software Architect, Application Security Engineer, Reality Checker and `loop-verifier` were listed with `Read, Grep, Glob`; Backend Architect, Developer Tooling Engineer, Frontend Developer and Rust Refactoring Specialist with no `tools` line in the frontmatter. It answered "yes" to the "In this repository" question for the nine Agency Agents roles and "no" for `loop-verifier`, and reported the skill `implement-ticket` as available. Not shown by this run: whether that answer came from the loaded definitions or from reading the files, the behaviour of a launched role, and automatic delegation during a real ticket; no role was launched.
