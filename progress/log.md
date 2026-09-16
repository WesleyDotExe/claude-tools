# Progress log

Newest entry on top. One entry per cycle: what was done, honestly.

## 2026-09-16 — fourth run: built discrete-probability

- Ran `tools/collection-index/index.py` first, per the loop: 3 tools
  existed. Nothing overlapped a fresh candidate need.
- Web-searched several candidate angles: general "wish Claude/ChatGPT
  could" complaints, hashing/checksums, readability/syllable counting,
  bitwise arithmetic, semver ranges, haversine geodistance, and discrete
  probability. The first six all landed on the same saturation outcome as
  the last two cycles -- notably discovering that a single account
  (pipeworx-io) already publishes dedicated MCP servers for
  readability/text-stats, semver, and geodistance, which is a stronger
  signal than before that the obvious "AI can't do X" calculator-shaped
  gaps are being actively picked over across the whole MCP ecosystem.
- Discrete probability broke the streak: a 2026 paper on counterintuitive
  discrete-probability problems (arxiv.org/pdf/2606.07516) found models
  average 0.96 accuracy on standard probability problems but only 0.59 on
  counterintuitive ones, and the "LLMs Can't Do Probability" writeup
  (brainsteam.co.uk) documents the same failure informally, with an active
  Hacker News discussion. Existing calculator MCP servers expose raw
  combinatorics primitives (nCr, nPr, factorial) but not pre-composed
  scenarios like the birthday paradox or Monty Hall, and none found pair
  the answer with a Monte Carlo cross-check.
- Built `tools/discrete-probability`: `probkit.py` (six exact functions --
  `birthday_collision`, `dice_sum_distribution`, `hypergeometric_probability`,
  `binomial_probability`, `bayes_update`, a generalized `monty_hall` -- using
  `fractions.Fraction`/`math.comb` for exact arithmetic, plus a from-scratch
  Wilson score confidence interval) and `server.py` (MCP stdio wrapper).
  Every function accepts `verify=true` to actually play the scenario out via
  CSPRNG draws (`secrets`, the same source `tools/secure-random` uses) and
  check the exact answer against the simulated frequency's 95% interval --
  deliberately building on the existing collection's proof-not-assertion
  pattern rather than reinventing it.
- Wrote 41 unit tests (`tests/test_probkit.py`): known textbook values
  (birthday-23/365 ~= 50.73%, classic Monty Hall 1/3 vs 2/3, 2d6-sums-to-7 =
  1/6, >=2 aces in a 5-card hand ~= 4.17%), input validation, and two
  correctness cross-checks: `bayes_update`'s general machinery and
  `monty_hall`'s independently-derived closed-form formula fed equivalent
  problems and landing on the exact same fraction via two unrelated code
  paths, and a "does the check have teeth" test proving the Wilson-interval
  logic actually flags a wrong claim, not just passes a correct one -- the
  same discipline `secure-random`'s chi-square tests apply to bias.
- Drove the live MCP server over stdio with a real client: `list_tools` plus
  all six tools called, several with `verify=true` (30,000 real CSPRNG
  trials each), and a deliberately invalid input (an impossible `reveal`
  count for a generalized Monty Hall) confirmed to come back as an MCP
  error result rather than a silently wrong number.
  `tools/discrete-probability/proof/run_2026-09-16.txt`.
