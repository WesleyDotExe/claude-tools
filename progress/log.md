# Progress log

Newest entry on top. One entry per cycle: what was done, honestly.

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
