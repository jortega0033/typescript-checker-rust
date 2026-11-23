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
- The ten rules in [ui-quality.md](ui-quality.md) still apply. Text never sits on a bare alpha layer.
- Where this document and the header comment of `tokens.css` differ, this document takes precedence. The header comment is narrower (it lists yellow only on the primary button, the current-step node and a few chips). The copy in `static/` must stay identical to the source, so the comment is not edited here.

### Yellow accent (UI rule 8)

Yellow is used for the primary action, the current-step marker and the current selection. Decided by the owner on 2026-11-23. Everything else stays neutral, and red is only for danger.

How a selection is marked (recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23):

- A solid `--primary` fill with `--on-primary` text. A yellow border alone is not enough: it is about 1.5:1 against white in the light theme.
- A second sign that is not colour: weight, an icon or text.
- The existing aria attribute (for example `aria-current` or `aria-selected`).
- Never a tint with a border of the same hue, and never a thick border on one side.

### Focus ring

`--focus` is a focus indicator. It is exempt from the accent limit, including where it is yellow in the dark theme. A ticket that says the focus style stays unchanged means the rule on `main` after the token pull request.

### Both themes

Contrast checks and no-colour-alone checks cover both the light block and the dark block of `tokens.css`.

### Page status

The page still marks selection in a neutral colour in places. It follows this rule in ticket work; that work is not done yet.

## Light and dark

Dark is the primary design. The light block is the matching light theme. The operating system colour scheme (`prefers-color-scheme`) picks one; there is no manual switch.
