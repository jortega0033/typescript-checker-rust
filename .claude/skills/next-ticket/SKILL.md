---
name: next-ticket
description: Owner-started driver that takes one ticket of epic #1 from the queue to a ready pull request, using the implement-ticket playbook. Starting it is the owner's go signal; it never merges.
argument-hint: "[issue number]"
disable-model-invocation: true
---

# Next ticket

Only the owner starts this skill (`/next-ticket` or `/next-ticket <issue number>`). Starting it is the go signal for one ticket, and counts as the owner's request, for this run, to push the ticket branch and open the pull request. Nothing starts it automatically and nothing schedules it: this repository is used to train AI models, so every run needs the owner's go.

Run exactly one ticket, then stop. Never merge, never tag or release, never start another run.

Epic: #1 (`jortega0033/typescript-checker-rust`). Dependency order: #7, #2, #3, #4, #5, #8, #9, #6, #10 (the table "Tickets, in dependency order" in the epic is the source).

## Labels

`status:ready`, `status:blocked`, `status:in-progress`, `needs-decision`. If a label does not exist yet, do not create it: say so in the run summary and use the epic's dependency table instead.

## Steps

1. **Refresh the queue.** `gh issue list --state open --label status:blocked`. For each one, read its "Needs" in the epic table and its native blocked-by links. If every blocker is closed and the ticket carries no `needs-decision`, change its label to `status:ready`. Do not touch anything else.
2. **Pick the ticket.** With an issue number: use it, and stop with a reason if it is closed, `status:blocked`, `status:in-progress` or `needs-decision`. Without one: the first `status:ready` ticket in the dependency order above that is not `status:in-progress` and not `needs-decision`. If none qualifies, say why (for example "#7 is `needs-decision`") and stop.
3. **Claim it.** Label it `status:in-progress` (`gh issue edit <n> --add-label status:in-progress --remove-label status:ready`).
4. **Branch in a fresh worktree**, as `CLAUDE.md` "Git workflow" says: `git fetch origin`, then `git worktree add ../typescript-checker-rust-issue-<n> -b issue-<n>-<short-slug> origin/main`. One branch and one pull request per issue. Never work on `main` and never touch the owner's checkout.
5. **Run the playbook** [`.claude/skills/implement-ticket/SKILL.md`](../implement-ticket/SKILL.md) for the ticket, in the new worktree. It runs the roles, both gates, the evidence list of `CLAUDE.md` and the UI and writing checks.
6. **Open the pull request** only after Code Reviewer and Reality Checker both ran on the current diff and passed. Push the branch (`git push -u origin <branch>`; the review gate hook blocks `gh pr create` and `gh pr ready` until both gates have run after the last code edit) and open it from `.github/pull_request_template.md` with `Closes #<n>` only when every acceptance criterion is met. Never leave a gate open to open the pull request.
7. **Wait for CI.** `gh pr checks`. Fix failures and re-run the gates on the new diff. Mark the pull request ready (`gh pr ready`) only when CI is green on the current diff.
8. **Report on the issue.** Comment on the issue with the pull request link, the CI result and anything not verified. Keep the label `status:in-progress` until the owner merges.
9. **Stop.** Print one summary: ticket, branch, pull request, CI result, open questions. The owner merges.

## Stop and say so

A ticket that needs an owner decision, a change to `CLAUDE.md`, `LOOP.md` or CI beyond its scope, a new dependency, or anything under the human gates in `LOOP.md`: stop, label it `needs-decision` if the label exists, comment what is needed, and end the run.
