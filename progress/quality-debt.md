# Quality debt

Honest list of known gaps and shortcuts. Not urgent by default — surfaced
so a future cycle (or the owner) can decide whether to pay them down.

## No CI actually runs tests before auto-merge

`.github/workflows/auto-merge.yml` waits for check runs matching
`/deploy|build|test/i` on the PR's head commit, but no workflow in this
repo currently *produces* a check with one of those names — there's no
`test.yml` or similar that runs `python3 -m unittest discover` (or
equivalent) on a PR. That means the "wait for checks to pass" step finds
zero relevant checks, treats that as nothing to wait for, and merges
immediately. In practice this hasn't caused a bad merge because each
cycle's session runs the tests by hand before opening the PR and won't
open one if they fail — but that's a human/session discipline
guarantee, not a repo guarantee. A malformed PR (wrong branch, bad merge,
anything that skips the "I ran the tests" step) would sail through
unchecked.

Fix would be a `.github/workflows/test.yml` that runs each
`tools/*/tests/` suite (and maybe `collection-index` itself as a sanity
check) on `pull_request`, matching one of the auto-merge workflow's name
patterns. Not fixed this cycle because it's infrastructure work orthogonal
to this cycle's tool, and touching CI/merge automation deserves its own
focused pass rather than a drive-by edit.

## `secure-random`'s `verify_uniformity` is O(samples) in Python, not vectorized

At the high end of its accepted range (up to 2,000,000 samples) it's a
plain Python loop calling `secrets.randbelow` per draw — correct, but slow
compared to, say, filling a NumPy array. Not a real problem at the sample
sizes the tool is meant for (thousands, to answer "is this range biased?"
in a reasonable diagnostic run), and adding NumPy would break the
"stdlib only, keyless, no dependency beyond `mcp`" property the whole
collection is built on. Documented, not fixed, because the tradeoff (stay
dependency-free vs. faster large-N) favors staying dependency-free.

## `pick_random`'s uniform-only sampling

`pick_random` (in `tools/secure-random`) only does uniform selection --
no weighted/biased sampling, even though callers sometimes want that
("pick a winner weighted by ticket count"). Noted as a candidate
extension in `special-projects/current.md` rather than built speculatively
this cycle, since no real expressed need for it surfaced in this cycle's
research (unlike the base uniform-randomness gap, which had direct
documentation).
