# Notes for owner

Things a future cycle (or a human) should know that don't fit elsewhere.
Per TASKS.md: this is also where an idea that needed an API key or account
gets parked instead of built, since this project only ships keyless tools.

## Ideas rejected this cycle, and why

- **Word/character/token counting MCP tool.** Real, well-documented need
  (models genuinely can't count reliably — see
  github.com/orgs/community/discussions/177647 and several explainer
  posts on tokenization). Not built: the space is already saturated with
  multiple existing, apparently-maintained MCP servers doing exactly this
  (text-count-mcp-server, mcp-wordcounter, several more on Glama/mcp.so).
  Nothing keyless-and-novel found. Worth revisiting only with a genuinely
  differentiated angle.
- **Precise text-diff MCP tool.** Same shape: real need (AI document-
  comparison write-ups explicitly say LLMs "cannot replace the precision
  of a deterministic diff"), but also already covered by several existing
  MCP diff/text-tools servers.
- **Cron expression parser/explainer, unit converter, subnet/CIDR
  calculator, generic calculator.** All genuinely "gap in what an LLM does
  reliably" problems, and all already have multiple existing, apparently
  solid MCP implementations found in search. Didn't build any of these
  this cycle for the same saturation reason.

None of the above needed an API key — they were passed over for being
already well-served elsewhere, not for infeasibility. If a future cycle
finds a genuinely differentiated angle on any of them (the way this
cycle's `secure-random` differentiates on randomness with a built-in,
checkable uniformity proof rather than just another number generator),
they're worth reconsidering.

## Nothing needing a key/account came up this cycle

No candidate was rejected specifically for needing credentials this time —
worth double-checking that's still true as ideas get more niche in future
cycles (the obvious keyless ones are getting picked over).

## Process note

Building and testing an MCP server locally requires `pip install mcp` (and,
in this container image specifically, `cffi` — the system `cryptography`
package needs it and errors with a confusing `pyo3_runtime.PanicException`
/ `ModuleNotFoundError: No module named '_cffi_backend'` without it).
Neither is committed to the repo (each tool declares its own
`requirements.txt`); noting it here so the next cycle doesn't lose time
rediscovering it if the same container image is reused.
