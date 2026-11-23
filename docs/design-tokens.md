# Design tokens

The workbench page uses the Pipenzo "Flow look" tokens: black page, Flow-style alpha layers, one accent (Pipenzo yellow `#FECE02`), red only for danger.

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
| Accent | `--primary`, `--primary-press`, `--primary-edge`, `--on-primary` (primary action and current step only) |
| Status | `--danger`, `--danger-bg`, `--success`, `--ok`, `--ok-bg`, `--warn-fg`, `--warn-bg`, `--info` |
| Focus | `--focus` |
| Dark blocks | `--ink`, `--on-ink`, `--on-ink-muted`, `--ink-border`, `--hero-*` |
| Layers and shadows | `--glass*`, `--scrim`, `--state-*`, `--btn-secondary*`, `--shadow-*` |
| Type, space, motion | `--font`, `--mono`, `--space-*`, `--radius-*`, `--dur-*`, `--ease-*` |

Note: `--ink` is a dark block colour here, not the text colour. Text is `--fg`.

## Rules

- New UI uses these tokens; no new colour literals in `app.css` or `app.js`.
- Yellow only on the primary action and the current-step marker. Text never sits on a bare alpha layer.
- The ten rules in [ui-quality.md](ui-quality.md) still apply.

## Light and dark

Dark is the primary design. The light block is the matching light theme. The operating system colour scheme (`prefers-color-scheme`) picks one; there is no manual switch.
