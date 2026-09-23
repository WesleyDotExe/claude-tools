# Wishlist — capability gaps for future tools

This is the demand signal for the collection (see TASKS.md). It is fed by the owner and by scheduled agent runs — this repo's and the owner's other agents — whenever they hit friction: a calculation done by hand that a tool would make reliable, a multi-step that should be one call, a check that could not be made, a gotcha re-discovered.

Each build cycle reads this FIRST and builds for the most-repeated real item. One line per item. When you hit an item again, add a `+1 (date)` so recurrence is visible. Move an item to Done (with the tool name + date) when a tool ships for it.

## Open

- [balance-stats] The AI TCG balance runs hand-roll win-rate comparison every cycle (is a 62% vs 55% gap over 300 games real, or noise?). A keyless "compare two proportions" tool — exact two-proportion test + Wilson confidence intervals, with a plain verdict — would make every balance report's flags rigorous instead of eyeballed. Caller: the AI TCG balance run (balanceReport). secure-random / discrete-probability are adjacent but do not expose this directly. +1 (2026-09-24)
- [build-env] Building/testing an MCP server here needs `pip install mcp` and (in this container image) `cffi`, or the stdlib crypto import fails with a confusing pyo3 panic. Re-discovered across several cycles. A documented one-shot preflight (or a tiny setup helper) would stop each run losing time to it. Caller: every build cycle in this repo. +1 (2026-09-24)
- [mcp-proof] The installed `mcp` client returns tool results only in the text content block, not `structured_content`; a proof-gathering run must parse `result.content[0].text` as JSON. A small "drive an MCP server over stdio and collect typed results" harness would remove this footgun from every future proof. Caller: every build cycle that proves an MCP server. +1 (2026-09-24)

## Done (tool shipped for it)

(none yet — move items here with the tool name + date when built)
