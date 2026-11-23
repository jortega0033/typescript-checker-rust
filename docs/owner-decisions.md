# Owner decisions

A dated record of the decisions the owner made for this repository, so the rules do not depend on anyone's memory of a conversation. Changing any entry needs the owner. An agent that finds a decision blocking a ticket stops and says so.

Entries 1 to 12 are dated 2026-11-22; later entries carry their own date.

| # | Decision | Date | Implemented in |
|---|---|---|---|
| 1 | The instructions, tooling and playbook live on the default branch (`main`). | 2026-11-22 | `CLAUDE.md`, `.claude/`, `.github/` |
| 2 | Persona agents run automatically during ticket work and carry instructions tailored to this project. | 2026-11-22 | `.claude/agents/` ("Use proactively" sentences, "In this repository" sections), `.claude/agency-agents/README.md`, `CLAUDE.md` "Agents and ticket work" |
| 3 | Every open ticket is about app implementation; tooling is installed, not ticketed. | 2026-11-22 | `.claude/`, `.github/`, `docs/`, `CLAUDE.md` "Delivery workflow" |
| 4 | Agents may take a ticket up to a ready pull request. Only the owner merges and releases. | 2026-11-22 | `CLAUDE.md` "Git workflow" and "Delivery workflow", `.claude/skills/next-ticket/SKILL.md`, `.claude/skills/implement-ticket/SKILL.md`, `docs/RELEASING.md`, `.claude/settings.json` (`gh pr merge` and `gh release create` denied) |
| 5 | No scheduler. Ticket work starts only on the owner's go signal (`/next-ticket`), because the repository is used to train AI models. | 2026-11-22 | `.claude/skills/next-ticket/SKILL.md` (`disable-model-invocation: true`), `LOOP.md` |
| 6 | A review gate hook blocks opening or readying a pull request until the gate roles have run after the last code edit. | 2026-11-22 | `.claude/hooks/role_gate.py`, `.claude/settings.json` (`hooks`), `.gitignore` (`.claude/state/`) |
| 7 | Loop Engineering stays at L1, report-only and unscheduled. | 2026-11-22 | `LOOP.md`, `loop-constraints.md`, `loop-budget.md` |
| 8 | Continuous integration runs on Linux and Windows; the default branch requires a pull request and green checks. | 2026-11-22 | `.github/workflows/ci.yml`; branch protection is a repository setting applied by the owner's orchestrator, not a file |
| 9 | Permission rules: documented commands are allowed; force pushes, pushes to the default branch, merges, releases and reads of secrets are denied; edits to CI, agent configuration and Loop files ask first. | 2026-11-22 | `.claude/settings.json` (`permissions`) |
| 10 | Open decisions on tickets are settled with the ticket's stated default; where a ticket states none, the conservative option is taken and flagged in the issue. | 2026-11-22 | The list below; the issues themselves |
| 11 | Rust is verified in CI only; nothing is installed on the owner's PC. | 2026-11-22 | `.github/workflows/ci.yml` (job `rust`), `CLAUDE.md` "If your machine has no Rust toolchain" |
| 12 | The ten UI rules in `docs/ui-quality.md` are binding, and the `ui-ux-pro-max` and `unslop` skills are installed in the repository and used for UI work and for copy. | 2026-11-22 | `docs/ui-quality.md`, `.claude/skills/ui-ux-pro-max/`, `.claude/skills/unslop/`, `.claude/skills/implement-ticket/SKILL.md` |
| 13 | Visual system: Pipenzo Flow look tokens (docs/design-tokens.md). SDLC kit version: jortega0033/sdlc-kit v1.0.0. | 2026-11-23 | `ts_checker_web/static/tokens.css`, `ts_checker_web/static/app.css`, `docs/design-tokens.md` |
| 14 | Yellow accent, focus ring, themes and linking: D1 to D4 (see the list below the table). | 2026-11-23 | `docs/design-tokens.md`, `docs/ui-quality.md` |

## Entry 14 detail (2026-11-23)

