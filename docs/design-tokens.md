# Design tokens

The workbench page uses the Pipenzo "Flow look" tokens: black page, Flow-style alpha layers, one accent (Pipenzo yellow `#FECE02`) for the primary action, the current step and the current selection, red only for danger.

## Source and resync

- Source: `jortega0033/clip-to-reel-studio`, `extension/sidepanel/tokens.css`, commit `a13378ce73e5b27213c9a200fc960ec93afef054` (2026-11-21).
- Installed unchanged as `ts_checker_web/static/tokens.css`, served at `/static/tokens.css` (exact allowlist in `ts_checker_web/server.py`).
- Resync: copy the file over `ts_checker_web/static/tokens.css`. Nothing else. Never edit the copy.

## Token names by role

| Role | Tokens |
|---|---|
| Surfaces | `--bg` (page), `--surface` (panels), `--bg-raised`, `--bg-sunken` |
| Text | `--fg`, `--muted`, `--faint` |
| Lines | `--border`, `--hairline`, `--control-border`, `--input-border` |
| Accent | `--primary`, `--primary-press`, `--primary-edge`, `--on-primary` (primary action, current step and current selection) |
| Status | `--danger`, `--danger-bg`, `--success`, `--ok`, `--ok-bg`, `--warn-fg`, `--warn-bg`, `--info` |
| Focus | `--focus` (focus indicator, not an accent use) |
| Dark blocks | `--ink`, `--on-ink`, `--on-ink-muted`, `--ink-border`, `--hero-*` |
| Layers and shadows | `--glass*`, `--scrim`, `--state-*`, `--btn-secondary*`, `--shadow-*` |
| Type, space, motion | `--font`, `--mono`, `--space-*`, `--radius-*`, `--dur-*`, `--ease-*` |

Note: `--ink` is a dark block colour here, not the text colour. Text is `--fg`.

## Rules

- New UI uses these tokens; no new colour literals in `app.css` or `app.js`.
- A ticket that creates a page or its static allowlist links `tokens.css` before any other stylesheet and serves it (allowlist and its test). Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23 (D4).
- The ten rules in [ui-quality.md](ui-quality.md) still apply. Text never sits on a bare alpha layer.
- Where this document and the header comment of `tokens.css` differ, this document takes precedence. The header comment of `tokens.css` lists other uses (primary button, current-step node, "your turn" chip, hero kicker dot, overlay opening dot) and does not list the current selection. On this page the list in this document applies. The copy must stay identical to the source, so the comment is not edited here.

### Yellow accent (UI rule 8)

Yellow is used only for the primary action, the current-step marker and the current selection. Decided by the owner on 2026-11-23.

Status colours stay for status only (rule 8).

How a selection is marked (recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23):

- A solid `--primary` fill with `--on-primary` text. A yellow border alone is not enough: it is about 1.5:1 against white in the light theme.
- A second sign that is not colour: weight, an icon or text.
- The existing aria attribute. The page has none today, so a ticket that adds a selection names the attribute it uses.
- Never a tint with a border of the same hue, and never a thick border on one side.

### Focus ring

`--focus` is a focus indicator. It is exempt from the accent limit, including where it is yellow in the dark theme. A ticket that says the focus style stays unchanged means the rule on `main` after the token pull request. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23 (D2).

### Both themes

Contrast checks and no-colour-alone checks cover both the light block and the dark block of `tokens.css`. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23 (D3).

### Page status

The page has no selection or current-step marker today; the only yellow fill is the primary button (`#check-btn`). A ticket that adds a selection (for example the Project view, #49) follows this rule.

## Light and dark

Dark is the primary design. The light block is the matching light theme. The operating system colour scheme (`prefers-color-scheme`) picks one; there is no manual switch.
