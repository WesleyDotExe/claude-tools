# Notes for owner

Things a future cycle (or a human) should know that don't fit elsewhere.
Per TASKS.md: this is also where an idea that needed an API key or account
gets parked instead of built, since this project only ships keyless tools.

## 2026-09-15: course-correction on the standing "next step" list

The previous `special-projects/current.md` suggested extending
`time-arithmetic` with natural-language relative-date parsing ("next
Friday", "in 3 business days") as future work. Re-reading that tool's own
README this cycle: its "What it doesn't do" section frames the *absence*
of natural-language parsing as a deliberate design boundary ("this tool is
for exact calculation once the inputs are already unambiguous, not for
interpreting vague scheduling language"), not an unbuilt feature. Building
it would cut against the tool's own stated scope. It's also a heavily
saturated space already (chrono-node, dateparser, parsedatetime, and
multiple existing NL-date MCP wrappers). Recommend dropping that specific
suggestion rather than carrying it forward again; if a future cycle wants
to revisit it, treat it as a *new, separate* tool decision (does the need
clear the saturation/feasibility bar on its own?), not as "finishing" what
time-arithmetic already deliberately declined to do.

## 2026-09-15: this cycle's research reinforces "the obvious ideas are saturated"

Checked several more candidates this cycle before deciding not to build a
new tool: AI-generated regex correctness/ReDoS detection, WCAG color
contrast checking, and general big-number/precise arithmetic. All three
are real, well-documented "LLMs get this wrong" problems, and all three
already have multiple existing MCP servers (including, for regex, at least
one dedicated ReDoS-heuristics guard). Same outcome as last cycle's
word-counting/diffing/cron/unit-conversion search: the visible, easy-to-
articulate "AI can't do X" gaps are getting picked over fast across the
whole MCP ecosystem, not just this repo. Future cycles may need to search
for less obvious angles, or accept doing more "harden/extend existing tool"
cycles (TASKS.md rule 9) than "ship a new tool" cycles.

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
- **Regex correctness / ReDoS (catastrophic backtracking) checker.**
  (2026-09-15) Real, sharply-documented problem — LLM-generated regexes are
  known to have inconsistent escaping and, more seriously, nested-quantifier
  ReDoS vulnerabilities exploitable as a DoS vector. Not built: multiple
  existing MCP servers already do exactly this, including at least one
  (Regex ReDoS Guard) whose entire focus is static ReDoS analysis with
  caller-defined complexity limits — closer to this repo's "checkable
  proof" style than a generic tester, so the differentiation this repo
  would need isn't there.
- **WCAG color contrast checker.** (2026-09-15) Real problem (models give
  wrong contrast ratios because they don't run the actual luminance/ratio
  math), but at least half a dozen existing MCP servers already compute
  WCAG 2.1 contrast ratios from hex/RGB/HSL input. No differentiated angle
  found.

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
