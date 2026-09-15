# Quality debt

Honest list of known gaps and shortcuts. Not urgent by default — surfaced
so a future cycle (or the owner) can decide whether to pay them down.

## Fixed this cycle (2026-09-15): no CI actually ran tests before auto-merge

Was: `.github/workflows/auto-merge.yml` waits for check runs matching
`/deploy|build|test/i` on the PR's head commit, but no workflow produced a
check with one of those names, so the "wait for checks to pass" step found
zero relevant checks and merged immediately without ever running a test.

Fixed by adding `.github/workflows/test.yml` (job name `test`, matches the
existing regex) that runs `python3 -m unittest discover -s tests` for every
`tools/*/tests/` directory plus a `collection-index` sanity check, on every
`pull_request` and on push to `main`.

While fixing it, found and fixed a second, subtler bug in the same file:
`auto-merge.yml` runs on `pull_request_target` (fires immediately when a PR
opens) while `test.yml` runs on the separate `pull_request` event — a race.
The old loop treated "no relevant check run exists yet" as "nothing to wait
for" and merged instantly, which meant even a correctly-named test workflow
could lose the race and never get waited on if its check run hadn't
registered in the few hundred milliseconds before `auto-merge.yml`'s first
poll. Fixed with a grace period (`GRACE_ITERATIONS`, 60s) before the loop
concludes there's truly nothing to wait for. Not covered by an automated
test (it's GitHub Actions timing behavior, hard to unit test locally) — the
real proof is this cycle's own PR going through the now-live `test` check
before merging; worth eyeballing that PR's checks tab to confirm.

## `secure-random`'s `verify_uniformity` is O(samples) in Python, not vectorized

At the high end of its accepted range (up to 2,000,000 samples) it's a
plain Python loop calling `secrets.randbelow` per draw — correct, but slow
compared to, say, filling a NumPy array. Not a real problem at the sample
sizes the tool is meant for (thousands, to answer "is this range biased?"
in a reasonable diagnostic run), and adding NumPy would break the
"stdlib only, keyless, no dependency beyond `mcp`" property the whole
collection is built on. Documented, not fixed, because the tradeoff (stay
dependency-free vs. faster large-N) favors staying dependency-free.

## Fixed this cycle (2026-09-15): `pick_random`'s uniform-only sampling

Was: `pick_random` (in `tools/secure-random`) only did uniform selection --
no weighted/biased sampling, even though callers sometimes want that
("pick a winner weighted by ticket count").

Fixed by adding an optional `weights` parameter to `pick_random` (both
unique and with-replacement modes) and a new `verify_weighted_distribution`
tool that chi-square-tests real draws against the requested weights,
extending the same proof-not-assertion pattern `verify_uniformity` already
used for the uniform case. 13 new unit tests plus a live MCP session
(`proof/run_2026-09-15.txt`).
