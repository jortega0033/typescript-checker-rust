# Releasing

Only the owner releases. Agents never tag, publish or create a GitHub release.

## What a release is here

A release is a Git tag on a commit of `main`, `vMAJOR.MINOR.PATCH`, matching `version` in `Cargo.toml`. The crate is not published (`publish = false`), nothing is deployed and there are no packaged artifacts. The product runs from a clone: `cargo build --release`, then `python -m ts_checker_web --data-dir ./data --port 8765`.

## Checks before tagging

1. CI is green on the tip of `main` for both jobs (`test` and `rust`) on Linux and Windows.
2. `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo build --locked --release` and `cargo test --locked` pass, from that CI run or from a local run.
3. `python -m unittest discover -s tests` passes.
4. The README smoke steps were run in a local browser against the real binary (the release check of epic #1 records this).
5. `Cargo.toml` has an empty `[dependencies]` table and `Cargo.lock` lists one package.
6. `CHANGELOG.md`: move the `Unreleased` entries under a new version heading with the date.

## Tagging

1. In a pull request, set `version` in `Cargo.toml` (and `Cargo.lock`) and update `CHANGELOG.md`; the owner merges it.
2. On the merge commit: `git tag -a vX.Y.Z -m "vX.Y.Z"` and `git push origin vX.Y.Z`.
3. Optional: create a GitHub release from the tag with the changelog section as its text.

Epic #1 owns the release check (ticket #10). Do not tag before it is done.
