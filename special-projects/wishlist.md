# Wishlist — capability gaps for future tools

This is the demand signal for the collection (see TASKS.md). It is fed by the owner and by scheduled agent runs — this repo's and the owner's other agents — whenever they hit friction: a calculation done by hand that a tool would make reliable, a multi-step that should be one call, a check that could not be made, a gotcha re-discovered.

Each build cycle reads this FIRST and builds for the most-repeated real item. One line per item. When you hit an item again, add a `+1 (date)` so recurrence is visible. Move an item to Done (with the tool name + date) when a tool ships for it.

## Open

- [stats-normal-vs-exact-pvalue] While building `compare_two_proportions` (2026-09-24), found that a pooled-variance two-proportion z-test's p-value and an exact/permutation-test p-value can legitimately diverge by several points of p at moderate sample sizes (confirmed against a hand-derived exact hypergeometric-tail calculation, not a bug) — this is a real, general statistical fact, not specific to this tool. Worth remembering for any *future* significance-test tool in this collection (e.g. if a chi-square/ANOVA/paired-test tool is ever built): don't design a "does the simulation match the analytic answer" check that assumes a normal-approximation p-value and an exact p-value must coincide — check agreement on the practical conclusion (the significance call) instead, and say so explicitly in the tool's own output so a caller isn't confused by the gap.

## Done (tool shipped for it)

- [balance-stats] `discrete-probability`'s `compare_two_proportions` (2026-09-24) — exact two-proportion z-test with Wilson CIs per group, a Newcombe CI for the difference, a plain verdict, and (verify=true) an independent CSPRNG permutation-test cross-check. Built for the AI TCG balance run's win-rate-gap-significance question.
- [build-env] `scripts/mcp_dev_setup.sh` (2026-09-25) — one-shot, idempotent `pip install --user mcp cffi` preflight, run once at the top of a build cycle instead of rediscovering the pyo3/cffi failure by hand. Confirmed as a genuine second recurrence (this cycle's fresh container hit the exact same `ModuleNotFoundError` before installing) rather than acted on from a single mention.
- [mcp-proof] `scripts/mcp_client.py` (2026-09-25) — a reusable stdio MCP client (library + CLI) that extracts a typed result from a `CallToolResult` (`structured_content` first, falls back to parsing text content as JSON) instead of every proof script re-deriving that by hand. `run` replays a whole JSON list of labeled calls against one server and prints/saves them in this repo's existing `--- label ---\n<value>` proof-file shape. Proof it works against two different existing servers (`secure-random`, `discrete-probability`), including error cases: `scripts/proof/run_2026-09-25.txt`.
