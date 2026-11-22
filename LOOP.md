# Loop Configuration: Issue Triage

Scaffolded with `npx --yes @cobusgreyling/loop@0.2.0 init . --pattern issue-triage --tool claude` ([Loop Engineering](https://github.com/cobusgreyling/loop-engineering), MIT). The generated `.grok/` and `.codex/` variants were removed; this repository uses the Claude Code files only. The scaffold generated no workflow file, and none was added.

## Active Loops

| Pattern | Cadence | Status | Command |
|---------|---------|--------|---------|
| Issue Triage | Manual, on request | L1 report-only | `/issue-triage` in a Claude Code session at the repository root |

## Operating level: L1 report-only

- The loop reads open issues with `gh issue list` and `gh issue view` and rewrites `issue-triage-state.md`. That file and `loop-run-log.md` are the only files it may change.
- It never applies labels, comments, closes or edits issues, edits source or tests, commits, pushes, opens pull requests or merges.
- No scheduler is configured. Do not wrap the skill in `/loop`, a cron entry, a scheduled task or a GitHub workflow. The "2h" cadence in the upstream pattern does not apply to this repository.
- `loop doctor` prints its own readiness score. That score describes the scaffold, not the operating level. The operating level here stays L1 until the owner changes this file.

## Next manual triage run

From the repository root, in a new Claude Code session:

```text
/loop-constraints
/issue-triage
```

Headless equivalent:

```text
claude -p "Run the loop-constraints skill, then the issue-triage skill in L1 report-only mode. Update issue-triage-state.md and append one entry to loop-run-log.md. Make no GitHub writes and change no other file."
```

Review the diff of `issue-triage-state.md` afterwards. Committing it is a human decision.

## Health checks

```text
npx --yes @cobusgreyling/loop@0.2.0 doctor .
npx --yes @cobusgreyling/loop@0.2.0 status .
```

Doctor exit codes: 0 healthy, 1 warnings, 2 blocked. Both commands fetch the package from npm, so they need a network connection and Node.js. The product itself needs neither.

## Human Gates

- Priority assignment (P0, P1): human only.
- Anything touching the checker's contract in `src/` (the `schema_version`, field shapes, diagnostic codes and their meaning, span units, exit codes, the 64 KiB source cap, the 50-diagnostic cap, nesting and instantiation limits, the rule that input is only tokenized and parsed and never executed), the request guards in `ts_checker_web/server.py` (loopback bind, Host and Origin checks, body caps, CSP and the other security headers, the static allowlist), how `ts_checker_web/checker.py` starts the checker (argument list, no shell, time and output caps, the concurrency limit), how diagnostic text reaches the page (`textContent` only), path handling for project directories and import specifiers, or the public JSON API under `/api/v1`: always escalate.
- Anything that would add a crate, a pip or npm dependency, an external request, a non-loopback listener, or an external tool such as the reference TypeScript compiler: always escalate. The product is offline and standard-library only by design, and the PRD requires approval before any external tool is staged ([docs/PRD.md](docs/PRD.md), sections 2 and 14).
- Any statement about speed: always escalate. No speed claim may be made before the timing report measures it ([docs/PRD.md](docs/PRD.md), section 14).
- Duplicate closure: human confirms.
- Stale issue closure: human confirms.
- Any change to this file, `loop-budget.md` or `loop-constraints.md`: human only.

## Verifier

`.claude/agents/loop-verifier.md` is the checker for a later maker/checker level. It is limited to `Read, Grep, Glob`, so it cannot run the tests itself and must answer `ESCALATE_HUMAN` when a verdict depends on a test run. It has no role at L1 because the loop proposes no changes.

## Budget

- Sub-agent spawns per run: 0 at L1.
- See `loop-budget.md`.

## MCP

MCP is not required for this pattern. The triage skill reads issues through the `gh` command line.

## Recorded doctor and status result

Run on 2026-11-22 (Windows 11, Node v22.23.4) in the Git worktree after the scaffold was adapted and before it was committed:

- `doctor .`: `Ready: 100/100 L2` ("Strong structure but no proven loop runs yet"), `Status: HEALTHY (exit 0)`, files `state=issue-triage-state.md LOOP.md=yes budget=yes run-log=yes gate=no`, `Sync: n/a`, note "Could not parse loop-sync JSON output". Suggested next actions: a `docs/safety.md`, issue and pull request templates with workflows, and worktree isolation notes (see the next section).
- `status .`: pattern `issue-triage`, `Ready: 100/100 L2`, state "not yet run", `gate=no`, `constraints=yes`, no recent runs. Its closing line suggests scheduling a first run; that advice is not followed here, runs stay manual.

Run again on 2026-11-22 in the same worktree after the files above were committed:

- `doctor .`: `Ready: 100/100 L3` ("good candidate for L3 with explicit gates"), `Status: HEALTHY (exit 0)`, process exit code 0, the same files line and note; its third suggestion is now a `patterns/registry.yaml` instead of worktree isolation notes.
- `status .`: the same lines with `Ready: 100/100 L3`, process exit code 0.

The label after the score changed from L2 to L3 between the two runs although no loop file changed, so it follows the repository state, not the configuration. It is the tool's view of the scaffold. No run of the loop has taken place and the operating level stays L1.

## Doctor suggestions that were not adopted

`loop doctor` suggests a `docs/safety.md`, issue and pull request templates with workflows, and either worktree isolation notes or a `patterns/registry.yaml`. They were left out on purpose: the denylists and merge policy are in `loop-constraints.md`; a workflow for the loop would be the scheduler that L1 excludes (the CI workflow planned in the backlog is a separate matter and runs only on pushes and pull requests); at L1 the loop edits two report files and never works in a worktree; and a pattern registry belongs to the upstream project, not to a repository that uses one pattern.

## Links

- Pattern: https://github.com/cobusgreyling/loop-engineering/blob/main/patterns/issue-triage.md
- Repository instructions: [CLAUDE.md](CLAUDE.md)
- Backlog source of truth: [docs/PRD.md](docs/PRD.md) and the epic issue (#1)
