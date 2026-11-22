# AGENTS.md

The full repository instructions are in [CLAUDE.md](CLAUDE.md). This file repeats only what an agent needs before it reads that.

## Test commands

```
cargo test
python -m unittest discover -s tests
```

(`python3` on Linux.) Run both from the repository root. The Rust tests need a Rust toolchain with `cargo`; on a machine without one, do not install it and do not claim the Rust tests passed: say they were not run and point at a CI run instead. The Python tests need only Python 3 and use a stand-in checker script, so they pass without the Rust binary.

There is no lint configuration and no package manifest besides `Cargo.toml`. Do not add crates, pip packages or npm packages.

## Run

```
cargo build --release
python -m ts_checker_web --data-dir ./data --port 8765
```

The server binds `127.0.0.1` only. `--data-dir` and `--port` are both required. Without a built checker the page still loads and every check answers `checker_unavailable`. Stop the server with Ctrl+C.

## Ticket work

To implement an issue, follow the steps in [.claude/skills/implement-ticket/SKILL.md](.claude/skills/implement-ticket/SKILL.md) and the section "Agents and ticket work" in [CLAUDE.md](CLAUDE.md). The roles it names are in `.claude/agents/`; each file starts with a section "In this repository" that holds the project rules for that role; where that section and `CLAUDE.md` differ, `CLAUDE.md` wins. An agent that cannot start those roles does each step itself, reads that section first, and says so in the pull request.

The owner starts ticket work with `/next-ticket`; agents stop at a ready pull request and only the owner merges. See the "Delivery workflow" part of [CLAUDE.md](CLAUDE.md).

## Loop conventions

- The loop runs at L1: report-only, started by hand. It proposes; it does not label, comment, close, edit source, push or merge.
- No scheduler and no loop workflow is installed by the loop setup (the CI workflow `.github/workflows/ci.yml` is separate). Do not add one for the loop without the owner's approval.
- See [LOOP.md](LOOP.md) for the manual command and the human gates.