- D1 Current selection: the yellow accent is used for the primary action, the current-step marker and the current selection (UI rule 8). Decided by the owner on 2026-11-23. How (recommended by the orchestrator, adopted under the owner's delegation of the same day): a selection uses a solid --primary fill with --on-primary text (not only a yellow border, which has about 1.5:1 against white on light), plus a second sign that is not colour (weight, icon or text) and the existing aria attribute. Never a tint with a same-hue border and never a thick one-sided border.
- D2 Focus ring: --focus is a focus indicator, exempt from the accent limit, including where it is yellow in dark. A ticket that says the focus style stays unchanged means the rule on main after the token pull request. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
- D3 Themes: contrast and no-colour-alone checks cover both the light and the dark block of tokens.css. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
- D4 Linking: a ticket that creates a page or its static allowlist links tokens.css before any other stylesheet and serves it (allowlist and its test). Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
- D5 does not apply to this repository (jortega0033/release-dependency-planner#11).

## Open ticket decisions settled by default (entry 10)

| Issue | Decision | Default or conservative option | Status |
|---|---|---|---|
| #1 (decision 1), #7 | Toolchain and CI | Default: pin Rust 1.100.0 in `rust-toolchain.toml` with `rustfmt` and `clippy`; GitHub Actions on pushes to `main` and on pull requests, no schedule. The SDLC kit already installed `.github/workflows/ci.yml` with this version; #7 narrows to the pin file, `.gitattributes`, the end-to-end tests and baseline fixes. | settled by default |
| #1 (decision 2), #6 | Reference compiler: which TypeScript version to pin and approval to stage it | No default is stated. Conservative option: choose no version, stage nothing, keep #6 part 1 blocked until the owner decides. #6 part 2 and every other ticket do not depend on it. | flag in issue |
| #1 (decision 3), #2 | Language rules of #2 | Defaults: unary minus accepts any operand and gives `number`; two adjacent `-` is `SC1004`; an empty statement is `SC1004`; `=` after an expression statement is `SC1004`; a statement with a syntax diagnostic gets no name or type diagnostics; a failed declaration does not declare its name (poisoned name); recovery skips to the next `;` with a brace counter; `summary.declarations` counts complete declarations in every scope. | settled by default |
| #1 (decision 3), #3 | Language rules of #3 | Defaults: union members are primitives and literal types only; a statement starting with `{` is a block; a literal initializer prints as its primitive unless the target has a literal type; an empty array literal is assignable to every array type; an optional source property is not assignable to a required target property. | settled by default |
| #1 (decision 3), #4 | Language rules of #4 | Defaults: functions are ambient `declare function` signatures; `declare` is a keyword only before `function` at top level; `type` and `declare function` are top-level only; an uncalled function name is `SC1004`; recursive aliases are `SC2012`; no built-in generic names; an alias or type parameter is not a union member; `any`, `unknown`, `never`, `void`, `null`, `undefined`, `object`, `symbol` and `bigint` stay `SC1005`; messages print expanded types. | settled by default |
| #1 (decision 3), #5 | Language and project rules of #5 | Defaults: `schema_version` stays 1 for the project report; a circular import is a diagnostic; `--max-bytes` is single-file only; every symbolic link is rejected; a Windows junction is rejected with `SC0003`; `import` is top level only; a file imports only from its own directory or below. | settled by default |
| #1 (decision 3), #6 | Rules of #6 | Defaults: the harness is a developer tool that may need `node`; the staged compiler is not committed, only its version and hash; agreement is on (line, category); the reports are committed and regenerated by hand. | settled by default |
| #1 (decision 3), #8 | Rules of #8 | Defaults: the service re-reads files on every request; reuse is per file; the cache is memory only. | settled by default |
| #1 (decision 3), #9 | Rules of #9 | Defaults: projects live under `<data-dir>/projects/<name>/`; project-mode tool errors answer 422 with the checker's code; one service child for the whole server. | settled by default |

Not in this batch: epic #1 decision 4 (saved documents in `--data-dir`, UTF-16 column units; PRD section 15). Nothing to settle. #10 states no owner decision.
