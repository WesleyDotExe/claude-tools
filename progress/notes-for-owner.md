# Notes for owner

Things a future cycle (or a human) should know that don't fit elsewhere.
Per TASKS.md: this is also where an idea that needed an API key or account
gets parked instead of built, since this project only ships keyless tools.

## 2026-09-16: ideas rejected this cycle, and a sharper saturation signal

Checked six more candidates before landing on `discrete-probability`:
hashing/checksums (SHA256/MD5), text readability/syllable counting
(Flesch-Kincaid), bitwise arithmetic (AND/OR/XOR on large numbers), semver
range satisfaction, and haversine great-circle geodistance. All had at
least one existing MCP server; readability, semver, and geodistance
specifically are all published by the same account (pipeworx-io), which
appears to be systematically working through exactly this "single
deterministic calculation as an MCP tool" space. That's a sharper signal
than the last two cycles' saturation findings: it's not just that any given
idea has *a* competitor, it's that the whole shape of idea ("wrap one
well-known formula/algorithm as an MCP tool") is being actively colonized.
A future cycle chasing a new tool in that shape should expect saturation as
the default outcome, not the exception, and either look for a fresh
*angle* on an already-covered domain (the way `secure-random`'s
`verify_uniformity` differentiates on checkability rather than novelty) or
a problem shape that isn't "one deterministic calculation" at all
(`discrete-probability`'s shape -- several related word-problem scenarios
sharing a verification mechanism -- was one way out this cycle).

- **Hashing/checksums (SHA256, MD5, etc.).** Real, well-documented failure
  (models return a plausible-looking but wrong hash rather than computing
  one). Not built: multiple existing MCP servers (Apify's hash-generator
  connectors, kanad13/MCP-Server-for-Hashing, a Glama "Hash Digest Tool")
  already cover exactly this.
- **Text readability / syllable counting (Flesch-Kincaid etc.).** Real (the
  syllable-counting heuristic is a documented weak point even for
  dedicated tools, let alone models). Not built: pipeworx-io/mcp-textstats
  and several older non-MCP libraries already do this.
- **Bitwise arithmetic (AND/OR/XOR/shift on large numbers).** Plausible
  failure mode, but no sharply-articulated real complaint turned up in
  search (mostly generic bitwise-operation reference material, not people
  reporting AI getting it wrong) -- didn't clear the "actually expressed
  need" bar in TASKS.md step 2, separately from any saturation question.
- **Semver range satisfaction (`^1.2.0`, `~1.2.0`, etc.).** Same shape as
  hashing: plausible, but pipeworx-io/mcp-semver already implements
  `satisfies_range` for caret/tilde/comparator/x-range/AND/OR syntax.
- **Haversine / great-circle geodistance.** Same shape again:
  pipeworx-io/mcp-geodistance and Mapbox's own MCP server both already
  compute this.

None of the above needed an API key or account — passed over for
saturation (or, for bitwise arithmetic, a weak source signal), not
infeasibility.

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
