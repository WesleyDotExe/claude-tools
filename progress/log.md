# Progress log

Newest entry on top. One entry per cycle: what was done, honestly.

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
