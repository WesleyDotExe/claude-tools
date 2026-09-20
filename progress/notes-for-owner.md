# Notes for owner

## 2026-09-20: ideas rejected this cycle before extending `graph-algorithms` with coloring

Checked two fresh candidates before deciding to pay down the deferred
graph-coloring gap in `graph-algorithms` instead (per TASKS.md rule 9,
"deepen/extend an existing tool" counts as a valid cycle outcome, and
`special-projects/current.md`'s own next-step list flagged this as the
most-ready option):

- **Symbolic/computer algebra (simplify, factor, solve, derivatives/
  integrals).** Real, sharply-documented failure mode (the ASyMOB
  benchmark and 2026 "Beyond Accuracy: Diagnosing Algebraic Reasoning
  Failures" paper both show LLMs failing symbolic manipulation tasks
  distinct from numeric calculation -- exactly the "exact symbolic/
  algebraic manipulation" unexplored shape the previous cycle's
  `current.md` flagged). Not built: heavily saturated -- sdiehl/sympy-mcp,
  codeprimate/math-mcp, matheusbgodoi/scimath-mcp, LBurny/symkit-mcp, and
  azzindani/MCP_Math all already wrap SymPy for exactly this. Also a weak
  fit regardless of saturation: SymPy is a large non-stdlib dependency,
  cutting against this collection's stdlib-only-where-possible discipline
  every other tool follows (the same tension `secure-random`'s
  `verify_uniformity` and `graph-algorithms`' own non-vectorized
  implementations already document for themselves).
- **Computational geometry (convex hull, polygon intersection, collision
  detection).** Plausible shape (a fifth structural/geometric algorithm
  family, distinct from graph algorithms), but didn't clear TASKS.md step
  2/3's "actually expressed need" bar -- search turned up geometry
  reference material and existing libraries/implementations, not a
  sharply-documented "LLMs get this wrong" complaint the way the graph-
  reasoning benchmarks motivated `graph-algorithms` itself. A PostGIS MCP
  server already exposes convex hull as one tool among many, further
  weakening the case. Worth reconsidering only if a future cycle's search
  finds a real, sharply-articulated source for this specific failure mode.

Chose graph coloring instead: it's real (documented in the same 2025/2026
graph-reasoning benchmark suite that motivated `graph-algorithms` itself),
it extends rather than duplicates an existing tool (no saturation risk --
it's this collection's own vocabulary, not a competing standalone MCP
server), and the full design (DSATUR + forward-checking backtracking,
`max_search_nodes` budget, clique-lower-bound minimality proof) was already
sketched out in the previous cycle's `progress/quality-debt.md` entry, so
it cleared TASKS.md's feasibility gate cleanly. See that file's now-"fixed"
entry for what was built.

## 2026-09-19: this session's designated branch was already merged+deleted before work started

The branch this run was told to develop on (`claude/happy-galileo-k8r2gx`)
turned out to already be the head of `main` (all 5 prior cycles' work) by
the time this session ran its first `git fetch` -- the branch had been
merged and auto-deleted between the session's initial clone and its next
fetch a few commands later, presumably a race with whatever merged the
previous cycle's PR. Handled per the standing merged-branch protocol:
restarted the branch from the fresh `main` tip and continued as a new
cycle. No work was lost -- worth knowing this can happen mid-session (not
just "checked once at the start"), so a future run shouldn't assume an
initial `git branch -a` listing is still accurate several commands later
without re-fetching.

## 2026-09-19: `CallToolResult` uses `is_error` (snake_case), not `isError`

While driving `graph-algorithms`' live-session proof, `result.isError`
raised `AttributeError` under the installed `mcp` client library --
pydantic's `main.py` explicitly suggested the fix. The correct attribute is
`result.is_error`. Camel case shows up in the *wire* JSON-RPC field name
(`isError`), but the Python `CallToolResult` model exposes it snake_cased.
Noting this so a future cycle writing its own live-session proof driver
doesn't lose time on the same `AttributeError`.

## 2026-09-18: the installed `mcp` package (2.2.0) doesn't populate structuredContent for any tool

While building this cycle's live-session proof for `strips-planner`, every
tool call's `CallToolResult.structured_content` came back `None` (and
`list_tools()`'s per-tool `output_schema` was also `None`) regardless of how
the tool's return type was annotated (`-> dict`, matching what
`logic-grid-solver` already does) -- spot-checked, and the same is true for
`logic-grid-solver`'s tools under this same installed `mcp==2.2.0`. The full,
correct JSON is still there, just only in the text content block
(`result.content[0].text`), which the server evidently populates via
`json.dumps` as a fallback. This is different from the `list`-typed-return
structured-output bug the second cycle found and fixed in `secure-random`
(that was about `list` return types specifically splitting into one text
block per element) -- this is broader and affects plain `dict` returns too,
and looks like a change in this `mcp` package version's behavior rather than
anything wrong in a specific tool's code. Not fixed because there's nothing
in this collection's tools to fix -- a calling MCP client still gets the
correct data either way, from `content` instead of `structured_content`. A
future cycle gathering a live-session proof should know to check
`result.content[0].text` (parsing it as JSON) when `structured_content` is
`None`, rather than assuming the earlier cycles' proof-gathering scripts
still work verbatim against whatever `mcp` version pip resolves at the time.


Things a future cycle (or a human) should know that don't fit elsewhere.
Per TASKS.md: this is also where an idea that needed an API key or account
gets parked instead of built, since this project only ships keyless tools.

## 2026-09-17: found a way out of the "single deterministic calculation" saturation, and a rejected optimization-solver candidate

The previous cycle's saturation warning held for the searches this cycle
tried directly (unit conversion, general "wish Claude could" threads
turned up nothing new) — but the fix wasn't finding an unsaturated
*calculator*, it was finding a different *problem shape* entirely:
constraint satisfaction puzzles, where the documented LLM failure isn't
"can't compute X" but "can't hold N simultaneous constraints consistent at
once." `logic-grid-solver` came from that shift. Future cycles stuck on
saturated calculator ideas should consider the same move — look for a
class of problem where the failure mode is qualitatively different (search
instead of arithmetic, cross-checking instead of computation, memory
instead of formula lookup) rather than a fresh spin on the same shape.

**Rejected this cycle: NP-hard combinatorial optimization (knapsack,
bin-packing, scheduling).** Real, well-documented failure (EHOP benchmark,
the ACL "A Knapsack by Any Other Name" paper, several others show LLM
end-to-end solving degrading sharply with instance scale). Not built:
already served by two existing MCP servers built on Google OR-Tools (MCP
Optimizer, Opti-MCP). Also a weaker fit than usual for this collection even
setting saturation aside — OR-Tools is a large native-binary dependency,
which doesn't need an API key (so it's not a "parked for needing
credentials" item) but sits awkwardly against the stdlib-only-where-possible
discipline every other tool here follows. If a future cycle wants to
revisit optimization, the differentiated angle would need to be something
neither existing server does — a checkable-proof angle (e.g. proving a
returned solution is provably optimal for small instances via exhaustive
cross-check, the same move `logic-grid-solver` makes for uniqueness) is the
most promising direction, not "another OR-Tools wrapper."

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