- Fixed one real bug caught while writing tests, not after shipping:
  `_parse_probability` treated a plain int (`1` or `0`) as inexact (a bare
  `float`/`int` branch), so `bayes_update("1/3", 1, 0)` silently downgraded
  from exact-fraction arithmetic to float arithmetic partway through and
  the returned `posterior` came back as a bare float instead of the
  `{fraction, decimal}` shape every other exact result uses. Fixed by
  making ints parse to `Fraction` like fraction strings do (floats still
  stay float, since a literal like `0.3` isn't exactly representable and
  shouldn't be laundered into a falsely-precise fraction).
- Updated root `README.md`, appended this cycle to
  `special-projects/cycles.json`, rebuilt `_site/dashboard.html`, updated
  `special-projects/current.md` and `progress/notes-for-owner.md`.

## 2026-09-15 — third run: hardened CI, extended secure-random

- Ran `tools/collection-index/index.py` first, per the loop: 3 tools
  existed. Nothing overlapped a fresh candidate need.
- Web-searched several candidate angles (general "wish Claude could"
  complaints, MCP-idea threads, AI regex/ReDoS correctness, WCAG color
  contrast, precise large-number arithmetic). All landed on the same
  outcome as last cycle: real, well-documented "LLMs get this wrong"
  problems, but every one already has multiple existing MCP servers
  (regex/ReDoS especially -- found a dedicated ReDoS-guard MCP server,
  which is close enough to this repo's own differentiation angle that
  building another wouldn't add anything). See
  `progress/notes-for-owner.md` for the full rejection notes.
- Rule 9 applied: no new-tool candidate cleared the bar, so this cycle
  hardened and extended the existing collection instead of shipping
  filler. Two pieces of work:
  1. **Fixed the standing CI gap** (`progress/quality-debt.md`, carried
     over from the first cycle): added `.github/workflows/test.yml`,
     which runs every `tools/*/tests/` suite plus a `collection-index`
     sanity check on `pull_request` and `push:main`, with a job name
     (`test`) that matches `auto-merge.yml`'s existing
     `/deploy|build|test/i` check-name filter. While doing this, found a
     second bug in `auto-merge.yml`: it runs on `pull_request_target`
     (fires immediately) racing against `test.yml` on the separate
     `pull_request` event, and treated "no relevant check registered
     yet" as "nothing to wait for" -- meaning even a correctly-named test
     workflow could lose the race and get skipped. Fixed with a 60s grace
     period before concluding there's genuinely nothing to wait for.
  2. **Extended `secure-random`** with weighted sampling: `pick_random`
     now takes an optional `weights` list (unique and with-replacement
     both supported), and a new `verify_weighted_distribution` tool
     extends the existing chi-square proof-not-assertion pattern to
     arbitrary weighted distributions instead of just the uniform case.
     This was flagged as a live option in the previous cycle's
     `quality-debt.md` and `special-projects/current.md`.
- Also caught, while re-reading `time-arithmetic`'s own README this
  cycle, that the previous cycle's "extend with natural-language date
  parsing" suggestion contradicts that tool's own stated design boundary
  ("What it doesn't do" frames the absence as deliberate, not unbuilt).
  Recorded the course-correction in `notes-for-owner.md` and dropped it
  from `current.md`'s next-step list.
- Added 13 new unit tests to `tools/secure-random/tests/test_randkit.py`
  (47 total, up from 34) covering weighted `pick_random` (favors the
  heavy item, never returns a zero-weight item, rejects mismatched/
  negative/all-zero weights, unique mode has no repeats) and
  `verify_weighted_distribution` (real CSPRNG draws over `[1,2,7]` land
  within 2% of the 10/20/70 split it should follow, p ≈ 0.13; input
  validation).
- Drove the live MCP server over stdio with a real client to prove the
  new tools work end-to-end, not just the underlying functions:
  `tools/secure-random/proof/run_2026-09-15.txt` -- weighted `pick_random`
  (both modes), unweighted `pick_random` still working unchanged, and
  `verify_weighted_distribution`. Read back `structured_content` (not just
  the display-oriented text blocks, which the MCP SDK still splits one
  block per list element for list-typed returns) to confirm the JSON
  array comes back correctly typed.
- Updated `tools/secure-random/README.md` and `manifest.json`
  (`tools_exposed`, `updated` date), root `README.md`,
  `progress/quality-debt.md` (closed both fixed items),
  `progress/notes-for-owner.md`, appended this cycle to
  `special-projects/cycles.json`, rebuilt `_site/dashboard.html`.

## 2026-09-14 — second run

- Ran `tools/collection-index/index.py` first, per the loop: 2 tools
  existed (`collection-index`, `time-arithmetic`), nothing to extend that
  clearly beat a fresh candidate this cycle.
- Web-searched for candidate needs across several angles: general "I wish
  Claude could" complaints (unproductive — mostly SEO content, not real
  threads), AI text-counting complaints, spreadsheet/calculation
  complaints, regex reliability, cron expressions, unit/subnet conversion,
  and LLM randomness. See `special-projects/cycles.json` for the full
  query list and findings.
- Found three real candidates (word/character counting, precise text
  diffing, LLM randomness bias) and checked each against the existing MCP
  ecosystem, not just this repo — word-counting and diffing are both
  already served by many existing MCP servers; randomness had a sharper,
  more specific documented failure mode (the "27" phenomenon) and this
  repo's angle (a checkable chi-square uniformity proof) isn't something
  the existing random-number MCP servers found in search results do.
- Built `tools/secure-random`: `randkit.py` (CSPRNG functions + a
  hand-rolled chi-square goodness-of-fit test, stdlib only) and
  `server.py` (MCP stdio wrapper, 10 tools).
- Wrote 34 unit tests (`tests/test_randkit.py`), including validating the
  hand-rolled chi-square p-value function against six textbook critical
  values, and a synthetic biased-histogram test proving the uniformity
  test actually catches bias rather than only ever passing real
  randomness.
- Drove the live MCP server over stdio with a real client (not just
  scaffolding): `list_tools` + all 10 tools called, captured in
  `tools/secure-random/proof/run_2026-09-14.txt`.
- **Caught and fixed a real bug during the live-session proof, not after
  shipping:** `shuffle_list`/`pick_random` were typed to return a bare
  `list`, which made the MCP SDK skip structured-output generation and
  split results across one text content block per element — silently
  losing type fidelity (e.g. a list of ints came back as separate string
  content blocks, `["20","30","10"]`-shaped rather than a JSON array of
  ints). Fixed by annotating both as `list[Any]`; re-ran the live session
  to confirm before writing the final proof transcript.
- Wrote `tools/secure-random/README.md`, added it to the root README's
  tool list, appended the cycle to `special-projects/cycles.json`, and
  rebuilt `_site/dashboard.html` via `scripts/build_site.py`.
- Created the four standing progress files for the first time this cycle
  (none existed yet): this log, `progress/quality-debt.md`,
  `progress/notes-for-owner.md`, `special-projects/current.md`.
- Installed `mcp`, `cffi` via `pip install --user` to actually run/drive
  the server locally (not committed — see requirements.txt for the tool's
  own declared dependency).

## 2026-09-13 — first run under the standing project

See `special-projects/cycles.json` for the full record (search queries,
source, why, proof). Summary: created `tools/` and the `manifest.json`
convention, built `collection-index` (the collection's own index/reporting
tool), then `time-arithmetic` (MCP server for deterministic date/time
math). 13 unit tests + a live MCP client session, both passing. Also added
the project README, MIT license, and the `auto-merge` GitHub workflow for
`claude/*` branch PRs (see `progress/quality-debt.md` for a gap noticed in
that workflow this cycle).
