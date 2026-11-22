# Issue Triage State: typescript-checker-rust

Last run: not yet run
Open actionable: 0
New since last run: 0
Needs human: 0

## Top 5 (by loop score)

- (none yet; the first manual run will populate this)

## Proposed Labels (not applied at L1)

- (none)

## Possible Duplicates (human confirm)

- (none)

## Noise / Ignored

- (none)

## Allowlisted labels (L2 only; nothing is applied at L1)

`area:*`, `needs-repro`, `needs-info`

## Denylist (always human)

The checker's JSON contract (`schema_version`, field shapes, diagnostic codes and their meaning, span units, exit codes), the input limits (64 KiB source cap, 50-diagnostic cap, nesting and instantiation limits), the rule that input is never executed, request guards in the wrapper (loopback bind, Host, Origin, body caps, security headers, static allowlist), how the checker process is started (argument list, no shell, time and output caps), path handling for project directories and import specifiers, new dependencies (crates, pip, npm), external requests or tools (including the reference compiler), the pinned toolchain and CI workflow, any speed claim, breaking-change
